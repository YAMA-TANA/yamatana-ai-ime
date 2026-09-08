from pathlib import Path
import tempfile
import unittest

from scripts.patch_mozc_surrounding_context import (
    SOURCE_RELATIVE_PATH,
    UPSTREAM_LIMIT,
    YAMATANA_LIMIT,
    patch_checkout,
)


class MozcSurroundingContextPatchTests(unittest.TestCase):
    def test_patch_increases_limit_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir)
            source = checkout / SOURCE_RELATIVE_PATH
            source.parent.mkdir(parents=True)
            source.write_text(f"before\n{UPSTREAM_LIMIT}\nafter\n", encoding="utf-8")

            patch_checkout(checkout)
            patch_checkout(checkout)

            result = source.read_text(encoding="utf-8")
            self.assertIn(YAMATANA_LIMIT, result)
            self.assertNotIn(UPSTREAM_LIMIT, result)

    def test_patch_fails_if_upstream_source_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir)
            source = checkout / SOURCE_RELATIVE_PATH
            source.parent.mkdir(parents=True)
            source.write_text("unexpected source\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "expected exactly one match"):
                patch_checkout(checkout)


if __name__ == "__main__":
    unittest.main()
