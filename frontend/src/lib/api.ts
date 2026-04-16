export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT_MS = 60000; // 1 minute for long-running narrative
const SESSION_FETCH_TIMEOUT_MS = 10_000;

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

export interface SessionInfo {
  family_name: string;
  region_of_origin: string;
  time_period: string;
}

export interface SessionResponse {
  user_input: SessionInfo;
}

/** Fetch session by ID. Returns null if session not found (404) or request fails. */
export async function getSession(sessionId: string): Promise<SessionResponse | null> {
  try {
    const res = await fetchWithTimeout(
      `${API_BASE}/api/session/${sessionId}`,
      { method: "GET" },
      SESSION_FETCH_TIMEOUT_MS
    );
    if (res.status === 404) return null;
    if (!res.ok) return null;
    const data = (await res.json().catch(() => null)) as SessionResponse | null;
    return data?.user_input ? data : null;
  } catch {
    return null;
  }
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
  question: string,
  audio: boolean = false
): Promise<{ segments: NarrativeSegment[] }> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/narrative/${sessionId}/followup`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, audio }),
    }
  );
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Follow-up failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getStreamUrl(sessionId: string, audio: boolean = false, useAdk: boolean = true): string {
  const params = new URLSearchParams();
  if (audio) params.set("audio", "true");
  if (!useAdk) params.set("use_adk", "false");
  const qs = params.toString();
  return `${API_BASE}/api/narrative/${sessionId}/stream${qs ? `?${qs}` : ""}`;
}

export function getFollowUpStreamUrl(
  sessionId: string,
  question: string,
  audio: boolean = false,
): string {
  const params = new URLSearchParams({ question });
  if (audio) params.set("audio", "true");
  return `${API_BASE}/api/narrative/${sessionId}/followup-stream?${params.toString()}`;
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

// Sample narrative types and functions
export interface ArcOutline {
  title: string;
  acts: Array<{
    act_number: number;
    title: string;
    summary: string;
    ambient_track: string;
  }>;
}

export interface SampleNarrativeResponse {
  session_id: string;
  user_input: UserInput;
  arc_outline: ArcOutline;
  segments: NarrativeSegment[];
}

export async function getSampleNarrative(): Promise<SampleNarrativeResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/narrative/sample`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export function getSampleStreamUrl(): string {
  return `${API_BASE}/api/narrative/sample/stream`;
}

// Contribution (tip jar) API functions

export interface ContributionCheckoutResponse {
  checkout_url: string;
}

export async function createContributionCheckout(
  sessionId: string,
  amountCents: number,
  email?: string
): Promise<ContributionCheckoutResponse> {
  const res = await fetch(`${API_BASE}/api/contribute/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      amount_cents: amountCents,
      email: email || undefined,
    }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Checkout failed: ${res.status}`);
  }
  return res.json();
}

export async function trackContributionEvent(
  eventType: string,
  sessionId: string,
  amountCents?: number
): Promise<void> {
  // Fire-and-forget tracking via the main analytics endpoint pattern
  // This is called from the frontend for tip_card_shown, tip_card_dismissed, tip_amount_selected
  try {
    await fetch(`${API_BASE}/api/analytics/track`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_type: eventType,
        session_id: sessionId,
        metadata: amountCents ? { amount_cents: amountCents } : undefined,
      }),
    });
  } catch {
    // Silently ignore tracking errors
  }
}
