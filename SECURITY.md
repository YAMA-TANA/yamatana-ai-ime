# Security Policy

## Supported versions

The latest public beta is the supported security-update target. Current public releases are unsigned beta builds and are not represented as signed or stable releases.

## Reporting a vulnerability

入力内容、権限昇格、MSIカスタムアクション、TSF/IME登録、Named Pipe、モデル／依存ファイル検証、AI rankerとのIPCに関する問題は、公開Issueへ機密情報や再現用入力を貼らず、GitHubの **Report a vulnerability / Private vulnerability reporting** を使用してください。有効化されていない場合は、個人情報を除いた最小限の内容でIssueを作成し、非公開連絡手段の案内を求めてください。

受領確認の目標は7日以内、初期評価は14日以内です。修正公開前の詳細開示は避けてください。

## Release integrity

- Release AssetsのMSIと同じReleaseにある `SHA256SUMS.txt` を照合してください。
- 現在公開中のBetaは未署名です。
- 将来の署名対象は、公開リポジトリからGitHub Actionsで生成・保存されたRelease成果物に限定します。
- SignPath導入後も、署名前のGitHub artifact、署名request、署名済みartifact、Release Assetの来歴を追跡できる工程を維持します。
- APIキー、証明書、秘密鍵をリポジトリへcommitしません。

## Runtime privacy boundary

Yamatana AI IMEの通常実行時は、IME入力、前後文脈、変換候補、辞書、カスタム指示、AI推論結果を外部サービスへ送信しません。テレメトリ、広告SDK、自動クラッシュ送信も実装していません。詳細は [PRIVACY.md](PRIVACY.md) を参照してください。

## Supply-chain controls

- Mozc forkとupstream revisionは `build-config.json` で固定します。
- 配布用モデルbundleは `model-manifest.json` でURL、サイズ、SHA-256を固定し、検証後のみ利用します。
- 署名・Release workflowで利用する第三者Actionはcommit SHAへ固定します。
- 署名方針とSignPath準備状況は [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md) と [docs/SIGNPATH_READINESS.md](docs/SIGNPATH_READINESS.md) に記録します。
