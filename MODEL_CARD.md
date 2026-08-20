# Yamatana Ruri IME reranker model card

## Summary

Yamatana AI IMEの変換候補再順位付け用モデルです。`cl-nagoya/ruri-v3-reranker-310m` を基礎に、IMEの正例・負例ペアでLoRA fine-tuningし、重みをmergeした後にONNXへ変換しています。文章生成には使用せず、Mozcが提示した候補へスコアを付けます。

## Version and provenance

- Bundle version: `v0.1.0`
- Base model: `cl-nagoya/ruri-v3-reranker-310m`
- Base revision: `bb46934ee9ed09f850b9fcff17501b3ef7ddb2b3`
- Base license: Apache License 2.0
- LoRA parameters: rank 16, alpha 32, dropout 0.05; ModernBERT `Wqkv`, `Wo`, `Wi`
- Export: ONNX opset 18
- CPU artifact: dynamic INT8
- GPU artifact: FP16

The bundle and every required file are pinned by SHA-256 in `model-manifest.json`. The model is published separately from Git history.

## Intended use

Japanese IME候補の文脈適合度を比較する用途です。医学・法律等の設定やカスタム指示は補助情報であり、専門家の判断や文章内容の正確性を保証しません。

## Limitations

- Betaモデルであり、誤変換、偏り、不自然な順位付けがあり得ます。
- 前後文脈が短い、候補に正解がない、固有名詞が未収録の場合は改善しません。
- モデル出力は候補間の相対順位であり、事実性や安全性の判定ではありません。
- DirectMLの利用可否はGPU、ドライバー、同梱ONNX Runtimeに依存します。

## Privacy

推論はローカルで実行され、モデル自身に通信機能はありません。

## Attribution and license

Base model copyright and credit belong to the CL Research Group in Nagoya, Japan and the Ruri authors. Base and Yamatana model modifications are distributed under Apache License 2.0. See `NOTICE` and `THIRD_PARTY_LICENSES.md`.

