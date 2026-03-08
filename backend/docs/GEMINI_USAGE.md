# How Sankofa Uses Gemini

## Current pipeline (why it feels slow)

We make **two sequential Gemini API calls** before any content reaches the user:

| Step | What happens | Model | Why it's slow |
|------|----------------|------|----------------|
| **1** | Build grounding context from knowledge base (region, era, user fragments). **No API** — local. | — | Fast (~50–200 ms). |
| **2** | **Arc planning:** Send full grounding context + instructions; Gemini returns a JSON outline (3 acts, tone, image prompts). | `gemini-2.0-flash` (text only) | One round-trip. **Large prompt** (we send the whole context). Typically **15–45 s**. |
| **3** | **Narrative + images:** Send full grounding context again + the arc; Gemini returns **all** narrative text (6–9 paragraphs) **and 3 images** in a single response. | `gemini-2.0-flash-exp` (text + image) | One very large request. **Image generation is slow**; we ask for 3 images in one go. Typically **30–90+ s**. |

So total time is roughly: **Step 2 time + Step 3 time** (fully sequential). The user sees nothing until **both** calls finish, then we stream the pre-generated segments with small delays.

## Inefficiencies

1. **Duplicate context** — The same grounding context (often 2k–4k chars) is sent in **both** API calls.
2. **Oversized prompts** — Arc planning doesn’t need the full context; narrative could use a cap.
3. **One big step 3** — All text and all 3 images are generated in a single call, so we wait for the slowest part (images) before returning anything.
4. **No streaming of generation** — We don’t stream tokens from Gemini; we wait for the full response, then “stream” segments to the client. So perceived latency = full Step 2 + full Step 3.

## Config (models)

Defaults (for Gemini API key, not Vertex):

- **Planning (arc):** `GEMINI_PLANNING_MODEL` → `gemini-2.5-flash` (text only)
- **Narrative + images:** `GEMINI_IMAGE_MODEL` → `gemini-2.5-flash-image` (Nano Banana; image+text output)
- **TTS:** `GEMINI_TTS_MODEL` → `gemini-2.5-pro-preview-tts`

Gemini 2.5 Flash is text-only; use an image-capable model (e.g. gemini-2.5-flash-image or gemini-3-pro-image-preview) for narrative generation.

Override in `backend/.env` if a model is not found (404). See https://ai.google.dev/gemini-api/docs/models for available model IDs.

Defined in `app/config.py`.

## Current optimizations

- **Context caps** (in `narrative_planner.py`):
  - Arc planning: grounding context is trimmed to **2,200 characters** so the first Gemini call uses a smaller prompt.
  - Narrative: grounding context is trimmed to **4,000 characters** for the second call.
- **Per-step timeouts** in the stream route (60 s arc, 120 s narrative) so we fail fast instead of hanging.

## Possible next steps (to reduce load time further)

- **Stream Gemini output** — If the API supports streaming for text+image responses, stream tokens to the client as they arrive so the user sees text before images are ready.
- **Fewer images** — e.g. one hero image instead of three, or generate images in a separate request after showing text.
- **Optional “fast” mode** — Skip arc planning and use a fixed template; one Gemini call instead of two (at the cost of a more generic structure).
- **Lighter image model** — Try a faster/smaller model for image generation if quality is acceptable.
