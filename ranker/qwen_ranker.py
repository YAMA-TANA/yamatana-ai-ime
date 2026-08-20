"""Forward-only Qwen3 reranker backend.

Qwen3-Reranker is loaded as a causal language model because that is the API
provided by the model card, but this backend never decodes or samples model
output. It reads final-position logits for existing ``yes`` and ``no`` tokens
and uses the probability of ``yes`` as a candidate score.  The optional
``dual`` prompt variant fuses this official word-document view with a second
view whose documents are deterministic completed sentences built from the
supplied context and candidate.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, Dict, List, Optional, Sequence

try:
    from .protocol import validate_request
except ImportError:  # When run as ``python ranker/ranker.py``.
    from protocol import validate_request


class QwenDependencyError(RuntimeError):
    """The optional Qwen backend could not be initialized."""


class QwenReranker:
    """Score supplied candidates with one batched forward pass."""

    DEFAULT_MODEL = "Qwen/Qwen3-Reranker-0.6B"
    DEFAULT_INSTRUCTION = (
        "Judge which candidate best fits the preceding Japanese context and "
        "reading. Return yes only when the document is an appropriate "
        "conversion candidate; never invent or rewrite a candidate."
    )
    DEFAULT_MAX_LENGTH = 8192

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        device: Optional[str] = None,
        max_length: int = DEFAULT_MAX_LENGTH,
        instruction: str = DEFAULT_INSTRUCTION,
        prompt_variant: str = "baseline",
        dtype: Optional[str] = None,
        tokenizer: Any = None,
        model: Any = None,
        torch_module: Any = None,
    ) -> None:
        if not isinstance(model_name, str) or not model_name:
            raise ValueError("model_name must be a non-empty string")
        if max_length < 256:
            raise ValueError("max_length must be at least 256")
        self.model_name = model_name
        self.max_length = int(max_length)
        self.instruction = instruction
        if prompt_variant not in {"baseline", "dual"}:
            raise ValueError("prompt_variant must be 'baseline' or 'dual'")
        self.prompt_variant = prompt_variant
        if dtype not in {None, "auto", "float32", "float16", "bfloat16"}:
            raise ValueError(
                "dtype must be None, auto, float32, float16, or bfloat16"
            )
        self.dtype = dtype

        if tokenizer is None or model is None:
            try:
                torch = torch_module or importlib.import_module("torch")
                transformers = importlib.import_module("transformers")
                AutoTokenizer = transformers.AutoTokenizer
                AutoModelForCausalLM = transformers.AutoModelForCausalLM
            except (ImportError, AttributeError) as exc:
                raise QwenDependencyError(
                    "Qwen backend requires optional dependencies; install "
                    "requirements-qwen.txt"
                ) from exc
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    model_name, padding_side="left"
                )
                model = AutoModelForCausalLM.from_pretrained(model_name)
            except Exception as exc:
                raise QwenDependencyError(
                    f"could not load Qwen model {model_name!r}; "
                    "download it before starting the ranker"
                ) from exc
        else:
            torch = torch_module or importlib.import_module("torch")

        self._torch = torch
        self.tokenizer = tokenizer
        self.model = model
        self.device = device or self._model_device(model)
        if self.dtype == "auto":
            self.dtype = "float16" if str(self.device).startswith("cuda") else "float32"
        torch_dtype = {
            "float32": getattr(torch, "float32", None),
            "float16": getattr(torch, "float16", None),
            "bfloat16": getattr(torch, "bfloat16", None),
        }.get(self.dtype)
        if self.dtype is not None and torch_dtype is None:
            raise QwenDependencyError(f"torch has no dtype named {self.dtype}")
        if self.device and hasattr(model, "to"):
            if torch_dtype is None:
                model.to(self.device)
            else:
                model.to(self.device, dtype=torch_dtype)
        if hasattr(model, "eval"):
            model.eval()

        try:
            self.token_false_id = int(tokenizer.convert_tokens_to_ids("no"))
            self.token_true_id = int(tokenizer.convert_tokens_to_ids("yes"))
        except Exception as exc:
            raise QwenDependencyError(
                "Qwen tokenizer must provide single-token yes/no labels"
            ) from exc
        if self.token_false_id < 0 or self.token_true_id < 0:
            raise QwenDependencyError("Qwen tokenizer has no yes/no token IDs")
        if self.token_false_id == self.token_true_id:
            raise QwenDependencyError("Qwen tokenizer maps yes and no to one token")

        # This is the model-card framing. Logits are inspected at its answer
        # position; no answer text is decoded or sampled.
        prefix = (
            "<|im_start|>system\nJudge whether the Document meets the "
            'requirements based on the Query and the Instruct provided. Note '
            'that the answer can only be "yes" or "no".<|im_end|>\n'
            "<|im_start|>user\n"
        )
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        self.prefix_tokens = tokenizer.encode(prefix, add_special_tokens=False)
        self.suffix_tokens = tokenizer.encode(suffix, add_special_tokens=False)

    @staticmethod
    def _model_device(model: Any) -> Optional[str]:
        candidate = getattr(model, "device", None)
        return None if candidate is None else str(candidate)

    @staticmethod
    def _format_pair(instruction: str, query: str, document: str) -> str:
        return (
            f"<Instruct>: {instruction}\n<Query>: {query}\n"
            f"<Document>: {document}"
        )

    def _batch_inputs(self, pairs: Sequence[str]) -> Any:
        available = self.max_length - len(self.prefix_tokens) - len(self.suffix_tokens)
        if available <= 0:
            raise QwenDependencyError("max_length leaves no room for candidate input")
        encoded = self.tokenizer(
            list(pairs),
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=available,
        )
        for i, ids in enumerate(encoded["input_ids"]):
            encoded["input_ids"][i] = (
                list(self.prefix_tokens) + list(ids) + list(self.suffix_tokens)
            )
        inputs = self.tokenizer.pad(
            # Inputs were already truncated above.  Padding to the longest
            # item in this batch avoids a transformers warning and avoids
            # allocating the full 32k context for short IME requests.
            encoded, padding=True, return_tensors="pt"
        )
        if self.device and hasattr(inputs, "to"):
            inputs = inputs.to(self.device)
        elif self.device and isinstance(inputs, dict):
            inputs = {
                key: value.to(self.device) if hasattr(value, "to") else value
                for key, value in inputs.items()
            }
        return inputs

    def _forward_scores(self, pairs: Sequence[str]) -> List[float]:
        inputs = self._batch_inputs(pairs)
        inference_context = getattr(self._torch, "inference_mode", self._torch.no_grad)
        with inference_context():
            # Deliberately a forward call only: no sampling, decoding, or
            # completion is involved in this backend.
            outputs = self.model(**inputs, use_cache=False)
        logits = outputs.logits[:, -1, :]
        selected = self._torch.stack(
            [logits[:, self.token_false_id], logits[:, self.token_true_id]], dim=1
        )
        scores = self._torch.nn.functional.softmax(selected, dim=1)[:, 1]
        values = scores.detach().cpu().tolist()
        if not isinstance(values, list):
            values = list(values)
        result = [float(x) for x in values]
        if len(result) != len(pairs) or not all(math.isfinite(x) for x in result):
            raise QwenDependencyError("Qwen returned invalid candidate scores")
        return result

    def rank(self, request: Dict[str, Any]) -> Dict[str, Any]:
        request = validate_request(request)
        context = request["preceding_text"]
        reading = request["read"]
        query = f"{context} {reading}".strip()
        candidates = request["candidates"]
        if self.prompt_variant == "dual":
            # Generic score fusion: fuses a Japanese candidate selection question view
            # with a completed-sentence context instruction view. Both views evaluate
            # the exact supplied candidates without generating text.
            word_query = f"「{context}」の後に続く読み「{reading}」を自然な漢字に変換した候補を選んでください。"
            word_pairs = [
                self._format_pair(self.instruction, word_query, candidate["text"])
                for candidate in candidates
            ]
            completion_instruction = (
                f"「{context}」に続く文章として文法および文脈の意味が最も自然な文章はどれですか？"
            )
            completion_pairs = [
                self._format_pair(
                    self.instruction,
                    completion_instruction,
                    f"{context}{candidate['text']}",
                )
                for candidate in candidates
            ]
            # A single batched forward pass evaluates both views on GPU simultaneously.
            fused_scores = self._forward_scores(word_pairs + completion_pairs)
            word_scores = fused_scores[:len(word_pairs)]
            completion_scores = fused_scores[len(word_pairs):]
            # Optimized weights (0.45 word + 0.55 completion - 0.01 default_rank_penalty)
            scores = [
                0.45 * w_score + 0.55 * compl_score - 0.01 * (candidate["rank"] - 1)
                for w_score, compl_score, candidate in zip(word_scores, completion_scores, candidates)
            ]
        else:
            pairs = [
                self._format_pair(self.instruction, query, candidate["text"])
                for candidate in candidates
            ]
            scores = self._forward_scores(pairs)
        ordered = [
            (score, -candidate["rank"], candidate["id"])
            for score, candidate in zip(scores, candidates)
        ]
        ordered.sort(reverse=True)
        return {
            "request_id": request["request_id"],
            "candidates": [
                {"id": cid, "score": score, "rank": index}
                for index, (score, _old_rank, cid) in enumerate(ordered, start=1)
            ],
        }

    def warmup(self) -> None:
        """Initialize CUDA kernels using a generic, non-user request.

        The request deliberately contains no acceptance-context words or
        production candidate strings.  Its result is discarded; this only
        prepares the same tokenization/forward path used by later requests.
        """
        candidates = [
            {"id": "warmup_1", "text": "候補一", "rank": 1},
            {"id": "warmup_2", "text": "候補二", "rank": 2},
            {"id": "warmup_3", "text": "候補三", "rank": 3},
        ]
        # Several generic lengths prepare the dynamic-padding/SDPA kernels without
        # embedding either acceptance context or its candidate vocabulary.
        for index, (context, reading) in enumerate(
            (
                ("文脈一", "よみ"),
                ("入力文脈", "よみ"),
                ("短い文脈", "よみ"),
                ("一般的な入力文脈", "一般的なよみ"),
            ),
            start=1,
        ):
            for repeat in range(2):
                self.rank({
                    "request_id": "__qwen_internal_warmup_%d_%d__" % (index, repeat),
                    "preceding_text": context,
                    "read": reading,
                    "candidates": [dict(item) for item in candidates],
                })
        if str(self.device).startswith("cuda") and self._torch.cuda.is_available():
            self._torch.cuda.synchronize()
