# Code signing policy

## Current status

`v0.1.0-beta` は未署名です。本プロジェクトは公開OSSとして実リリースと保守履歴を作った後、SignPath Foundationへ申請する方針です。採択や証明書発行を現在保証するものではありません。

採択後は次の文言をReleaseページにも表示します。

> Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

## Signing scope and provenance

- 署名対象は本リポジトリの保護されたタグから、GitHub-hosted Windows runner上のRelease workflowが生成したDLL、EXE、MSIのみです。
- ローカルビルド、手動差し替え、Pull Request由来の未信頼コード、GitHub Actions外から持ち込んだYamatanaバイナリは署名しません。
- ソースcommit、workflow run、未署名workflow artifact、SignPath signing request、署名済みartifact、GitHub Releaseを追跡可能にします。
- 署名要求前に未署名artifactをGitHub Actionsへuploadし、そのartifact IDをSignPathへ渡します。
- 署名後にSHA-256を生成し、署名済みRelease Assetと同じReleaseで公開します。
- 上流OSSバイナリはYamatana名義で再署名しません。改変Mozcは公開forkと固定commitからビルドし、適用した差分をレビュー可能にします。

## Team roles

個人アカウントで開始するため、現時点の役割は以下です。追加メンバー参加時に分離します。

- Authors / Committers: [YAMA-TANA](https://github.com/YAMA-TANA)
- Reviewers: [repository collaborators](https://github.com/YAMA-TANA/yamatana-ai-ime/graphs/contributors)
- Approvers: [YAMA-TANA](https://github.com/YAMA-TANA)

外部Contributorの変更はMaintainerがレビューします。各SignPath署名要求はApproverが手動承認します。GitHubとSignPathに関わるメンバーは多要素認証を有効にします。

## Privacy

[Privacy Policy](PRIVACY.md) に記載のとおり、本プログラムは、利用者またはインストール・運用者が明示的に要求しない限り、他のネットワークシステムへ情報を転送しません。アプリ本体にテレメトリはありません。

## Build and release controls

- `main` とRelease workflowの変更はレビュー対象にします。
- 将来はbranch ruleset、CODEOWNERS、必須CI、force-push禁止を有効化します。
- モデルと外部依存は固定revisionとSHA-256で検証します。
- GitHub Actionsは最小権限を使用し、第三者Actionはcommit SHAへ固定します。
- SignPathのorganization ID、project slug、signing policy slugは採択後にGitHub Actions Variablesへ、API tokenはGitHub Actions Secretへ設定します。リポジトリには値を記録しません。
- SignPath接続前のworkflowは必要なVariables/Secretがない限り署名処理を実行しません。

## Foundation readiness checklist

- [x] OSI承認ライセンスで公開
- [x] 製品機能、インストール、アンインストール、プライバシーを文書化
- [x] 未署名Betaを公開する工程を用意
- [x] CI artifactとReleaseのSHA-256を生成
- [x] 署名方針とチーム役割を公開
- [ ] 公開Releaseと継続的な開発履歴を蓄積
- [ ] 改変Mozcの公開fork／レビュー履歴を確立
- [ ] Branch protectionとprivate vulnerability reportingを有効化
- [ ] SignPath Foundationへ申請し、発行された実ID／policyを設定
- [ ] Artifact Configurationで製品名と全バイナリのversion metadataを強制

SignPath Foundationの現行条件: https://signpath.org/terms.html

