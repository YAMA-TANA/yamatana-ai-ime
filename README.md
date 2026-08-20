# Yamatana AI IME (MOZC Ver)

Yamatana AI IMEは、Mozcの変換候補をローカルAI rerankerで並べ替えるWindows向け日本語IMEです。文脈、文書分野、ユーザー辞書相当の語彙情報を変換判断に使いながら、入力内容を外部へ送信しません。

> **Beta / 未署名** — `v0.1.0-beta` は検証用の未署名Betaです。Windowsの警告が表示される場合があります。現在はSignPath Foundationによる署名を申請する前段階であり、署名済みであるかのような表示は行いません。

## 特徴

- Mozcベースの通常変換を保ったまま、AI有効時だけ候補を再順位付け
- Ruri v3 rerankerをIME向けLoRAで調整し、ONNX Runtimeで実行
- 入力、前後文脈、カスタム指示、辞書、推論をPC内だけで処理
- タスクバートレイからAI ON/OFF、文脈保持、文書分野、カスタム指示、CPU/GPU設定を変更
- AIは初期OFF。トレイは状態切替と設定のため起動しますが、OFF時はAIモデルをロードしません
- 医学・法律・技術などの文書分野を指定し、その指示をrerankerへ渡せる
- AIが失敗・停止してもMozcの候補を使うフェイルセーフ設計

## 対応OSと必要環境

- Windows 10 22H2（build 19045）またはWindows 11、x64
- 8GB RAM以上（16GB推奨）
- 空き容量 約3GB
- CPU実行対応。GPU実行はDirectML対応GPUと対応ランタイムがある場合に利用可能
- インストールには管理者権限が必要

詳細は [システム要件](docs/SYSTEM_REQUIREMENTS_JA.md) を参照してください。

## インストール

1. [Releases](https://github.com/YAMA-TANA/yamatana-ai-ime/releases) から最新の `.msi` と `SHA256SUMS.txt` をダウンロードします。
2. PowerShellで `Get-FileHash .\Yamatana-AI-IME-MOZC-Ver-0.1.0-beta-x64.msi -Algorithm SHA256` を実行し、公開ハッシュと一致することを確認します。
3. MSIをダブルクリックし、プライバシー説明を確認してインストールします。
4. サインアウトまたは再起動後、`Win + Space` で **Yamatana AI IME (MOZC Ver)** を選択します。
5. 通知領域のYamatanaアイコンを開き、必要なときだけ **AIをON** にします。初期状態はOFFです。アイコンが隠れている場合は、タスクバーの `^` を開いてください。

本ソフトはMSIXではありません。既存のMozc TSF登録順序を維持したMSIで配布します。

## AI設定

トレイメニューの「設定」から、前後文脈の保持量、文書分野、任意のカスタム指示、辞書認識、CPU/GPU/自動選択を変更できます。カスタム指示には、変換判断に必要な内容だけを入力してください。設定と入力内容はローカルに保存・処理されます。

## アンインストール

Windowsの **設定 → アプリ → インストールされているアプリ → Yamatana AI IME (MOZC Ver) → アンインストール** を選びます。完了後にサインアウトまたは再起動してください。

## プライバシー

アプリ本体は入力文字、文脈、辞書、AI処理結果を外部へ送信せず、テレメトリも実装していません。詳細は [PRIVACY.md](PRIVACY.md) を参照してください。GitHubからリリースやモデルを取得する操作は、GitHub側の通常のアクセスログ・プライバシーポリシーの対象です。

## 開発と再現可能性

大容量ONNXモデルはGit履歴に含めません。[model-manifest.json](model-manifest.json) に固定したリリース資産を [fetch-model.ps1](scripts/fetch-model.ps1) が取得し、SHA-256一致時のみ展開します。Windowsワークフローはテスト、Mozc/AIランタイムのビルド、MSI生成、ハッシュ生成を自動化します。

開発参加方法は [CONTRIBUTING.md](CONTRIBUTING.md)、脆弱性報告は [SECURITY.md](SECURITY.md) を参照してください。

## ライセンス

Yamatana独自部分は [Apache License 2.0](LICENSE) です。Mozc、Ruri/ONNXモデル、辞書、同梱ライブラリには各上流ライセンスが適用されます。詳細は [NOTICE](NOTICE) と [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) を参照してください。

## Code signing policy

署名対象は、保護されたリリース工程でソースから生成され、GitHub Actionsの成果物として保存されたDLL / EXE / MSIだけです。現在のBetaは未署名です。方針とSignPath Foundation申請準備は [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md) に記載しています。

