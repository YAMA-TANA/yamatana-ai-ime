"""Self-contained ONNX Runtime backend for Yamatana AI IME."""

from __future__ import annotations

import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from product_settings import domain_instruction, load_settings, normalize_settings
from ranker.lexicon import LexicalKnowledge, contextual_candidate_bonus


LOG = logging.getLogger("yamatana_ai_ime.onnx_ranker")
_CONTEXT_NOISE = set(" \t\r\n、。,.!?！？「」『』（）()［］[]【】{}・:：;；")
_RANK_PRIOR_REFERENCE_INDEX = 19


def _runtime_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "_MEIPASS", None):
        roots.append(Path(getattr(sys, "_MEIPASS")))
    roots.extend((Path(sys.executable).parent, Path(__file__).resolve().parents[1]))
    return roots


def _resolve_first(relative_paths: tuple[str, ...]) -> Optional[Path]:
    for root in _runtime_roots():
        for relative in relative_paths:
            candidate = root / relative
            if candidate.exists():
                return candidate
    return None


def _context_signal_length(prefix: str, suffix: str) -> int:
    """Approximate how much real linguistic evidence surrounds the conversion."""
    return sum(1 for char in prefix + suffix if char not in _CONTEXT_NOISE)


def _rank_prior_penalty(original_index: int, max_penalty: float) -> float:
    """Return a bounded logarithmic Mozc-rank prior.

    Rank still matters, but unlike the old linear `0.1 * index` penalty it can
    never grow without bound.  With the production max_penalty=0.1, Mozc rank
    2 pays about 0.02, rank 5 about 0.05, rank 10 about 0.08, and rank 20+
    saturates at 0.10.  A clear AI score lead can therefore promote any depth.
    """
    index = max(0, int(original_index))
    cap = max(0.0, float(max_penalty))
    if index == 0 or cap == 0.0:
        return 0.0
    normalized = math.log1p(min(index, _RANK_PRIOR_REFERENCE_INDEX)) / math.log1p(
        _RANK_PRIOR_REFERENCE_INDEX
    )
    return cap * normalized


def _required_override_margin(context_len: int) -> float:
    """Minimum score lead over Mozc rank 1 before replacing it.

    Short context keeps a small safety margin, while useful sentence context
    quickly lowers it.  Candidate depth is already represented by the bounded
    rank prior and is not charged a second time here.
    """
    context_len = max(0, int(context_len))
    return 0.05 + 0.25 / (1.0 + context_len / 3.0)


def _preserve_mozc_top_if_uncertain(
    scored: list[tuple[float, int, str]], prefix: str, suffix: str
) -> list[tuple[float, int, str]]:
    """Keep Mozc rank 1 only when the post-prior score lead is genuinely small.

    Context-free calls are reserved for explicit compound-boundary repair and
    keep free reranking behaviour.
    """
    if not scored:
        return scored
    context_len = _context_signal_length(prefix, suffix)
    if context_len == 0:
        return scored

    mozc_top = next((item for item in scored if item[1] == 0), None)
    ai_top = scored[0]
    if mozc_top is None or ai_top[1] == 0:
        return scored

    actual_margin = ai_top[0] - mozc_top[0]
    required_margin = _required_override_margin(context_len)
    if actual_margin >= required_margin:
        return scored

    LOG.debug(
        "preserving Mozc top: ai_index=%s actual_margin=%.3f required_margin=%.3f context_len=%s",
        ai_top[1], actual_margin, required_margin, context_len,
    )
    return [mozc_top] + [item for item in scored if item is not mozc_top]


class OnnxRuriReranker:
    """Ruri IME reranker without a Python, PyTorch, or CUDA prerequisite."""

    def __init__(
        self,
        settings: Optional[Mapping[str, Any]] = None,
        settings_path: Optional[str | Path] = None,
        prior_w: float = 0.1,
        model_path: Optional[str | Path] = None,
    ) -> None:
        self.settings = normalize_settings(settings) if settings is not None else load_settings(settings_path)
        # `prior_w` is now the maximum total Mozc-rank penalty, not a per-rank
        # multiplier.  This preserves useful Mozc prior information without
        # making deep candidates impossible to promote.
        self.prior_w = max(0.0, float(prior_w))
        self.context_enabled = bool(self.settings["context_enabled"])
        self.context_chars = int(self.settings["context_chars"])
        self.document_domain = str(self.settings["document_domain"])
        self.document_instruction = domain_instruction(self.settings)
        self.enable_lexical_grounding = bool(self.settings["lexical_grounding"])
        self.lexicon = LexicalKnowledge() if self.enable_lexical_grounding else None

        available = set(ort.get_available_providers())
        requested = str(self.settings["compute_mode"])
        use_gpu = requested in {"auto", "gpu"} and "DmlExecutionProvider" in available
        if requested == "gpu" and not use_gpu:
            raise RuntimeError(
                "GPU演算が選択されていますがDirectML対応GPUを利用できません。"
                "設定で「自動選択」または「CPU」を選んでください。"
            )

        if model_path is not None:
            resolved_model = Path(model_path)
        elif use_gpu:
            resolved_model = _resolve_first((
                "build/onnx-model-70m/ruri-ime-fp16.onnx",
                "models/onnx/ruri-ime-fp16.onnx",
                "build/onnx-model/ruri-ime-fp16.onnx",
                "models/onnx/ruri-ime-fp32.onnx",
            ))
        else:
            resolved_model = _resolve_first((
                "build/onnx-model-70m/ruri-ime-int8.onnx",
                "models/onnx/ruri-ime-int8.onnx",
                "build/onnx-model/ruri-ime-int8.onnx",
                "models/onnx/ruri-ime-fp32.onnx",
            ))
        if not resolved_model or not resolved_model.exists():
            raise FileNotFoundError("配布用ONNXモデルが見つかりません。再インストールしてください。")
        tokenizer_path = _resolve_first((
            "build/onnx-model-70m/tokenizer.json",
            "models/onnx/tokenizer.json",
            "models/ruri-v3-70m-ime-distilled/tokenizer.json",
            "models/ruri-v3-reranker-310m-ime-tuned/tokenizer.json",
        ))
        if tokenizer_path is None:
            raise FileNotFoundError("AI tokenizer.json が見つかりません。再インストールしてください。")

        self.model_path = str(resolved_model.resolve())
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding(pad_id=3, pad_token="<pad>")

        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.intra_op_num_threads = min(8, max(2, os.cpu_count() or 2))
        options.inter_op_num_threads = 1
        if use_gpu:
            options.enable_mem_pattern = False
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            requested_providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
        else:
            requested_providers = ["CPUExecutionProvider"]
        LOG.info("loading %s with providers=%s", resolved_model, requested_providers)
        self.session = ort.InferenceSession(
            str(resolved_model), sess_options=options, providers=requested_providers
        )
        self.providers = tuple(self.session.get_providers())
        self.device = (
            "gpu-directml"
            if "DmlExecutionProvider" in self.providers
            else "cpu"
        )
        if requested == "gpu" and self.device != "gpu-directml":
            raise RuntimeError(
                "DirectML provider was requested but the ONNX session did not activate it."
            )
        LOG.info("active ONNX providers=%s device=%s", self.providers, self.device)
        self._warmup()

    def _encode(self, queries: list[str], documents: list[str]) -> dict[str, np.ndarray]:
        encodings = self.tokenizer.encode_batch(list(zip(queries, documents)))
        return {
            "input_ids": np.asarray([encoding.ids for encoding in encodings], dtype=np.int64),
            "attention_mask": np.asarray(
                [encoding.attention_mask for encoding in encodings], dtype=np.int64
            ),
        }

    def _warmup(self) -> None:
        warmup_count = 32
        query = "文書方針: 一般的な日本語文書。\n文脈に合う表記を選びなさい。"
        inputs = self._encode(
            [query] * warmup_count,
            [f"文章の変換候補{index}" for index in range(warmup_count)],
        )
        self.session.run(["logits"], inputs)

    def rank(self, request: Dict[str, Any]) -> Dict[str, Any]:
        started = time.perf_counter()
        request_id = request.get("request_id", 0)
        prefix = str(request.get("preceding_text", request.get("prefix", "")))
        suffix = str(request.get("following_text", request.get("suffix", "")))
        reading = str(request.get("read", request.get("reading", "")))
        candidates = request.get("candidates", [])
        if not candidates:
            return {"request_id": request_id, "candidates": []}

        if not self.context_enabled or self.context_chars <= 0:
            prefix = ""
            suffix = ""
        else:
            prefix = prefix[-self.context_chars :]
            suffix = suffix[: self.context_chars]

        all_candidates = []
        for index, candidate in enumerate(candidates):
            word = str(candidate.get("text", candidate.get("word", "")))
            candidate_id = str(candidate.get("id", f"c{index + 1}"))
            all_candidates.append((index, candidate_id, word))

        query = (
            f"文書方針: {self.document_instruction}\n"
            f"文脈「{prefix}____{suffix}」に最も適切な表記を選びなさい。"
        )
        inputs = self._encode(
            [query] * len(all_candidates),
            [f"{prefix}{word}{suffix}" for _index, _candidate_id, word in all_candidates],
        )
        logits = np.asarray(self.session.run(["logits"], inputs)[0]).reshape(-1)

        scored = []
        for original_index, candidate_id, word in all_candidates:
            raw_score = float(logits[original_index])
            lexical_penalty = (
                self.lexicon.compute_lexical_penalty(word, reading)
                if self.lexicon and reading
                else 0.0
            )
            context_bonus = contextual_candidate_bonus(f"{prefix} {suffix}", word)
            rank_penalty = _rank_prior_penalty(original_index, self.prior_w)
            final_score = raw_score + context_bonus - lexical_penalty - rank_penalty
            scored.append((final_score, original_index, candidate_id))
        scored.sort(key=lambda item: item[0], reverse=True)
        scored = _preserve_mozc_top_if_uncertain(scored, prefix, suffix)
        self.last_latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return {
            "request_id": request_id,
            "candidates": [
                {"id": candidate_id, "rank": rank, "score": float(score)}
                for rank, (score, _original_index, candidate_id) in enumerate(scored, start=1)
            ],
        }
