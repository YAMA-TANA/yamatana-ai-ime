const API_BASE = "https://form-lens-api.hurukigeoetym.workers.dev";
const POSE_WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm";
const POSE_MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

const TRANSLATIONS = {
  ja: {
    navLabel: "メインナビゲーション", navLive: "ライブ分析", navLibrary: "エクササイズ辞典", navLog: "セッションログ", heroTitle: "フォームを、<br><span class=\"accent-word\">鏡より</span>正確に。", heroLede: "カメラの映像から身体のランドマークを読み取り、回数・角度・テンポ・左右差をリアルタイムに可視化。動画をサーバーへ送らず、家の一角を小さな分析室に変えます。", heroOpen: "スタジオを開く", heroHow: "仕組みを見る", privacyHero: "カメラ映像は端末内で処理。録画・アップロードは行いません。", visualAngle: "KNEE ANGLE<br><strong id=\"heroAngle\">—°</strong>", visualReps: "REP COUNT<br><strong id=\"heroReps\">00</strong>", visualInference: "ON-DEVICE INFERENCE", studioTitle: "動きを、<br>数字と感覚のあいだへ。", studioIntro: "まず種目を選び、カメラを起動。画面に身体全体が収まる距離で、ゆっくり1回動いてください。", selectMode: "SELECT MODE", fourModes: "4 MODES", exerciseSquat: "スクワット", exerciseSquatMeta: "knee angle / rep", exercisePushup: "腕立て伏せ", exercisePushupMeta: "elbow angle / rep", exercisePlank: "プランク", exercisePlankMeta: "body line / hold", exerciseLunge: "ランジ", exerciseLungeMeta: "balance / rep", setupNoteLabel: "SETUP NOTE", privacyRail: "映像はローカル処理<br><small>MediaPipe Pose / no upload</small>", statusStandby: "待機中", stageMessage: "カメラを起動して<br>最初の1回を分析", cameraPermission: "ブラウザのカメラ許可が必要です", startCamera: "カメラを起動", thisSession: "this session", reset: "リセット", finishSession: "セッション終了", liveMetrics: "LIVE METRICS", currentAngle: "CURRENT ANGLE", metricStarts: "動き始めると計測", qualitySignal: "QUALITY SIGNAL", tempo: "TEMPO", secPerRep: "sec / rep", tempoHint: "回数を重ねると表示", lastCue: "LAST CUE", cueStandby: "カメラを起動すると、フォームのヒントがここに出ます。", disclaimer: "※ 本ツールはトレーニングの補助を目的としたものです。痛みや体調不良がある場合は中止し、必要に応じて専門家へ相談してください。", signalsTitle: "フォームの「なんとなく」を、<br>観察できるものに。", signalsIntro: "カメラから取得するのは、関節の位置情報だけ。映像そのものは保存せず、3つの信号へ変換します。", signalAngle: "関節角度", signalAngleCopy: "肩・肘・腰・膝・足首の位置から、深さや伸びを一瞬ごとに読み取ります。", signalTempo: "テンポ", signalTempoCopy: "下ろす・止める・戻すのリズムを記録。急ぎすぎや反動を見直すきっかけになります。", signalBalance: "左右差", signalBalanceTitle: "左右のバランス", signalBalanceCopy: "左右のランドマークを比較し、片側だけに寄った動きをヒントとして表示します。", libraryTitle: "次に試す動きを、<br>辞典から探す。", libraryIntro: "公開運動データをWorkers API経由で取得。フォーム分析できる種目と、周辺の種目を同じ場所で見つけられます。", librarySearch: "種目名・筋肉で検索", libraryFilter: "種目フィルター", filterAll: "すべて", filterLegs: "脚", filterChest: "胸", filterBack: "背中", libraryLoading: "運動データを読み込んでいます…", logTitle: "続けた記録が、<br>フォームを育てる。", logIntro: "ログはこの端末に保存されます。アカウント登録なしで、前回の回数や品質シグナルを振り返れます。", localHistory: "LOCAL HISTORY", recentSessions: "最近のセッション", clearHistory: "履歴を消去", emptyHistory: "まだセッションがありません", emptyHistoryCopy: "カメラを起動して、1回分の動きを記録しましょう。", weeklySignal: "WEEKLY SIGNAL", recentLog: "reps<br>in recent log", recentChart: "最近の回数グラフ", insightEmpty: "1回目は、記録を始めるための1回。数字は比較ではなく、次の動きを選ぶメモです。", exportHistory: "ログをJSONで保存", conditionTitle: "外で動く日の<br><span class=\"accent-word\">コンディション</span>も見る。", conditionCopy: "位置情報を許可すると、Open-Meteo APIから現在の気温・風を読み込みます。室内トレーニングに切り替える目安としてどうぞ。", weatherButton: "現在地の天気を読む", locationNotLoaded: "LOCATION NOT LOADED", weatherHint: "ボタンを押すと取得します", adLabel: "広告", adTitle: "今日のトレーニング環境を整える", adCopy: "フォーム分析のあとに、運動まわりの便利な情報を見る。", adLink: "外部リンクを開く ↗", faqTitle: "使う前に<br>知っておくこと。", faqPrivacy: "動画はどこへ送られますか？<span>+</span>", faqPrivacyCopy: "送信しません。ブラウザ内のMediaPipe Pose Landmarkerがカメラフレームから関節位置を計算し、画面上の数値だけを更新します。", faqAccuracy: "どのくらい正確ですか？<span>+</span>", faqAccuracyCopy: "照明、服装、カメラ角度、身体の向きで精度は変わります。画面に全身を入れ、床とカメラを安定させると読み取りやすくなります。医療的な判定ではありません。", faqSource: "運動データの出典は？<span>+</span>", faqSourceCopy: "エクササイズ辞典の一部はwgerの公開APIを参照しています。APIが利用できない場合も、FORM LENSの基本種目は表示されます。", footerTagline: "Web motion studio for everyday training.", footerLibrary: "辞典", apiOnline: "API接続中", apiBasic: "基本モード", modelLoading: "モデル読み込み中…", statusAnalyzing: "分析中", statusLaunchFailed: "起動できません", cameraStop: "■ 分析を停止", qualityStable: "安定", qualityAdjust: "調整", qualityCheck: "要確認", cueFullBody: "全身を画面に入れると、フォームのヒントが出ます。", cueNoBody: "身体が見つかりません。少しカメラから離れてください。", cuePlankLow: "腰が落ちています。おへそを背中へ近づける意識で。", cuePlankHigh: "少し反り気味です。肋骨を静かに下げます。", cuePlankGood: "いい一直線。呼吸を止めず、その姿勢を保ちます。", cueGoDeeper: "もう少し深く、ゆっくり動きます。", cueBendElbow: "もう少し肘を曲げて、ゆっくり動きます。", cueEnough: "深さは十分。反動を使わずに戻ります。", cuePushLine: "肩・腰・足首をひとつの線に保ちます。", cueFeet: "足裏で床を押し、膝とつま先の向きをそろえます。", saved: "セッションを保存しました。動きのメモは履歴から確認できます。", noReps: "回数が記録されなかったため、履歴には保存していません。", resetDone: "セッションをリセットしました。最初の1回をどうぞ。", libraryLive: "{{count}}種目を表示中 · Workers API経由", libraryFallback: "基本種目を表示中 · APIは一時的に利用できません", cameraPermissionError: "カメラの許可が必要です。ブラウザのアドレスバーから許可してください。", cameraError: "カメラを起動できませんでした。HTTPS接続と端末のカメラを確認してください。", weatherLocError: "位置情報が許可されていません。許可なしでもライブ分析は使えます。", weatherUnavailable: "天気データを取得できませんでした。"
  },
  en: {
    navLabel: "Main navigation", navLive: "Live analysis", navLibrary: "Exercise atlas", navLog: "Session log", heroTitle: "Form, made<br><span class=\"accent-word\">visible.</span>", heroLede: "Read body landmarks from your camera and turn reps, angles, tempo and balance into a live signal. Your video stays on the device; your corner becomes a small motion lab.", heroOpen: "Open the studio", heroHow: "How it works", privacyHero: "Camera frames are processed on-device. No recording or upload.", visualAngle: "KNEE ANGLE<br><strong id=\"heroAngle\">—°</strong>", visualReps: "REP COUNT<br><strong id=\"heroReps\">00</strong>", visualInference: "ON-DEVICE INFERENCE", studioTitle: "Put movement<br>between feeling and data.", studioIntro: "Choose a mode, start the camera, and make one slow repetition with your whole body in frame.", selectMode: "SELECT MODE", fourModes: "4 MODES", exerciseSquat: "Squat", exerciseSquatMeta: "knee angle / rep", exercisePushup: "Push-up", exercisePushupMeta: "elbow angle / rep", exercisePlank: "Plank", exercisePlankMeta: "body line / hold", exerciseLunge: "Lunge", exerciseLungeMeta: "balance / rep", setupNoteLabel: "SETUP NOTE", privacyRail: "Video stays local<br><small>MediaPipe Pose / no upload</small>", statusStandby: "Standby", stageMessage: "Start the camera to<br>analyze your first rep", cameraPermission: "Browser camera permission required", startCamera: "Start camera", thisSession: "this session", reset: "Reset", finishSession: "Finish session", liveMetrics: "LIVE METRICS", currentAngle: "CURRENT ANGLE", metricStarts: "Moves appear here", qualitySignal: "QUALITY SIGNAL", tempo: "TEMPO", secPerRep: "sec / rep", tempoHint: "Appears after more reps", lastCue: "LAST CUE", cueStandby: "Start the camera to see form cues here.", disclaimer: "Note: This is a training aid, not medical advice. Stop if you feel pain or unwell and consult a professional when needed.", signalsTitle: "Turn the vague feeling of form<br>into something you can observe.", signalsIntro: "Only joint landmark positions are read from the camera. The video itself is not saved; it becomes three simple signals.", signalAngle: "Joint angles", signalAngleCopy: "Track depth and extension from the positions of shoulders, elbows, hips, knees and ankles.", signalTempo: "Tempo", signalTempoCopy: "See the rhythm of lowering, pausing and returning. A cue to slow down or lose the bounce.", signalBalance: "ASYMMETRY", signalBalanceTitle: "Left / right balance", signalBalanceCopy: "Compare left and right landmarks and surface a hint when one side carries more of the movement.", libraryTitle: "Find your next movement<br>in the atlas.", libraryIntro: "Public exercise metadata arrives through the Workers API, so analyzed moves and neighboring exercises live in one place.", librarySearch: "Search exercise or muscle", libraryFilter: "Exercise filters", filterAll: "All", filterLegs: "Legs", filterChest: "Chest", filterBack: "Back", libraryLoading: "Loading exercise data…", logTitle: "The record of showing up<br>builds better form.", logIntro: "Logs stay on this device. No account is needed to look back at your reps and quality signals.", localHistory: "LOCAL HISTORY", recentSessions: "Recent sessions", clearHistory: "Clear history", emptyHistory: "No sessions yet", emptyHistoryCopy: "Start the camera and record one small session.", weeklySignal: "WEEKLY SIGNAL", recentLog: "reps<br>in recent log", recentChart: "Recent rep chart", insightEmpty: "The first rep is a beginning. Numbers are notes for choosing your next movement, not a comparison.", exportHistory: "Save log as JSON", conditionTitle: "Read the<br><span class=\"accent-word\">conditions</span> before going outside.", conditionCopy: "Allow location to read current temperature and wind from Open-Meteo. Use it as a cue to move indoors when needed.", weatherButton: "Read local weather", locationNotLoaded: "LOCATION NOT LOADED", weatherHint: "Press the button to fetch", adLabel: "Advertisement", adTitle: "Set up your training environment", adCopy: "After form analysis, browse a useful external fitness link.", adLink: "Open external link ↗", faqTitle: "Before you start,<br>know this.", faqPrivacy: "Where does the video go?<span>+</span>", faqPrivacyCopy: "Nowhere. MediaPipe Pose Landmarker calculates joint positions in your browser and updates only the numbers on screen.", faqAccuracy: "How accurate is it?<span>+</span>", faqAccuracyCopy: "Lighting, clothing, camera angle and orientation affect accuracy. Keep your full body in frame and stabilize the camera. This is not a medical assessment.", faqSource: "Where does exercise data come from?<span>+</span>", faqSourceCopy: "Parts of the exercise atlas reference the public wger API. FORM LENS basic modes remain available if the API is unavailable.", footerTagline: "Web motion studio for everyday training.", footerLibrary: "Atlas", apiOnline: "API online", apiBasic: "Basic mode", modelLoading: "Loading model…", statusAnalyzing: "Analyzing", statusLaunchFailed: "Could not start", cameraStop: "■ Stop analysis", qualityStable: "Stable", qualityAdjust: "Adjust", qualityCheck: "Check", cueFullBody: "Keep your whole body in frame to see form cues.", cueNoBody: "Body not detected. Move a little farther from the camera.", cuePlankLow: "Hips are dropping. Think of bringing your navel toward your back.", cuePlankHigh: "You are slightly arched. Let the ribs settle down.", cuePlankGood: "Nice long line. Keep breathing and hold it.", cueGoDeeper: "Move a little deeper, slowly.", cueBendElbow: "Bend the elbows a little more, slowly.", cueEnough: "Depth is enough. Return without using momentum.", cuePushLine: "Keep shoulders, hips and ankles in one line.", cueFeet: "Push through the feet and align knees with toes.", saved: "Session saved. Review the movement note in your history.", noReps: "No reps were recorded, so this session was not saved.", resetDone: "Session reset. Take your first rep.", libraryLive: "Showing {{count}} exercises · via Workers API", libraryFallback: "Showing core exercises · API temporarily unavailable", cameraPermissionError: "Camera permission is required. Allow it from the browser address bar.", cameraError: "Could not start the camera. Check HTTPS and your device camera.", weatherLocError: "Location was not allowed. Live analysis works without it.", weatherUnavailable: "Could not load weather data."
  },
  zh: {
    navLabel: "主导航", navLive: "实时分析", navLibrary: "动作图鉴", navLog: "训练记录", heroTitle: "让动作，<br><span class=\"accent-word\">看得见。</span>", heroLede: "从摄像头读取身体关键点，将次数、角度、节奏和左右平衡变成实时信号。视频留在设备中。", heroOpen: "打开工作室", heroHow: "了解原理", privacyHero: "视频在设备本地处理，不录制、不上传。", studioTitle: "让动作<br>连接感觉与数据。", studioIntro: "选择动作，打开摄像头，让全身进入画面并慢慢完成一次动作。", selectMode: "选择模式", fourModes: "4种模式", exerciseSquat: "深蹲", exercisePushup: "俯卧撑", exercisePlank: "平板支撑", exerciseLunge: "弓步", setupNoteLabel: "准备提示", privacyRail: "视频仅本地处理<br><small>MediaPipe Pose / 不上传</small>", statusStandby: "待机", stageMessage: "打开摄像头<br>分析第一次动作", cameraPermission: "需要浏览器摄像头权限", startCamera: "打开摄像头", reset: "重置", finishSession: "结束训练", liveMetrics: "实时指标", currentAngle: "当前角度", metricStarts: "动作后显示", qualitySignal: "质量信号", tempo: "节奏", lastCue: "最后提示", cueStandby: "打开摄像头后，这里会显示动作提示。", libraryTitle: "在图鉴中<br>寻找下一个动作。", libraryIntro: "通过Workers API获取公开动作数据，将可分析动作和相关动作放在一起。", librarySearch: "按动作或肌肉搜索", libraryFilter: "动作筛选", filterAll: "全部", filterLegs: "腿部", filterChest: "胸部", filterBack: "背部", libraryLoading: "正在加载动作数据…", logTitle: "持续记录，<br>让动作变得更好。", logIntro: "记录保存在本设备，无需注册即可回顾次数和质量信号。", localHistory: "本地记录", recentSessions: "最近训练", clearHistory: "清除记录", emptyHistory: "还没有训练记录", emptyHistoryCopy: "打开摄像头，记录一次小训练。", weeklySignal: "近期信号", exportHistory: "保存JSON记录", conditionTitle: "查看户外运动的<br><span class=\"accent-word\">天气条件。</span>", conditionCopy: "允许定位后，从Open-Meteo获取当前温度和风速，作为室内外切换的参考。", weatherButton: "读取本地天气", locationNotLoaded: "尚未读取位置", weatherHint: "点击按钮获取", adLabel: "广告", adTitle: "准备你的训练环境", adCopy: "完成动作分析后，查看运动相关外部信息。", adLink: "打开外部链接 ↗", faqTitle: "开始之前，<br>请先了解。", faqPrivacy: "视频会发送到哪里？<span>+</span>", faqPrivacyCopy: "不会发送。MediaPipe在浏览器内计算关键点，只更新屏幕上的数字。", faqAccuracy: "准确度如何？<span>+</span>", faqAccuracyCopy: "光线、衣服、摄像头角度和身体方向都会影响结果。请让全身进入画面，并固定摄像头。", faqSource: "动作数据来自哪里？<span>+</span>", faqSourceCopy: "动作图鉴部分参考wger公开API。API不可用时，FORM LENS的基本模式仍可使用。", apiOnline: "API已连接", apiBasic: "基础模式", modelLoading: "模型加载中…", statusAnalyzing: "分析中", statusLaunchFailed: "无法启动", cameraStop: "■ 停止分析", qualityStable: "稳定", qualityAdjust: "调整", qualityCheck: "需确认", cueFullBody: "请让全身进入画面。", cueNoBody: "未检测到身体，请稍微离摄像头远一点。", cuePlankLow: "髋部下沉了，想象肚脐靠近背部。", cuePlankHigh: "身体略微拱起，让肋骨自然下沉。", cuePlankGood: "身体线条很好，保持呼吸。", cueGoDeeper: "再深一点，慢慢移动。", cueBendElbow: "肘部再弯曲一些，慢慢移动。", cueEnough: "深度足够，不要借助惯性。", cuePushLine: "保持肩、髋、脚踝在一条线上。", cueFeet: "用脚掌发力，让膝盖与脚尖方向一致。", saved: "训练已保存，可在记录中回顾。", noReps: "没有记录到次数，因此未保存。", resetDone: "已重置训练，开始第一次动作。", libraryLive: "显示{{count}}个动作 · Workers API", libraryFallback: "显示基本动作 · API暂时不可用", cameraPermissionError: "需要摄像头权限，请在地址栏允许。", cameraError: "无法打开摄像头，请检查HTTPS和设备摄像头。", weatherLocError: "未允许定位。无需定位也可使用实时分析。", weatherUnavailable: "无法获取天气数据。", thisSession: "本次训练", secPerRep: "秒 / 次", tempoHint: "完成更多次数后显示", footerLibrary: "图鉴", signalsTitle: "把动作的模糊感觉，<br>变成可观察的信号。", signalsIntro: "摄像头只读取关节关键点，不保存视频，并将其转换成三个信号。", signalAngle: "关节角度", signalAngleCopy: "读取肩、肘、髋、膝和脚踝的位置，观察深度和伸展。", signalTempo: "节奏", signalTempoCopy: "记录下沉、停顿和返回的节奏。", signalBalance: "左右差", signalBalanceTitle: "左右平衡", signalBalanceCopy: "比较左右关键点，在一侧承担更多动作时给出提示。", navLog: "训练记录", footerTagline: "日常训练的Web动作工作室。", thisSession: "本次训练", recentSessions: "最近训练", recentLog: "次<br>最近记录", recentChart: "最近次数图", insightEmpty: "第一次动作是开始。数字是下一次动作的笔记，不是比较。", conditionTitle: "查看户外运动的<br><span class=\"accent-word\">天气条件。</span>"
  },
  ko: {
    navLabel: "메인 내비게이션", navLive: "실시간 분석", navLibrary: "운동 도감", navLog: "세션 기록", heroTitle: "폼을<br><span class=\"accent-word\">보이게.</span>", heroLede: "카메라에서 신체 랜드마크를 읽어 횟수, 각도, 템포와 좌우 균형을 실시간 신호로 바꿉니다. 영상은 기기에 남습니다.", heroOpen: "스튜디오 열기", heroHow: "원리 보기", privacyHero: "카메라 영상은 기기에서 처리됩니다. 녹화·업로드 없음.", studioTitle: "움직임을<br>감각과 데이터 사이로.", studioIntro: "모드를 선택하고 카메라를 켠 뒤, 몸 전체가 보이는 거리에서 천천히 한 번 움직여 보세요.", selectMode: "모드 선택", fourModes: "4 MODES", exerciseSquat: "스쿼트", exercisePushup: "푸시업", exercisePlank: "플랭크", exerciseLunge: "런지", setupNoteLabel: "준비 메모", privacyRail: "영상은 로컬 처리<br><small>MediaPipe Pose / 업로드 없음</small>", statusStandby: "대기 중", stageMessage: "카메라를 켜고<br>첫 동작을 분석하세요", cameraPermission: "브라우저 카메라 권한 필요", startCamera: "카메라 켜기", reset: "초기화", finishSession: "세션 종료", liveMetrics: "실시간 지표", currentAngle: "현재 각도", metricStarts: "움직이면 측정", qualitySignal: "품질 신호", tempo: "템포", lastCue: "마지막 큐", cueStandby: "카메라를 켜면 자세 힌트가 표시됩니다.", libraryTitle: "도감에서<br>다음 동작을 찾으세요.", libraryIntro: "Workers API로 공개 운동 데이터를 가져와 분석 가능한 동작과 주변 동작을 함께 보여줍니다.", librarySearch: "운동 또는 근육 검색", libraryFilter: "운동 필터", filterAll: "전체", filterLegs: "하체", filterChest: "가슴", filterBack: "등", libraryLoading: "운동 데이터 불러오는 중…", logTitle: "기록이 쌓이면<br>폼이 자랍니다.", logIntro: "기록은 이 기기에 저장됩니다. 계정 없이 횟수와 품질 신호를 돌아볼 수 있습니다.", localHistory: "로컬 기록", recentSessions: "최근 세션", clearHistory: "기록 지우기", emptyHistory: "아직 세션이 없습니다", emptyHistoryCopy: "카메라를 켜고 작은 세션을 기록하세요.", weeklySignal: "최근 신호", exportHistory: "JSON으로 저장", conditionTitle: "밖에서 움직이기 전<br><span class=\"accent-word\">컨디션</span> 확인", conditionCopy: "위치를 허용하면 Open-Meteo API에서 현재 기온과 바람을 읽습니다.", weatherButton: "현재 날씨 읽기", locationNotLoaded: "위치 미확인", weatherHint: "버튼을 눌러 가져오기", adLabel: "광고", adTitle: "운동 환경을 준비하세요", adCopy: "폼 분석 후 운동 관련 외부 정보를 확인하세요.", adLink: "외부 링크 열기 ↗", faqTitle: "시작하기 전에<br>알아둘 것.", faqPrivacy: "영상은 어디로 가나요?<span>+</span>", faqPrivacyCopy: "어디에도 보내지 않습니다. MediaPipe가 브라우저에서 관절 위치를 계산하고 화면의 숫자만 갱신합니다.", faqAccuracy: "얼마나 정확한가요?<span>+</span>", faqAccuracyCopy: "조명, 옷, 카메라 각도와 방향에 따라 달라집니다. 몸 전체를 화면에 넣고 카메라를 고정하세요.", faqSource: "운동 데이터의 출처는?<span>+</span>", faqSourceCopy: "운동 도감 일부는 wger 공개 API를 참고합니다. API가 없어도 기본 모드는 사용할 수 있습니다.", apiOnline: "API 연결됨", apiBasic: "기본 모드", modelLoading: "모델 준비 중…", statusAnalyzing: "분석 중", statusLaunchFailed: "시작할 수 없음", cameraStop: "■ 분석 중지", qualityStable: "안정", qualityAdjust: "조정", qualityCheck: "확인 필요", cueFullBody: "몸 전체가 화면에 들어오게 하세요.", cueNoBody: "몸을 찾지 못했습니다. 카메라에서 조금 멀어지세요.", cuePlankLow: "허리가 내려갑니다. 배꼽을 등 쪽으로 당긴다고 생각하세요.", cuePlankHigh: "조금 휘었습니다. 갈비뼈를 내려보세요.", cuePlankGood: "좋은 직선입니다. 호흡을 계속하세요.", cueGoDeeper: "조금 더 깊게, 천천히 움직이세요.", cueBendElbow: "팔꿈치를 조금 더 굽혀 천천히 움직이세요.", cueEnough: "깊이는 충분합니다. 반동 없이 돌아오세요.", cuePushLine: "어깨·허리·발목을 한 줄로 유지하세요.", cueFeet: "발바닥으로 밀고 무릎과 발끝 방향을 맞추세요.", saved: "세션을 저장했습니다. 기록에서 확인하세요.", noReps: "횟수가 기록되지 않아 저장하지 않았습니다.", resetDone: "세션을 초기화했습니다. 첫 동작을 시작하세요.", libraryLive: "{{count}}개 동작 표시 · Workers API", libraryFallback: "기본 동작 표시 · API 일시 unavailable", cameraPermissionError: "카메라 권한이 필요합니다. 주소창에서 허용하세요.", cameraError: "카메라를 시작할 수 없습니다. HTTPS와 카메라를 확인하세요.", weatherLocError: "위치가 허용되지 않았습니다. 실시간 분석은 계속 사용할 수 있습니다.", weatherUnavailable: "날씨 데이터를 가져올 수 없습니다.", thisSession: "이번 세션", secPerRep: "초 / 회", tempoHint: "횟수가 쌓이면 표시", footerLibrary: "도감", footerTagline: "일상 운동을 위한 Web 모션 스튜디오.", signalsTitle: "폼의 막연한 느낌을<br>관찰 가능한 신호로.", signalsIntro: "카메라는 관절 랜드마크만 읽습니다. 영상은 저장하지 않고 세 가지 신호로 바꿉니다.", signalAngle: "관절 각도", signalAngleCopy: "어깨, 팔꿈치, 엉덩이, 무릎과 발목 위치에서 깊이와 신전을 읽습니다.", signalTempo: "템포", signalTempoCopy: "내려가기, 멈춤, 돌아오기 리듬을 기록합니다.", signalBalance: "좌우 차이", signalBalanceTitle: "좌우 균형", signalBalanceCopy: "좌우 랜드마크를 비교해 한쪽에 더 실릴 때 힌트를 줍니다.", recentLog: "회<br>최근 기록", recentChart: "최근 횟수 그래프", insightEmpty: "첫 동작은 시작입니다. 숫자는 비교가 아니라 다음 동작을 위한 메모입니다."
  }
};

const EXTRA_TRANSLATIONS = {
  ja: { outdoorNote: "OPTIONAL / OUTDOOR NOTE", sponsored: "SPONSORED", notesKicker: "06 / NOTES", footerNote: "Pose inference by MediaPipe Tasks Vision.<br>Exercise metadata: wger public API.", noResults: "該当する種目がありません", noResultsCopy: "検索語を変えて、別の動きを探してみてください。", historyCount: "{{count}}回の記録があります。前回の自分のテンポと、今日の1回を比べてみてください。", weatherLoading: "位置情報を確認中…", weatherRefresh: "現在地を更新", weatherNoGeo: "この端末では位置情報を利用できません。", cameraUnsupported: "カメラ非対応", cameraUnsupportedCopy: "このブラウザではカメラを利用できません。HTTPSのページでお試しください。" },
  en: { outdoorNote: "OPTIONAL / OUTDOOR NOTE", sponsored: "SPONSORED", notesKicker: "06 / NOTES", footerNote: "Pose inference by MediaPipe Tasks Vision.<br>Exercise metadata: wger public API.", noResults: "No matching exercises", noResultsCopy: "Try another search to find a different movement.", historyCount: "{{count}} logged sessions. Compare today's rep with your own previous tempo.", weatherLoading: "Checking location…", weatherRefresh: "Refresh local weather", weatherNoGeo: "Location is not available on this device.", cameraUnsupported: "Camera unavailable", cameraUnsupportedCopy: "This browser cannot use the camera. Try this HTTPS page on a supported device." },
  zh: { outdoorNote: "OPTIONAL / OUTDOOR NOTE", sponsored: "赞助内容", notesKicker: "06 / NOTES", footerNote: "姿态推理由 MediaPipe Tasks Vision 提供。<br>动作数据：wger 公开 API。", noResults: "没有匹配动作", noResultsCopy: "换一个搜索词，寻找其他动作。", historyCount: "已记录{{count}}次训练。比较今天的动作与自己之前的节奏。", weatherLoading: "正在确认位置…", weatherRefresh: "刷新本地天气", weatherNoGeo: "此设备无法使用定位。", cameraUnsupported: "摄像头不可用", cameraUnsupportedCopy: "此浏览器无法使用摄像头，请在支持摄像头的HTTPS设备上打开。" },
  ko: { outdoorNote: "OPTIONAL / OUTDOOR NOTE", sponsored: "스폰서 콘텐츠", notesKicker: "06 / NOTES", footerNote: "자세 추론: MediaPipe Tasks Vision.<br>운동 데이터: wger 공개 API.", noResults: "일치하는 운동이 없습니다", noResultsCopy: "검색어를 바꾸어 다른 동작을 찾아보세요.", historyCount: "{{count}}개의 세션이 기록되었습니다. 오늘의 동작을 이전 템포와 비교해 보세요.", weatherLoading: "위치를 확인하는 중…", weatherRefresh: "현지 날씨 새로고침", weatherNoGeo: "이 기기에서는 위치를 사용할 수 없습니다.", cameraUnsupported: "카메라를 사용할 수 없음", cameraUnsupportedCopy: "이 브라우저에서는 카메라를 사용할 수 없습니다. HTTPS 기기에서 시도하세요." }
};

let currentLanguage = localStorage.getItem("form-lens-language") || "ja";
const tr = (key, variables = {}) => {
  const source = { ...EXTRA_TRANSLATIONS.en, ...EXTRA_TRANSLATIONS[currentLanguage], ...(TRANSLATIONS[currentLanguage] || {}) };
  let value = source[key] ?? TRANSLATIONS.en[key] ?? TRANSLATIONS.ja[key] ?? key;
  Object.entries(variables).forEach(([name, replacement]) => { value = value.replace(`{{${name}}}`, String(replacement)); });
  return value;
};

function applyLanguage() {
  const languageSelect = $("#languageSelect");
  if (languageSelect) languageSelect.value = currentLanguage;
  document.documentElement.lang = currentLanguage;
  document.querySelectorAll("[data-i18n]").forEach((element) => { element.textContent = tr(element.dataset.i18n); });
  document.querySelectorAll("[data-i18n-html]").forEach((element) => { element.innerHTML = tr(element.dataset.i18nHtml); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => { element.placeholder = tr(element.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => { element.setAttribute("aria-label", tr(element.dataset.i18nAria)); });
  setText("#apiStatus", tr("apiOnline"));
  if (libraryLoaded) setText("#libraryStatus", libraryAvailable ? tr("libraryLive", { count: libraryData.length }) : tr("libraryFallback"));
  updateExerciseLabels();
  if (session) { updateMetrics({ metric: tracker?.lastMetric ?? null, quality: tracker?.lastMetric === null ? null : scoreMetric(tracker.lastMetric, EXERCISES[activeExercise]), confidence: tracker?.maxConfidence || null, cue: tracker?.lastCue || tr("cueStandby") }); }
  renderHistory();
}

const FALLBACK_EXERCISES = [
  { id: "local-squat", name: "Bodyweight Squat", description: "A knee-dominant lower body movement. Keep your ribcage stacked over your pelvis.", muscles: "legs", category: "legs", source: "FORM LENS" },
  { id: "local-pushup", name: "Push-up", description: "A bodyweight press that asks the shoulders, elbows and trunk to move as one line.", muscles: "chest", category: "chest", source: "FORM LENS" },
  { id: "local-plank", name: "Plank", description: "An isometric trunk hold. Think long from the crown of the head to the heels.", muscles: "core", category: "core", source: "FORM LENS" },
  { id: "local-lunge", name: "Forward Lunge", description: "A split-stance leg pattern for balance, control and single-leg strength.", muscles: "legs", category: "legs", source: "FORM LENS" },
  { id: "local-glute-bridge", name: "Glute Bridge", description: "Lift through the hips without arching the lower back at the top.", muscles: "glutes", category: "legs", source: "FORM LENS" },
  { id: "local-wall-sit", name: "Wall Sit", description: "A quiet lower-body hold that makes time and knee angle visible.", muscles: "legs", category: "legs", source: "FORM LENS" }
];

const EXERCISES = {
  squat: { title: "スクワット", kicker: "MODE 01 / LOWER BODY", stage: "SQUAT", unit: "REPS", metric: "膝の角度", down: 118, up: 158, target: 98, setup: "横向きに立ち、頭から足先まで画面に入る位置へ。膝がつま先より内側へ入らないよう意識します。" },
  pushup: { title: "腕立て伏せ", kicker: "MODE 02 / UPPER BODY", stage: "PUSH-UP", unit: "REPS", metric: "肘の角度", down: 105, up: 158, target: 86, setup: "斜め横から全身が入る位置へ。肩・腰・足首が長い線になるように構えます。" },
  plank: { title: "プランク", kicker: "MODE 03 / ISOMETRIC", stage: "PLANK", unit: "HOLD SEC", down: 160, up: 180, target: 172, setup: "横向きに身体全体を入れます。腰が落ちたり反ったりしない、長い一直線を探します。" },
  lunge: { title: "ランジ", kicker: "MODE 04 / SINGLE LEG", stage: "LUNGE", unit: "REPS", down: 120, up: 158, target: 98, setup: "正面または斜め前から、左右の足先まで画面に入れます。下りるときに軸足を急がせません。" }
};

const EXERCISE_LOCALES = {
  squat: { title: { ja: "スクワット", en: "Squat", zh: "深蹲", ko: "스쿼트" }, kicker: { ja: "MODE 01 / LOWER BODY", en: "MODE 01 / LOWER BODY", zh: "模式01 / 下肢", ko: "모드 01 / 하체" }, metric: { ja: "膝の角度", en: "Knee angle", zh: "膝盖角度", ko: "무릎 각도" }, setup: { ja: "横向きに立ち、頭から足先まで画面に入る位置へ。膝がつま先より内側へ入らないよう意識します。", en: "Stand side-on with your whole body in frame. Keep the knees tracking over the toes.", zh: "侧身站立，让全身进入画面。注意膝盖不要向脚尖内侧塌入。", ko: "옆으로 서서 몸 전체가 화면에 들어오게 하세요. 무릎과 발끝 방향을 맞춥니다." } },
  pushup: { title: { ja: "腕立て伏せ", en: "Push-up", zh: "俯卧撑", ko: "푸시업" }, kicker: { ja: "MODE 02 / UPPER BODY", en: "MODE 02 / UPPER BODY", zh: "模式02 / 上肢", ko: "모드 02 / 상체" }, metric: { ja: "肘の角度", en: "Elbow angle", zh: "肘部角度", ko: "팔꿈치 각도" }, setup: { ja: "斜め横から全身が入る位置へ。肩・腰・足首が長い線になるように構えます。", en: "Use a diagonal side view with your whole body in frame. Keep shoulders, hips and ankles in one long line.", zh: "从斜侧面让全身进入画面。保持肩、髋和脚踝在一条长线上。", ko: "비스듬한 옆모습으로 몸 전체를 잡습니다. 어깨·허리·발목을 한 줄로 유지하세요." } },
  plank: { title: { ja: "プランク", en: "Plank", zh: "平板支撑", ko: "플랭크" }, kicker: { ja: "MODE 03 / ISOMETRIC", en: "MODE 03 / ISOMETRIC", zh: "模式03 / 等长", ko: "모드 03 / 등척성" }, metric: { ja: "体幹の角度", en: "Body-line angle", zh: "身体线角度", ko: "몸 라인 각도" }, setup: { ja: "横向きに身体全体を入れます。腰が落ちたり反ったりしない、長い一直線を探します。", en: "Use a side view with your whole body in frame. Find one long line without dropping or arching the hips.", zh: "侧面拍摄全身。寻找一条不塌腰也不过度拱起的长直线。", ko: "옆모습으로 몸 전체를 잡습니다. 허리가 처지거나 꺾이지 않는 긴 직선을 찾으세요." } },
  lunge: { title: { ja: "ランジ", en: "Lunge", zh: "弓步", ko: "런지" }, kicker: { ja: "MODE 04 / SINGLE LEG", en: "MODE 04 / SINGLE LEG", zh: "模式04 / 单腿", ko: "모드 04 / 한쪽 다리" }, metric: { ja: "膝の角度", en: "Knee angle", zh: "膝盖角度", ko: "무릎 각도" }, setup: { ja: "正面または斜め前から、左右の足先まで画面に入れます。下りるときに軸足を急がせません。", en: "Use a front or diagonal view with both feet in frame. Keep the supporting leg patient on the way down.", zh: "从正面或斜前方拍摄，让双脚进入画面。下蹲时不要急着移动支撑腿。", ko: "정면 또는 대각선에서 양발이 보이게 합니다. 내려갈 때 중심 다리를 서두르지 마세요." } }
};
const exerciseText = (mode, field) => EXERCISE_LOCALES[mode]?.[field]?.[currentLanguage] || EXERCISE_LOCALES[mode]?.[field]?.en || EXERCISES[mode]?.[field] || "";

function updateExerciseLabels() {
  const labels = { squat: ["exerciseSquat", "exerciseSquatMeta"], pushup: ["exercisePushup", "exercisePushupMeta"], plank: ["exercisePlank", "exercisePlankMeta"], lunge: ["exerciseLunge", "exerciseLungeMeta"] };
  Object.entries(labels).forEach(([mode, [titleKey, metaKey]]) => {
    setText(`[data-exercise="${mode}"] strong`, tr(titleKey));
    setText(`[data-exercise="${mode}"] small`, tr(metaKey));
  });
  const definition = EXERCISES[activeExercise];
  setText("#modeKicker", exerciseText(activeExercise, "kicker"));
  setText("#modeTitle", exerciseText(activeExercise, "title"));
  setText("#stageMode", definition.stage);
  setText("#setupNote", exerciseText(activeExercise, "setup"));
  const unit = document.querySelector(".live-count b");
  if (unit) unit.textContent = definition.unit;
}

const LANDMARK = { leftShoulder: 11, rightShoulder: 12, leftElbow: 13, rightElbow: 14, leftWrist: 15, rightWrist: 16, leftHip: 23, rightHip: 24, leftKnee: 25, rightKnee: 26, leftAnkle: 27, rightAnkle: 28 };
const CONNECTIONS = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [24, 26], [26, 28]];

const $ = (selector) => document.querySelector(selector);
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const formatNumber = (value) => String(Math.round(value)).padStart(2, "0");
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);

let activeExercise = "squat";
let poseLandmarker = null;
let cameraStream = null;
let animationFrame = 0;
let lastVideoTime = -1;
let lastFrameAt = 0;
let session = null;
let tracker = null;
let libraryData = FALLBACK_EXERCISES;
let libraryLoaded = false;
let libraryAvailable = false;

function resetTracker() {
  tracker = { phase: "up", reps: 0, holdSeconds: 0, lastRepAt: 0, minAngle: 180, maxConfidence: 0, lastCue: tr("cueStandby"), lastMetric: null };
}

function resetSessionState() {
  session = { exercise: activeExercise, startedAt: Date.now(), reps: 0, quality: 0, durationSeconds: 0, samples: [] };
  resetTracker();
  updateMetrics({ metric: null, quality: null, confidence: null, cue: tr("cueStandby") });
}

function setText(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value;
}

function setBar(selector, percentage) {
  const element = $(selector);
  if (element) element.style.width = `${clamp(percentage, 0, 100)}%`;
}

function averagePoint(points, leftIndex, rightIndex) {
  const left = points[leftIndex];
  const right = points[rightIndex];
  if (!left || !right || (left.visibility ?? 1) < 0.32 || (right.visibility ?? 1) < 0.32) return null;
  return { x: (left.x + right.x) / 2, y: (left.y + right.y) / 2, z: (left.z + right.z) / 2, visibility: Math.min(left.visibility ?? 1, right.visibility ?? 1) };
}

function angleAt(a, b, c) {
  if (!a || !b || !c) return null;
  const ab = { x: a.x - b.x, y: a.y - b.y };
  const cb = { x: c.x - b.x, y: c.y - b.y };
  const dot = ab.x * cb.x + ab.y * cb.y;
  const magnitude = Math.sqrt(ab.x ** 2 + ab.y ** 2) * Math.sqrt(cb.x ** 2 + cb.y ** 2);
  if (!magnitude) return null;
  return Math.round((Math.acos(clamp(dot / magnitude, -1, 1)) * 180) / Math.PI);
}

function visiblePoint(points, index) {
  const point = points[index];
  return point && (point.visibility ?? 1) >= 0.32 ? point : null;
}

function getMetric(points, mode) {
  if (mode === "plank") {
    const shoulder = averagePoint(points, LANDMARK.leftShoulder, LANDMARK.rightShoulder);
    const hip = averagePoint(points, LANDMARK.leftHip, LANDMARK.rightHip);
    const ankle = averagePoint(points, LANDMARK.leftAnkle, LANDMARK.rightAnkle);
    return { value: angleAt(shoulder, hip, ankle), confidence: [shoulder, hip, ankle].filter(Boolean).reduce((sum, point) => sum + point.visibility, 0) / 3 };
  }
  if (mode === "pushup") {
    const left = angleAt(visiblePoint(points, LANDMARK.leftShoulder), visiblePoint(points, LANDMARK.leftElbow), visiblePoint(points, LANDMARK.leftWrist));
    const right = angleAt(visiblePoint(points, LANDMARK.rightShoulder), visiblePoint(points, LANDMARK.rightElbow), visiblePoint(points, LANDMARK.rightWrist));
    const values = [left, right].filter((value) => value !== null);
    const confidencePoints = [LANDMARK.leftShoulder, LANDMARK.leftElbow, LANDMARK.leftWrist, LANDMARK.rightShoulder, LANDMARK.rightElbow, LANDMARK.rightWrist].map((index) => visiblePoint(points, index)).filter(Boolean);
    return { value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null, confidence: confidencePoints.length ? confidencePoints.reduce((sum, point) => sum + (point.visibility ?? 1), 0) / confidencePoints.length : 0 };
  }
  const left = angleAt(visiblePoint(points, LANDMARK.leftHip), visiblePoint(points, LANDMARK.leftKnee), visiblePoint(points, LANDMARK.leftAnkle));
  const right = angleAt(visiblePoint(points, LANDMARK.rightHip), visiblePoint(points, LANDMARK.rightKnee), visiblePoint(points, LANDMARK.rightAnkle));
  const values = [left, right].filter((value) => value !== null);
  const confidencePoints = [LANDMARK.leftHip, LANDMARK.leftKnee, LANDMARK.leftAnkle, LANDMARK.rightHip, LANDMARK.rightKnee, LANDMARK.rightAnkle].map((index) => visiblePoint(points, index)).filter(Boolean);
  return { value: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null, confidence: confidencePoints.length ? confidencePoints.reduce((sum, point) => sum + (point.visibility ?? 1), 0) / confidencePoints.length : 0 };
}

function scoreMetric(value, definition) {
  if (value === null) return 0;
  const tolerance = definition === EXERCISES.plank ? 10 : 28;
  return clamp(100 - (Math.abs(value - definition.target) / tolerance) * 100, 0, 100);
}

function getCue(value, definition, mode, phase) {
  if (value === null) return tr("cueFullBody");
  if (mode === "plank") {
    if (value < 160) return tr("cuePlankLow");
    if (value > 179) return tr("cuePlankHigh");
    return tr("cuePlankGood");
  }
  if (phase === "down" && value > definition.down) return mode === "pushup" ? tr("cueBendElbow") : tr("cueGoDeeper");
  if (phase === "down" && value < definition.target - 22) return tr("cueEnough");
  if (mode === "pushup") return tr("cuePushLine");
  return tr("cueFeet");
}

function updateMetrics({ metric, quality, confidence, cue }) {
  const definition = EXERCISES[activeExercise];
  const metricText = metric === null || metric === undefined ? "—°" : `${Math.round(metric)}°`;
  setText("#angleMetric", metricText);
  setText("#heroAngle", metricText);
  setText("#angleCaption", metric === null || metric === undefined ? tr("metricStarts") : exerciseText(activeExercise, "metric"));
  setBar("#angleBar", metric === null ? 0 : (metric / 180) * 100);
  const score = quality === null || quality === undefined ? null : Math.round(quality);
  setText("#qualityMetric", score === null ? "—" : `${score}`);
  setText("#qualityLabel", score === null ? tr("statusStandby") : score >= 78 ? tr("qualityStable") : score >= 52 ? tr("qualityAdjust") : tr("qualityCheck"));
  setBar("#qualityBar", score ?? 0);
  setText("#confidenceMetric", confidence === null || confidence === undefined ? "—" : `${Math.round(confidence * 100)}%`);
  setText("#cueMetric", cue || "—");
  setText("#metricState", cameraStream ? "LIVE" : "STANDBY");
  setText("#heroReps", formatNumber(activeExercise === "plank" ? Math.floor(tracker?.holdSeconds ?? 0) : tracker?.reps ?? 0));
  setText("#liveReps", formatNumber(activeExercise === "plank" ? Math.floor(tracker?.holdSeconds ?? 0) : tracker?.reps ?? 0));
  const unit = document.querySelector(".live-count b");
  if (unit) unit.textContent = definition.unit;
}

function analyzePose(points, timestamp) {
  const definition = EXERCISES[activeExercise];
  const reading = getMetric(points, activeExercise);
  if (reading.value === null) {
    updateMetrics({ metric: null, quality: null, confidence: reading.confidence, cue: tr("cueFullBody") });
    return;
  }
  const quality = scoreMetric(reading.value, definition);
  const deltaSeconds = lastFrameAt ? Math.min(0.12, (timestamp - lastFrameAt) / 1000) : 0;
  if (activeExercise === "plank") {
    if (reading.value >= definition.down && reading.value <= definition.up) tracker.holdSeconds += deltaSeconds;
  } else {
    if (tracker.phase === "up" && reading.value < definition.down) {
      tracker.phase = "down";
      tracker.minAngle = reading.value;
    } else if (tracker.phase === "down") {
      tracker.minAngle = Math.min(tracker.minAngle, reading.value);
      if (reading.value > definition.up) {
        tracker.phase = "up";
        tracker.reps += 1;
        const now = performance.now();
        if (tracker.lastRepAt) setText("#tempoMetric", `${((now - tracker.lastRepAt) / 1000).toFixed(1)}`);
        tracker.lastRepAt = now;
        session.reps = tracker.reps;
        session.quality = Math.round((session.quality * Math.max(0, tracker.reps - 1) + quality) / tracker.reps);
      }
    }
  }
  tracker.maxConfidence = Math.max(tracker.maxConfidence, reading.confidence);
  tracker.lastMetric = reading.value;
  tracker.lastCue = getCue(reading.value, definition, activeExercise, tracker.phase);
  session.samples.push({ t: Date.now(), metric: Math.round(reading.value), quality: Math.round(quality) });
  if (session.samples.length > 180) session.samples.shift();
  updateMetrics({ metric: reading.value, quality, confidence: reading.confidence, cue: tracker.lastCue });
  lastFrameAt = timestamp;
}

function drawPose(points) {
  const canvas = $("#poseCanvas");
  const video = $("#cameraVideo");
  if (!canvas || !video) return;
  const width = video.videoWidth || 1280;
  const height = video.videoHeight || 720;
  if (canvas.width !== width) canvas.width = width;
  if (canvas.height !== height) canvas.height = height;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, width, height);
  const styles = getComputedStyle(document.documentElement);
  const signal = styles.getPropertyValue("--color-signal").trim() || "#a4d33c";
  const white = styles.getPropertyValue("--color-white").trim() || "#ffffff";
  context.lineWidth = Math.max(3, width / 420);
  context.strokeStyle = signal;
  CONNECTIONS.forEach(([from, to]) => {
    const a = visiblePoint(points, from);
    const b = visiblePoint(points, to);
    if (!a || !b) return;
    context.beginPath();
    context.moveTo(a.x * width, a.y * height);
    context.lineTo(b.x * width, b.y * height);
    context.stroke();
  });
  context.fillStyle = white;
  points.forEach((point) => {
    if ((point.visibility ?? 1) < 0.32) return;
    context.beginPath();
    context.arc(point.x * width, point.y * height, Math.max(4, width / 170), 0, Math.PI * 2);
    context.fill();
  });
}

async function ensurePoseLandmarker() {
  if (poseLandmarker) return poseLandmarker;
  setSystemStatus(tr("modelLoading"), false);
  const { FilesetResolver, PoseLandmarker } = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/+esm");
  const vision = await FilesetResolver.forVisionTasks(POSE_WASM);
  poseLandmarker = await PoseLandmarker.createFromOptions(vision, { baseOptions: { modelAssetPath: POSE_MODEL, delegate: "GPU" }, runningMode: "VIDEO", numPoses: 1, minPoseDetectionConfidence: 0.55, minPosePresenceConfidence: 0.55, minTrackingConfidence: 0.55 });
  return poseLandmarker;
}

function setSystemStatus(text, live) {
  const element = $("#systemStatus");
  if (!element) return;
  element.innerHTML = `<span class="status-dot"></span>${text}`;
  element.classList.toggle("is-live", Boolean(live));
}

async function processCameraFrame(now) {
  const video = $("#cameraVideo");
  if (!video || !cameraStream) return;
  if (poseLandmarker && video.readyState >= 2 && video.currentTime !== lastVideoTime) {
    lastVideoTime = video.currentTime;
    const result = poseLandmarker.detectForVideo(video, now);
    const points = result.landmarks?.[0];
    if (points) {
      drawPose(points);
      analyzePose(points, now);
    } else {
      updateMetrics({ metric: null, quality: null, confidence: 0, cue: tr("cueNoBody") });
    }
  }
  animationFrame = requestAnimationFrame(processCameraFrame);
}

async function startCamera() {
  if (cameraStream) {
    stopCamera();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setSystemStatus(tr("cameraUnsupported"), false);
    setText("#cueMetric", tr("cameraUnsupportedCopy"));
    return;
  }
  const button = $("#startCamera");
  button.disabled = true;
  button.innerHTML = tr("modelLoading");
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    const video = $("#cameraVideo");
    video.srcObject = cameraStream;
    await video.play();
    await ensurePoseLandmarker();
    resetSessionState();
    $("#cameraStage").classList.add("is-live");
    setSystemStatus(tr("statusAnalyzing"), true);
    setText("#stageMode", EXERCISES[activeExercise].stage);
    setText("#stageMessage", tr("statusAnalyzing"));
    button.disabled = false;
    button.innerHTML = tr("cameraStop");
    $("#finishSession").disabled = false;
    sendEvent("camera_start");
    animationFrame = requestAnimationFrame(processCameraFrame);
  } catch (error) {
    cameraStream = null;
    button.disabled = false;
    button.innerHTML = `<span>◎</span> ${tr("startCamera")}`;
    setSystemStatus(tr("statusLaunchFailed"), false);
    setText("#cueMetric", error?.name === "NotAllowedError" ? tr("cameraPermissionError") : tr("cameraError"));
  }
}

function stopCamera() {
  cancelAnimationFrame(animationFrame);
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  const video = $("#cameraVideo");
  if (video) video.srcObject = null;
  $("#cameraStage")?.classList.remove("is-live");
  setSystemStatus(tr("statusStandby"), false);
  const button = $("#startCamera");
  if (button) { button.disabled = false; button.innerHTML = `<span>◎</span> ${tr("startCamera")}`; }
  $("#finishSession").disabled = true;
  setText("#metricState", "STANDBY");
}

async function finishSession() {
  const duration = Math.max(0, Math.round((Date.now() - (session?.startedAt || Date.now())) / 1000));
  const reps = activeExercise === "plank" ? Math.floor(tracker?.holdSeconds ?? 0) : tracker?.reps ?? 0;
  if (reps > 0) {
    const record = { id: crypto.randomUUID(), date: new Date().toISOString(), exercise: activeExercise, reps, quality: session.quality || null, durationSeconds: duration };
    const history = readHistory();
    history.unshift(record);
    localStorage.setItem("form-lens-history", JSON.stringify(history.slice(0, 30)));
    renderHistory();
    sendSession(record);
  }
  sendEvent("session_finish");
  stopCamera();
  setText("#cueMetric", reps > 0 ? tr("saved") : tr("noReps"));
}

function readHistory() {
  try { return JSON.parse(localStorage.getItem("form-lens-history") || "[]"); } catch { return []; }
}

function renderHistory() {
  const history = readHistory();
  const list = $("#historyList");
  const labels = { squat: tr("exerciseSquat"), pushup: tr("exercisePushup"), plank: tr("exercisePlank"), lunge: tr("exerciseLunge") };
  if (!history.length) {
    list.innerHTML = `<div class="empty-state"><span>◎</span><strong>${escapeHtml(tr("emptyHistory"))}</strong><p>${escapeHtml(tr("emptyHistoryCopy"))}</p></div>`;
  } else {
    const locale = currentLanguage === "ja" ? "ja-JP" : currentLanguage === "zh" ? "zh-CN" : currentLanguage === "ko" ? "ko-KR" : "en-US";
    list.innerHTML = history.slice(0, 6).map((item) => `<div class="history-item"><div><strong>${escapeHtml(labels[item.exercise] || item.exercise)}</strong><small>${new Date(item.date).toLocaleDateString(locale, { month: "short", day: "numeric" })}</small></div><span>${formatNumber(item.reps)} ${item.exercise === "plank" ? "sec" : "reps"}</span><span>${item.quality ? `${item.quality} / 100` : "—"}</span><span>${item.durationSeconds || 0}s</span></div>`).join("");
  }
  const total = history.reduce((sum, item) => sum + Number(item.reps || 0), 0);
  setText("#weeklyReps", formatNumber(total));
  setText("#insightCopy", history.length ? tr("historyCount", { count: history.length }) : tr("insightEmpty"));
  const bars = document.querySelectorAll("#miniChart span");
  const recent = history.slice(0, 7).reverse();
  const max = Math.max(...recent.map((item) => item.reps), 1);
  bars.forEach((bar, index) => { const value = recent[index]?.reps || 0; bar.style.setProperty("--h", `${Math.max(8, (value / max) * 84)}%`); });
}

function exportHistory() {
  const blob = new Blob([JSON.stringify(readHistory(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `form-lens-history-${new Date().toISOString().slice(0, 10)}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6500);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal, headers: { accept: "application/json", ...(options.headers || {}) } });
    if (!response.ok) throw new Error(`API ${response.status}`);
    return await response.json();
  } finally { clearTimeout(timer); }
}

function sendEvent(eventName) {
  apiRequest("/api/events", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ site: "form-lens", eventName, exercise: activeExercise }) }).catch(() => {});
}

function sendSession(record) {
  apiRequest("/api/sessions", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ site: "form-lens", exercise: record.exercise, reps: record.reps, quality: record.quality, durationSeconds: record.durationSeconds }) }).catch(() => {});
}

function normaliseExercise(item) {
  const muscle = Array.isArray(item.muscles) ? item.muscles.map((m) => m.name || m).join(", ") : item.muscles || item.category || "general";
  return { id: item.id, name: item.name || "Unnamed exercise", description: (item.description || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim() || "公開運動データから取得したエクササイズです。", muscles: muscle, category: item.category || (String(muscle).toLowerCase().includes("leg") ? "legs" : "all"), source: item.source || "wger" };
}

function renderLibrary() {
  const query = $("#exerciseSearch").value.trim().toLowerCase();
  const filter = document.querySelector(".filter-pill.is-active")?.dataset.filter || "all";
  const filtered = libraryData.filter((item) => {
    const searchable = `${item.name} ${item.description} ${item.muscles}`.toLowerCase();
    return (!query || searchable.includes(query)) && (filter === "all" || String(item.category).toLowerCase().includes(filter) || String(item.muscles).toLowerCase().includes(filter));
  }).slice(0, 12);
  const grid = $("#libraryGrid");
  grid.innerHTML = filtered.length ? filtered.map((item, index) => `<article class="exercise-card"><div class="card-top"><span>${String(index + 1).padStart(2, "0")} / ATLAS</span><span>${escapeHtml(item.source)}</span></div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.description)}</p><span class="tag">${escapeHtml(item.muscles || item.category)}</span></article>`).join("") : `<div class="empty-state"><span>⌕</span><strong>${escapeHtml(tr("noResults"))}</strong><p>${escapeHtml(tr("noResultsCopy"))}</p></div>`;
}

async function loadLibrary() {
  try {
    const payload = await apiRequest("/api/exercises?limit=30");
    libraryAvailable = Array.isArray(payload.exercises) && payload.exercises.length > 0;
    if (libraryAvailable) libraryData = payload.exercises.map(normaliseExercise);
    setText("#libraryStatus", tr("libraryLive", { count: libraryData.length }));
    setText("#apiStatus", tr("apiOnline"));
  } catch {
    libraryAvailable = false;
    setText("#libraryStatus", tr("libraryFallback"));
    setText("#apiStatus", tr("apiBasic"));
  }
  libraryLoaded = true;
  renderLibrary();
}

async function loadWeather() {
  const button = $("#weatherButton");
  button.disabled = true;
  button.textContent = tr("weatherLoading");
  const showError = (message) => { setText("#weatherReadout", message); button.disabled = false; button.textContent = tr("weatherButton"); };
  if (!navigator.geolocation) { showError(tr("weatherNoGeo")); return; }
  navigator.geolocation.getCurrentPosition(async ({ coords }) => {
    try {
      const payload = await apiRequest(`/api/weather?lat=${encodeURIComponent(coords.latitude)}&lon=${encodeURIComponent(coords.longitude)}`);
      const current = payload.current;
      const code = Number(current.weather_code);
      const icon = code <= 3 ? "☼" : code <= 67 ? "☂" : "◌";
      $("#weatherReadout").innerHTML = `<span class="weather-icon">${icon}</span><strong>${Math.round(current.temperature_2m)}°</strong><span>${Math.round(current.wind_speed_10m)} KM/H WIND</span><small>${payload.timezone || "local time"}</small>`;
      sendEvent("weather_load");
    } catch { showError(tr("weatherUnavailable")); return; }
    button.disabled = false;
    button.textContent = tr("weatherRefresh");
  }, () => showError(tr("weatherLocError")), { enableHighAccuracy: false, timeout: 5000, maximumAge: 600000 });
}

function selectExercise(mode) {
  if (!EXERCISES[mode]) return;
  activeExercise = mode;
  document.querySelectorAll(".exercise-option").forEach((button) => button.classList.toggle("is-active", button.dataset.exercise === mode));
  const definition = EXERCISES[mode];
  setText("#modeKicker", exerciseText(mode, "kicker"));
  setText("#modeTitle", exerciseText(mode, "title"));
  setText("#stageMode", definition.stage);
  setText("#setupNote", exerciseText(mode, "setup"));
  resetSessionState();
  sendEvent("exercise_select");
}

function setupInteractions() {
  document.querySelectorAll(".exercise-option").forEach((button) => button.addEventListener("click", () => selectExercise(button.dataset.exercise)));
  document.querySelectorAll(".filter-pill").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll(".filter-pill").forEach((item) => item.classList.remove("is-active")); button.classList.add("is-active"); renderLibrary(); }));
  $("#exerciseSearch").addEventListener("input", renderLibrary);
  $("#languageSelect").addEventListener("change", (event) => { currentLanguage = event.target.value; localStorage.setItem("form-lens-language", currentLanguage); applyLanguage(); });
  $("#startCamera").addEventListener("click", startCamera);
  $("#finishSession").addEventListener("click", finishSession);
  $("#resetSession").addEventListener("click", () => { resetSessionState(); setText("#cueMetric", tr("resetDone")); });
  $("#clearHistory").addEventListener("click", () => { localStorage.removeItem("form-lens-history"); renderHistory(); });
  $("#exportHistory").addEventListener("click", exportHistory);
  $("#weatherButton").addEventListener("click", loadWeather);
  $("#themeToggle").addEventListener("click", () => { document.body.classList.toggle("theme-light"); localStorage.setItem("form-lens-theme", document.body.classList.contains("theme-light") ? "dark" : "light"); });
}

function boot() {
  if (localStorage.getItem("form-lens-theme") === "dark") document.body.classList.add("theme-light");
  resetSessionState();
  applyLanguage();
  renderHistory();
  setupInteractions();
  sendEvent("page_view");
  loadLibrary();
}

boot();

