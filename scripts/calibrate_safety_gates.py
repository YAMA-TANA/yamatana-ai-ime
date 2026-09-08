"""Re-evaluate Mozc-preservation gates from saved single-call study traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MARGINS = (0.0, 0.15, 0.25, 0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0)
RUNNER_GAPS = (0.0, 0.15, 0.25, 0.4, 0.6)


def projected_surface(row: dict, margin: float, runner_gap: float) -> str:
    if not row["traces"]:
        return row["raw_surface"]
    if len(row["traces"]) != 1:
        raise ValueError("Calibration requires one ranker call per row")
    explanation = row["traces"][0]["explanation"]
    decision = explanation["decision"]
    neural_id = decision["neural_top_id"]
    candidates = {item["id"]: item for item in explanation["candidates"]}
    mozc = next(item for item in candidates.values() if item["original_rank"] == 1)
    neural = candidates[neural_id]
    if neural_id == mozc["id"]:
        return row["raw_surface"]
    lead = decision["lead_over_mozc"]
    runner = decision["lead_over_runner"]
    if lead is not None and runner is not None and lead >= margin and runner >= runner_gap:
        return neural["text"]
    return row["raw_surface"]


def evaluate(rows: list[dict], margin: float, runner_gap: float) -> dict:
    correct = recoveries = regressions = changed = 0
    for row in rows:
        surface = projected_surface(row, margin, runner_gap)
        is_correct = surface == row["expected"]
        correct += int(is_correct)
        changed += int(surface != row["raw_surface"])
        recoveries += int(not row["raw_correct"] and is_correct)
        regressions += int(row["raw_correct"] and not is_correct)
    return {
        "margin": margin,
        "runner_gap": runner_gap,
        "correct": correct,
        "total": len(rows),
        "recoveries": recoveries,
        "regressions": regressions,
        "changed": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studies", nargs="+", type=Path)
    parser.add_argument("--context-mode", default="both")
    parser.add_argument("--parity", choices=("all", "even", "odd"), default="all")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    all_rows = []
    for path in args.studies:
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = [
            row for row in data["rows"]
            if row["context_mode"] == args.context_mode
            and (
                args.parity == "all"
                or (
                    int.from_bytes(
                        hashlib.sha256(row["label"].encode("utf-8")).digest()[:2],
                        "big",
                    )
                    % 2
                    == (0 if args.parity == "even" else 1)
                )
            )
        ]
        all_rows.extend(rows)

    results = [
        evaluate(all_rows, margin, gap)
        for margin in MARGINS
        for gap in RUNNER_GAPS
    ]
    results.sort(
        key=lambda item: (
            item["regressions"], -item["correct"], -item["recoveries"],
            item["changed"], item["margin"], item["runner_gap"],
        )
    )
    lines = [
        "# 安全ゲート再校正",
        "",
        f"- 入力: {', '.join(str(path) for path in args.studies)}",
        f"- 文脈条件: `{args.context_mode}`",
        f"- 固定ラベル分割: `{args.parity}`",
        f"- 判定数: {len(all_rows)}",
        "",
        "改悪数が少ない順、その中で正答数が多い順の上位20設定。",
        "",
        "| Mozcとの差 | 異表記2位との差 | 正答 | 回復 | 改悪 | 変更 |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results[:20]:
        lines.append(
            f"| {item['margin']:.2f} | {item['runner_gap']:.2f} | "
            f"{item['correct']}/{item['total']} | {item['recoveries']} | "
            f"{item['regressions']} | {item['changed']} |"
        )
    report = "\n".join(lines) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
