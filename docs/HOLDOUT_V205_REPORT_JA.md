# v2.0.5-beta 70Mモデル更新・holdout検証

2026-09-09に、ローカルの70Mモデル／Tokenizer更新版を、現行のAI安全ゲート・候補補完・文脈処理を含む状態で検証した。

## モデル差分

| artifact | 旧版SHA-256 | 更新版SHA-256 |
|---|---|---|
| `ruri-ime-int8.onnx` | `45CF8E81E77A6C534D19CEDB6C9291DE8F7D0F791E24B229D7542B81B0FF37D4` | `A46196C7220340416D81F43C3F1E02FFF6C084F0C15E620323825B9B1090EED8` |
| `ruri-ime-fp16.onnx` | `4EFC910770388CEAAA190FF69CC748B4A2C2FB1C1E3B616BDC9B7DC14F33EE77` | `2F854E38B9F6F4053377E427DCE2F12382CB97E4E6977DD7521D844F3AF89C13` |
| `tokenizer.json` | `7213428EFF7B2DD113C725E20E1D2711926B3AC4CD1AE22303B106CD37AD8F38` | `DE5307DD1171C748294224C016189C0FA364168AD4560736EC2BA5EC5A032657` |

## 厳密120問holdout

`scripts/create_and_evaluate_holdout_120.py` の、学習データとの完全一致を検査する120問セットをCPU INT8で実行した。

| 指標 | 旧70M | 更新70M |
|---|---:|---:|
| 正解 | 103/120 (85.83%) | **105/120 (87.50%)** |
| 平均レイテンシ | - | 18.03 ms |

更新版は旧版より2問改善した。これは難例を意図的に集めた厳密holdoutであり、前文脈210件の実用ベンチ（自然な表記揺れを許容）とは別の指標である。前文脈210件は実用正解210/210、回帰0件、タイムアウト0件だった。

## 配布固定

更新版のbundle、各ファイル、Tokenizer、manifestのSHA-256を一致確認済み。配布bundleは`v2.0.5-beta-70m`として公開する。
