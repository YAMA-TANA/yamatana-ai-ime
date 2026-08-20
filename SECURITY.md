# Security Policy

## Supported versions

現在は最新Betaだけをセキュリティ更新対象とします。Betaは未署名であり、正式な安定版ではありません。

## Reporting a vulnerability

入力内容、権限昇格、MSIカスタムアクション、Named Pipe、モデル／依存ファイル検証に関する問題は、公開Issueへ機密情報や再現用入力を貼らず、GitHubの **Report a vulnerability / Private vulnerability reporting** を使用してください。有効化されていない場合は、個人情報を除いた最小限の内容でIssueを作成し、非公開連絡手段の案内を求めてください。

受領確認の目標は7日以内、初期評価は14日以内です。修正公開前の詳細開示は避けてください。

## Release integrity

- Release AssetsのMSIと `SHA256SUMS.txt` を照合してください。
- `v0.1.0-beta` は未署名です。
- 将来の署名対象はGitHub Actionsで生成・保存されたRelease成果物に限定します。
- APIキー、証明書、秘密鍵をリポジトリへcommitしません。

