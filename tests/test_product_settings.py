from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from product_settings import (
    DEFAULT_SETTINGS,
    domain_instruction,
    load_settings,
    normalize_settings,
    save_settings,
    settings_runtime_signature,
)


class ProductSettingsTests(unittest.TestCase):
    def test_missing_file_uses_ai_off_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            settings = load_settings(Path(temp) / "missing.json")
        self.assertFalse(settings["ai_autostart"])
        self.assertTrue(settings["context_enabled"])
        self.assertEqual(settings["context_chars"], 128)
        self.assertEqual(settings["compute_mode"], "auto")

    def test_invalid_values_are_normalized(self) -> None:
        settings = normalize_settings(
            {
                "ai_autostart": "yes",
                "context_chars": 140,
                "document_domain": "unknown",
                "compute_mode": "quantum",
                "custom_instruction": "x" * 800,
            }
        )
        self.assertFalse(settings["ai_autostart"])
        self.assertEqual(settings["context_chars"], 128)
        self.assertEqual(settings["document_domain"], "general")
        self.assertEqual(settings["compute_mode"], "auto")
        self.assertEqual(len(settings["custom_instruction"]), 500)

    def test_settings_round_trip_is_local_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            saved = dict(DEFAULT_SETTINGS)
            saved.update(
                document_domain="medical",
                custom_instruction="循環器内科。薬剤名は正式名称を優先する。",
                compute_mode="cpu",
            )
            save_settings(saved, path)
            loaded = load_settings(path)
        self.assertEqual(loaded["document_domain"], "medical")
        self.assertIn("循環器内科", loaded["custom_instruction"])
        self.assertEqual(loaded["compute_mode"], "cpu")

    def test_custom_instruction_is_added_to_every_domain(self) -> None:
        instruction = domain_instruction(
            {
                **DEFAULT_SETTINGS,
                "document_domain": "medical",
                "custom_instruction": "循環器内科の記録。",
            }
        )
        self.assertIn("医学・医療文書", instruction)
        self.assertIn("循環器内科の記録", instruction)

    def test_ai_autostart_does_not_require_model_restart(self) -> None:
        first = dict(DEFAULT_SETTINGS)
        second = {**first, "ai_autostart": True}
        self.assertEqual(settings_runtime_signature(first), settings_runtime_signature(second))


if __name__ == "__main__":
    unittest.main()
