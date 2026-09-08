"""Stress the ONNX reranker with full candidate lists from the local database."""

from __future__ import annotations

import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import statistics
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ranker.onnx_ranker import OnnxRuriReranker


def load_holdout() -> list[dict]:
    path = ROOT / "scripts" / "create_and_evaluate_holdout_120.py"
    spec = importlib.util.spec_from_file_location("holdout_120", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(module.HOLDOUT_TEST_SET)


def rank_bucket(rank: int) -> str:
    if rank == 1:
        return "1"
    if rank <= 5:
        return "2-5"
    if rank <= 10:
        return "6-10"
    if rank <= 25:
        return "11-25"
    return "26+"


def aggregate(rows: Iterable[dict], key: str) -> dict[str, dict[str, int | float]]:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        group = str(row[key])
        totals[group][1] += 1
        totals[group][0] += int(row["correct"])
    return {
        group: {
            "correct": values[0],
            "total": values[1],
            "accuracy": round(values[0] / values[1], 4),
        }
        for group, values in sorted(totals.items())
    }


def run_study(compute_mode: str, database_path: Path) -> dict:
    database = json.loads(database_path.read_text(encoding="utf-8"))
    cases = []
    skipped = []
    for item in load_holdout():
        entry = database.get(item["reading"])
        if entry is None or item["expected"] not in entry["candidates"]:
            skipped.append(item["id"])
            continue
        cases.append((item, list(entry["candidates"])))

    ranker = OnnxRuriReranker(
        settings={
            "compute_mode": compute_mode,
            "context_enabled": True,
            "context_chars": 128,
            "document_domain": "general",
            "custom_instruction": "",
            "lexical_grounding": True,
        }
    )
    rows = []
    for item, natural_candidates in cases:
        for order in ("database", "control"):
            candidates = (
                natural_candidates
                if order == "database"
                else [item["expected"]]
                + [word for word in natural_candidates if word != item["expected"]]
            )
            request = {
                "request_id": f"full:{item['id']}:{order}",
                "preceding_text": item["prefix"],
                "following_text": item["suffix"],
                "read": item["reading"],
                "candidates": [
                    {"id": f"c{index}", "text": word, "rank": index}
                    for index, word in enumerate(candidates, start=1)
                ],
            }
            response = ranker.rank(request)
            by_id = {candidate["id"]: candidate["text"] for candidate in request["candidates"]}
            selected = by_id[response["candidates"][0]["id"]]
            expected_rank = candidates.index(item["expected"]) + 1
            rows.append(
                {
                    "id": item["id"],
                    "category": item["category"],
                    "reading": item["reading"],
                    "context": f"{item['prefix']}［変換］{item['suffix']}",
                    "order": order,
                    "candidate_count": len(candidates),
                    "expected": item["expected"],
                    "expected_rank": expected_rank,
                    "expected_rank_bucket": rank_bucket(expected_rank),
                    "selected": selected,
                    "correct": selected == item["expected"],
                    "latency_ms": ranker.last_latency_ms,
                    "explanation": ranker.last_explanation,
                }
            )

    correct = sum(int(row["correct"]) for row in rows)
    return {
        "compute_mode": compute_mode,
        "model_path": str(ranker.model_path),
        "database_path": str(database_path),
        "covered_cases": len(cases),
        "skipped_case_ids": skipped,
        "decision_count": len(rows),
        "correct": correct,
        "accuracy": round(correct / len(rows), 4),
        "candidate_count": {
            "min": min(len(words) for _, words in cases),
            "median": statistics.median(len(words) for _, words in cases),
            "mean": round(statistics.mean(len(words) for _, words in cases), 2),
            "max": max(len(words) for _, words in cases),
        },
        "latency_ms": {
            "median": round(statistics.median(row["latency_ms"] for row in rows), 2),
            "mean": round(statistics.mean(row["latency_ms"] for row in rows), 2),
            "max": round(max(row["latency_ms"] for row in rows), 2),
        },
        "by_order": aggregate(rows, "order"),
        "by_category": aggregate(rows, "category"),
        "by_expected_rank_bucket": aggregate(
            (row for row in rows if row["order"] == "database"),
            "expected_rank_bucket",
        ),
        "rows": rows,
    }


def markdown_report(result: dict) -> str:
    counts = result["candidate_count"]
    latency = result["latency_ms"]
    lines = [
        "# 全候補リスト・ストレス試験",
        "",
        f"- 演算: `{result['compute_mode']}`",
        f"- モデル: `{result['model_path']}`",
        f"- 対象: {result['covered_cases']}ケース / {result['decision_count']}判定",
        f"- 候補数: 最小{counts['min']}・中央値{counts['median']}・平均{counts['mean']}・最大{counts['max']}",
        f"- 正答: {result['correct']}/{result['decision_count']} ({result['accuracy']:.1%})",
        f"- 遅延: 中央値{latency['median']}ms・平均{latency['mean']}ms・最大{latency['max']}ms",
        "",
        "## 候補順別",
        "",
        "| 候補順 | 正答 | 正答率 |",
        "|---|---:|---:|",
    ]
    for name, values in result["by_order"].items():
        lines.append(f"| {name} | {values['correct']}/{values['total']} | {values['accuracy']:.1%} |")
    lines.extend(("", "## 正解候補の元順位別（DB順）", "", "| 元順位 | 正答 | 正答率 |", "|---|---:|---:|"))
    for name, values in result["by_expected_rank_bucket"].items():
        lines.append(f"| {name} | {values['correct']}/{values['total']} | {values['accuracy']:.1%} |")
    failures = [row for row in result["rows"] if row["order"] == "database" and not row["correct"]]
    lines.extend(("", "## DB順での失敗", "", "| ID | 分野 | 読み | 候補数 | 正解元順位 | 期待 | 実結果 |", "|---|---|---|---:|---:|---|---|"))
    for row in failures:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['reading']} | {row['candidate_count']} | "
            f"{row['expected_rank']} | {row['expected']} | {row['selected']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compute-mode", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data" / "massive_homophone_database.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "build" / "full_candidate_stress_study.json",
    )
    args = parser.parse_args()
    result = run_study(args.compute_mode, args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report_path = args.output.with_suffix(".md")
    report_path.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['correct']}/{result['decision_count']} "
        f"({result['accuracy']:.1%}) -> {report_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
