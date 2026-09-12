type ExerciseRow = {
  id: number;
  name: string;
  description: string;
  muscles: string;
  equipment: string;
  category: string;
  source: string;
};

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type, accept",
  "access-control-max-age": "86400"
};

const FALLBACK_EXERCISES: ExerciseRow[] = [
  { id: -1, name: "Bodyweight Squat", description: "A knee-dominant lower body movement. Keep your ribcage stacked over your pelvis.", muscles: "legs", equipment: "none", category: "legs", source: "FORM LENS" },
  { id: -2, name: "Push-up", description: "A bodyweight press that asks the shoulders, elbows and trunk to move as one line.", muscles: "chest", equipment: "none", category: "chest", source: "FORM LENS" },
  { id: -3, name: "Plank", description: "An isometric trunk hold. Think long from the crown of the head to the heels.", muscles: "core", equipment: "none", category: "core", source: "FORM LENS" },
  { id: -4, name: "Forward Lunge", description: "A split-stance leg pattern for balance, control and single-leg strength.", muscles: "legs", equipment: "none", category: "legs", source: "FORM LENS" },
  { id: -5, name: "Glute Bridge", description: "Lift through the hips without arching the lower back at the top.", muscles: "glutes", equipment: "none", category: "legs", source: "FORM LENS" },
  { id: -6, name: "Wall Sit", description: "A quiet lower-body hold that makes time and knee angle visible.", muscles: "legs", equipment: "wall", category: "legs", source: "FORM LENS" }
];

const json = (payload: unknown, status = 200, extraHeaders: Record<string, string> = {}) => new Response(JSON.stringify(payload), {
  status,
  headers: { "content-type": "application/json; charset=UTF-8", ...CORS_HEADERS, "cache-control": "no-store", ...extraHeaders }
});

const cleanText = (value: unknown, fallback = "") => String(value ?? fallback).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 1200);

function externalExercise(raw: Record<string, unknown>): ExerciseRow | null {
  const id = Number(raw.id);
  if (!Number.isInteger(id)) return null;
  const translations = Array.isArray(raw.translations) ? raw.translations as Array<Record<string, unknown>> : [];
  const translation = translations.find((item) => Number(item.language) === 2) || translations[0] || {};
  const category = raw.category && typeof raw.category === "object" ? (raw.category as Record<string, unknown>).name : raw.category;
  const muscles = Array.isArray(raw.muscles) ? raw.muscles.map((muscle) => cleanText((muscle as Record<string, unknown>).name || muscle)).filter(Boolean).join(", ") : "general";
  const equipment = Array.isArray(raw.equipment) ? raw.equipment.map((item) => cleanText((item as Record<string, unknown>).name || item)).filter(Boolean).join(", ") : "none";
  const categoryName = cleanText(category, "general").toLowerCase();
  return { id, name: cleanText(translation.name || raw.name, `Exercise ${id}`), description: cleanText(translation.description || raw.description, "公開運動データから取得したエクササイズです。"), muscles: muscles || "general", equipment: equipment || "none", category: categoryName, source: "wger" };
}

async function fetchExternalJson(url: string, ctx: ExecutionContext): Promise<unknown> {
  const cacheKey = new Request(url, { method: "GET" });
  const cached = await caches.default.match(cacheKey);
  if (cached) return cached.json();
  const response = await fetch(url, { headers: { accept: "application/json", "user-agent": "FORM-LENS/1.0" } });
  if (!response.ok) throw new Error(`External API returned ${response.status}`);
  const payload: unknown = await response.json();
  const cacheResponse = json(payload, 200, { "cache-control": "public, max-age=900" });
  ctx.waitUntil(caches.default.put(cacheKey, cacheResponse.clone()));
  return payload;
}

async function ensureCatalog(env: Env, ctx: ExecutionContext): Promise<void> {
  const existing = await env.DB.prepare("SELECT COUNT(*) AS count FROM exercise_catalog").first<{ count: number }>();
  if (Number(existing?.count || 0) > 0) return;
  let rows = FALLBACK_EXERCISES;
  try {
    const endpoint = `${env.WGER_API_BASE}/exerciseinfo/?language=2&limit=40&status=2&ordering=name`;
    const payload = await fetchExternalJson(endpoint, ctx) as { results?: unknown[] };
    const externalRows = (payload.results || []).map((item) => externalExercise(item as Record<string, unknown>)).filter((item): item is ExerciseRow => Boolean(item));
    if (externalRows.length) rows = externalRows;
  } catch {
    // The curated fallback keeps the app useful when the public API is unavailable.
  }
  const statements = rows.map((row) => env.DB.prepare("INSERT OR IGNORE INTO exercise_catalog (id, name, description, muscles, equipment, category, source) VALUES (?, ?, ?, ?, ?, ?, ?)").bind(row.id, row.name, row.description, row.muscles, row.equipment, row.category, row.source));
  if (statements.length) await env.DB.batch(statements);
}

async function listExercises(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
  await ensureCatalog(env, ctx);
  const url = new URL(request.url);
  const query = cleanText(url.searchParams.get("q"), "").toLowerCase();
  const category = cleanText(url.searchParams.get("category"), "").toLowerCase();
  const limit = Math.min(50, Math.max(1, Number(url.searchParams.get("limit") || 30)));
  const pattern = `%${query}%`;
  const categoryPattern = `%${category}%`;
  const result = await env.DB.prepare("SELECT id, name, description, muscles, equipment, category, source FROM exercise_catalog WHERE (? = '' OR lower(name) LIKE ? OR lower(description) LIKE ? OR lower(muscles) LIKE ?) AND (? = '' OR lower(category) LIKE ? OR lower(muscles) LIKE ?) ORDER BY name COLLATE NOCASE LIMIT ?")
    .bind(query, pattern, pattern, pattern, category, categoryPattern, categoryPattern, limit).all<ExerciseRow>();
  return json({ source: "wger public API / cached in commomd1", count: result.results.length, exercises: result.results });
}

async function getExercise(request: Request, env: Env, ctx: ExecutionContext, idText: string): Promise<Response> {
  await ensureCatalog(env, ctx);
  const id = Number(idText);
  if (!Number.isInteger(id)) return json({ error: "invalid exercise id" }, 400);
  const result = await env.DB.prepare("SELECT id, name, description, muscles, equipment, category, source FROM exercise_catalog WHERE id = ?").bind(id).first<ExerciseRow>();
  return result ? json({ exercise: result }) : json({ error: "exercise not found" }, 404);
}

async function recordEvent(request: Request, env: Env): Promise<Response> {
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 2048) return json({ error: "payload too large" }, 413);
  const body = await request.json() as { site?: unknown; eventName?: unknown; exercise?: unknown };
  const site = cleanText(body.site, "unknown").slice(0, 40);
  const eventName = cleanText(body.eventName, "event").slice(0, 60);
  const exercise = cleanText(body.exercise, "").slice(0, 40) || null;
  await env.DB.prepare("INSERT INTO activity_events (site, event_name, exercise) VALUES (?, ?, ?)").bind(site, eventName, exercise).run();
  return json({ ok: true }, 201);
}

async function recordSession(request: Request, env: Env): Promise<Response> {
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 2048) return json({ error: "payload too large" }, 413);
  const body = await request.json() as { site?: unknown; exercise?: unknown; reps?: unknown; quality?: unknown; durationSeconds?: unknown };
  const site = cleanText(body.site, "unknown").slice(0, 40);
  const exercise = cleanText(body.exercise, "general").slice(0, 40);
  const reps = clampInt(body.reps, 0, 9999);
  const quality = body.quality === null || body.quality === undefined ? null : clampInt(body.quality, 0, 100);
  const duration = clampInt(body.durationSeconds, 0, 86400);
  await env.DB.prepare("INSERT INTO session_summaries (site, exercise, reps, quality, duration_seconds) VALUES (?, ?, ?, ?, ?)").bind(site, exercise, reps, quality, duration).run();
  return json({ ok: true }, 201);
}

function clampInt(value: unknown, min: number, max: number): number {
  const number = Number(value);
  return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : min;
}

async function getInsights(env: Env, site: string): Promise<Response> {
  const safeSite = cleanText(site, "form-lens").slice(0, 40);
  const summary = await env.DB.prepare("SELECT COUNT(*) AS sessions, COALESCE(SUM(reps), 0) AS reps, COALESCE(AVG(quality), 0) AS quality FROM session_summaries WHERE site = ? AND created_at >= datetime('now', '-30 day')").bind(safeSite).first<{ sessions: number; reps: number; quality: number }>();
  const popular = await env.DB.prepare("SELECT exercise, SUM(reps) AS reps FROM session_summaries WHERE site = ? AND created_at >= datetime('now', '-30 day') GROUP BY exercise ORDER BY reps DESC LIMIT 5").bind(safeSite).all<{ exercise: string; reps: number }>();
  return json({ site: safeSite, period: "30d", sessions: Number(summary?.sessions || 0), reps: Number(summary?.reps || 0), averageQuality: Math.round(Number(summary?.quality || 0)), popular: popular.results });
}

async function getWeather(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
  const url = new URL(request.url);
  const lat = Number(url.searchParams.get("lat"));
  const lon = Number(url.searchParams.get("lon"));
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) return json({ error: "invalid coordinates" }, 400);
  const endpoint = new URL(env.OPEN_METEO_BASE);
  endpoint.searchParams.set("latitude", lat.toFixed(3));
  endpoint.searchParams.set("longitude", lon.toFixed(3));
  endpoint.searchParams.set("current", "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m");
  endpoint.searchParams.set("timezone", "auto");
  try {
    const payload = await fetchExternalJson(endpoint.toString(), ctx) as Record<string, unknown>;
    return json({ timezone: payload.timezone, current: payload.current, source: "Open-Meteo" }, 200, { "cache-control": "public, max-age=300" });
  } catch { return json({ error: "weather service unavailable" }, 502); }
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_HEADERS });
    const url = new URL(request.url);
    try {
      if (request.method === "GET" && url.pathname === "/health") return json({ ok: true, service: "form-lens-api", database: "commomd1" }, 200, { "cache-control": "no-store" });
      if (request.method === "GET" && url.pathname === "/api/exercises") return listExercises(request, env, ctx);
      if (request.method === "GET" && url.pathname.startsWith("/api/exercises/")) return getExercise(request, env, ctx, url.pathname.split("/").pop() || "");
      if (request.method === "GET" && url.pathname === "/api/insights") return getInsights(env, url.searchParams.get("site") || "form-lens");
      if (request.method === "GET" && url.pathname === "/api/weather") return getWeather(request, env, ctx);
      if (request.method === "POST" && url.pathname === "/api/events") return recordEvent(request, env);
      if (request.method === "POST" && url.pathname === "/api/sessions") return recordSession(request, env);
      if (url.pathname === "/") return json({ service: "FORM LENS API", endpoints: ["/health", "/api/exercises", "/api/insights", "/api/weather"] });
      return json({ error: "not found" }, 404);
    } catch (error) {
      console.error(JSON.stringify({ service: "form-lens-api", path: url.pathname, error: error instanceof Error ? error.message : "unknown" }));
      return json({ error: "internal error" }, 500);
    }
  }
};

