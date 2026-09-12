# FORM LENS

カメラ映像を端末内で骨格推定し、日常のトレーニングフォームを観察するWebスタジオです。

- MediaPipe Pose Landmarkerによるローカル推定
- Workers API経由のwger運動データとOpen-Meteo天気データ
- 辞典はwger公開APIをCloudflare Cache API経由で取得。セッション履歴は端末内localStorageに保存し、D1は使用しません
- 日本語・English・中文・한국어のUI切り替えに対応
- セッション履歴はブラウザ内保存。動画はアップロードしません

