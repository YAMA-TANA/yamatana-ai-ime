# Yamatana AI IME (MOZC Ver) v0.1.0-beta

最初の公開Betaです。

## 重要

このReleaseのMSI、DLL、EXEは**未署名**です。SignPath Foundationにはまだ採択・接続されていません。`SHA256SUMS.txt` を照合し、Betaであることを理解した検証環境で使用してください。

## 内容

- Mozcベース日本語IME
- ローカルRuri/LoRA ONNX reranker
- タスクバートレイからのAI ON/OFF（初期OFF）
- 文脈保持、辞書認識、文書分野、カスタム指示、CPU/GPU設定
- 初回ガイド、MSIインストール、通常のアンインストール
- 入力・文脈の外部送信なし、テレメトリなし

## 既知の制限

- 未署名のためWindowsの警告が表示されることがあります。
- Betaのため誤変換やアプリ互換性の問題があり得ます。
- DirectML GPU実行はGPU・ドライバー・ランタイム構成に依存します。利用できない場合はCPUを選択してください。

