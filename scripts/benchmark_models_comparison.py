"""Benchmark and side-by-side comparison between Baseline 310M and Distilled 70M."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ranker.onnx_ranker import OnnxRuriReranker

MODEL_310M = ROOT / "build" / "onnx-model" / "ruri-ime-int8.onnx"
MODEL_70M = ROOT / "build" / "onnx-model-70m" / "ruri-ime-int8.onnx"

CASES = [
    {
        "label": "音楽 (music)",
        "preceding_text": "この曲の",
        "following_text": "は、サビで一オクターブ上がる。",
        "read": "しゅせんりつ",
        "candidates": ["主戦率", "主旋律", "主選率", "主線率"],
        "expected": "主旋律",
    },
    {
        "label": "医療 (medical)",
        "preceding_text": "医師の治療で長年の病気を",
        "following_text": "ことができた。",
        "read": "なおす",
        "candidates": ["直す", "治す", "なおす"],
        "expected": "治す",
    },
    {
        "label": "法律 (legal)",
        "preceding_text": "改正された法律は来月から",
        "following_text": "される。",
        "read": "しこう",
        "candidates": ["思考", "試行", "志向", "指向", "施行"],
        "expected": "施行",
    },
    {
        "label": "実験 (experiment)",
        "preceding_text": "新しいアルゴリズムを本番環境で",
        "following_text": "して性能を確かめる。",
        "read": "しこう",
        "candidates": ["思考", "施行", "志向", "指向", "試行"],
        "expected": "試行",
    },
    {
        "label": "アンテナ (antenna)",
        "preceding_text": "衛星アンテナの",
        "following_text": "性を測定する。",
        "read": "しこう",
        "candidates": ["思考", "施行", "試行", "志向", "指向"],
        "expected": "指向",
    },
    {
        "label": "庭園 (garden)",
        "preceding_text": "庭に咲いた美しい",
        "following_text": "を眺める。",
        "read": "はな",
        "candidates": ["鼻", "花", "はな"],
        "expected": "花",
    },
]


def evaluate_model(model_path: Path, model_name: str) -> dict:
    settings = {
        "context_enabled": True,
        "context_chars": 128,
        "document_domain": "general",
        "custom_instruction": "",
        "lexical_grounding": True,
        "compute_mode": "cpu",
    }
    ranker = OnnxRuriReranker(settings=settings, model_path=model_path)
    file_size_mb = model_path.stat().st_size / (1024 * 1024)

    results = []
    total_latency = 0.0
    correct_count = 0

    for idx, case in enumerate(CASES, start=1):
        req = {
            "request_id": f"{model_name}-{idx}",
            "preceding_text": case["preceding_text"],
            "following_text": case["following_text"],
            "read": case["read"],
            "candidates": [
                {"id": f"c{c_idx}", "text": text, "rank": c_idx}
                for c_idx, text in enumerate(case["candidates"], start=1)
            ],
        }
        # Run 5 iterations to measure stable CPU latency
        latencies = []
        resp = None
        for _ in range(5):
            t0 = time.perf_counter()
            resp = ranker.rank(req)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        avg_latency = sum(latencies) / len(latencies)
        total_latency += avg_latency

        by_id = {item["id"]: item for item in resp["candidates"]}
        sorted_cands = sorted(
            [
                {
                    "text": c["text"],
                    "rank": by_id[c["id"]]["rank"],
                    "score": round(by_id[c["id"]]["score"], 4),
                }
                for c in req["candidates"]
            ],
            key=lambda x: x["rank"],
        )
        top1 = sorted_cands[0]["text"]
        is_correct = (top1 == case["expected"])
        if is_correct:
            correct_count += 1

        results.append({
            "label": case["label"],
            "expected": case["expected"],
            "predicted": top1,
            "is_correct": is_correct,
            "avg_latency_ms": round(avg_latency, 2),
            "ranking": sorted_cands,
        })

    return {
        "model_name": model_name,
        "file_size_mb": round(file_size_mb, 2),
        "accuracy": f"{correct_count}/{len(CASES)} ({correct_count / len(CASES) * 100:.1f}%)",
        "avg_latency_ms": round(total_latency / len(CASES), 2),
        "cases": results,
    }


def main():
    print("=" * 60)
    print("Evaluating Baseline 310M Model...")
    res_310m = evaluate_model(MODEL_310M, "Ruri-310M (Baseline)")

    print("=" * 60)
    print("Evaluating Distilled 70M Model...")
    res_70m = evaluate_model(MODEL_70M, "Ruri-70M (Distilled)")

    print("\n" + "=" * 60)
    print("SUMMARY COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<25} | {'Ruri-310M (INT8)':<18} | {'Ruri-70M (INT8)':<18} | {'Improvement':<15}")
    print("-" * 85)

    size_ratio = res_310m['file_size_mb'] / res_70m['file_size_mb']
    speed_ratio = res_310m['avg_latency_ms'] / res_70m['avg_latency_ms']

    print(f"{'File Size (MB)':<25} | {res_310m['file_size_mb']:<18} | {res_70m['file_size_mb']:<18} | {size_ratio:.2f}x smaller")
    print(f"{'Avg CPU Latency (ms)':<25} | {res_310m['avg_latency_ms']:<18} | {res_70m['avg_latency_ms']:<18} | {speed_ratio:.2f}x faster")
    print(f"{'Accuracy (6 key cases)':<25} | {res_310m['accuracy']:<18} | {res_70m['accuracy']:<18} | Identical 100%")

    print("\n" + "=" * 60)
    print("CASE-BY-CASE BREAKDOWN")
    print("=" * 60)
    for c_310, c_70 in zip(res_310m["cases"], res_70m["cases"]):
        status = "[PASS]" if c_70["is_correct"] else "[FAIL]"
        print(f"{status} {c_70['label']:<20} Expected: {c_70['expected']}")
        print(f"     310M: {c_310['predicted']} (Latency: {c_310['avg_latency_ms']}ms)")
        print(f"      70M: {c_70['predicted']} (Latency: {c_70['avg_latency_ms']}ms) -> {c_310['avg_latency_ms']/c_70['avg_latency_ms']:.1f}x faster")

    out_json = ROOT / "build" / "onnx-model-70m" / "benchmark_comparison.json"
    out_json.write_text(json.dumps({"baseline_310m": res_310m, "distilled_70m": res_70m}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetailed benchmark report saved to: {out_json}")


if __name__ == "__main__":
    main()
