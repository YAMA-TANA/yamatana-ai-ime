from __future__ import annotations

import argparse
from pathlib import Path


SOURCE_RELATIVE_PATH = Path("src/win32/tip/tip_surrounding_text.cc")
UPSTREAM_LIMIT = "constexpr int kMaxSurroundingLength = 20;"
YAMATANA_LIMIT = "constexpr int kMaxSurroundingLength = 128;"


def patch_checkout(checkout: Path) -> None:
    source = checkout / SOURCE_RELATIVE_PATH
    text = source.read_text(encoding="utf-8")
    if YAMATANA_LIMIT in text:
        return
    count = text.count(UPSTREAM_LIMIT)
    if count != 1:
        raise RuntimeError(
            f"surrounding context limit: expected exactly one match in {source}, "
            f"found {count}"
        )
    source.write_text(
        text.replace(UPSTREAM_LIMIT, YAMATANA_LIMIT, 1),
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Increase Mozc TSF surrounding context for AI reranking."
    )
    parser.add_argument("--checkout", required=True, type=Path)
    args = parser.parse_args()
    patch_checkout(args.checkout.resolve())


if __name__ == "__main__":
    main()
