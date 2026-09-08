"""Evaluate the AI pipeline using candidate lists emitted by Mozc itself."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ranker.onnx_ranker import OnnxRuriReranker
from ranker.candidate_supplements import (
    merge_supplemental_surfaces,
    prepare_supplemented_segments,
)
from scripts.preliminary_conversion_study import CASES


SEGMENT_RE = re.compile(r"^---------- Segment (\d+)/(\d+) \[.*\] ----------$")
CANDIDATE_RE = re.compile(r"^\s+(\d+)/(\d+) (.*)$")
KANJI_NUMBER_RE = re.compile(r"[〇零一二三四五六七八九十百千万]+")
FULLWIDTH_ASCII = str.maketrans("０１２３４５６７８９％", "0123456789%")
KANJI_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
                "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
KANJI_UNITS = {"十": 10, "百": 100, "千": 1000, "万": 10000}
EXPERIMENTAL_NUMERIC_BONUS = 1.0


def parse_kanji_number(text: str) -> int:
    if all(char in KANJI_DIGITS for char in text):
        return int("".join(str(KANJI_DIGITS[char]) for char in text))
    total = 0
    section = 0
    digit = 0
    for char in text:
        if char in KANJI_DIGITS:
            digit = KANJI_DIGITS[char]
        elif char == "万":
            section += digit
            total += (section or 1) * 10000
            section = 0
            digit = 0
        else:
            unit = KANJI_UNITS[char]
            section += (digit or 1) * unit
            digit = 0
    return total + section + digit


def canonical_numeric_surface(text: str) -> str:
    translated = text.translate(FULLWIDTH_ASCII).replace("パーセント", "%")
    return KANJI_NUMBER_RE.sub(
        lambda match: str(parse_kanji_number(match.group(0))), translated
    )


def experimental_numeric_style_bonus(
    candidate_text: str, alternatives: list[str]
) -> float:
    canonical = canonical_numeric_surface(candidate_text)
    if canonical != candidate_text or not any(char.isdigit() or char == "%" for char in canonical):
        return 0.0
    if any(
        alternative != candidate_text
        and canonical_numeric_surface(alternative) == canonical
        for alternative in alternatives
    ):
        return EXPERIMENTAL_NUMERIC_BONUS
    return 0.0


def dump_mozc_candidates(
    cli_path: Path,
    runfiles_dir: Path,
    profile_dir: Path,
    study_cases=CASES,
) -> list[dict]:
    commands = ["disableuserhistory"]
    for item in study_cases:
        commands.extend(("reset", f"start {item.reading}"))
    completed = subprocess.run(
        [
            str(cli_path),
            "--max_conversion_candidates_size=200",
            "--max_candidates_to_show=500",
            f"--user_profile_dir={profile_dir}",
        ],
        input="\n".join(commands) + "\n",
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        cwd=runfiles_dir,
        timeout=max(180, len(study_cases) * 2),
        check=True,
    )

    conversions: list[list[dict]] = []
    current_conversion: list[dict] | None = None
    current_segment: dict | None = None
    for line in completed.stdout.splitlines():
        segment_match = SEGMENT_RE.match(line)
        if segment_match:
            index = int(segment_match.group(1))
            count = int(segment_match.group(2))
            if index == 0:
                current_conversion = []
                conversions.append(current_conversion)
            if current_conversion is None:
                raise RuntimeError("Mozc output began with a nonzero segment")
            current_segment = {
                "index": index,
                "segment_count": count,
                "key": None,
                "candidates": [],
            }
            current_conversion.append(current_segment)
            continue
        if current_segment is not None and current_segment["key"] is None:
            if line and not line.startswith(" "):
                current_segment["key"] = line
            continue
        candidate_match = CANDIDATE_RE.match(line)
        if current_segment is not None and candidate_match:
            current_segment["candidates"].append(candidate_match.group(3))

    if len(conversions) != len(study_cases):
        raise RuntimeError(
            f"Expected {len(study_cases)} Mozc conversions, received {len(conversions)}"
        )
    result = []
    for item, segments in zip(study_cases, conversions):
        if any(segment["key"] is None or not segment["candidates"] for segment in segments):
            raise RuntimeError(f"Incomplete Mozc output for {item.label}")
        result.append(
            {
                "label": item.label,
                "category": item.category,
                "form": getattr(item, "form", "基本"),
                "reading": item.reading,
                "prefix": item.prefix,
                "suffix": item.suffix,
                "expected": item.expected,
                "acceptable": list(getattr(item, "acceptable", (item.expected,))),
                "segments": segments,
            }
        )
    return result


def context_for_mode(item: dict, mode: str) -> tuple[str, str]:
    if mode == "both":
        return item["prefix"], item["suffix"]
    if mode == "prefix_only":
        return item["prefix"], ""
    if mode == "suffix_only":
        return "", item["suffix"]
    if mode == "no_context":
        return "", ""
    if mode == "short_prefix":
        return item["prefix"][-2:], ""
    if mode == "previous_sentence":
        return f"前回の資料は確認済み。{item['prefix']}", item["suffix"]
    raise ValueError(mode)


def simulate_pipeline(
    ranker: OnnxRuriReranker,
    item: dict,
    context_mode: str,
    budget_ms: float,
    candidate_limit: int,
    deduplicate_surfaces: bool,
    include_numeric_representatives: bool,
) -> dict:
    prefix, suffix = context_for_mode(item, context_mode)
    segments = prepare_supplemented_segments(item["reading"], item["segments"])
    raw_tops = [segment["candidates"][0] for segment in segments]
    tops = list(raw_tops)
    ai_called = bool(prefix or suffix) or len(segments) > 1 or len(item["reading"]) >= 6
    traces = []
    elapsed_ms = 0.0
    if ai_called:
        # A whole-phrase deadline must not starve the leftmost/target segment
        # after a few expensive later-segment calls.  Reserve a fair slice for
        # every segment while retaining the total elapsed time for diagnostics.
        segment_budget_ms = max(450.0, budget_ms / max(len(segments), 1))
        for index in range(len(segments) - 1, -1, -1):
            segment = segments[index]
            segment_prefix = prefix + "".join(tops[:index])
            segment_suffix = "".join(tops[index + 1 :]) + suffix
            candidates = segment["candidates"]
            if deduplicate_surfaces:
                candidates = list(dict.fromkeys(candidates))
            if candidate_limit > 0:
                all_candidates = candidates
                base_candidates = all_candidates[:candidate_limit]
                candidates = merge_supplemental_surfaces(segment["key"], base_candidates)
                if include_numeric_representatives:
                    base_canonical = {
                        canonical_numeric_surface(candidate) for candidate in candidates
                    }
                    candidates.extend(
                        candidate
                        for candidate in all_candidates[candidate_limit:]
                        if candidate == canonical_numeric_surface(candidate)
                        and candidate in base_canonical
                    )
            else:
                candidates = merge_supplemental_surfaces(segment["key"], candidates)
            request = {
                "request_id": f"mozc:{item['label']}:{context_mode}:{index}",
                "preceding_text": segment_prefix,
                "following_text": segment_suffix,
                "read": segment["key"],
                "candidates": [
                    {"id": f"c{candidate_index}", "text": text, "rank": candidate_index + 1}
                    for candidate_index, text in enumerate(candidates)
                ],
            }
            started = time.perf_counter()
            response = ranker.rank(request)
            call_ms = (time.perf_counter() - started) * 1000.0
            elapsed_ms += call_ms
            timed_out = call_ms > segment_budget_ms
            by_id = {candidate["id"]: candidate["text"] for candidate in request["candidates"]}
            selected = by_id[response["candidates"][0]["id"]]
            traces.append(
                {
                    "segment_index": index,
                    "key": segment["key"],
                    "candidate_count": len(candidates),
                    "prefix": segment_prefix,
                    "suffix": segment_suffix,
                    "raw_top": raw_tops[index],
                    "ranker_top": selected,
                    "latency_ms": round(call_ms, 2),
                    "timed_out": timed_out,
                    "explanation": ranker.last_explanation,
                }
            )
            if not timed_out:
                tops[index] = selected
    raw_surface = "".join(raw_tops)
    ai_surface = "".join(tops)
    return {
        "label": item["label"],
        "category": item["category"],
        "form": item["form"],
        "reading": item["reading"],
        "context_mode": context_mode,
        "expected": item["expected"],
        "acceptable": item["acceptable"],
        "segment_keys": [segment["key"] for segment in segments],
        "candidate_counts": [len(segment["candidates"]) for segment in segments],
        "raw_surface": raw_surface,
        "raw_correct": raw_surface in item["acceptable"],
        "ai_called": ai_called,
        "ai_surface": ai_surface,
        "ai_correct": ai_surface in item["acceptable"],
        "ai_changed": ai_surface != raw_surface,
        "budget_exhausted": any(trace["timed_out"] for trace in traces),
        "elapsed_ms": round(elapsed_ms, 2),
        "traces": traces,
    }


def simulate_joint_pipeline(
    ranker: OnnxRuriReranker,
    item: dict,
    context_mode: str,
    budget_ms: float,
    top_per_segment: int,
    include_numeric_representatives: bool,
    beam_width: int,
) -> dict:
    prefix, suffix = context_for_mode(item, context_mode)
    segments = item["segments"]
    raw_tops = [segment["candidates"][0] for segment in segments]
    raw_surface = "".join(raw_tops)
    ai_called = len(segments) > 1 and top_per_segment > 0
    traces = []
    ai_surface = raw_surface
    elapsed_ms = 0.0

    if ai_called:
        choices = []
        for segment in segments:
            all_candidates = list(dict.fromkeys(segment["candidates"]))
            selected = all_candidates[:top_per_segment]
            selected = merge_supplemental_surfaces(segment["key"], selected)
            if include_numeric_representatives:
                base_canonical = {
                    canonical_numeric_surface(candidate) for candidate in selected
                }
                selected.extend(
                    candidate
                    for candidate in all_candidates[top_per_segment:]
                    if candidate == canonical_numeric_surface(candidate)
                    and any(char.isdigit() or char == "%" for char in candidate)
                    and candidate in base_canonical
                )
            choices.append(selected)
        ranked_hypotheses: list[tuple[tuple[str, ...], int]] = [((), 0)]
        for segment_choices in choices:
            expanded = [
                (parts + (surface,), cost + local_rank)
                for parts, cost in ranked_hypotheses
                for local_rank, surface in enumerate(segment_choices)
            ]
            expanded.sort(key=lambda item: (item[1], item[0]))
            ranked_hypotheses = expanded[:beam_width] if beam_width > 0 else expanded
        hypotheses = [parts for parts, _cost in ranked_hypotheses]
        # Product order guarantees the all-Mozc-top baseline is p0.
        request = {
            "request_id": f"mozc-joint:{item['label']}:{context_mode}",
            "preceding_text": prefix,
            "following_text": suffix,
            "read": item["reading"],
            "candidates": [
                {"id": f"p{index}", "text": "".join(parts), "rank": index + 1}
                for index, parts in enumerate(hypotheses)
            ],
        }
        started = time.perf_counter()
        response = ranker.rank(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        timed_out = elapsed_ms > budget_ms
        by_id = {
            candidate["id"]: candidate["text"]
            for candidate in request["candidates"]
        }
        selected_id = response["candidates"][0]["id"]
        selected_index = int(selected_id[1:])
        selected_parts = hypotheses[selected_index]
        if not timed_out:
            ai_surface = by_id[selected_id]
        traces.append(
            {
                "segment_index": None,
                "key": item["reading"],
                "candidate_count": len(hypotheses),
                "prefix": prefix,
                "suffix": suffix,
                "raw_top": raw_surface,
                "ranker_top": by_id[selected_id],
                "selected_parts": list(selected_parts),
                "latency_ms": round(elapsed_ms, 2),
                "timed_out": timed_out,
                "explanation": ranker.last_explanation,
            }
        )

    return {
        "label": item["label"],
        "category": item["category"],
        "form": item["form"],
        "reading": item["reading"],
        "context_mode": context_mode,
        "expected": item["expected"],
        "acceptable": item["acceptable"],
        "segment_keys": [segment["key"] for segment in segments],
        "candidate_counts": [len(segment["candidates"]) for segment in segments],
        "raw_surface": raw_surface,
        "raw_correct": raw_surface in item["acceptable"],
        "ai_called": ai_called,
        "ai_surface": ai_surface,
        "ai_correct": ai_surface in item["acceptable"],
        "ai_changed": ai_surface != raw_surface,
        "budget_exhausted": any(trace["timed_out"] for trace in traces),
        "elapsed_ms": round(elapsed_ms, 2),
        "traces": traces,
    }


def aggregate(rows: list[dict], field: str) -> dict[str, int | float]:
    correct = sum(int(row[field]) for row in rows)
    return {
        "correct": correct,
        "total": len(rows),
        "accuracy": round(correct / len(rows), 4),
    }


def run_study(
    compute_mode: str,
    cli_path: Path,
    runfiles_dir: Path,
    profile_dir: Path,
    budget_ms: float,
    candidate_limit: int,
    deduplicate_surfaces: bool,
    experimental_numeric_normalization: bool,
    include_numeric_representatives: bool,
    numeric_style_bonus: float,
    joint_top_per_segment: int,
    joint_beam_width: int,
    study_cases=CASES,
    extended_contexts: bool = False,
    context_modes_override: list[str] | None = None,
    cached_mozc_cases: Path | None = None,
) -> dict:
    global EXPERIMENTAL_NUMERIC_BONUS
    EXPERIMENTAL_NUMERIC_BONUS = numeric_style_bonus
    if cached_mozc_cases and cached_mozc_cases.exists():
        raw_data = json.loads(cached_mozc_cases.read_text(encoding="utf-8"))
        cases = raw_data.get("mozc_cases", raw_data) if isinstance(raw_data, dict) else raw_data
        print(f"Loaded {len(cases)} cached Mozc candidate cases from {cached_mozc_cases}")
    else:
        cases = dump_mozc_candidates(
            cli_path, runfiles_dir, profile_dir, study_cases=study_cases
        )
    if experimental_numeric_normalization:
        import ranker.onnx_ranker as onnx_ranker_module

        onnx_ranker_module.orthographic_style_bonus = experimental_numeric_style_bonus
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
    if experimental_numeric_normalization:
        original_lexical_penalty = ranker.lexicon.compute_lexical_penalty

        def numeric_aware_lexical_penalty(word: str, reading: str | None = None) -> float:
            canonical = canonical_numeric_surface(word)
            if (
                canonical == word
                and any(char.isdigit() or char == "%" for char in canonical)
            ):
                return 0.0
            return original_lexical_penalty(word, reading)

        ranker.lexicon.compute_lexical_penalty = numeric_aware_lexical_penalty
    def simulate_item(item: dict, mode: str) -> dict:
        if joint_top_per_segment > 0 and len(item["segments"]) > 1:
            return simulate_joint_pipeline(
                ranker,
                item,
                mode,
                budget_ms,
                joint_top_per_segment,
                include_numeric_representatives,
                joint_beam_width,
            )
        return simulate_pipeline(
            ranker,
            item,
            mode,
            budget_ms,
            candidate_limit,
            deduplicate_surfaces,
            include_numeric_representatives,
        )

    context_modes = context_modes_override or [
        "both", "prefix_only", "suffix_only", "no_context"
    ]
    if extended_contexts and context_modes_override is None:
        context_modes.extend(("short_prefix", "previous_sentence"))
    rows = [
        simulate_item(item, mode)
        for item in cases
        for mode in context_modes
    ]
    by_mode = {}
    for mode in context_modes:
        selected = [row for row in rows if row["context_mode"] == mode]
        by_mode[mode] = {
            "raw": aggregate(selected, "raw_correct"),
            "ai": aggregate(selected, "ai_correct"),
            "changed": sum(int(row["ai_changed"]) for row in selected),
            "budget_exhausted": sum(int(row["budget_exhausted"]) for row in selected),
        }
    all_candidate_counts = [
        count for item in cases for segment in item["segments"] for count in [len(segment["candidates"])]
    ]
    return {
        "compute_mode": compute_mode,
        "model_path": str(ranker.model_path),
        "mozc_cli": str(cli_path),
        "case_count": len(cases),
        "decision_count": len(rows),
        "budget_ms": budget_ms,
        "candidate_limit": candidate_limit,
        "deduplicate_surfaces": deduplicate_surfaces,
        "experimental_numeric_normalization": experimental_numeric_normalization,
        "include_numeric_representatives": include_numeric_representatives,
        "numeric_style_bonus": numeric_style_bonus,
        "joint_top_per_segment": joint_top_per_segment,
        "joint_beam_width": joint_beam_width,
        "extended_contexts": extended_contexts,
        "context_modes": context_modes,
        "by_category": {
            category: {
                "raw": aggregate(selected, "raw_correct"),
                "ai": aggregate(selected, "ai_correct"),
                "regressions": sum(
                    int(row["raw_correct"] and not row["ai_correct"])
                    for row in selected
                ),
                "recoveries": sum(
                    int(not row["raw_correct"] and row["ai_correct"])
                    for row in selected
                ),
            }
            for category in sorted({row["category"] for row in rows})
            for selected in [[row for row in rows if row["category"] == category]]
        },
        "by_form": {
            form: {
                "raw": aggregate(selected, "raw_correct"),
                "ai": aggregate(selected, "ai_correct"),
                "regressions": sum(
                    int(row["raw_correct"] and not row["ai_correct"])
                    for row in selected
                ),
                "recoveries": sum(
                    int(not row["raw_correct"] and row["ai_correct"])
                    for row in selected
                ),
            }
            for form in sorted({row["form"] for row in rows})
            for selected in [[row for row in rows if row["form"] == form]]
        },
        "segment_count": sum(len(item["segments"]) for item in cases),
        "candidate_count_per_segment": {
            "min": min(all_candidate_counts),
            "median": statistics.median(all_candidate_counts),
            "mean": round(statistics.mean(all_candidate_counts), 2),
            "max": max(all_candidate_counts),
        },
        "by_context_mode": by_mode,
        "mozc_cases": cases,
        "rows": rows,
    }


def markdown_report(result: dict) -> str:
    counts = result["candidate_count_per_segment"]
    report_mode = result.get("context_modes", ["both"])[0]
    context_label = {
        "both": "前後文脈",
        "prefix_only": "前文脈のみ",
        "suffix_only": "後続文脈のみ",
        "none": "文脈なし",
        "short": "短い文脈",
    }.get(report_mode, report_mode)
    lines = [
        "# Mozc実候補列による変換パイプライン予備調査",
        "",
        f"- 演算: `{result['compute_mode']}`",
        f"- Mozc CLI: `{result['mozc_cli']}`",
        f"- 基本ケース: {result['case_count']} / 文脈別判定: {result['decision_count']}",
        f"- Mozcセグメント総数: {result['segment_count']}",
        f"- AIへ送る候補上限: {result['candidate_limit'] or '全件'}",
        f"- 同一表記の重複除去: {result['deduplicate_surfaces']}",
        f"- 実験的な数字表記正規化: {result['experimental_numeric_normalization']}",
        f"- 上限外の半角数字代表を追加: {result['include_numeric_representatives']}",
        f"- 数字表記ボーナス: {result['numeric_style_bonus']}",
        f"- 句単位ビーム（各セグメント上位）: {result['joint_top_per_segment'] or '無効'}",
        f"- 句単位ビーム幅: {result['joint_beam_width'] or '無制限'}",
        f"- 拡張文脈条件: {result['extended_contexts']}",
        f"- 1セグメント候補数: 最小{counts['min']}・中央値{counts['median']}・平均{counts['mean']}・最大{counts['max']}",
        "",
        "## 文脈別比較",
        "",
        "| 文脈 | Mozc素順位 | AI後 | AI変更 | 2秒枯渇 |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode, values in result["by_context_mode"].items():
        raw = values["raw"]
        ai = values["ai"]
        lines.append(
            f"| {mode} | {raw['correct']}/{raw['total']} ({raw['accuracy']:.1%}) | "
            f"{ai['correct']}/{ai['total']} ({ai['accuracy']:.1%}) | {values['changed']} | "
            f"{values['budget_exhausted']} |"
        )
    lines.extend((
        "",
        "## 分野別（全ての文脈条件）",
        "",
        "| 分野 | Mozc素順位 | AI後 | 回復 | 改悪 |",
        "|---|---:|---:|---:|---:|",
    ))
    for name, values in result["by_category"].items():
        raw = values["raw"]
        ai = values["ai"]
        lines.append(
            f"| {name} | {raw['correct']}/{raw['total']} ({raw['accuracy']:.1%}) | "
            f"{ai['correct']}/{ai['total']} ({ai['accuracy']:.1%}) | "
            f"{values['recoveries']} | {values['regressions']} |"
        )
    lines.extend((
        "",
        "## 入力形別（全ての文脈条件）",
        "",
        "| 入力形 | Mozc素順位 | AI後 | 回復 | 改悪 |",
        "|---|---:|---:|---:|---:|",
    ))
    for name, values in result["by_form"].items():
        raw = values["raw"]
        ai = values["ai"]
        lines.append(
            f"| {name} | {raw['correct']}/{raw['total']} ({raw['accuracy']:.1%}) | "
            f"{ai['correct']}/{ai['total']} ({ai['accuracy']:.1%}) | "
            f"{values['recoveries']} | {values['regressions']} |"
        )
    lines.extend((
        "",
        f"## {context_label}でAIが悪化させた例",
        "",
        "| ケース | 読み | 分節 | 候補数 | 期待 | Mozc | AI後 |",
        "|---|---|---|---|---|---|---|",
    ))
    for row in result["rows"]:
        if row["context_mode"] == report_mode and row["raw_correct"] and not row["ai_correct"]:
            lines.append(
                f"| {row['label']} | {row['reading']} | {' / '.join(row['segment_keys'])} | "
                f"{' / '.join(map(str, row['candidate_counts']))} | {row['expected']} | "
                f"{row['raw_surface']} | {row['ai_surface']} |"
            )
    lines.extend((
        "",
        f"## {context_label}でAIが改善した例",
        "",
        "| ケース | 読み | 分節 | 期待 | Mozc | AI後 |",
        "|---|---|---|---|---|---|",
    ))
    for row in result["rows"]:
        if row["context_mode"] == report_mode and not row["raw_correct"] and row["ai_correct"]:
            lines.append(
                f"| {row['label']} | {row['reading']} | {' / '.join(row['segment_keys'])} | "
                f"{row['expected']} | {row['raw_surface']} | {row['ai_surface']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compute-mode", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument(
        "--cli",
        type=Path,
        default=ROOT / "build" / "diagnostics" / "mozc_converter_raw.exe",
    )
    parser.add_argument(
        "--runfiles",
        type=Path,
        default=(
            ROOT
            / "build/mozc-fork-work/src/bazel-bin/converter/"
            "converter_main.exe.runfiles/_main"
        ),
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=ROOT / "build" / "mozc-candidate-profile",
    )
    parser.add_argument("--budget-ms", type=float, default=2000.0)
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=0,
        help="Maximum Mozc candidates sent per segment; zero sends all",
    )
    parser.add_argument("--deduplicate-surfaces", action="store_true")
    parser.add_argument("--experimental-numeric-normalization", action="store_true")
    parser.add_argument("--include-numeric-representatives", action="store_true")
    parser.add_argument("--numeric-style-bonus", type=float, default=1.0)
    parser.add_argument(
        "--joint-top-per-segment",
        type=int,
        default=0,
        help="Score Cartesian phrase hypotheses using this many distinct surfaces per segment",
    )
    parser.add_argument(
        "--joint-beam-width",
        type=int,
        default=0,
        help="Maximum whole-phrase hypotheses retained after each segment",
    )
    parser.add_argument(
        "--corpus", choices=("core", "practical", "phrases", "human_prefix"), default="core"
    )
    parser.add_argument("--extended-contexts", action="store_true")
    parser.add_argument(
        "--context-modes",
        help="Comma-separated modes; e.g. prefix_only",
    )
    parser.add_argument(
        "--cached-mozc-cases",
        type=Path,
        default=None,
        help="Path to JSON containing cached mozc_cases to bypass Mozc binary execution",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "build" / "mozc_candidate_pipeline_study.json",
    )
    args = parser.parse_args()
    if args.corpus == "human_prefix":
        from scripts.human_prefix_benchmark_cases import CASES as study_cases
    elif args.corpus == "practical":
        from scripts.practical_conversion_cases import CASES as study_cases
    elif args.corpus == "phrases":
        from scripts.practical_phrase_cases import CASES as study_cases
    else:
        study_cases = CASES
    args.profile.mkdir(parents=True, exist_ok=True)
    result = run_study(
        args.compute_mode,
        args.cli.resolve(),
        args.runfiles.resolve(),
        args.profile.resolve(),
        args.budget_ms,
        args.candidate_limit,
        args.deduplicate_surfaces,
        args.experimental_numeric_normalization,
        args.include_numeric_representatives,
        args.numeric_style_bonus,
        args.joint_top_per_segment,
        args.joint_beam_width,
        study_cases,
        args.extended_contexts,
        ([item.strip() for item in args.context_modes.split(",") if item.strip()]
         if args.context_modes else None),
        cached_mozc_cases=args.cached_mozc_cases.resolve() if args.cached_mozc_cases else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report_path = args.output.with_suffix(".md")
    report_path.write_text(markdown_report(result), encoding="utf-8")
    print(f"wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
