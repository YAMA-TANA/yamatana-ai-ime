# Yamatana AI IME v2.0.5-beta

## 変更

- AI1とMozc1の差、AI margin、Mozc順位、表記タイプを併用する安全ゲートを更新。
- 読みそのまま候補の条件付きペナルティと実務フレーム補正を追加。
- `API`、数詞・日付・年度・順位、`健診`の候補補完を追加。
- 複数セグメントの文脈連結と公平な推論時間配分を修正。
- 70M ONNX／Tokenizer更新版を同梱し、manifestでSHA-256を固定。

## 検証

- 前文脈210件: 実用正解 210/210 (100.0%)、回帰0、タイムアウト0。
- 厳密120問holdout: 更新70Mは105/120 (87.50%)。
- Python: 65 passed, 2 skipped（loading indicator lifecycleを除外）。
- Mozc AI rewriter native test: 1/1 passed。

厳密holdoutは意図的に難例を集めた別指標であり、詳細は`docs/HOLDOUT_V205_REPORT_JA.md`を参照。
