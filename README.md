# Sankofa — Ancestral Heritage Narrator

> *"Se wo were fi na wosankofa a yenkyi."* — It is not wrong to go back for that which you have forgotten.

Sankofa is a multimodal AI agent that transforms sparse personal and familial inputs into immersive heritage narratives — weaving together oral-history-style narration, AI-generated period imagery, ambient audio, and contextual text into a single cohesive experience.

Named after the Akan concept of "go back and get it," Sankofa addresses a profound gap: hundreds of millions of people in diaspora communities have lost tangible connection to their ancestral heritage.

**Sankofa doesn't just tell you where you're from — it makes you *feel* it.**

## The Problem

An estimated 200+ million people in the African diaspora alone have limited or no access to their ancestral stories. Existing tools give data (DNA percentages, country names) without emotional resonance. Heritage is inherently multimodal — it lives in the sound of a language, the landscape of a homeland, the visual texture of traditional craft, and the rhythm of oral storytelling. No single modality can capture it.

## What It Does

A user provides a few seeds: a family surname, a country or region, a time period, and optionally any fragments they know. From these seeds, Sankofa generates a flowing, interleaved narrative with:

- **Griot-inspired narration** — Warm, oral storytelling voice grounded in historical fact
- **AI-generated period imagery** — Watercolor-style illustrations of landscapes, people, and cultural artifacts
- **Trust indicators** — Every segment marked as Historical, Cultural, or Reconstructed
- **Audio narration** — TTS audio for each text segment in a warm storytelling voice
- **Follow-up exploration** — Ask Sankofa to go deeper into any aspect of the heritage

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│          Next.js / React / Tailwind              │
│   Landing → Intake Flow → Narrative Display      │
└─────────────────┬───────────────────────────────┘
                  │ SSE (Server-Sent Events)
                  ▼
┌─────────────────────────────────────────────────┐
│              Backend Orchestrator                 │
│            Python / FastAPI / Cloud Run           │
│                                                   │
│  ┌──────────┐ ┌────────────────────────────────┐ │
│  │ Session   │ │  3-Step Narrative Planner      │ │
│  │ Store     │ │  1. Context Assembly           │ │
│  │(In-memory)│ │  2. Arc Planning (Gemini)      │ │
│  └──────────┘ │  3. Interleaved Generation      │ │
│               └────────────────────────────────┘ │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │          Gemini API (GenAI SDK)             │  │
│  │  • gemini-2.5-flash-image (text + images)  │  │
│  │  • gemini-2.5-flash-tts (audio narration)  │  │
│  │  • gemini-2.0-flash (arc planning)         │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  ┌──────────────┐  ┌────────────────────────┐    │
│  │ Cultural      │  │  Trust Classifier      │    │
│  │ Knowledge Base│  │  (Fact vs. Imagination) │    │
│  │ (West Africa, │  └────────────────────────┘    │
│  │  Caribbean,   │                                │
│  │  South Asia)  │                                │
│  └──────────────┘                                 │
└─────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Google Cloud Service |
|---|---|---|
| AI Models | Gemini 2.5 Flash Image, Gemini 2.5 Flash TTS, Gemini 2.0 Flash | Vertex AI / GenAI SDK |
| Backend | Python 3.12 / FastAPI | Cloud Run |
| Frontend | Next.js 16 / React 19 / Tailwind CSS v4 | Cloud Run |
| Streaming | Server-Sent Events (SSE) via sse-starlette | Cloud Run |
| Session Store | In-memory (default) or Firestore via `USE_FIRESTORE` | Firestore (production) |

## Supported Regions

### Deep Coverage (detailed decade-by-decade data)
- **West Africa:** Ghana (Gold Coast), Nigeria (Yorubaland), Senegambia, Dahomey (Benin), Sierra Leone
- **Caribbean:** Jamaica, Haiti, Trinidad and Tobago
- **South Asia:** Punjab (India/Pakistan), Bengal (India/Bangladesh)

### Generic Coverage (Gemini knowledge-grounded)
- Any region worldwide — Sankofa will use its general knowledge when detailed knowledge base data isn't available

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+
- A Google API key with Gemini API access (or GCP project with Vertex AI)

### Backend

```bash
cd backend
cp .env.example .env   # Edit with your Google API key (from https://aistudio.google.com/apikey)
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

- Use `python -m uvicorn` if `uvicorn` is not on your PATH (e.g. when not activating a venv).
- **Windows:** If `--reload` causes a permission or multiprocessing error, run without reload:  
  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (restart the process manually after code changes).
- The backend reads `.env` only at startup; restart the backend after changing any `.env` values.

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Visit http://localhost:3000 to begin.

### Test API and network

With the backend running, verify it’s reachable:

```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/health" -Method Get
```

You should see `status: healthy` and `service: sankofa-api`. In the app, on the narrative “Ready to weave your narrative” screen, use **Test API connection** to check from the browser before clicking Begin.

## Google Cloud Deployment

```bash
# Set your GCP project
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1

# Deploy (requires gcloud CLI)
chmod +x deploy.sh
./deploy.sh
```

## Session store (Firestore)

Sessions are persisted in **Firestore** in production so they survive restarts. Locally, the backend uses an **in-memory** store by default.

- **Config:** Set `USE_FIRESTORE=true` and `GOOGLE_CLOUD_PROJECT` when using Firestore. Optional: `FIRESTORE_SESSIONS_COLLECTION` (default `sessions`).
- **Data model:** One Firestore document per session (document ID = `session_id`) with `user_input`, `narrative_context`, `is_generating`, and `arc_outline`. Segments are stored in a **subcollection** `segments` (one doc per segment, keyed by sequence) to stay under Firestore’s 1 MiB document limit when narratives include base64 images and audio.
- **Backend:** `app/store/` provides the active store: `FirestoreSessionStore` (when `USE_FIRESTORE=true`) or `InMemorySessionStore`. Routes use `session_store` from `app.store`; no route logic depends on which backend is used.
- **Deployment:** The deploy script sets `USE_FIRESTORE=True` for the backend. Enable the Firestore API and grant the Cloud Run service account the **Cloud Datastore User** role. See `backend/docs/DEPLOYMENT.md` for steps.

## Trust & Accuracy

Sankofa clearly distinguishes between:
- **Historical** — Based on documented historical facts about the region and era
- **Cultural** — Based on well-documented cultural practices of the community
- **Reconstructed** — Imaginative reconstruction informed by historical context

These appear as subtle margin annotations in the narrative, building trust without breaking the storytelling flow. Sankofa never fabricates specific genealogical claims.

## Hackathon

Built for the **Gemini Live Agent Challenge** (Google / Devpost) in the **Creative Storyteller** category.

## Author

**Jeremiah Sakuda**

---

*Sankofa — because heritage is not data. It's a story.*
