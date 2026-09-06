"""Knowledge Distillation from Ruri-v3-310m-ime-tuned (Teacher) to Ruri-v3-70m (Student).

Combines:
1. Hard MarginRankingLoss (task discrimination)
2. Margin-MSE Loss (replicates teacher's score gaps between positive and negative candidates)
3. Soft-target KL Divergence (smooth candidate probability distribution matching)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    ModernBertForSequenceClassification,
    get_cosine_schedule_with_warmup,
)


class IMERerankerDataset(Dataset):
    def __init__(self, data_path: Path):
        self.samples = json.loads(data_path.read_text(encoding="utf-8"))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


def collate_fn(batch: List[Dict[str, Any]], tokenizer: Any, max_length: int = 128) -> Dict[str, torch.Tensor]:
    queries = [b["query"] for b in batch]
    positives = [b["positive"] for b in batch]
    negatives = [b["negative"] for b in batch]

    pos_enc = tokenizer(
        queries,
        positives,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )

    neg_enc = tokenizer(
        queries,
        negatives,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt",
    )

    return {
        "pos_input_ids": pos_enc["input_ids"],
        "pos_attention_mask": pos_enc["attention_mask"],
        "neg_input_ids": neg_enc["input_ids"],
        "neg_attention_mask": neg_enc["attention_mask"],
    }


def distill(
    teacher_path: Path,
    student_base_path: Path,
    output_dir: Path,
    train_path: Path,
    val_path: Path,
    epochs: int = 2,
    batch_size: int = 16,
    grad_accum_steps: int = 4,
    lr: float = 2e-4,
    margin: float = 1.0,
    kd_temp: float = 2.0,
    kd_alpha: float = 1.0,
    kd_soft_alpha: float = 0.5,
    max_length: int = 128,
) -> int:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})", flush=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load Tokenizer
    print(f"Loading tokenizer from {teacher_path}...", flush=True)
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(teacher_path), trust_remote_code=True, fix_mistral_regex=False)
    except (TypeError, ValueError):
        tokenizer = AutoTokenizer.from_pretrained(str(teacher_path), trust_remote_code=True)

    # 2. Load Teacher Model (Fixed)
    print(f"Loading Teacher Model from {teacher_path} in bfloat16...", flush=True)
    teacher = AutoModelForSequenceClassification.from_pretrained(
        str(teacher_path),
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        trust_remote_code=True,
    ).to(device)
    teacher.eval()
    for param in teacher.parameters():
        param.requires_grad = False
    teacher_params = sum(p.numel() for p in teacher.parameters())
    print(f"Teacher loaded ({teacher_params:,} parameters, frozen).", flush=True)

    # 3. Load Student Model
    print(f"Loading Student Model from {student_base_path} in bfloat16...", flush=True)
    try:
        student = ModernBertForSequenceClassification.from_pretrained(
            str(student_base_path),
            num_labels=1,
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        ).to(device)
    except Exception:
        student = AutoModelForSequenceClassification.from_pretrained(
            str(student_base_path),
            num_labels=1,
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
            trust_remote_code=True,
        ).to(device)
    student.train()
    student_params = sum(p.numel() for p in student.parameters())
    print(f"Student loaded ({student_params:,} parameters, {student_params / teacher_params * 100:.1f}% size of teacher).", flush=True)

    # 4. Load Datasets
    print(f"Loading datasets:\n  Train: {train_path}\n  Val: {val_path}...", flush=True)
    train_dataset = IMERerankerDataset(train_path)
    val_dataset = IMERerankerDataset(val_path)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, tokenizer, max_length=max_length),
        pin_memory=(device == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, tokenizer, max_length=max_length),
        pin_memory=(device == "cuda"),
    )

    # 5. Losses, Optimizer, Scheduler
    hard_loss_fn = nn.MarginRankingLoss(margin=margin)
    kl_loss_fn = nn.KLDivLoss(reduction="batchmean")

    optimizer = torch.optim.AdamW(student.parameters(), lr=lr, weight_decay=0.01)
    total_steps = (len(train_loader) // grad_accum_steps) * epochs
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=max(10, int(total_steps * 0.05)),
        num_training_steps=total_steps,
    )

    print(f"\nStarting Distillation Training for {epochs} epochs ({total_steps} optimizer steps)...", flush=True)
    print(f"Effective batch size: {batch_size * grad_accum_steps} (batch={batch_size}, accum={grad_accum_steps})", flush=True)
    print(f"Distillation weights: task=1.0, margin_mse={kd_alpha}, soft_kd={kd_soft_alpha} (T={kd_temp})\n", flush=True)

    best_val_acc = 0.0
    t_start = time.time()

    for epoch in range(epochs):
        student.train()
        total_loss = 0.0
        total_task_loss = 0.0
        total_kd_loss = 0.0
        step_count = 0
        correct_count = 0
        total_pairs = 0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            pos_in = {
                "input_ids": batch["pos_input_ids"].to(device),
                "attention_mask": batch["pos_attention_mask"].to(device),
            }
            neg_in = {
                "input_ids": batch["neg_input_ids"].to(device),
                "attention_mask": batch["neg_attention_mask"].to(device),
            }

            # Teacher forward pass (inference mode)
            with torch.inference_mode():
                t_pos_logits = teacher(**pos_in).logits.squeeze(-1).float()
                t_neg_logits = teacher(**neg_in).logits.squeeze(-1).float()
                t_delta = t_pos_logits - t_neg_logits

            # Student forward pass
            s_pos_logits = student(**pos_in).logits.squeeze(-1).float()
            s_neg_logits = student(**neg_in).logits.squeeze(-1).float()
            s_delta = s_pos_logits - s_neg_logits

            # 1. Hard margin loss
            targets = torch.ones_like(s_pos_logits)
            l_hard = hard_loss_fn(s_pos_logits, s_neg_logits, targets)

            # 2. Margin-MSE loss (teaches exact preference score gaps)
            l_margin_mse = torch.mean((s_delta - t_delta) ** 2)

            # 3. Soft-target KL divergence
            t_pair = torch.stack([t_pos_logits, t_neg_logits], dim=-1) / kd_temp
            s_pair = torch.stack([s_pos_logits, s_neg_logits], dim=-1) / kd_temp
            p_teacher = torch.softmax(t_pair, dim=-1)
            log_p_student = torch.log_softmax(s_pair, dim=-1)
            l_soft_kd = (kd_temp ** 2) * kl_loss_fn(log_p_student, p_teacher)

            batch_loss = l_hard + (kd_alpha * l_margin_mse) + (kd_soft_alpha * l_soft_kd)
            (batch_loss / grad_accum_steps).backward()

            with torch.no_grad():
                correct_count += (s_pos_logits > s_neg_logits).sum().item()
                total_pairs += len(s_pos_logits)
                total_loss += batch_loss.item()
                total_task_loss += l_hard.item()
                total_kd_loss += (kd_alpha * l_margin_mse + kd_soft_alpha * l_soft_kd).item()
                step_count += 1

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(student.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            if (step + 1) % (50 * grad_accum_steps) == 0 or (step + 1) == len(train_loader):
                avg_loss = total_loss / step_count
                avg_hard = total_task_loss / step_count
                avg_kd = total_kd_loss / step_count
                acc = (correct_count / total_pairs) * 100
                lr_curr = scheduler.get_last_lr()[0]
                elapsed = time.time() - t_start
                print(
                    f"Epoch [{epoch+1}/{epochs}] Step [{step+1}/{len(train_loader)}] | "
                    f"Loss: {avg_loss:.4f} (Hard: {avg_hard:.4f}, KD: {avg_kd:.4f}) | "
                    f"Train Acc: {acc:.2f}% | LR: {lr_curr:.2e} | Elapsed: {elapsed:.1f}s",
                    flush=True,
                )
                if device == "cuda":
                    torch.cuda.empty_cache()

        # Validation Phase
        student.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        teacher_val_correct = 0

        with torch.no_grad():
            for v_batch in val_loader:
                v_pos = {
                    "input_ids": v_batch["pos_input_ids"].to(device),
                    "attention_mask": v_batch["pos_attention_mask"].to(device),
                }
                v_neg = {
                    "input_ids": v_batch["neg_input_ids"].to(device),
                    "attention_mask": v_batch["neg_attention_mask"].to(device),
                }
                # Student
                sp_out = student(**v_pos).logits.squeeze(-1).float()
                sn_out = student(**v_neg).logits.squeeze(-1).float()
                v_targets = torch.ones_like(sp_out)
                v_l = hard_loss_fn(sp_out, sn_out, v_targets)
                val_loss += v_l.item()
                val_correct += (sp_out > sn_out).sum().item()
                val_total += len(sp_out)

                # Teacher comparison
                tp_out = teacher(**v_pos).logits.squeeze(-1).float()
                tn_out = teacher(**v_neg).logits.squeeze(-1).float()
                teacher_val_correct += (tp_out > tn_out).sum().item()

        val_acc = (val_correct / val_total) * 100
        teacher_acc = (teacher_val_correct / val_total) * 100
        val_loss_avg = val_loss / len(val_loader)
        print(
            f"\n>>> Epoch {epoch+1} Validation Results:\n"
            f"    Student Accuracy: {val_acc:.2f}%\n"
            f"    Teacher Accuracy: {teacher_acc:.2f}%\n"
            f"    Student/Teacher Ratio: {(val_acc / teacher_acc) * 100:.2f}%\n"
            f"    Validation Loss: {val_loss_avg:.4f}\n",
            flush=True,
        )

        # Save checkpoint if best
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            print(f"New Best Accuracy! Saving checkpoint to {output_dir}...", flush=True)
            student.save_pretrained(str(output_dir))
            tokenizer.save_pretrained(str(output_dir))
            print(f"[SUCCESS] Distilled student saved with {val_acc:.2f}% accuracy!\n", flush=True)

    print(f"\n========================================================")
    print(f"Distillation complete! Best Val Accuracy: {best_val_acc:.2f}%")
    print(f"Model saved to: {output_dir}")
    print(f"========================================================\n", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Distill Ruri-310M to Ruri-70M for AI IME")
    parser.add_argument("--teacher-path", type=Path, default=ROOT / "models" / "ruri-v3-reranker-310m-ime-tuned")
    parser.add_argument("--student-base-path", type=Path, default=ROOT / "models" / "ruri-v3-70m-base")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "models" / "ruri-v3-70m-ime-distilled")
    parser.add_argument("--train-path", type=Path, default=ROOT / "integration" / "ime_combined_stress_train_30k.json")
    parser.add_argument("--val-path", type=Path, default=ROOT / "integration" / "ime_massive_val_2k.json")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--grad-accum-steps", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--margin", type=float, default=1.0)
    parser.add_argument("--kd-temp", type=float, default=2.0)
    parser.add_argument("--kd-alpha", type=float, default=1.0)
    parser.add_argument("--kd-soft-alpha", type=float, default=0.5)
    parser.add_argument("--max-length", type=int, default=128)
    args = parser.parse_args()

    return distill(
        teacher_path=args.teacher_path.resolve(),
        student_base_path=args.student_base_path.resolve(),
        output_dir=args.output_dir.resolve(),
        train_path=args.train_path.resolve(),
        val_path=args.val_path.resolve(),
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum_steps,
        lr=args.lr,
        margin=args.margin,
        kd_temp=args.kd_temp,
        kd_alpha=args.kd_alpha,
        kd_soft_alpha=args.kd_soft_alpha,
        max_length=args.max_length,
    )


if __name__ == "__main__":
    raise SystemExit(main())
