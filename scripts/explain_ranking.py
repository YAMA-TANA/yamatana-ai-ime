"""Show exactly how an ONNX IME request is scored and ranked."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ranker.onnx_ranker import OnnxRuriReranker


def format_explanation(explanation: dict) -> str:
    context = explanation["context"]
    parameters = explanation["parameters"]
    decision = explanation["decision"]
    lines = [
        f"前方文脈: {context['preceding_text']!r}",
        f"後方文脈: {context['following_text']!r}",
        f"読み: {context['reading']!r}",
        f"文脈信号長: {context['signal_length']}",
        f"計算式: {explanation['formula']}",
        (
            "パラメータ: "
            f"prior_weight={parameters['rank_prior_weight']:.2f}, "
            f"numeric_style={parameters['arabic_numeral_style_bonus']:.2f}"
        ),
        (
            "判定: "
            + ("Mozc 1位を維持" if decision["preserved_mozc_top"] else "AI順位を採用")
        ),
    ]
    if decision["lead_over_mozc"] is not None:
        lines.append(
            "根拠差: "
            f"対Mozc={decision['lead_over_mozc']:.4f}, "
            f"対2位={decision['lead_over_runner']:.4f}"
        )
    if "neural_top_probability" in decision:
        lines.append(
            "AI信頼度: "
            f"softmax={decision['neural_top_probability']:.4f}, "
            f"候補内部文脈={decision['internal_context_length']}"
        )
        lines.append(
            "非線形ゲート: "
            f"softmax>={parameters['high_neural_confidence']:.2f}; "
            "前後両側または候補内部文脈ありなら "
            f"softmax>={parameters['contextual_neural_confidence']:.2f} かつ "
            f"Mozc差>={parameters['contextual_lead_over_mozc']:.2f}; "
            f"外部文脈>={parameters['minimum_external_context']} または "
            f"候補内部文脈>={parameters['minimum_internal_context']}"
        )
    lines.extend(
        ("", "順位  候補  Mozc  モデル素点  表記加点  辞書罰点  順位罰点  最終点")
    )
    for item in explanation["candidates"]:
        lines.append(
            f"{item['output_rank']:>4}  {item['text']}  "
            f"{item['original_rank']:>4}  {item['model_score']:>10.4f}  "
            f"{item['style_bonus']:>8.4f}  "
            f"{item['lexical_penalty']:>8.4f}  "
            f"{item['rank_prior_penalty']:>8.4f}  "
            f"{item['final_score']:>8.4f}"
        )
    selected = explanation["candidates"][0]
    lines.extend(("", f"1位: {selected['text']} ({selected['id']})"))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preceding", default="", help="変換対象より前の文脈")
    parser.add_argument("--following", default="", help="変換対象より後の文脈")
    parser.add_argument("--read", required=True, help="変換対象の読み")
    parser.add_argument(
        "--candidate", action="append", required=True, help="Mozc候補（順位順、複数指定）"
    )
    parser.add_argument("--model", type=Path, default=None, help="使用するONNXモデル")
    parser.add_argument("--compute-mode", choices=("auto", "cpu", "gpu"), default="auto")
    args = parser.parse_args()

    ranker = OnnxRuriReranker(
        settings={
            "compute_mode": args.compute_mode,
            "context_enabled": True,
            "context_chars": 128,
            "document_domain": "general",
            "custom_instruction": "",
            "lexical_grounding": True,
        },
        model_path=args.model,
    )
    request = {
        "request_id": "explain",
        "preceding_text": args.preceding,
        "following_text": args.following,
        "read": args.read,
        "candidates": [
            {"id": f"c{index}", "text": text, "rank": index}
            for index, text in enumerate(args.candidate, start=1)
        ],
    }
    ranker.rank(request)
    print(format_explanation(ranker.last_explanation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
