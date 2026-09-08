"""Inspect candidate-level safety-gate features on a saved benchmark run."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def trace_features(trace: dict) -> dict:
    explanation = trace.get("explanation") or {}
    decision = explanation.get("decision") or {}
    candidates = explanation.get("candidates") or []
    by_id = {item["id"]: item for item in candidates}
    ordered = sorted(candidates, key=lambda item: item["final_score"], reverse=True)
    if not ordered:
        return {}
    ai1 = ordered[0]
    ai2 = ordered[1] if len(ordered) > 1 else ai1
    mozc = by_id.get(next((item["id"] for item in candidates if item["original_rank"] == 1), ""), ai1)
    return {
        "label": trace.get("key"),
        "prefix": trace.get("prefix", ""),
        "suffix": trace.get("suffix", ""),
        "reading": explanation.get("context", {}).get("reading", ""),
        "ai1": ai1["text"],
        "ai2": ai2["text"],
        "mozc": mozc["text"],
        "delta": ai1["evidence_score"] - mozc["evidence_score"],
        "margin": ai1["evidence_score"] - ai2["evidence_score"],
        "confidence": decision.get("neural_top_probability", 0.0),
        "mozc_rank": mozc["original_rank"],
        "selected": candidates[0]["text"],
    }


def main() -> int:
    path = ROOT / "build" / "human_prefix_benchmark_report_v12.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for row in data["rows"]:
        for trace in row["traces"]:
            feature = trace_features(trace)
            if feature and feature["ai1"] != feature["mozc"]:
                feature["case"] = row["label"]
                feature["raw_ok"] = row["raw_surface"] in row["acceptable"]
                feature["ai1_ok"] = row["neural_surface"] in row["acceptable"]
                rows.append(feature)
    rows.sort(key=lambda item: (item["ai1_ok"], item["confidence"]), reverse=True)
    for item in rows:
        print(
            f"{item['case']} | {item['mozc']} -> {item['ai1']} / {item['ai2']} "
            f"delta={item['delta']:.3f} margin={item['margin']:.3f} "
            f"p={item['confidence']:.3f} mozcrank={item['mozc_rank']} "
            f"raw={'Y' if item['raw_ok'] else 'N'} ai1={'Y' if item['ai1_ok'] else 'N'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
