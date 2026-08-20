"""Local lexical grounding shared by the development and ONNX rankers."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Set


LOG = logging.getLogger("yamatana_ai_ime.lexicon")
PRODUCTIVE_AFFIXES = {
    "的", "化", "性", "力", "員", "車", "感", "所", "界", "法", "前", "後",
    "時", "用", "製", "器", "機", "線", "風", "代", "費", "料", "率",
}


def resolve_lexicon_path(db_path: Optional[Path] = None) -> Path:
    if db_path is not None:
        return db_path
    candidates = [
        getattr(sys, "_MEIPASS", None)
        and Path(getattr(sys, "_MEIPASS")) / "data" / "massive_homophone_database.json",
        Path(sys.executable).parent / "data" / "massive_homophone_database.json",
        Path(__file__).resolve().parents[1] / "data" / "massive_homophone_database.json",
    ]
    return next((Path(path) for path in candidates if path and Path(path).exists()), candidates[-1])


class LexicalKnowledge:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.exact_words: Set[str] = set()
        self.reading_map: Dict[str, Set[str]] = {}
        path = resolve_lexicon_path(db_path)
        if not path.exists():
            LOG.warning("lexicon not found: %s", path)
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for reading, entry in data.items():
                candidates = set(entry.get("candidates", []))
                self.reading_map[reading] = candidates
                self.exact_words.update(candidates)
            LOG.info(
                "loaded %s words across %s readings",
                len(self.exact_words), len(self.reading_map),
            )
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError) as exc:
            LOG.warning("could not load lexicon from %s: %s", path, exc)

    def is_known_word(self, word: str) -> bool:
        if word in self.exact_words:
            return True
        return any(
            word.endswith(affix)
            and len(word) > len(affix)
            and word[: -len(affix)] in self.exact_words
            for affix in PRODUCTIVE_AFFIXES
        )

    def compute_lexical_penalty(self, word: str, reading: Optional[str] = None) -> float:
        if not word or not reading:
            return 0.0
        known_candidates = self.reading_map.get(reading, set())
        if not known_candidates or word in known_candidates:
            return 0.0
        has_exact_registered = any(
            len(candidate) == len(word) and candidate in self.exact_words
            for candidate in known_candidates
        )
        if has_exact_registered and not self.is_known_word(word):
            return 1.5
        return 0.0
