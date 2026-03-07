const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export async function createSession(input: UserInput): Promise<IntakeResponse> {
  const res = await fetch(`${API_BASE}/api/intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Intake failed: ${res.statusText}`);
  return res.json();
}

export async function submitFollowUp(
  sessionId: string,
  question: string
): Promise<{ segments: NarrativeSegment[] }> {
  const res = await fetch(`${API_BASE}/api/narrative/${sessionId}/followup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`Follow-up failed: ${res.statusText}`);
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
