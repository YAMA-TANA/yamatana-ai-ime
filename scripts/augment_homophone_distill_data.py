"""Augment distillation training data with targeted Japanese homophone pairs formatted for IME inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

TARGET_HOMOPHONE_CONTEXTS = [
    # しこう (思考, 施行, 試行, 志向, 指向)
    {
        "reading": "しこう",
        "prefix": "新しいアルゴリズムを本番環境で",
        "suffix": "して性能を確かめる。",
        "pos": "試行",
        "negs": ["思考", "施行", "志向", "指向"],
        "domain": "IT・ソフトウェア文書として、技術用語、製品名、コード周辺の表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "新機能を実験的に",
        "suffix": "する。",
        "pos": "試行",
        "negs": ["思考", "施行", "志向", "指向"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "衛星アンテナの",
        "suffix": "性を測定する。",
        "pos": "指向",
        "negs": ["思考", "施行", "試行", "志向"],
        "domain": "IT・ソフトウェア文書として、技術用語、製品名、コード周辺の表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "マイクの",
        "suffix": "パターンを調整する。",
        "pos": "指向",
        "negs": ["思考", "施行", "試行", "志向"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "改正された法律は来月から",
        "suffix": "される。",
        "pos": "施行",
        "negs": ["思考", "試行", "志向", "指向"],
        "domain": "法律・行政文書として、法令、契約、制度に適切な正式表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "新しい条例を来年度から",
        "suffix": "する予定だ。",
        "pos": "施行",
        "negs": ["思考", "試行", "志向", "指向"],
        "domain": "法律・行政文書として、法令、契約、制度に適切な正式表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "深く論理的に",
        "suffix": "を巡らせる。",
        "pos": "思考",
        "negs": ["施行", "試行", "志向", "指向"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "哲学的な",
        "suffix": "を深める。",
        "pos": "思考",
        "negs": ["施行", "試行", "志向", "指向"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "消費者の健康",
        "suffix": "が高まっている。",
        "pos": "志向",
        "negs": ["思考", "施行", "試行", "指向"],
        "domain": "ビジネス文書として、簡潔で正式な表記と一般的な業務用語を優先する。",
    },
    {
        "reading": "しこう",
        "prefix": "若者の海外",
        "suffix": "が強まる。",
        "pos": "志向",
        "negs": ["思考", "施行", "試行", "指向"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    # なおす (治す, 直す)
    {
        "reading": "なおす",
        "prefix": "医師の治療で長年の病気を",
        "suffix": "ことができた。",
        "pos": "治す",
        "negs": ["直す"],
        "domain": "医学・医療文書として、疾患名、解剖、薬剤、治療に適切な専門表記を優先する。",
    },
    {
        "reading": "なおす",
        "prefix": "虫歯の痛みを歯医者で",
        "suffix": "。",
        "pos": "治す",
        "negs": ["直す"],
        "domain": "医学・医療文書として、疾患名、解剖、薬剤、治療に適切な専門表記を優先する。",
    },
    {
        "reading": "なおす",
        "prefix": "狂った時計の時刻を正しく",
        "suffix": "。",
        "pos": "直す",
        "negs": ["治す"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "なおす",
        "prefix": "プログラムのバグを",
        "suffix": "。",
        "pos": "直す",
        "negs": ["治す"],
        "domain": "IT・ソフトウェア文書として、技術用語、製品名、コード周辺の表記を優先する。",
    },
    # しゅせんりつ (主旋律, 主戦率)
    {
        "reading": "しゅせんりつ",
        "prefix": "この曲の",
        "suffix": "は、サビで一オクターブ上がる。",
        "pos": "主旋律",
        "negs": ["主戦率", "主選率", "主線率"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "しゅせんりつ",
        "prefix": "ピアノの美しい",
        "suffix": "がホールに響く。",
        "pos": "主旋律",
        "negs": ["主戦率", "主選率", "主線率"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    # しゅうかんし (週刊誌, 週間誌)
    {
        "reading": "しゅうかんし",
        "prefix": "出張のたびに買っていたので、いつの間にか",
        "suffix": "を読む習慣が付いた。",
        "pos": "週刊誌",
        "negs": ["週間誌"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    # きかい (機械, 機会, 器械)
    {
        "reading": "きかい",
        "prefix": "電子工学の分野において、計算",
        "suffix": "の小型化が進んだ。",
        "pos": "機械",
        "negs": ["機会", "器械"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "きかい",
        "prefix": "この貴重な",
        "suffix": "を逃さずに挑戦する。",
        "pos": "機会",
        "negs": ["機械", "器械"],
        "domain": "ビジネス文書として、簡潔で正式な表記と一般的な業務用語を優先する。",
    },
    # はな (花, 鼻)
    {
        "reading": "はな",
        "prefix": "庭に咲いた美しい",
        "suffix": "を眺める。",
        "pos": "花",
        "negs": ["鼻"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
    {
        "reading": "はな",
        "prefix": "象は",
        "suffix": "がとても長い動物だ。",
        "pos": "鼻",
        "negs": ["花"],
        "domain": "自然で一般的な日本語として、文脈に合う表記を優先する。",
    },
]


def create_augmented_dataset() -> Path:
    base_train = json.loads((ROOT / "integration" / "ime_combined_stress_train_30k.json").read_text(encoding="utf-8"))
    augmented_samples: List[Dict[str, Any]] = []

    for entry in TARGET_HOMOPHONE_CONTEXTS:
        reading = entry["reading"]
        prefix = entry["prefix"]
        suffix = entry["suffix"]
        pos = entry["pos"]
        domain = entry["domain"]
        query = (
            f"文書方針: {domain}\n"
            f"文脈「{prefix}____{suffix}」に最も適切な表記を選びなさい。"
        )
        pos_doc = f"{prefix}{pos}{suffix}"
        for neg in entry["negs"]:
            neg_doc = f"{prefix}{neg}{suffix}"
            # Over-sample the prompt-matched hard pairs
            for _ in range(30):
                augmented_samples.append({
                    "reading": reading,
                    "query": query,
                    "positive": pos_doc,
                    "negative": neg_doc,
                })

    print(f"Generated {len(augmented_samples)} prompt-matched hard homophone training pairs.")
    combined = augmented_samples + base_train
    print(f"Combined total training dataset size: {len(combined):,}")

    out_path = ROOT / "integration" / "ime_augmented_train.json"
    out_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SUCCESS] Augmented dataset saved to {out_path}")
    return out_path


if __name__ == "__main__":
    create_augmented_dataset()
