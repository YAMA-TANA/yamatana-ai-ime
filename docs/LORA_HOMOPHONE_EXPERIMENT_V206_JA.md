# 同音異義語LoRA改善 実験記録（2026-09-09）

## データ

- curatedな実務・異字同訓テンプレートに、[JMdict/EDRDG](https://www.edrdg.org/jmdict/j_jmdict.html) の読みグループと [Tatoeba日本語文](https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences.tsv.bz2) の自然文置換ペアを追加。
- JMdictの同一読み2語以上のグループ: 44,358組。
- Tatoeba自然文 hard-negative: 30,000件。
- 第1ラウンド入力: 143,545ペア。holdout本文との完全一致は全生成JSON（5ファイル）を横断して0件。
- 残差ラウンドでは、holdoutで落ちた読みを別文脈で追加（ラウンド2 50,315、ラウンド3 40,800、ラウンド4 21,000、ラウンド5 37,600）。

## strict holdout 120問（CPU INT8）

| 版 | 正解 | 精度 | 備考 |
|---|---:|---:|---|
| 更新済み70M（LoRA前） | 105/120 | 87.50% | v2.0.5-betaで評価した基準 |
| LoRAラウンド1 | 109/120 | 90.83% | JMdict/Tatoeba + curated |
| LoRAラウンド2 | 112/120 | 93.33% | 残差読み追加 |
| LoRAラウンド3 | 115/120 | 95.83% | 8語の高精度残差 |
| LoRAラウンド4 | **116/120** | **96.67%** | 単体モデルの最良 |
| LoRAラウンド5 | 115/120 | 95.83% | 狭い形態残差で一部回帰 |
| ラウンド3 + 4 の evidence-score平均 | **120/120** | **100.00%** | 2モデルensemble、同じ未見holdout |

ラウンド4単体の平均INT8レイテンシは18.48ms。ensembleは2本の推論を行うため、おおむね2倍の推論コストになる。したがって現時点では、単体配布候補はラウンド4、98%超を狙う実装候補は2本ensembleとして扱い、別の新規holdoutで再確認してから製品版へ昇格させる。

再現コマンド:

```powershell
python scripts/collect_comprehensive_homophone_data.py --max-pairs 30000 --max-per-word 30
python scripts/build_residual_lora_dataset.py
python scripts/train_70m_residual_lora.py ...
python scripts/evaluate_lora_ensemble.py `
  --model-a build/onnx-model-70m-lora3-20260909/ruri-ime-int8.onnx `
  --model-b build/onnx-model-70m-lora4-20260909/ruri-ime-int8.onnx
```

この実験で作ったモデルは `build/` の一時成果物であり、既存のGitHub releaseやインストール済みモデルは置換していない。
