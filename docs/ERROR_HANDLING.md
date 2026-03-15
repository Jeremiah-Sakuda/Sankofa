# Error Handling Report — Sankofa

This document describes how errors are handled across the stack and recommends improvements.

---

## 1. Current State

### 1.1 Backend

#### 1.1.1 Configuration & Startup

| Location | Behavior |
|----------|----------|
| `app/config.py` | `Settings.validate()` raises `ValueError` for missing/invalid config (e.g. no `GOOGLE_CLOUD_PROJECT` when using Vertex/Firestore). |
| `app/main.py` lifespan | Calls `settings.validate()`; in **production** re-raises, in **development** logs a warning and continues. Logs Gemini key presence (length only) and session store type. |

**Gap:** In development, invalid config (e.g. empty API key) is only warned; narrative generation then fails at first Gemini call with a generic or translated error.

#### 1.1.2 Request Validation (Pydantic)

- **Intake:** `UserInput` enforces required fields and max lengths (`MAX_FIELD_LEN`, `MAX_FREE_TEXT_LEN`).
- **Follow-up:** `FollowUpRequest` enforces `question` length.
- **Audio:** `AudioGenerateRequest` enforces `text` and `voice` length.

FastAPI turns validation failures into **422 Unprocessable Entity** with a JSON body listing field errors. The frontend does not currently parse or display these field-level messages; it relies on generic “Intake failed” / “Follow-up failed” from non-OK status.

#### 1.1.3 HTTP Semantics

| Route | Condition | Response |
|-------|-----------|----------|
| `GET /api/session/{id}` | Session missing | 404, `detail="Session not found"` |
| `GET /api/narrative/{id}/stream` | Session missing | 404 |
| `GET /api/narrative/{id}/stream` | Already generating | 409, `detail="Narrative already generating"` |
| `POST /api/narrative/{id}/followup` | Session missing | 404 |
| `POST /api/audio/generate` | TTS returns `None` | 500, `detail="Audio generation failed"` |

No global exception handler is registered. Unhandled exceptions (e.g. from Firestore or Gemini) become **500** with Starlette’s default response; the body may expose raw exception messages in non-production.

#### 1.1.4 Narrative Stream (SSE)

- **Before stream:** 404/409 as above.
- **During stream:**
  - `asyncio.TimeoutError`: one SSE event `event: error`, `data: {"error": "The request took too long. Check your API key and network, then try again."}`; then generator exits.
  - Any other exception: logged with `exc_info=True`, same SSE `error` event with `str(e)`, then `finally` sets `session.is_generating = False` and calls `session_store.update(session)`.
- **TTS per segment:** Failures are caught per segment; a warning is logged and the stream continues without that audio. No error event is sent for partial TTS failure.

**Gaps:**

- If `session_store.update(session)` in `finally` fails (e.g. Firestore timeout), that exception propagates and can mask the original error or produce a 500 after the stream has already started.
- Timeout message does not distinguish “arc planning” vs “narrative generation” timeout.
- Raw exception messages (e.g. from Gemini) are sent to the client and may be technical or unsuitable for end users.

#### 1.1.5 Gemini Service

- **API key:** Detects known API-key-invalid phrasing and re-raises with a fixed, user-facing message (link to aistudio, set `GOOGLE_API_KEY`, restart).
- **Model not found (404):** Re-raises with a short message and link to docs.
- **Text-only model used for image narrative:** Re-raises with a message to set `GEMINI_IMAGE_MODEL=gemini-2.5-flash-image`.
- All Gemini errors are logged with `logger.error(..., exc_info=True)` before re-raising.
- Empty or no candidates: logged as warning; narrative returns empty segment list (no exception).

#### 1.1.6 TTS Service

- Input: returns `None` if text is empty or too short.
- Exceptions in `_generate_narration_sync`: caught in `generate_narration()`, logged as warning with `exc_info=True`, and converted to `None` (no exception). Callers (narrative stream, audio route) handle `None` by either skipping the segment or returning 500.

**Gap:** TTS-specific errors (e.g. quota, unsupported voice) are not translated into user-facing messages; the client only sees “Audio generation failed” or a generic stream error.

#### 1.1.7 Narrative Planner

- Arc JSON parsing: on `json.JSONDecodeError` or `IndexError`, falls back to `_fallback_arc(user_input)` and logs a warning. Generation continues with the template arc.
- Ambient track validation: after a successful arc parse, `_validate_ambient_tracks` checks each act's `ambient_track` against the five valid filenames (`fire.wav`, `wind.wav`, `nature.wav`, `market.wav`, `drums.wav`). Invalid or missing values are silently replaced with per-act defaults (`wind.wav`, `market.wav`, `drums.wav` for acts 1–3). The fallback arc already includes valid defaults.

#### 1.1.8 Session Store

- **In-memory:** No I/O; no explicit error handling.
- **Firestore:** No try/except in `create`, `get`, `update`, or `exists`. Any Firestore error (permissions, network, not found, etc.) propagates and results in a 500 or aborted stream.

#### 1.1.9 Security / Middleware

- **SecurityHeadersMiddleware:** Rejects large body by `Content-Length` and returns 413. If `int(content_length)` raises `ValueError` or `TypeError`, the current code still returns **413** (see “Bugs” below). Intended behavior: on parse error, ignore and continue.

---

### 1.2 Frontend

#### 1.2.1 API Layer (`lib/api.ts`)

| Function | On failure | User-visible |
|----------|------------|--------------|
| `checkBackendHealth()` | Catches all errors; returns `{ ok: false, message }`. Maps abort to “Request timed out”. | Yes, via Test API connection |
| `getSession()` | 404 or any error → returns `null`. No thrown error. | Caller shows “session invalid” |
| `createSession()` | Non-OK → reads `detail` from JSON or falls back to status text; throws `Error(message)`. | Yes, IntakeFlow shows message |
| `submitFollowUp()` | Same as createSession. | Yes, NarrativeStream footer |
| `generateAudio()` | Non-OK or throw → returns `null`. No message. | Silent failure |
| SSE stream | No direct API call; `useSSEStream` uses `fetchEventSource`. | See below |

Timeouts: `checkBackendHealth` uses 5s; `fetchWithTimeout` used for intake/follow-up (default 60s). Session fetch uses 10s.

#### 1.2.2 SSE Stream (`useSSEStream.ts`)

- **`event: error`:** Parses `data` as `{ error?: string }`, sets state to `setError(data?.error || "Generation failed")`, sets `isStreaming` false.
- **`onerror`:** Sets error to `err?.message || "Connection lost"` and stops streaming (unless aborted).
- **Parse error in `onmessage`:** Sets error to `"Received malformed stream data"` and stops.
- **Abort:** `onerror` is not treated as fatal when the controller is already aborted; state is still set.

**Gaps:**

- No distinction between “server sent error event” and “connection dropped” for retry or messaging.
- No timeout on the SSE connection itself (only backend step timeouts).
- Backend can send raw exception text; frontend shows it as-is (may be technical or long).

#### 1.2.3 UI Surfaces

| Place | What’s shown | Retry / recovery |
|-------|----------------|------------------|
| IntakeFlow | Validation (required, max length); submit error from `createSession` | User corrects and resubmits; “Try again” not offered explicitly |
| Narrative page (pre-stream) | Session invalid; “Test API connection” result | Link to start over; Retry by re-running test |
| Narrative page (streaming) | “Sankofa is reaching back…”; progress step; after 90s no segments → “taking longer” + Retry | Retry button aborts, resets, allows Begin again |
| Narrative page (error) | `error` string + “Try again” button | Try again resets and allows Begin again |
| NarrativeStream (footer) | `followUpError` or validation error (e.g. 500 chars) | User can edit and re-ask |
| NarrationBar / AudioPlayer | `loadError` → “Audio unavailable” / disabled play | No retry; user can skip or reload |

**Gaps:**

- No React error boundary; an uncaught render error can blank the app.
- No global “offline” or “server unreachable” handling.
- Follow-up 422 (validation) is shown as generic “Follow-up failed” without field-level hint.

---

## 2. Bugs Identified

1. **Audio route return value (`backend/app/routes/audio.py`)**  
   `generate_narration()` returns `(base64_string, mime_type)`. The route assigns this tuple to `audio_data` and returns `{"audio_data": audio_data, "media_type": "audio/wav"}`. So `audio_data` is the whole tuple, not the base64 string. The frontend expects `audio_data` to be a string. **Fix:** Unpack the tuple and return `{"audio_data": b64, "media_type": mime}`.

2. **SecurityHeadersMiddleware (`backend/app/main.py`)**  
   In the `except (ValueError, TypeError)` block the code does `pass` but then unconditionally returns 413. So any invalid `Content-Length` (e.g. non-numeric) results in 413 instead of continuing. **Fix:** In the except block, only `pass` (or skip the 413) and fall through to `call_next(request)`.

---

## 3. Recommendations

### 3.1 High impact

- **Fix the two bugs above** (audio route, middleware).
- **Sanitize stream error messages:** In the narrative stream’s `except` block, map known exceptions (e.g. `ValueError` from Gemini helpers) to a short user-facing message; do not send `str(e)` for arbitrary exceptions (log full trace server-side only).
- **Guard `session_store.update(session)` in stream `finally`:** Wrap in try/except; log failure and optionally retry once. Avoid letting a store failure override the SSE error response.
- **Firestore store:** Add try/except in `get`, `create`, `update`; convert to appropriate HTTP status (e.g. 503 for transient errors, 500 for unexpected) or re-raise with a safe message so the API layer can return a consistent error body.

### 3.2 Medium impact

- **Global exception handler (FastAPI):** Register a handler for `Exception` that logs the full trace, returns 500 with a generic message in production, and (optionally) returns more detail in development.
- **Validation error format:** Either keep 422 as-is and improve frontend parsing of `detail` to show field errors, or add a custom `RequestValidationError` handler that returns a simpler `{ "message": "...", "errors": [...] }` for the client.
- **SSE connection timeout:** On the frontend, start a timer when the stream starts; if no event (e.g. no `status`/segment) is received within e.g. 120s, close the stream and set a “Request timed out” error.
- **React error boundary:** Add an error boundary around the main app (or narrative flow) with a fallback UI and “Reload” so a single component error does not blank the page.

### 3.3 Lower priority

- **Config validation at startup:** In development, optionally fail fast if `GOOGLE_API_KEY` is missing so the cause is clear before the first request.
- **TTS-specific messages:** In TTS service or audio route, catch known Gemini TTS errors (e.g. quota, voice) and return 503 or 400 with a short message instead of generic “Audio generation failed”.
- **Distinguish stream failure modes:** Send a small set of error “codes” or types in the SSE `error` event (e.g. `timeout`, `api_error`, `server_error`) so the frontend can show a specific message or retry policy.
- **Offline / network:** Use `navigator.onLine` or a failed fetch to show a banner when the app is offline or the backend is unreachable, with a retry or “Check connection” message.

---

## 4. Summary Table

| Layer | What’s in place | Main gaps |
|-------|------------------|-----------|
| Backend config | Validate on startup; in dev only warn | Dev can proceed with invalid config; first failure is at Gemini call |
| Backend validation | Pydantic + FastAPI 422 | No custom 422 handler; frontend doesn’t show field errors |
| Backend HTTP | 404/409/500 where used; no global handler | 500 can expose raw messages; Firestore/store errors unhandled |
| Stream (SSE) | Timeout and generic catch; error event; finally update session | Store update can throw; raw `str(e)` to client; no error codes |
| Gemini | User-facing messages for key/model/text-only; logging | Other Gemini errors still raw |
| TTS | Swallow exceptions → None; log | No user-facing TTS-specific messages |
| Frontend API | Timeouts; map status to thrown Error or null | 422 not parsed for fields; generateAudio fails silently |
| Frontend SSE | Parse error event; onerror; malformed data | No SSE timeout; no error taxonomy |
| Frontend UI | Errors and retry in key flows | No error boundary; no offline/network handling |

Implementing the high-impact items and the two bug fixes will make behavior more predictable and user-friendly while keeping implementation cost reasonable.
