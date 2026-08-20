"""Self-contained ONNX Runtime backend for Yamatana AI IME."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from product_settings import domain_instruction, load_settings, normalize_settings
from ranker.lexicon import LexicalKnowledge


LOG = logging.getLogger("yamatana_ai_ime.onnx_ranker")


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
        self.prior_w = prior_w
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
                "models/onnx/ruri-ime-fp16.onnx",
                "models/onnx/ruri-ime-fp32.onnx",
            ))
        else:
            resolved_model = _resolve_first((
                "models/onnx/ruri-ime-int8.onnx",
                "models/onnx/ruri-ime-fp32.onnx",
            ))
        if not resolved_model or not resolved_model.exists():
            raise FileNotFoundError("配布用ONNXモデルが見つかりません。再インストールしてください。")
        tokenizer_path = _resolve_first((
            "models/onnx/tokenizer.json",
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
        if use_gpu:
            options.enable_mem_pattern = False
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
            self.device = "gpu-directml"
        else:
            providers = ["CPUExecutionProvider"]
            self.device = "cpu"
        LOG.info("loading %s with providers=%s", resolved_model, providers)
        self.session = ort.InferenceSession(
            str(resolved_model), sess_options=options, providers=providers
        )
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
        # DirectML compiles graphs lazily for new batch shapes.  Warm the
        # common Mozc candidate count so the user's first conversion does not
        # pay that one-time cost.
        warmup_count = 20 if self.device == "gpu-directml" else 4
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
        unique_words: list[str] = []
        word_indexes: dict[str, int] = {}
        for index, candidate in enumerate(candidates):
            word = str(candidate.get("text", candidate.get("word", "")))
            candidate_id = str(candidate.get("id", f"c{index + 1}"))
            all_candidates.append((index, candidate_id, word))
            if word not in word_indexes:
                word_indexes[word] = len(unique_words)
                unique_words.append(word)

        query = (
            f"文書方針: {self.document_instruction}\n"
            f"文脈「{prefix}____{suffix}」に最も適切な表記を選びなさい。"
        )
        inputs = self._encode([query] * len(unique_words), [f"{prefix}{word}{suffix}" for word in unique_words])
        logits = np.asarray(self.session.run(["logits"], inputs)[0]).reshape(-1)

        scored = []
        for original_index, candidate_id, word in all_candidates:
            raw_score = float(logits[word_indexes[word]])
            lexical_penalty = (
                self.lexicon.compute_lexical_penalty(word, reading)
                if self.lexicon and reading
                else 0.0
            )
            final_score = raw_score - lexical_penalty - self.prior_w * original_index
            scored.append((final_score, original_index, candidate_id))
        scored.sort(key=lambda item: item[0], reverse=True)
        self.last_latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return {
            "request_id": request_id,
            "candidates": [
                {"id": candidate_id, "rank": rank, "score": float(score)}
                for rank, (score, _original_index, candidate_id) in enumerate(scored, start=1)
            ],
        }
