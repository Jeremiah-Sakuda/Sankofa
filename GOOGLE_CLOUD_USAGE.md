# Google Cloud Services & API Usage

Sankofa is built on Google Cloud's AI and infrastructure stack. This document catalogs every Google Cloud service and API integration in the project.

---

## Architecture Overview

```
┌─────────────┐    SSE / WebSocket    ┌──────────────────────────────────────────┐
│  Next.js UI  │◄────────────────────►│  FastAPI Backend (Cloud Run)             │
│  (Cloud Run) │                      │                                          │
└─────────────┘                      │  ┌──────────────────────────────────────┐ │
                                     │  │  Google ADK Agent Orchestrator       │ │
                                     │  │  ┌────────────┐ ┌────────────────┐  │ │
                                     │  │  │ 11 Tools   │ │ Gemini 2.5     │  │ │
                                     │  │  │ (planning, │ │ Flash / Pro    │  │ │
                                     │  │  │  research, │ │ (text, image,  │  │ │
                                     │  │  │  generate) │ │  audio, live)  │  │ │
                                     │  │  └────────────┘ └────────────────┘  │ │
                                     │  └──────────────────────────────────────┘ │
                                     │                                          │
                                     │  ┌──────────────┐  ┌─────────────────┐  │
                                     │  │  Firestore    │  │ Google Search   │  │
                                     │  │  (sessions)   │  │ (grounding)     │  │
                                     │  └──────────────┘  └─────────────────┘  │
                                     └──────────────────────────────────────────┘
```

---

## 1. Gemini API — Multi-Modal Content Generation

### Text Generation (Narrative Planning & Validation)

**Model:** `gemini-2.5-flash`
**File:** [`backend/app/services/gemini_service.py`](backend/app/services/gemini_service.py)

```python
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool

client = genai.Client()  # or Vertex AI mode

response = client.models.generate_content(
    model=settings.GEMINI_PLANNING_MODEL,  # gemini-2.5-flash
    contents=prompt,
    config=GenerateContentConfig(
        temperature=0.8,
        tools=[Tool(google_search=GoogleSearch())]  # grounded in real facts
    ),
)
```

Used for:
- **Arc planning** — Structures the 3-act narrative outline with historically grounded facts
- **Arc validation** — Verifies cultural accuracy and narrative coherence
- **Context quality assessment** — Evaluates knowledge base coverage for a given region/era
- **Follow-up question validation** — Filters prompt injection attempts

### Interleaved Text + Image Generation

**Model:** `gemini-2.5-flash-image`
**File:** [`backend/app/services/gemini_service.py`](backend/app/services/gemini_service.py)

```python
response = client.models.generate_content(
    model=settings.GEMINI_IMAGE_MODEL,  # gemini-2.5-flash-image
    contents=prompt,
    config=GenerateContentConfig(
        temperature=1.0,
        response_modalities=[Modality.TEXT, Modality.IMAGE],
    ),
)

# Response contains alternating text and inline watercolor-style images
for part in response.candidates[0].content.parts:
    if part.text:
        # Narrative paragraph
    elif part.inline_data:
        # Watercolor illustration (PNG)
```

Used for:
- **Narrative generation** — Produces the full story with interleaved watercolor illustrations
- **Follow-up responses** — Generates additional narrative content with images when users ask questions

### Text-to-Speech (TTS)

**Model:** `gemini-2.5-pro-preview-tts`
**File:** [`backend/app/services/tts_service.py`](backend/app/services/tts_service.py)

```python
from google.genai.types import (
    GenerateContentConfig, Modality,
    PrebuiltVoiceConfig, SpeechConfig, VoiceConfig,
)

response = client.models.generate_content(
    model=settings.GEMINI_TTS_MODEL,  # gemini-2.5-pro-preview-tts
    contents=sentence,
    config=GenerateContentConfig(
        response_modalities=[Modality.AUDIO],
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Kore")
            )
        ),
    ),
)

# Extract PCM audio → convert to WAV
audio_data = response.candidates[0].content.parts[0].inline_data.data
```

Used for:
- **Griot narration** — Every narrative paragraph is spoken aloud with the "Kore" voice
- **Concurrent generation** — Sentences are split and TTS-generated in parallel with `asyncio.gather()`

### Gemini Live — Real-Time Bidirectional Audio

**Model:** `gemini-live-2.5-flash-native-audio` (Vertex AI) / `gemini-2.5-flash-native-audio-preview-12-2025` (API key)
**File:** [`backend/app/routes/live.py`](backend/app/routes/live.py)

```python
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.runners import Runner
from google.adk.agents.run_config import StreamingMode

run_config = RunConfig(
    streaming_mode=StreamingMode.BIDI,
    response_modalities=["AUDIO"],
    output_audio_transcription=AudioTranscriptionConfig(),
    input_audio_transcription=AudioTranscriptionConfig(),
)

async for event in runner.run_live(
    session=session,
    live_request_queue=request_queue,
    run_config=run_config,
):
    # Stream audio chunks back over WebSocket
```

Used for:
- **"Talk to the Griot"** — Users speak to an AI griot in real-time via WebSocket
- **Bidirectional streaming** — 16kHz PCM audio in, Gemini Live audio out
- **Live transcription** — Both input and output audio are transcribed in real-time

---

## 2. Google ADK (Agent Development Kit)

**File:** [`backend/app/services/adk_agent.py`](backend/app/services/adk_agent.py)

```python
from google.adk import Agent
from google.adk.models.google_llm import Gemini

sankofa_agent = Agent(
    model=Gemini(model=settings.GEMINI_PLANNING_MODEL),
    name="sankofa_griot",
    instruction="""You are Sankofa, an AI griot...""",
    tools=[
        lookup_cultural_context,
        assess_context_quality,
        research_region_history,
        plan_narrative_arc,
        validate_narrative_arc,
        generate_act_segments,
        generate_follow_up,
        generate_audio_narration,
        notify_user,
        report_progress,
        mark_complete,
    ],
)
```

The ADK agent orchestrates 11 specialized tool functions that form the narrative pipeline:

| Tool | Purpose | Google API Used |
|------|---------|-----------------|
| `lookup_cultural_context` | Load regional knowledge base | — (local) |
| `assess_context_quality` | Evaluate coverage quality | — (local) |
| `research_region_history` | Web research for sparse regions | Gemini + Google Search |
| `plan_narrative_arc` | Structure 3-act story outline | Gemini + Google Search |
| `validate_narrative_arc` | Check cultural accuracy | Gemini |
| `generate_act_segments` | Generate text + images per act | Gemini (multimodal) |
| `generate_follow_up` | Handle user follow-up questions | Gemini (multimodal) |
| `generate_audio_narration` | Convert text to speech | Gemini TTS |
| `notify_user` | Send status messages to UI | — (SSE) |
| `report_progress` | Report pipeline progress | — (SSE) |
| `mark_complete` | Signal completion | — (SSE) |

**ADK Runner** (in [`adk_orchestrator.py`](backend/app/services/adk_orchestrator.py)):

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    agent=sankofa_agent,
    app_name="sankofa",
    session_service=InMemorySessionService(),
)

async for event in runner.run_async(
    session_id=session_id,
    user_id=user_id,
    new_message=content,
):
    # Parse tool calls, extract media, emit SSE events
```

---

## 3. Google Search Grounding

**File:** [`backend/app/services/gemini_service.py`](backend/app/services/gemini_service.py)

```python
from google.genai.types import GoogleSearch, Tool

response = client.models.generate_content(
    model=model,
    contents=prompt,
    config=GenerateContentConfig(
        tools=[Tool(google_search=GoogleSearch())],
    ),
)

# Grounding metadata (search queries used)
if response.candidates[0].grounding_metadata:
    queries = response.candidates[0].grounding_metadata.web_search_queries
```

Used in two critical paths:
1. **Region research** — When the knowledge base has sparse coverage for a user's region/era, Google Search fills gaps with real historical data
2. **Arc planning** — Every narrative arc is grounded in web-sourced facts to prevent hallucination of family-specific genealogical claims

---

## 4. Cloud Firestore

**File:** [`backend/app/store/firestore_store.py`](backend/app/store/firestore_store.py)

```python
from google.cloud import firestore

db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT)

# Create session
doc_ref = db.collection(collection).document(session_id)
doc_ref.set({...})

# Store segments in subcollection (avoids 1MiB document limit)
seg_ref = doc_ref.collection("segments").document(str(sequence))
seg_ref.set(segment_data)

# Retrieve session with ordered segments
segments = (
    doc_ref.collection("segments")
    .order_by("sequence")
    .stream()
)
```

Used for:
- **Session persistence** — User sessions survive backend restarts
- **Segment storage** — Narrative segments (text, images, audio) stored in subcollections
- **Media handling** — Large media blobs (>900KB) stripped before Firestore storage to respect document size limits

---

## 5. Cloud Run (Production Deployment)

**File:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

```yaml
# Backend deployment
gcloud run deploy sankofa-api \
  --source ./backend \
  --region us-central1 \
  --project ${{ secrets.GCP_PROJECT_ID }} \
  --set-env-vars "\
    ENVIRONMENT=production,\
    GOOGLE_CLOUD_PROJECT=${{ secrets.GCP_PROJECT_ID }},\
    GOOGLE_GENAI_USE_VERTEXAI=True,\
    USE_FIRESTORE=True" \
  --min-instances 1 \
  --max-instances 5 \
  --memory 1Gi \
  --timeout 300

# Frontend deployment
gcloud run deploy sankofa-web \
  --source ./frontend \
  --region us-central1 \
  --min-instances 1 \
  --max-instances 3 \
  --memory 512Mi
```

- **Backend:** FastAPI on Cloud Run with Vertex AI enabled, Firestore persistence, 300s timeout for long generation calls
- **Frontend:** Next.js on Cloud Run with dynamic API URL injection
- **CI/CD:** GitHub Actions with automatic deployment on push to main

---

## 6. Vertex AI Integration

**File:** [`backend/app/config.py`](backend/app/config.py)

```python
# Supports both API key mode (development) and Vertex AI mode (production)
GOOGLE_GENAI_USE_VERTEXAI: bool = False   # Set True in production
GOOGLE_CLOUD_PROJECT: str = ""            # Required for Vertex AI
GOOGLE_CLOUD_LOCATION: str = "us-central1"
GOOGLE_API_KEY: str = ""                  # Used when Vertex AI is disabled
```

**Client initialization** ([`gemini_service.py`](backend/app/services/gemini_service.py)):

```python
if settings.GOOGLE_GENAI_USE_VERTEXAI:
    client = genai.Client(
        vertexai=True,
        project=settings.GOOGLE_CLOUD_PROJECT,
        location=settings.GOOGLE_CLOUD_LOCATION,
    )
else:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
```

---

## Summary

| Google Cloud Service | Models / APIs | Purpose |
|---|---|---|
| **Gemini API** | `gemini-2.5-flash` | Narrative planning, validation, grounding |
| **Gemini API** | `gemini-2.5-flash-image` | Interleaved text + watercolor image generation |
| **Gemini API** | `gemini-2.5-pro-preview-tts` | Text-to-speech narration (voice: "Kore") |
| **Gemini Live** | `gemini-live-2.5-flash-native-audio` | Real-time bidirectional voice conversation |
| **Google ADK** | Agent + Runner + Tools | Multi-step orchestration of 11 tool functions |
| **Google Search** | Grounding API | Fact-checked historical research |
| **Cloud Firestore** | Document database | Session and segment persistence |
| **Cloud Run** | Serverless containers | Production hosting (backend + frontend) |
| **Vertex AI** | Managed AI platform | Production model serving with project-level auth |

### Dependencies

```
google-genai==1.67.0           # Gemini API client (text, image, audio, live)
google-cloud-firestore==2.25.0 # Firestore database client
google-adk==1.27.1             # Agent Development Kit
```
