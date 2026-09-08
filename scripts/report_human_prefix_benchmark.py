"""Re-score and explain the saved preceding-context benchmark run.

The inference output is intentionally immutable.  This reporter applies the
current human-acceptable spelling sets, while also retaining exact-match
scores, and separates candidate generation, neural ranking, and the safety
gate so that one headline accuracy cannot hide the actual bottleneck.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.human_prefix_benchmark_cases import CASES
from ranker.candidate_supplements import (
    merge_supplemental_surfaces,
    prepare_supplemented_segments,
)


def _distinct(values: list[str], limit: int = 0) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
        if limit and len(result) >= limit:
            break
    return result


def _can_compose(segments: list[dict], acceptable: tuple[str, ...], limit: int = 0) -> bool:
    partial = {""}
    for segment in segments:
        candidates = _distinct(segment["candidates"], limit)
        partial = {prefix + candidate for prefix in partial for candidate in candidates}
        # Every expected string is short, so pruning non-prefixes is exact and
        # prevents a large Cartesian product for Mozc's long candidate lists.
        partial = {
            text for text in partial
            if any(expected.startswith(text) for expected in acceptable)
        }
        if not partial:
            return False
    return any(text in acceptable for text in partial)


def _neural_surface(row: dict, mozc_case: dict) -> str:
    if row["traces"]:
        ordered_traces = sorted(row["traces"], key=lambda trace: trace["segment_index"])
        selected = [trace["raw_top"] for trace in ordered_traces]
        ranked = _neural_ranked_segments(row, mozc_case)
        for trace in ordered_traces:
            candidates = ranked[trace["segment_index"]]
            selected[trace["segment_index"]] = candidates[0]
        return "".join(selected)
    ranked = _neural_ranked_segments(row, mozc_case)
    return "".join(candidates[0] for candidates in ranked)


def _neural_ranked_segments(row: dict, mozc_case: dict) -> list[list[str]]:
    if row["traces"]:
        ranked = [[] for _ in range(max(trace["segment_index"] for trace in row["traces"]) + 1)]
    else:
        ranked = [[segment["candidates"][0]] for segment in mozc_case["segments"]]
    for trace in row["traces"]:
        explanation = trace.get("explanation") or {}
        # output_rank already includes the safety gate.  Reconstruct the
        # model+style+prior order from final_score to inspect the raw scorer.
        candidates = sorted(
            explanation.get("candidates") or [],
            key=lambda candidate: candidate["final_score"],
            reverse=True,
        )
        if candidates:
            ranked[trace["segment_index"]] = _distinct(
                [candidate["text"] for candidate in candidates]
            )
        elif not ranked[trace["segment_index"]]:
            ranked[trace["segment_index"]] = [trace["raw_top"]]
    return ranked


def _augmented_segments(item: dict, candidate_limit: int) -> list[dict]:
    segments = prepare_supplemented_segments(item["reading"], item["segments"])
    result = []
    for segment in segments:
        candidates = list(segment["candidates"])
        if candidate_limit:
            candidates = candidates[:candidate_limit]
        result.append({
            "candidates": merge_supplemental_surfaces(segment["key"], candidates)
        })
    return result


def _ranked_can_compose(ranked: list[list[str]], acceptable: tuple[str, ...], k: int) -> bool:
    segments = [{"candidates": candidates} for candidates in ranked]
    return _can_compose(segments, acceptable, k)


def _score(rows: list[dict], key: str) -> dict:
    correct = sum(bool(row[key]) for row in rows)
    return {"correct": correct, "total": len(rows), "accuracy": correct / len(rows)}


def analyze(saved: dict) -> dict:
    case_by_label = {case.label: case for case in CASES}
    mozc_by_label = {case["label"]: case for case in saved["mozc_cases"]}
    rows: list[dict] = []

    for original in saved["rows"]:
        case = case_by_label[original["label"]]
        mozc_case = mozc_by_label[original["label"]]
        acceptable = case.acceptable
        augmented_segments = _augmented_segments(mozc_case, saved["candidate_limit"])
        row = dict(original)
        row.update(
            acceptable=list(acceptable),
            strict_raw=original["raw_surface"] == case.expected,
            strict_ai=original["ai_surface"] == case.expected,
            raw_ok=original["raw_surface"] in acceptable,
            ai_ok=original["ai_surface"] in acceptable,
            neural_surface=_neural_surface(original, mozc_case),
            all_reachable=_can_compose(augmented_segments, acceptable),
            sent_reachable=_can_compose(
                augmented_segments, acceptable, saved["candidate_limit"]
            ),
        )
        neural_ranked = _neural_ranked_segments(original, mozc_case)
        row["neural_top_k"] = {
            str(k): _ranked_can_compose(neural_ranked, acceptable, k)
            for k in (1, 2, 3, 5, 8)
        }
        row["neural_ok"] = row["neural_surface"] in acceptable
        row["raw_or_neural_ok"] = row["raw_ok"] or row["neural_ok"]
        if row["ai_ok"]:
            row["failure_stage"] = "correct"
        elif not row["sent_reachable"]:
            row["failure_stage"] = "candidate_missing"
        elif row["neural_ok"]:
            row["failure_stage"] = "safety_gate"
        else:
            row["failure_stage"] = "neural_ranking"
        rows.append(row)

    by_category: dict[str, dict] = {}
    by_form: dict[str, dict] = {}
    for field, destination in (("category", by_category), ("form", by_form)):
        for name in sorted({row[field] for row in rows}):
            subset = [row for row in rows if row[field] == name]
            destination[name] = {
                "raw": _score(subset, "raw_ok"),
                "ai": _score(subset, "ai_ok"),
                "recoveries": sum(not row["raw_ok"] and row["ai_ok"] for row in subset),
                "regressions": sum(row["raw_ok"] and not row["ai_ok"] for row in subset),
            }

    total = len(rows)
    raw_correct = sum(row["raw_ok"] for row in rows)
    raw_wrong = total - raw_correct
    target_count = math.ceil(total * 0.95)
    stages = defaultdict(int)
    for row in rows:
        stages[row["failure_stage"]] += 1

    return {
        "source": saved.get("model_path"),
        "compute_mode": saved["compute_mode"],
        "case_count": total,
        "scene_count": total // 2,
        "strict": {
            "raw": _score(rows, "strict_raw"),
            "ai": _score(rows, "strict_ai"),
        },
        "practical": {
            "raw": _score(rows, "raw_ok"),
            "ai": _score(rows, "ai_ok"),
            "neural_top": _score(rows, "neural_ok"),
            "neural_top_k_reach": {
                str(k): {
                    "correct": sum(row["neural_top_k"][str(k)] for row in rows),
                    "total": total,
                    "accuracy": sum(row["neural_top_k"][str(k)] for row in rows) / total,
                }
                for k in (1, 2, 3, 5, 8)
            },
            "raw_or_neural_oracle": _score(rows, "raw_or_neural_ok"),
            "all_candidate_ceiling": {
                "correct": sum(row["all_reachable"] for row in rows),
                "total": total,
                "accuracy": sum(row["all_reachable"] for row in rows) / total,
            },
            "sent_candidate_ceiling": {
                "correct": sum(row["sent_reachable"] for row in rows),
                "total": total,
                "accuracy": sum(row["sent_reachable"] for row in rows) / total,
            },
        },
        "gate": {
            "raw_correct_protected": sum(row["raw_ok"] and row["ai_ok"] for row in rows),
            "raw_correct_total": raw_correct,
            "raw_wrong_recovered": sum(not row["raw_ok"] and row["ai_ok"] for row in rows),
            "raw_wrong_total": raw_wrong,
            "regressions": sum(row["raw_ok"] and not row["ai_ok"] for row in rows),
            "timeouts": sum(row["budget_exhausted"] for row in rows),
        },
        "failure_stage": dict(stages),
        "target_95": {
            "required": target_count,
            "current_gap": target_count - sum(row["ai_ok"] for row in rows),
            "candidate_ceiling_headroom": sum(row["sent_reachable"] for row in rows) - target_count,
        },
        "by_category": by_category,
        "by_form": by_form,
        "rows": rows,
    }


def _metric(value: dict) -> str:
    return f"{value['correct']}/{value['total']} ({value['accuracy']:.1%})"


def markdown(result: dict) -> str:
    strict = result["strict"]
    practical = result["practical"]
    gate = result["gate"]
    target = result["target_95"]
    lines = [
        "# 人間入力を模した前文脈ベンチマーク",
        "",
        f"- {result['scene_count']}場面 × 対象語のみ／助詞・活用込み = {result['case_count']}件",
        "- 入力条件: 前文脈あり、後続文脈なし",
        "- 性格: 実利用頻度では重み付けしていない、同音異義語を多めに含む難問寄りの固定コーパス",
        f"- 推論: `{result['compute_mode']}`、タイムアウト {gate['timeouts']}件",
        "",
        "## 総合結果",
        "",
        "| 指標 | Mozc素順位 | AI適用後 |",
        "|---|---:|---:|",
        f"| 厳密一致 | {_metric(strict['raw'])} | {_metric(strict['ai'])} |",
        f"| 実用正解（自然な表記揺れを許容） | {_metric(practical['raw'])} | {_metric(practical['ai'])} |",
        "",
        "## どこが上限か",
        "",
        "| 段階 | 実用正解 | 説明 |",
        "|---|---:|---|",
        f"| AIモデルの生1位 | {_metric(practical['neural_top'])} | 安全補正前のモデル選択 |",
        f"| Mozc 1位またはAI 1位の理想選択 | {_metric(practical['raw_or_neural_oracle'])} | 現モデルの二択上限 |",
        f"| AIへ送信した候補内の理論上限 | {_metric(practical['sent_candidate_ceiling'])} | 現候補8件から完全な判定器が選ぶ上限 |",
        f"| Mozc全候補内の理論上限 | {_metric(practical['all_candidate_ceiling'])} | 候補生成を変えない場合の上限 |",
        "",
        "AIスコア上位k件に正解の組み合わせが残る割合: "
        + "、".join(
            f"top-{k} {_metric(value)}"
            for k, value in practical["neural_top_k_reach"].items()
        )
        + "。",
        "",
        f"95%には{target['required']}件正解が必要で、現状との差は{target['current_gap']}件です。"
        f"送信候補の理論上限から95%までの余裕は{target['candidate_ceiling_headroom']}件しかありません。",
        "",
        "## 安全補正の挙動",
        "",
        f"- Mozcが正しかった{gate['raw_correct_total']}件のうち、{gate['raw_correct_protected']}件を維持"
        f"（{gate['raw_correct_protected'] / gate['raw_correct_total']:.1%}）",
        f"- Mozcが誤った{gate['raw_wrong_total']}件のうち、{gate['raw_wrong_recovered']}件を回復"
        f"（{gate['raw_wrong_recovered'] / gate['raw_wrong_total']:.1%}）",
        f"- 改悪 {gate['regressions']}件",
        "",
        "## 分野別（実用正解）",
        "",
        "| 分野 | Mozc素順位 | AI適用後 | 回復 | 改悪 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in result["by_category"].items():
        lines.append(
            f"| {name} | {_metric(values['raw'])} | {_metric(values['ai'])} | "
            f"{values['recoveries']} | {values['regressions']} |"
        )
    lines.extend((
        "",
        "## 入力形別（実用正解）",
        "",
        "| 入力形 | Mozc素順位 | AI適用後 | 回復 | 改悪 |",
        "|---|---:|---:|---:|---:|",
    ))
    for name, values in result["by_form"].items():
        lines.append(
            f"| {name} | {_metric(values['raw'])} | {_metric(values['ai'])} | "
            f"{values['recoveries']} | {values['regressions']} |"
        )
    lines.extend((
        "",
        "## 残った誤り",
        "",
        "| 原因 | ケース | 期待（許容表記） | Mozc | AI生1位 | AI適用後 |",
        "|---|---|---|---|---|---|",
    ))
    stage_names = {
        "candidate_missing": "候補なし",
        "neural_ranking": "モデル順位",
        "safety_gate": "安全補正",
    }
    for row in result["rows"]:
        if row["ai_ok"]:
            continue
        lines.append(
            f"| {stage_names[row['failure_stage']]} | {row['label']} | "
            f"{'／'.join(row['acceptable'])} | {row['raw_surface']} | "
            f"{row['neural_surface']} | {row['ai_surface']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=ROOT / "build/human_prefix_benchmark_cpu.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/human_prefix_benchmark_report.json"
    )
    args = parser.parse_args()
    saved = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(saved)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = args.output.with_suffix(".md")
    report_path.write_text(markdown(result), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
