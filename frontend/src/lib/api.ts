const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 60000; // 1 minute for long-running narrative

export interface HealthCheckResult {
  ok: boolean;
  message?: string;
  status?: string;
  service?: string;
}

/** Call before starting a narrative to verify backend is reachable. */
export async function checkBackendHealth(): Promise<HealthCheckResult> {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 5000);
    const res = await fetch(`${API_BASE}/api/health`, { signal: controller.signal });
    clearTimeout(id);
    if (!res.ok) {
      return { ok: false, message: `Backend returned ${res.status}` };
    }
    const data = (await res.json()) as { status?: string; service?: string };
    return {
      ok: true,
      status: data.status,
      service: data.service,
    };
  } catch (e) {
    const message = e instanceof Error ? e.message : "Request failed";
    return {
      ok: false,
      message: message.includes("abort") ? "Request timed out" : message,
    };
  }
}

export interface UserInput {
  family_name: string;
  region_of_origin: string;
  time_period: string;
  known_fragments?: string;
  language_or_ethnicity?: string;
  specific_interests?: string;
}

export interface NarrativeSegment {
  type: "text" | "image" | "audio" | "map";
  content?: string;
  media_data?: string;
  media_type?: string;
  trust_level: "historical" | "cultural" | "reconstructed";
  sequence: number;
  act?: number;
  is_hero?: boolean;
}

export interface IntakeResponse {
  session_id: string;
  message: string;
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = API_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(id);
  }
}

export async function createSession(input: UserInput): Promise<IntakeResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/api/intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Intake failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function submitFollowUp(
  sessionId: string,
  question: string
): Promise<{ segments: NarrativeSegment[] }> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/narrative/${sessionId}/followup`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }
  );
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Follow-up failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getStreamUrl(sessionId: string, audio: boolean = false): string {
  const base = `${API_BASE}/api/narrative/${sessionId}/stream`;
  return audio ? `${base}?audio=true` : base;
}

export async function generateAudio(text: string): Promise<{ audio_data: string; media_type: string } | null> {
  try {
    const res = await fetch(`${API_BASE}/api/audio/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
