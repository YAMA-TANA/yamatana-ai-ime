"""Compare nonlinear confidence gates on saved practical conversion traces.

The target is not merely exact-match accuracy.  A gate is rewarded for fixing a
wrong Mozc top candidate and penalized more heavily for replacing a correct one.
All models make an accept/reject decision about the neural winner; candidate
generation and neural inference are kept identical across policies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Callable

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler


def _split(label: str) -> str:
    value = int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:2], "big")
    return "train" if value % 2 == 0 else "validation"


def _sigmoid(value: float) -> float:
    value = max(-60.0, min(60.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def _shared_context(left: str, right: str) -> int:
    prefix = 0
    limit = min(len(left), len(right))
    while prefix < limit and left[prefix] == right[prefix]:
        prefix += 1
    suffix = 0
    while suffix < limit - prefix and left[-1 - suffix] == right[-1 - suffix]:
        suffix += 1
    return prefix + suffix


def _trace_features(row: dict) -> dict | None:
    if len(row.get("traces", [])) != 1:
        return None
    explanation = row["traces"][0]["explanation"]
    decision = explanation["decision"]
    if decision["neural_top_id"] is None:
        return None
    candidates = {item["id"]: item for item in explanation["candidates"]}
    neural = candidates[decision["neural_top_id"]]
    mozc = next(item for item in candidates.values() if item["original_rank"] == 1)
    if neural["id"] == mozc["id"]:
        return None

    evidence = np.asarray([item["evidence_score"] for item in candidates.values()])
    shifted = evidence - evidence.max()
    probabilities = np.exp(shifted) / np.exp(shifted).sum()
    top_probability = float(probabilities.max())
    entropy = float(-(probabilities * np.log(probabilities + 1e-12)).sum())
    entropy /= max(math.log(len(probabilities)), 1e-9)

    prefix = explanation["context"]["preceding_text"]
    suffix = explanation["context"]["following_text"]
    direction = (
        "both" if prefix and suffix else "prefix" if prefix else "suffix" if suffix else "none"
    )
    neural_text = str(neural["text"])
    char_count = max(len(neural_text), 1)
    lead = float(decision["lead_over_mozc"])
    runner = float(decision["lead_over_runner"])
    return {
        "lead": lead,
        "runner": runner,
        "top_model": float(neural["model_score"]),
        "top_model_per_char": float(neural["model_score"]) / char_count,
        "mozc_model_per_char": float(mozc["model_score"]) / max(len(str(mozc["text"])), 1),
        "top_probability": top_probability,
        "entropy": entropy,
        "context_len": float(explanation["context"]["signal_length"]),
        "internal_context_len": float(
            _shared_context(neural_text, str(mozc["text"]))
        ),
        "candidate_count": float(len(candidates)),
        "neural_rank_log": math.log1p(int(neural["original_rank"]) - 1),
        "direction": direction,
        "neural_surface": neural_text,
    }


def _load(paths: list[Path], context_modes: set[str]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        provider = "gpu" if "gpu" in path.name.lower() else "cpu"
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data["rows"]:
            if row["context_mode"] not in context_modes:
                continue
            features = _trace_features(row)
            if features is None:
                continue
            enriched = dict(row)
            enriched["features"] = features
            enriched["provider"] = provider
            enriched["split"] = _split(row["label"])
            rows.append(enriched)
    return rows


def _project(row: dict, accept: bool) -> str:
    return row["features"]["neural_surface"] if accept else row["raw_surface"]


def _metrics(rows: list[dict], policy: Callable[[dict], bool]) -> dict:
    correct = recoveries = regressions = changed = accepted = 0
    for row in rows:
        accept = bool(policy(row))
        surface = _project(row, accept)
        is_correct = surface == row["expected"]
        correct += int(is_correct)
        changed += int(surface != row["raw_surface"])
        accepted += int(accept)
        recoveries += int(not row["raw_correct"] and is_correct)
        regressions += int(row["raw_correct"] and not is_correct)
    return {
        "correct": correct,
        "total": len(rows),
        "recoveries": recoveries,
        "regressions": regressions,
        "changed": changed,
        "accepted": accepted,
    }


def _fixed_policies() -> list[tuple[str, Callable[[dict], bool]]]:
    policies = []
    for margin in (0.4, 0.8, 1.0, 1.3, 1.6, 2.0):
        for gap in (0.0, 0.15, 0.3, 0.5):
            policies.append((
                f"fixed m={margin:.2f} g={gap:.2f}",
                lambda row, m=margin, g=gap: (
                    row["features"]["lead"] >= m and row["features"]["runner"] >= g
                ),
            ))
    return policies


def _nonlinear_policies() -> list[tuple[str, Callable[[dict], bool]]]:
    policies: list[tuple[str, Callable[[dict], bool]]] = []

    for probability in (0.70, 0.75, 0.80, 0.85, 0.90):
        policies.append((
            f"structured-softmax p={probability:.2f}",
            lambda row, p=probability: (
                (
                    row["features"]["context_len"] >= 3
                    or row["features"]["internal_context_len"] >= 4
                )
                and row["features"]["top_probability"] >= p
            ),
        ))

    for lower_probability in (0.30, 0.35, 0.40, 0.45):
        policies.append((
            f"directional-tiered p_hi=0.80 p_lo={lower_probability:.2f} lead=1.80",
            lambda row, p_lo=lower_probability: (
                (
                    row["features"]["context_len"] >= 3
                    or row["features"]["internal_context_len"] >= 4
                )
                and (
                    row["features"]["top_probability"] >= 0.80
                    or (
                        (
                            row["features"]["direction"] == "both"
                            or row["features"]["internal_context_len"] >= 4
                        )
                        and row["features"]["top_probability"] >= p_lo
                        and row["features"]["lead"] >= 1.80
                    )
                )
            ),
        ))

    # Interpretable two-level confidence policy.  This is the production-sized
    # alternative to the learned polynomial model below.
    for high_probability in (0.75, 0.80, 0.85, 0.90):
        policies.append((
            f"tiered p_hi={high_probability:.2f} p_lo=0.35 lead=1.80",
            lambda row, p_hi=high_probability: (
                (
                    row["features"]["context_len"] >= 3
                    or row["features"]["internal_context_len"] >= 4
                )
                and (
                    row["features"]["top_probability"] >= p_hi
                    or (
                        row["features"]["top_probability"] >= 0.35
                        and row["features"]["lead"] >= 1.80
                    )
                )
            ),
        ))

    # A smooth hyperbolic boundary: a small runner gap demands a much larger
    # lead over Mozc, while a decisive runner gap asymptotically relaxes it.
    for base in (0.4, 0.8, 1.0, 1.3):
        for scale in (0.3, 0.6, 1.0, 1.5):
            for tau in (0.1, 0.25, 0.5, 1.0):
                policies.append((
                    f"curve b={base:.2f} a={scale:.2f} t={tau:.2f}",
                    lambda row, b=base, a=scale, t=tau: row["features"]["lead"]
                    >= b + a * math.exp(-max(row["features"]["runner"], 0.0) / t),
                ))

    # Shift-invariant confidence from the complete AI score distribution.
    for probability in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80):
        for margin in (0.0, 0.4, 0.8, 1.3):
            policies.append((
                f"softmax p={probability:.2f} m={margin:.2f}",
                lambda row, p=probability, m=margin: (
                    row["features"]["top_probability"] >= p
                    and row["features"]["lead"] >= m
                ),
            ))

    # Smoothly combine three independent-looking signals.  The absolute score
    # is normalized by output length because raw sequence scores are length-sensitive.
    for threshold in (0.20, 0.30, 0.40, 0.50, 0.60):
        for floor in (-5.0, -3.5, -2.5, -1.5):
            policies.append((
                f"sigmoid q={threshold:.2f} floor={floor:.1f}",
                lambda row, q=threshold, f=floor: (
                    _sigmoid((row["features"]["lead"] - 0.8) / 0.6)
                    * _sigmoid((row["features"]["runner"] - 0.15) / 0.25)
                    * _sigmoid((row["features"]["top_model_per_char"] - f) / 0.8)
                    >= q
                ),
            ))

    # Explicit absolute-score floor, included to test whether raw AI score adds
    # anything beyond pairwise score gaps.
    for floor in (-6.0, -4.5, -3.5, -2.5, -1.5):
        for margin in (0.4, 0.8, 1.3):
            policies.append((
                f"absolute floor={floor:.1f} m={margin:.2f}",
                lambda row, f=floor, m=margin: (
                    row["features"]["top_model_per_char"] >= f
                    and row["features"]["lead"] >= m
                    and row["features"]["runner"] >= 0.15
                ),
            ))
    return policies


FEATURE_NAMES = (
    "lead", "runner", "top_model_per_char", "mozc_model_per_char",
    "top_probability", "entropy", "context_len", "internal_context_len", "candidate_count",
    "neural_rank_log",
)


def _matrix(rows: list[dict], feature_names: tuple[str, ...] = FEATURE_NAMES) -> np.ndarray:
    values = []
    for row in rows:
        feature = row["features"]
        direction = feature["direction"]
        values.append(
            [feature[name] for name in feature_names]
            + [float(direction == value) for value in ("prefix", "suffix", "none")]
        )
    return np.asarray(values, dtype=np.float64)


def _fit_logistic(train: list[dict], feature_names: tuple[str, ...] = FEATURE_NAMES):
    x = _matrix(train, feature_names)
    y = np.asarray([
        int(not row["raw_correct"] and row["features"]["neural_surface"] == row["expected"])
        for row in train
    ])
    weights = np.asarray([
        8.0 if row["raw_correct"] else 1.0 for row in train
    ])
    model = make_pipeline(
        StandardScaler(),
        PolynomialFeatures(degree=2, include_bias=False),
        LogisticRegression(C=0.08, max_iter=5000),
    )
    model.fit(x, y, logisticregression__sample_weight=weights)
    return model


def _score(name: str, rows: list[dict], policy: Callable[[dict], bool]) -> dict:
    result = {"policy": name}
    for split in ("train", "validation", "all"):
        subset = rows if split == "all" else [row for row in rows if row["split"] == split]
        result[split] = _metrics(subset, policy)
    for provider in ("gpu", "cpu"):
        subset = [row for row in rows if row["provider"] == provider]
        result[provider] = _metrics(subset, policy)
    return result


def _sort_key(item: dict) -> tuple:
    validation = item["validation"]
    return (
        validation["regressions"],
        -validation["correct"],
        -validation["recoveries"],
        item["all"]["regressions"],
        -item["all"]["correct"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studies", nargs="+", type=Path)
    parser.add_argument(
        "--context-modes", default="both,prefix_only,suffix_only,no_context,short_prefix,previous_sentence"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    modes = {item.strip() for item in args.context_modes.split(",") if item.strip()}
    rows = _load(args.studies, modes)
    train = [row for row in rows if row["split"] == "train"]

    results = [
        _score(name, rows, policy)
        for name, policy in _fixed_policies() + _nonlinear_policies()
    ]
    feature_sets = {
        "gaps": ("lead", "runner"),
        "distribution": ("lead", "runner", "top_probability", "entropy"),
        "absolute": (
            "lead", "runner", "top_model_per_char", "mozc_model_per_char"
        ),
        "full": FEATURE_NAMES,
    }
    for model_name, feature_names in feature_sets.items():
        model = _fit_logistic(train, feature_names)
        probabilities = model.predict_proba(_matrix(rows, feature_names))[:, 1]
        probability_by_id = {
            id(row): float(value) for row, value in zip(rows, probabilities)
        }
        for threshold in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90):
            results.append(_score(
                f"logistic2-{model_name} p={threshold:.2f}", rows,
                lambda row, t=threshold, values=probability_by_id: values[id(row)] >= t,
            ))
    results.sort(key=_sort_key)

    def cells(metrics: dict) -> str:
        return (
            f"{metrics['correct']}/{metrics['total']} | {metrics['recoveries']} | "
            f"{metrics['regressions']} | {metrics['changed']}"
        )

    lines = [
        "# 非線形・AI信頼度ゲート比較",
        "",
        f"- 判断対象: {len(rows)}（AI 1位とMozc 1位が異なる呼び出しのみ）",
        f"- 文脈条件: `{', '.join(sorted(modes))}`",
        "- 分割: ラベルSHA-256偶数=train、奇数=validation（同一例の文脈違いは同じ側）",
        "- logistic2の学習では、Mozc正解を壊す例を8倍重くした。",
        "",
        "検証側の改悪数、正答数、回復数の順で並べた上位30方式。",
        "",
        "| 方式 | validation 正答 | 回復 | 改悪 | 変更 | 全体 正答 | 回復 | 改悪 | 変更 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results[:30]:
        val = item["validation"]
        all_metrics = item["all"]
        lines.append(
            f"| {item['policy']} | {val['correct']}/{val['total']} | "
            f"{val['recoveries']} | {val['regressions']} | {val['changed']} | "
            f"{all_metrics['correct']}/{all_metrics['total']} | "
            f"{all_metrics['recoveries']} | {all_metrics['regressions']} | "
            f"{all_metrics['changed']} |"
        )
    report = "\n".join(lines) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    if args.json_output:
        args.json_output.write_text(
            json.dumps({"rows": len(rows), "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
