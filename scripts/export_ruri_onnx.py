"""Export the tuned Ruri reranker for the self-contained Windows runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForSequenceClassification, AutoTokenizer


ROOT = Path(__file__).resolve().parents[1]


class LogitsOnly(torch.nn.Module):
    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        return self.model(input_ids=input_ids, attention_mask=attention_mask).logits


def load_tokenizer(model_dir: Path):
    try:
        return AutoTokenizer.from_pretrained(
            str(model_dir), trust_remote_code=True, fix_mistral_regex=True
        )
    except (TypeError, ValueError):
        return AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)


def export_native_fp16(model_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = load_tokenizer(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir), dtype=torch.float16, trust_remote_code=True
    ).to(device).eval()
    wrapper = LogitsOnly(model).eval()
    pairs = tokenizer(
        ["文書方針: 医学文書。\n文脈「医師が病気を____」に適切な表記を選ぶ。"],
        ["医師が病気を治す"],
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )
    input_ids = pairs["input_ids"].to(device)
    attention_mask = pairs["attention_mask"].to(device)
    fp16_path = output_dir / "ruri-ime-fp16.onnx"
    with torch.inference_mode():
        torch.onnx.export(
            wrapper,
            (input_ids, attention_mask),
            str(fp16_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "sequence"},
                "attention_mask": {0: "batch", 1: "sequence"},
                "logits": {0: "batch"},
            },
            opset_version=18,
            do_constant_folding=True,
            dynamo=False,
        )
    print(f"exported native FP16 model: {fp16_path} ({fp16_path.stat().st_size} bytes)")
    return fp16_path


def export_model(model_dir: Path, output_dir: Path, quantize: bool, reuse_fp32: bool = False) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = load_tokenizer(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(model_dir), dtype=torch.float32, trust_remote_code=True
    ).cpu().eval()
    wrapper = LogitsOnly(model).eval()

    pairs = tokenizer(
        ["文書方針: 医学文書。\n文脈「医師が病気を____」に適切な表記を選ぶ。"],
        ["医師が病気を治す"],
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )
    float_path = output_dir / "ruri-ime-fp32.onnx"
    if not reuse_fp32 or not float_path.exists():
        with torch.inference_mode():
            torch.onnx.export(
                wrapper,
                (pairs["input_ids"], pairs["attention_mask"]),
                str(float_path),
                input_names=["input_ids", "attention_mask"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch", 1: "sequence"},
                    "attention_mask": {0: "batch", 1: "sequence"},
                    "logits": {0: "batch"},
                },
                opset_version=18,
                do_constant_folding=True,
                dynamo=False,
            )

    fp16_path = output_dir / "ruri-ime-fp16.onnx"

    final_path = float_path
    if quantize:
        final_path = output_dir / "ruri-ime-int8.onnx"
        quantize_dynamic(
            model_input=str(float_path),
            model_output=str(final_path),
            weight_type=QuantType.QInt8,
            per_channel=True,
            reduce_range=False,
            extra_options={"MatMulConstBOnly": True},
        )

    session = ort.InferenceSession(str(final_path), providers=["CPUExecutionProvider"])
    ort_logits = session.run(
        ["logits"],
        {
            "input_ids": pairs["input_ids"].numpy().astype(np.int64),
            "attention_mask": pairs["attention_mask"].numpy().astype(np.int64),
        },
    )[0]
    with torch.inference_mode():
        torch_logits = wrapper(pairs["input_ids"], pairs["attention_mask"]).numpy()
    report = {
        "model": str(final_path),
        "bytes": final_path.stat().st_size,
        "fp32_bytes": float_path.stat().st_size,
        "fp16_bytes": fp16_path.stat().st_size if fp16_path.exists() else None,
        "torch_logits": torch_logits.reshape(-1).tolist(),
        "onnx_logits": np.asarray(ort_logits).reshape(-1).tolist(),
        "absolute_error": np.abs(torch_logits - ort_logits).reshape(-1).tolist(),
    }
    (output_dir / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return final_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=ROOT / "models" / "ruri-v3-reranker-310m-ime-tuned",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "build" / "onnx-model",
    )
    parser.add_argument("--no-quantize", action="store_true")
    parser.add_argument("--reuse-fp32", action="store_true")
    parser.add_argument("--fp16-only", action="store_true")
    args = parser.parse_args()
    if args.fp16_only:
        export_native_fp16(args.model_dir.resolve(), args.output_dir.resolve())
        return 0
    export_model(
        args.model_dir.resolve(), args.output_dir.resolve(),
        not args.no_quantize, reuse_fp32=args.reuse_fp32,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
