"""Memory-optimized, ultra-fast LoRA fine-tuning for Ruri-v3-reranker-310m on Japanese IME Disambiguation."""

from __future__ import annotations

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
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_cosine_schedule_with_warmup
from peft import LoraConfig, get_peft_model, TaskType


class IMERerankerDataset(Dataset):
    def __init__(self, data_path: Path):
        self.samples = json.loads(data_path.read_text(encoding="utf-8"))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.samples[idx]


def collate_fn(batch: List[Dict[str, Any]], tokenizer: Any) -> Dict[str, torch.Tensor]:
    queries = [b["query"] for b in batch]
    positives = [b["positive"] for b in batch]
    negatives = [b["negative"] for b in batch]

    pos_enc = tokenizer(
        queries,
        positives,
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors="pt",
    )

    neg_enc = tokenizer(
        queries,
        negatives,
        padding=True,
        truncation=True,
        max_length=128,
        return_tensors="pt",
    )

    return {
        "pos_input_ids": pos_enc["input_ids"],
        "pos_attention_mask": pos_enc["attention_mask"],
        "neg_input_ids": neg_enc["input_ids"],
        "neg_attention_mask": neg_enc["attention_mask"],
    }


def train() -> int:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})", flush=True)

    base_model_path = ROOT / "models" / "ruri-v3-reranker-310m"
    output_dir = ROOT / "models" / "ruri-v3-reranker-310m-ime-lora"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading Base Tokenizer and Model from {base_model_path} in bfloat16...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(str(base_model_path), trust_remote_code=True)
    base_model = AutoModelForSequenceClassification.from_pretrained(
        str(base_model_path),
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        trust_remote_code=True,
    ).to(device)

    print("Configuring PEFT LoRA on ModernBert Wqkv, Wo, Wi layers...", flush=True)
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=["Wqkv", "Wo", "Wi"],
    )

    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # Load Massive Combined Dataset
    train_path = ROOT / "integration" / "ime_combined_stress_train_30k.json"
    val_path = ROOT / "integration" / "ime_massive_val_2k.json"

    train_dataset = IMERerankerDataset(train_path)
    val_dataset = IMERerankerDataset(val_path)

    batch_size = 16
    grad_accum_steps = 4
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, tokenizer),
        pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, tokenizer),
        pin_memory=True,
    )

    epochs = 2
    lr = 3e-4
    margin = 1.0
    loss_fn = nn.MarginRankingLoss(margin=margin)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_steps = (len(train_loader) // grad_accum_steps) * epochs
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=int(total_steps * 0.05), num_training_steps=total_steps)

    print(f"\nStarting Memory-Safe LoRA Fine-Tuning for {epochs} epochs ({total_steps} optimizer steps)...", flush=True)
    model.train()

    t_start = time.time()
    for epoch in range(epochs):
        total_loss = 0.0
        step_count = 0
        correct_count = 0
        total_pairs = 0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            pos_inputs = {
                "input_ids": batch["pos_input_ids"].to(device),
                "attention_mask": batch["pos_attention_mask"].to(device),
            }
            neg_inputs = {
                "input_ids": batch["neg_input_ids"].to(device),
                "attention_mask": batch["neg_attention_mask"].to(device),
            }

            pos_logits = model(**pos_inputs).logits.squeeze(-1).float()
            neg_logits = model(**neg_inputs).logits.squeeze(-1).float()
            targets = torch.ones_like(pos_logits)

            loss = loss_fn(pos_logits, neg_logits, targets) / grad_accum_steps
            loss.backward()

            with torch.no_grad():
                correct_count += (pos_logits > neg_logits).sum().item()
                total_pairs += len(pos_logits)
                total_loss += (loss.item() * grad_accum_steps)
                step_count += 1

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            if (step + 1) % (50 * grad_accum_steps) == 0 or (step + 1) == len(train_loader):
                avg_loss = total_loss / step_count
                acc = (correct_count / total_pairs) * 100
                lr_curr = scheduler.get_last_lr()[0]
                elapsed = time.time() - t_start
                print(f"Epoch [{epoch+1}/{epochs}] Step [{step+1}/{len(train_loader)}] | Loss: {avg_loss:.4f} | Margin Acc: {acc:.2f}% | LR: {lr_curr:.2e} | Elapsed: {elapsed:.1f}s", flush=True)
                torch.cuda.empty_cache()

        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for v_batch in val_loader:
                v_pos = {"input_ids": v_batch["pos_input_ids"].to(device), "attention_mask": v_batch["pos_attention_mask"].to(device)}
                v_neg = {"input_ids": v_batch["neg_input_ids"].to(device), "attention_mask": v_batch["neg_attention_mask"].to(device)}
                p_out = model(**v_pos).logits.squeeze(-1).float()
                n_out = model(**v_neg).logits.squeeze(-1).float()
                v_targets = torch.ones_like(p_out)
                v_l = loss_fn(p_out, n_out, v_targets)
                val_loss += v_l.item()
                val_correct += (p_out > n_out).sum().item()
                val_total += len(p_out)

        val_acc = (val_correct / val_total) * 100
        val_loss_avg = val_loss / len(val_loader)
        print(f"\n>>> Epoch {epoch+1} Validation Loss: {val_loss_avg:.4f} | Validation Margin Accuracy: {val_acc:.2f}%\n", flush=True)
        model.train()

    print(f"Saving LoRA Adapter Checkpoint to {output_dir}...", flush=True)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print("[SUCCESS] LoRA training complete and checkpoint saved!", flush=True)

    # Merge LoRA weights into standalone model
    merged_dir = ROOT / "models" / "ruri-v3-reranker-310m-ime-tuned"
    merged_dir.mkdir(parents=True, exist_ok=True)
    print(f"Merging LoRA weights into standalone checkpoint at {merged_dir}...", flush=True)
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(str(merged_dir))
    tokenizer.save_pretrained(str(merged_dir))
    print(f"[SUCCESS] Standalone Merged Model saved to: {merged_dir}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(train())
