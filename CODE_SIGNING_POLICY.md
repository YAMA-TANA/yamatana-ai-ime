# Code signing policy

## Current status

The current public beta (`v2.0.1-beta`) is unsigned. Yamatana AI IME is preparing an application to SignPath Foundation for free code signing for open-source projects. This document does not imply acceptance by SignPath Foundation or that any currently published binary is signed.

After adoption, releases signed through SignPath will display the acknowledgement required by SignPath Foundation:

> Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).

## Signing scope and provenance

- Only DLL, EXE and MSI files produced from this public repository by the designated GitHub Actions release process are eligible for Yamatana signing.
- Local builds, manually replaced binaries, untrusted pull-request artifacts and binaries introduced outside the documented release process are not eligible for signing.
- Source commit, workflow run, unsigned workflow artifact, SignPath signing request, signed artifact and GitHub Release must remain traceable to one another.
- The unsigned artifact is uploaded by GitHub Actions before any SignPath request. SignPath receives the GitHub-hosted artifact rather than an arbitrary local file.
- SHA-256 hashes are generated for release artifacts and published with the corresponding GitHub Release.
- Unmodified third-party binaries are not re-signed as Yamatana software. Modified Mozc components are built from the public `YAMA-TANA/mozc` fork pinned in `build-config.json`, with the corresponding upstream revision recorded there as well.
- Model assets are pinned by URL, byte size and SHA-256 in `model-manifest.json`; the build only accepts assets matching the recorded digest.

## Team roles

This project is currently maintained primarily by one account. Roles are documented now so that signing approval remains explicit and can be separated when additional maintainers join.

- Authors / Committers: [YAMA-TANA](https://github.com/YAMA-TANA)
- Reviewers: repository collaborators and maintainers reviewing contributed changes
- Signing approver: [YAMA-TANA](https://github.com/YAMA-TANA)

External contributions are reviewed by a maintainer before release. Each SignPath signing request will require an explicit approver action. Accounts participating in GitHub release administration or SignPath signing are expected to use multi-factor authentication.

## Privacy

As documented in [PRIVACY.md](PRIVACY.md), the installed application does not transmit IME input, surrounding text, conversion candidates, custom instructions, dictionaries or inference results to external network services. It contains no telemetry, advertising SDK or automatic crash-report upload.

Network access used by development/build tooling to retrieve pinned source code, dependencies or model assets is separate from runtime behavior and is documented in the privacy and build-provenance material.

## Build and release controls

- Release-signing configuration, installer code, dependency retrieval and build workflows are security-sensitive changes and are reviewed before use in a public release.
- The model bundle and Mozc source revision are pinned and integrity-checked.
- GitHub Actions workflows use explicit permissions. Third-party signing actions are pinned to a commit SHA rather than a floating tag.
- SignPath organization ID, project slug and signing-policy slug will be stored as GitHub Actions Variables after adoption; the API token will be stored as a GitHub Actions Secret. These values are not committed to the repository.
- The SignPath submission workflow remains inert until the required SignPath Variables are configured.
- `.github/CODEOWNERS` identifies security- and release-sensitive paths for review visibility.

## Foundation readiness checklist

- [x] Public repository under an OSI-approved license (Apache-2.0)
- [x] Product purpose, installation and uninstallation documented
- [x] Privacy policy published
- [x] Security policy and vulnerability-reporting guidance published
- [x] Public beta releases exist (`v2.0.0-beta`, `v2.0.1-beta`)
- [x] Release MSI and SHA-256 checksum are published together
- [x] Public GitHub Actions build/release workflows exist
- [x] Modified Mozc source is available from the public `YAMA-TANA/mozc` fork and pinned by commit
- [x] Model assets are pinned by SHA-256
- [x] Code-signing policy and team roles are public
- [x] SignPath submission workflow is present but inactive until adoption
- [x] Security-sensitive paths have CODEOWNERS coverage
- [ ] Repository branch/ruleset protections enabled in GitHub settings
- [ ] GitHub Private Vulnerability Reporting enabled in repository settings
- [ ] SignPath Foundation application submitted and accepted
- [ ] Issued organization/project/signing-policy identifiers configured
- [ ] SignPath Artifact Configuration validated against the exact files intended for signing

See [docs/SIGNPATH_READINESS.md](docs/SIGNPATH_READINESS.md) for a concise application dossier and source/build provenance map.

SignPath Foundation terms: https://signpath.org/terms.html
