const API_BASE = "https://form-lens-api.hurukigeoetym.workers.dev";
const POSE_WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22/wasm";
const POSE_MODEL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

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

function resetTracker() {
  tracker = { phase: "up", reps: 0, holdSeconds: 0, lastRepAt: 0, minAngle: 180, maxConfidence: 0, lastCue: "カメラを起動すると、フォームのヒントがここに出ます。", lastMetric: null };
}

function resetSessionState() {
  session = { exercise: activeExercise, startedAt: Date.now(), reps: 0, quality: 0, durationSeconds: 0, samples: [] };
  resetTracker();
  updateMetrics({ metric: null, quality: null, confidence: null, cue: "カメラを起動すると、フォームのヒントがここに出ます。" });
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
  if (value === null) return "全身を画面に入れると、フォームのヒントが出ます。";
  if (mode === "plank") {
    if (value < 160) return "腰が落ちています。おへそを背中へ近づける意識で。";
    if (value > 179) return "少し反り気味です。肋骨を静かに下げます。";
    return "いい一直線。呼吸を止めず、その姿勢を保ちます。";
  }
  if (phase === "down" && value > definition.down) return `もう少し${mode === "pushup" ? "肘を曲げて" : "深く"}、ゆっくり動きます。`;
  if (phase === "down" && value < definition.target - 22) return "深さは十分。反動を使わずに戻ります。";
  if (mode === "pushup") return "肩・腰・足首をひとつの線に保ちます。";
  return "足裏で床を押し、膝とつま先の向きをそろえます。";
}

function updateMetrics({ metric, quality, confidence, cue }) {
  const definition = EXERCISES[activeExercise];
  const metricText = metric === null || metric === undefined ? "—°" : `${Math.round(metric)}°`;
  setText("#angleMetric", metricText);
  setText("#heroAngle", metricText);
  setText("#angleCaption", metric === null || metric === undefined ? "動き始めると計測" : definition.metric);
  setBar("#angleBar", metric === null ? 0 : (metric / 180) * 100);
  const score = quality === null || quality === undefined ? null : Math.round(quality);
  setText("#qualityMetric", score === null ? "—" : `${score}`);
  setText("#qualityLabel", score === null ? "待機中" : score >= 78 ? "安定" : score >= 52 ? "調整" : "要確認");
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
    updateMetrics({ metric: null, quality: null, confidence: reading.confidence, cue: "全身を画面に入れると、フォームのヒントが出ます。" });
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
  setSystemStatus("モデル読み込み中…", false);
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
      updateMetrics({ metric: null, quality: null, confidence: 0, cue: "身体が見つかりません。少しカメラから離れてください。" });
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
    setSystemStatus("カメラ非対応", false);
    setText("#cueMetric", "このブラウザではカメラを利用できません。HTTPSのページでお試しください。");
    return;
  }
  const button = $("#startCamera");
  button.disabled = true;
  button.innerHTML = "モデルを準備中…";
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    const video = $("#cameraVideo");
    video.srcObject = cameraStream;
    await video.play();
    await ensurePoseLandmarker();
    resetSessionState();
    $("#cameraStage").classList.add("is-live");
    setSystemStatus("分析中", true);
    setText("#stageMode", EXERCISES[activeExercise].stage);
    setText("#stageMessage", "分析中");
    button.disabled = false;
    button.innerHTML = "■ 分析を停止";
    $("#finishSession").disabled = false;
    sendEvent("camera_start");
    animationFrame = requestAnimationFrame(processCameraFrame);
  } catch (error) {
    cameraStream = null;
    button.disabled = false;
    button.innerHTML = "<span>◎</span> カメラを起動";
    setSystemStatus("起動できません", false);
    setText("#cueMetric", error?.name === "NotAllowedError" ? "カメラの許可が必要です。ブラウザのアドレスバーから許可してください。" : "カメラを起動できませんでした。HTTPS接続と端末のカメラを確認してください。");
  }
}

function stopCamera() {
  cancelAnimationFrame(animationFrame);
  if (cameraStream) cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  const video = $("#cameraVideo");
  if (video) video.srcObject = null;
  $("#cameraStage")?.classList.remove("is-live");
  setSystemStatus("待機中", false);
  const button = $("#startCamera");
  if (button) { button.disabled = false; button.innerHTML = "<span>◎</span> カメラを起動"; }
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
  setText("#cueMetric", reps > 0 ? "セッションを保存しました。動きのメモは履歴から確認できます。" : "回数が記録されなかったため、履歴には保存していません。");
}

function readHistory() {
  try { return JSON.parse(localStorage.getItem("form-lens-history") || "[]"); } catch { return []; }
}

function renderHistory() {
  const history = readHistory();
  const list = $("#historyList");
  const labels = { squat: "スクワット", pushup: "腕立て伏せ", plank: "プランク", lunge: "ランジ" };
  if (!history.length) {
    list.innerHTML = `<div class="empty-state"><span>◎</span><strong>まだセッションがありません</strong><p>カメラを起動して、1回分の動きを記録しましょう。</p></div>`;
  } else {
    list.innerHTML = history.slice(0, 6).map((item) => `<div class="history-item"><div><strong>${escapeHtml(labels[item.exercise] || item.exercise)}</strong><small>${new Date(item.date).toLocaleDateString("ja-JP", { month: "short", day: "numeric" })}</small></div><span>${formatNumber(item.reps)} ${item.exercise === "plank" ? "sec" : "reps"}</span><span>${item.quality ? `${item.quality} / 100` : "—"}</span><span>${item.durationSeconds || 0}s</span></div>`).join("");
  }
  const total = history.reduce((sum, item) => sum + Number(item.reps || 0), 0);
  setText("#weeklyReps", formatNumber(total));
  setText("#insightCopy", history.length ? `${history.length}回の記録があります。前回の自分のテンポと、今日の1回を比べてみてください。` : "1回目は、記録を始めるための1回。数字は比較ではなく、次の動きを選ぶメモです。");
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
  grid.innerHTML = filtered.length ? filtered.map((item, index) => `<article class="exercise-card"><div class="card-top"><span>${String(index + 1).padStart(2, "0")} / ATLAS</span><span>${escapeHtml(item.source)}</span></div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.description)}</p><span class="tag">${escapeHtml(item.muscles || item.category)}</span></article>`).join("") : `<div class="empty-state"><span>⌕</span><strong>該当する種目がありません</strong><p>検索語を変えて、別の動きを探してみてください。</p></div>`;
}

async function loadLibrary() {
  try {
    const payload = await apiRequest("/api/exercises?limit=30");
    if (Array.isArray(payload.exercises) && payload.exercises.length) libraryData = payload.exercises.map(normaliseExercise);
    setText("#libraryStatus", `${libraryData.length}種目を表示中 · Workers API経由`);
    setText("#apiStatus", "API接続中");
  } catch {
    setText("#libraryStatus", "基本種目を表示中 · APIは一時的に利用できません");
    setText("#apiStatus", "基本モード");
  }
  renderLibrary();
}

async function loadWeather() {
  const button = $("#weatherButton");
  button.disabled = true;
  button.textContent = "位置情報を確認中…";
  const showError = (message) => { setText("#weatherReadout", message); button.disabled = false; button.textContent = "現在地の天気を読む"; };
  if (!navigator.geolocation) { showError("この端末では位置情報を利用できません。"); return; }
  navigator.geolocation.getCurrentPosition(async ({ coords }) => {
    try {
      const payload = await apiRequest(`/api/weather?lat=${encodeURIComponent(coords.latitude)}&lon=${encodeURIComponent(coords.longitude)}`);
      const current = payload.current;
      const code = Number(current.weather_code);
      const icon = code <= 3 ? "☼" : code <= 67 ? "☂" : "◌";
      $("#weatherReadout").innerHTML = `<span class="weather-icon">${icon}</span><strong>${Math.round(current.temperature_2m)}°</strong><span>${Math.round(current.wind_speed_10m)} KM/H WIND</span><small>${payload.timezone || "local time"}</small>`;
      sendEvent("weather_load");
    } catch { showError("天気データを取得できませんでした。"); return; }
    button.disabled = false;
    button.textContent = "現在地を更新";
  }, () => showError("位置情報が許可されていません。許可なしでもライブ分析は使えます。"), { enableHighAccuracy: false, timeout: 5000, maximumAge: 600000 });
}

function selectExercise(mode) {
  if (!EXERCISES[mode]) return;
  activeExercise = mode;
  document.querySelectorAll(".exercise-option").forEach((button) => button.classList.toggle("is-active", button.dataset.exercise === mode));
  const definition = EXERCISES[mode];
  setText("#modeKicker", definition.kicker);
  setText("#modeTitle", definition.title);
  setText("#stageMode", definition.stage);
  setText("#setupNote", definition.setup);
  resetSessionState();
  sendEvent("exercise_select");
}

function setupInteractions() {
  document.querySelectorAll(".exercise-option").forEach((button) => button.addEventListener("click", () => selectExercise(button.dataset.exercise)));
  document.querySelectorAll(".filter-pill").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll(".filter-pill").forEach((item) => item.classList.remove("is-active")); button.classList.add("is-active"); renderLibrary(); }));
  $("#exerciseSearch").addEventListener("input", renderLibrary);
  $("#startCamera").addEventListener("click", startCamera);
  $("#finishSession").addEventListener("click", finishSession);
  $("#resetSession").addEventListener("click", () => { resetSessionState(); setText("#cueMetric", "セッションをリセットしました。最初の1回をどうぞ。"); });
  $("#clearHistory").addEventListener("click", () => { localStorage.removeItem("form-lens-history"); renderHistory(); });
  $("#exportHistory").addEventListener("click", exportHistory);
  $("#weatherButton").addEventListener("click", loadWeather);
  $("#themeToggle").addEventListener("click", () => { document.body.classList.toggle("theme-light"); localStorage.setItem("form-lens-theme", document.body.classList.contains("theme-light") ? "dark" : "light"); });
}

function boot() {
  if (localStorage.getItem("form-lens-theme") === "dark") document.body.classList.add("theme-light");
  resetSessionState();
  renderHistory();
  setupInteractions();
  loadLibrary();
}

boot();

