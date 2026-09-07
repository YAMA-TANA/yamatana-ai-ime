# Yamatana AI IME v2.0.3-beta

v2.0.2-beta のモダンUIを引き継ぎつつ、AI rerankerがMozcの元順位に引っ張られすぎないよう、候補順位の決定方法を見直したBetaです。

## AI再ランキング

- Mozcの元順位に対する線形ペナルティをやめ、対数型のsoft priorへ変更しました。
- 下位候補でも、AIのスコア差が十分に大きければ1位へ昇格できます。
- Mozc 1位を入れ替えるかどうかは、候補の元順位を二重に罰するのではなく、AIの実際のevidence gapと文脈量を中心に判断します。
- 文脈が弱く差が小さい場合はMozc 1位を維持し、文脈が十分でAIの差が明確な場合はAIを優先します。
- compound segment repairなど既存の安全策は維持しています。
- `AI` 表示は、AIが元のMozc 1位とは別の候補を実際に1位へ昇格させた場合だけ表示します。

## GPU / 推論

- ONNX RuntimeのDirectML providerをGPU候補として使用します。
- Session作成後に実際に有効になったproviderを確認し、DirectMLが有効な場合だけGPU動作として扱います。
- GPU固定設定でDirectMLが有効化されなかった場合は、黙ってCPU扱いにせず明示的にエラーを返します。

## UI

- v2.0.2-betaで導入したWindows 11向け候補ウィンドウ、角丸選択カード、整理した余白・フッター・スクロール表示を継続します。

## プライバシー

AI推論はローカルで完結し、入力内容や文脈を外部AIサービスへ送信しません。

## 注意

**Unsigned Beta:** このMSIはコード署名前のBetaビルドです。Windowsの警告が表示される場合があります。
