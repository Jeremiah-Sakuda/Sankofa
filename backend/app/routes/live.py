"""
WebSocket endpoint for Gemini Live API — "Talk to the Griot" mode.

Enables real-time bidirectional voice conversation with the Sankofa agent
using the ADK's run_live() with the Gemini Live API.
"""

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import StreamingMode
from google.adk.runners import RunConfig, Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import (
    AudioTranscriptionConfig,
    Blob,
    Content,
    Part,
)

from app.services.adk_agent import sankofa_live_agent
from app.store import session_store

# Context window limit for prompt truncation (characters)
_CTX_EXISTING_NARRATIVE = 3000

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["live"])

# Dedicated session service for live sessions
_live_session_service = InMemorySessionService()
_live_runner = Runner(
    agent=sankofa_live_agent,
    app_name="sankofa_live",
    session_service=_live_session_service,
)


def _build_run_config() -> RunConfig:
    """Build a RunConfig for bidirectional audio streaming.

    Note: Voice/speech_config is set at the Agent level via the Gemini(...)
    wrapper in adk_agent.py, NOT here. Passing speech_config in RunConfig
    causes WebSocket error 1007 with run_live() (ADK issue #2934).
    """
    return RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        output_audio_transcription=AudioTranscriptionConfig(),
        input_audio_transcription=AudioTranscriptionConfig(),
    )


@router.websocket("/narrative/{session_id}/live")
async def live_griot(websocket: WebSocket, session_id: str):
    """Bidirectional voice conversation with the Sankofa Griot.

    Protocol (JSON messages over WebSocket):
      Client → Server:
        {"type": "audio", "data": "<base64 PCM 16-bit 16kHz mono>"}
        {"type": "start"}   — user started speaking
        {"type": "end"}     — user stopped speaking
        {"type": "text", "content": "..."}  — optional text input
        {"type": "close"}

      Server → Client:
        {"type": "audio", "data": "<base64 audio>", "mime_type": "audio/pcm;rate=24000"}
        {"type": "transcript_in", "text": "..."}   — what user said
        {"type": "transcript_out", "text": "..."}   — what griot said
        {"type": "tool_call", "name": "...", "message": "..."}  — agent thinking
        {"type": "turn_complete"}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()

    # Validate session
    session = session_store.get(session_id)
    if not session:
        await websocket.send_json({"type": "error", "message": "Session not found"})
        await websocket.close(code=4004)
        return

    ui = session.user_input

    # Create ADK live session with context priming
    adk_session = await _live_session_service.create_session(
        app_name="sankofa_live",
        user_id=session_id,
    )

    # Build context primer — give the agent the narrative context
    existing_narrative = "\n".join(
        seg.content for seg in session.segments if seg.type == "text" and seg.content
    )
    context_primer = (
        f"You are Sankofa, a warm and wise West African griot narrator. "
        f"Speak in a warm, unhurried cadence — resonant, deep, with occasional "
        f"pauses for emphasis. Let your words breathe. This is oral storytelling, "
        f"not news reading. "
        f"You are having a live voice conversation about the heritage of the "
        f"{ui.family_name} family from {ui.region_of_origin} during {ui.time_period}.\n\n"
    )
    if existing_narrative:
        context_primer += (
            f"You have already told this narrative:\n"
            f"{existing_narrative[:_CTX_EXISTING_NARRATIVE]}\n\n"
        )
    context_primer += (
        "Speak warmly and conversationally. Keep responses concise (2-3 sentences) "
        "since this is a live voice conversation, not a written narrative. "
        "Use your tools when the listener asks factual questions. "
        "Do NOT call generate_audio_narration — you are already speaking via audio."
    )

    queue = LiveRequestQueue()
    run_config = _build_run_config()

    # Send the context primer as the initial message
    queue.send_content(Content(role="user", parts=[Part(text=context_primer)]))

    # Task to process events from the ADK agent and send to client
    async def _process_events():
        # Track last-sent transcripts to deduplicate cumulative updates
        last_in_transcript = ""
        last_out_transcript = ""

        try:
            async for event in _live_runner.run_live(
                user_id=session_id,
                session_id=adk_session.id,
                live_request_queue=queue,
                run_config=run_config,
            ):
                if not event.content or not event.content.parts:
                    # Check for transcriptions
                    if event.input_transcription:
                        text = (
                            event.input_transcription.text
                            if hasattr(event.input_transcription, "text")
                            else str(event.input_transcription)
                        )
                        if text and text != last_in_transcript:
                            last_in_transcript = text
                            await websocket.send_json({
                                "type": "transcript_in",
                                "text": text,
                            })
                    if event.output_transcription:
                        text = (
                            event.output_transcription.text
                            if hasattr(event.output_transcription, "text")
                            else str(event.output_transcription)
                        )
                        if text and text != last_out_transcript:
                            last_out_transcript = text
                            await websocket.send_json({
                                "type": "transcript_out",
                                "text": text,
                            })
                    if event.turn_complete:
                        last_in_transcript = ""
                        last_out_transcript = ""
                        await websocket.send_json({"type": "turn_complete"})
                    continue

                has_text_part = False

                for part in event.content.parts:
                    # Audio output from the agent
                    if part.inline_data and part.inline_data.data:
                        audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                        await websocket.send_json({
                            "type": "audio",
                            "data": audio_b64,
                            "mime_type": part.inline_data.mime_type or "audio/pcm;rate=24000",
                        })

                    # Track text parts (don't send yet — prefer output_transcription)
                    if part.text:
                        has_text_part = True

                    # Tool calls — surface as thinking messages
                    if part.function_call:
                        await websocket.send_json({
                            "type": "tool_call",
                            "name": part.function_call.name,
                            "message": f"Looking up: {part.function_call.name}...",
                        })

                # Check event-level transcriptions (deduplicated)
                if hasattr(event, "input_transcription") and event.input_transcription:
                    text = (
                        event.input_transcription.text
                        if hasattr(event.input_transcription, "text")
                        else str(event.input_transcription)
                    )
                    if text and text != last_in_transcript:
                        last_in_transcript = text
                        await websocket.send_json({"type": "transcript_in", "text": text})

                # Prefer output_transcription (canonical); fall back to part.text
                transcript_sent = False
                if hasattr(event, "output_transcription") and event.output_transcription:
                    text = (
                        event.output_transcription.text
                        if hasattr(event.output_transcription, "text")
                        else str(event.output_transcription)
                    )
                    if text and text != last_out_transcript:
                        last_out_transcript = text
                        await websocket.send_json({"type": "transcript_out", "text": text})
                        transcript_sent = True

                if not transcript_sent and has_text_part:
                    for part in event.content.parts:
                        if part.text and part.text != last_out_transcript:
                            last_out_transcript = part.text
                            await websocket.send_json({
                                "type": "transcript_out",
                                "text": part.text,
                            })
                            break

                if event.turn_complete:
                    last_in_transcript = ""
                    last_out_transcript = ""
                    await websocket.send_json({"type": "turn_complete"})

        except WebSocketDisconnect:
            logger.info("[live] Client disconnected during event processing")
        except Exception as e:
            logger.error("[live] Event processing error: %s", e, exc_info=True)
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass

    # Start the event processor in background
    event_task = asyncio.create_task(_process_events())

    # Main loop: receive from client and feed to the LiveRequestQueue
    try:
        while True:
            # Check if event processor has died — surface error to client
            if event_task.done():
                exc = event_task.exception() if not event_task.cancelled() else None
                if exc:
                    logger.error("[live] Event processor failed: %s", exc)
                    try:
                        await websocket.send_json({"type": "error", "message": str(exc)})
                    except Exception:
                        pass
                break

            # Wait for client message with a timeout so we can check event_task health
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "audio":
                # Base64-encoded PCM audio from the client
                audio_bytes = base64.b64decode(msg["data"])
                queue.send_realtime(
                    Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
                )

            elif msg_type == "start":
                queue.send_activity_start()

            elif msg_type == "end":
                queue.send_activity_end()

            elif msg_type == "text":
                # Text input (fallback or typed question)
                text = msg.get("content", "")
                if text:
                    queue.send_content(
                        Content(role="user", parts=[Part(text=text)])
                    )

            elif msg_type == "close":
                break

    except WebSocketDisconnect:
        logger.info("[live] Client disconnected from session %s", session_id)
    except json.JSONDecodeError:
        logger.warning("[live] Received non-JSON message, ignoring")
    except Exception as e:
        logger.error("[live] WebSocket error: %s", e, exc_info=True)
    finally:
        queue.close()
        event_task.cancel()
        try:
            await event_task
        except (asyncio.CancelledError, Exception):
            pass
        logger.info("[live] Live session ended for %s", session_id)
