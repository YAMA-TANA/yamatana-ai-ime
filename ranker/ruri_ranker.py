"""Ruri-v3 Reranker Engine for AI-powered Japanese IME contextual conversion.
Supports LoRA-tuned weights, lexical grounding, and non-lexical compound suppression.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from product_settings import domain_instruction, load_settings, normalize_settings

logger = logging.getLogger("ai_ime.ruri_ranker")

# Productive Japanese affixes that legitimately form new compound words
PRODUCTIVE_AFFIXES = {
    "的", "化", "性", "力", "員", "車", "感", "所", "界", "法", "前", "後", "時", "用", "製", "器", "機", "線", "風", "代", "費", "料", "率"
}


class LexicalKnowledge:
    """Fast in-memory index of Japanese dictionary entries from Mozc / Agency for Cultural Affairs."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.exact_words: Set[str] = set()
        self.reading_map: Dict[str, Set[str]] = {}

        if db_path is None:
            # Check MEIPASS (PyInstaller bundled), executable dir, and source root
            candidates = [
                getattr(sys, "_MEIPASS", None) and Path(getattr(sys, "_MEIPASS")) / "data" / "massive_homophone_database.json",
                Path(sys.executable).parent / "data" / "massive_homophone_database.json",
                Path(__file__).resolve().parents[1] / "data" / "massive_homophone_database.json",
            ]
            for cand in candidates:
                if cand and Path(cand).exists():
                    db_path = Path(cand)
                    break
            else:
                db_path = Path(__file__).resolve().parents[1] / "data" / "massive_homophone_database.json"

        if db_path.exists():
            try:
                data = json.loads(db_path.read_text(encoding="utf-8"))
                for reading, entry in data.items():
                    cands = set(entry.get("candidates", []))
                    self.reading_map[reading] = cands
                    self.exact_words.update(cands)
                logger.info(f"Loaded {len(self.exact_words)} dictionary words across {len(self.reading_map)} readings.")
            except Exception as e:
                logger.warning(f"Could not load lexical database from {db_path}: {e}")

    def is_known_word(self, word: str) -> bool:
        if word in self.exact_words:
            return True
        # Check if single word + productive affix
        for affix in PRODUCTIVE_AFFIXES:
            if word.endswith(affix) and len(word) > len(affix):
                base = word[:-len(affix)]
                if base in self.exact_words:
                    return True
        return False

    def compute_lexical_penalty(self, word: str, reading: Optional[str] = None) -> float:
        """Computes penalty for fragmented non-words (e.g. 週間誌 when 週刊誌 exists)."""
        if not word or not reading:
            return 0.0

        known_cands = self.reading_map.get(reading, set())
        if not known_cands:
            return 0.0

        # If this exact word is in dictionary for this reading, 0 penalty
        if word in known_cands:
            return 0.0

        # If dictionary has registered 1-word entries for this reading, but candidate is not one of them
        # (e.g. 週間誌 for しゅうかんし)
        has_exact_registered = any(len(c) == len(word) and c in self.exact_words for c in known_cands)
        if has_exact_registered and not self.is_known_word(word):
            return 1.5  # Non-lexical compound suppression penalty

        return 0.0


class RuriReranker:
    """Japanese CrossEncoder Reranker using Ruri-v3-reranker-310m with Lexical Grounding."""

    def __init__(
        self,
        model_path: str | Path = "models/ruri-v3-reranker-310m-ime-tuned",
        base_fallback_path: str | Path = "models/ruri-v3-reranker-310m",
        device: Optional[str] = None,
        w_bidi: float = 1.0,
        prior_w: float = 0.1,
        enable_lexical_grounding: bool = True,
        settings: Optional[Mapping[str, Any]] = None,
        settings_path: Optional[str | Path] = None,
    ) -> None:
        self.settings = normalize_settings(settings) if settings is not None else load_settings(settings_path)
        compute_mode = self.settings["compute_mode"]
        if device:
            self.device = device
        elif compute_mode == "cpu":
            self.device = "cpu"
        elif compute_mode == "gpu":
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "GPU演算が選択されていますが、対応するCUDA GPUを利用できません。"
                    "設定で「自動選択」または「CPU」を選んでください。"
                )
            self.device = "cuda"
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.w_bidi = w_bidi
        self.prior_w = prior_w
        self.enable_lexical_grounding = bool(
            enable_lexical_grounding and self.settings["lexical_grounding"]
        )
        self.context_enabled = bool(self.settings["context_enabled"])
        self.context_chars = int(self.settings["context_chars"])
        self.document_domain = str(self.settings["document_domain"])
        self.document_instruction = domain_instruction(self.settings)

        # Load Lexicon
        self.lexicon = LexicalKnowledge() if self.enable_lexical_grounding else None

        # Resolve model path across standalone exe and development
        candidates = []
        if getattr(sys, "_MEIPASS", None):
            candidates.append(Path(getattr(sys, "_MEIPASS")) / model_path)
        candidates.append(Path(sys.executable).parent / model_path)
        candidates.append(Path(__file__).resolve().parents[1] / model_path)
        candidates.append(Path(model_path))

        path = None
        for cand in candidates:
            if cand and cand.exists():
                path = cand
                break

        if path is None:
            # Try base fallback
            for cand in [
                getattr(sys, "_MEIPASS", None) and Path(getattr(sys, "_MEIPASS")) / base_fallback_path,
                Path(sys.executable).parent / base_fallback_path,
                Path(__file__).resolve().parents[1] / base_fallback_path,
            ]:
                if cand and cand.exists():
                    path = cand
                    break
            if path is None:
                path = Path(__file__).resolve().parents[1] / model_path
            logger.info(f"Tuned model not found at {model_path}, falling back to {path}")

        self.model_path = str(path.resolve())
        self.is_lora_tuned = path.name == "ruri-v3-reranker-310m-ime-tuned"

        logger.info(f"Loading Ruri Reranker from {path} on {self.device}...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(str(path), trust_remote_code=True, fix_mistral_regex=True)
        except Exception:
            from transformers.models.auto.tokenization_auto import AutoTokenizer as FallbackTokenizer
            self.tokenizer = FallbackTokenizer.from_pretrained(str(path), trust_remote_code=True)

        try:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(path),
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True,
            ).to(self.device)
        except Exception as auto_err:
            logger.warning(f"AutoModel failed ({auto_err}), falling back to direct ModernBert import...")
            from transformers.models.modernbert.modeling_modernbert import ModernBertForSequenceClassification
            self.model = ModernBertForSequenceClassification.from_pretrained(
                str(path),
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            ).to(self.device)

        self.model.eval()

        # Warmup GPU
        self._warmup()
        logger.info(f"Ruri Reranker initialized successfully on {self.device}.")

    def _warmup(self) -> None:
        with torch.no_grad():
            enc = self.tokenizer(["文脈のテスト"], ["完成文のテスト"], return_tensors="pt", padding=True, truncation=True)
            enc = {k: v.to(self.device) for k, v in enc.items()}
            _ = self.model(**enc)

    def rank(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Ranks candidates for a given context and candidates list."""
        t_start = time.perf_counter()
        req_id = request.get("request_id", 0)
        prefix = request.get("preceding_text", request.get("prefix", ""))
        suffix = request.get("following_text", request.get("suffix", ""))
        reading = request.get("read", request.get("reading", ""))
        raw_candidates = request.get("candidates", [])

        if not raw_candidates:
            return {"request_id": req_id, "candidates": []}

        context_enabled = bool(getattr(self, "context_enabled", True))
        context_chars = int(getattr(self, "context_chars", 128))
        if not context_enabled or context_chars <= 0:
            prefix = ""
            suffix = ""
        else:
            prefix = str(prefix)[-context_chars:]
            suffix = str(suffix)[:context_chars]
        instruction = str(
            getattr(
                self,
                "document_instruction",
                "自然で一般的な日本語として、文脈に合う表記を優先する。",
            )
        )

        # Score each distinct surface form once, then expand the score back to
        # every original candidate ID.  Mozc legitimately emits duplicate
        # surface forms with different metadata/IDs, and the wire protocol
        # requires the response to contain a complete permutation of all IDs.
        all_candidates = []
        unique_words = []
        word_indexes = {}
        for idx, c in enumerate(raw_candidates):
            w = c.get("text", c.get("word", ""))
            c_id = c.get("id", f"c{idx+1}")
            all_candidates.append((idx, c_id, c, w))
            if w not in word_indexes:
                word_indexes[w] = len(unique_words)
                unique_words.append(w)

        # Build Bidirectional Sentence Pairs
        queries = []
        documents = []
        for w in unique_words:
            query = (
                f"文書方針: {instruction}\n"
                f"文脈「{prefix}____{suffix}」に最も適切な表記を選びなさい。"
            )
            doc = f"{prefix}{w}{suffix}"
            queries.append(query)
            documents.append(doc)

        with torch.no_grad():
            enc = self.tokenizer(
                queries,
                documents,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            enc = {k: v.to(self.device) for k, v in enc.items()}
            logits = self.model(**enc).logits.squeeze(-1).float()
            if logits.ndim == 0:
                logits = logits.unsqueeze(0)
            ai_scores = logits.cpu().tolist()
            if not isinstance(ai_scores, list):
                ai_scores = [ai_scores]

        scored = []
        for orig_idx, c_id, orig_cand, w in all_candidates:
            raw_s = ai_scores[word_indexes[w]]
            # Lexical Grounding Penalty
            lex_penalty = 0.0
            if self.lexicon and reading:
                lex_penalty = self.lexicon.compute_lexical_penalty(w, reading)

            # Prior rank damping tie-breaker
            prior_penalty = self.prior_w * orig_idx

            final_score = float(raw_s) - lex_penalty - prior_penalty
            scored.append({
                "id": c_id,
                "cand": orig_cand,
                "word": w,
                "orig_idx": orig_idx,
                "ai_score": round(float(raw_s), 4),
                "final_score": round(float(final_score), 4),
            })

        # Sort descending by final score
        scored.sort(key=lambda x: x["final_score"], reverse=True)

        ranked = []
        for r_idx, item in enumerate(scored):
            c_dict = {
                "id": item["id"],
                "rank": r_idx + 1,
                "score": item["final_score"],
            }
            ranked.append(c_dict)

        self.last_latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        return {
            "request_id": req_id,
            "candidates": ranked,
        }
