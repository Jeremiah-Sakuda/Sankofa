import { useState, useCallback, useRef } from "react";
import { fetchEventSource, EventStreamContentType } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getStreamUrl } from "../lib/api";

/** Progress step from backend: planning_arc | generating_narrative | generating_audio */
export type StreamProgressStep = "planning_arc" | "generating_narrative" | "generating_audio" | null;

export interface ArcOutline {
  act1_setting?: { title?: string; focus?: string; image_prompt?: string; ambient_track?: string };
  act2_people?: { title?: string; focus?: string; image_prompt?: string; ambient_track?: string };
  act3_thread?: { title?: string; focus?: string; image_prompt?: string; ambient_track?: string };
  tone?: string;
  narrative_voice?: string;
}

interface UseSSEStreamReturn {
  segments: NarrativeSegment[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  progressStep: StreamProgressStep;
  thinkingMessage: string | null;
  arcOutline: ArcOutline | null;
  startStream: (sessionId: string, enableAudio?: boolean) => void;
  reset: () => void;
  abort: () => void;
}

export function useSSEStream(): UseSSEStreamReturn {
  const [segments, setSegments] = useState<NarrativeSegment[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progressStep, setProgressStep] = useState<StreamProgressStep>(null);
  const [thinkingMessage, setThinkingMessage] = useState<string | null>(null);
  const [arcOutline, setArcOutline] = useState<ArcOutline | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSegments([]);
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
    setProgressStep(null);
    setThinkingMessage(null);
    setArcOutline(null);
  }, []);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  const startStream = useCallback((sessionId: string, enableAudio: boolean = false) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setIsStreaming(true);
    setError(null);
    setSegments([]);
    setIsComplete(false);
    setProgressStep(null);
    setThinkingMessage(null);
    setArcOutline(null);

    fetchEventSource(getStreamUrl(sessionId, enableAudio), {
      signal: ctrl.signal,
      async onopen(response) {
        const ct = response.headers.get("content-type") || "";
        if (response.ok && ct.includes(EventStreamContentType)) {
          return; // valid SSE stream
        }
        // Server returned a non-SSE response (JSON error, 500, etc.)
        let message = `Server error (${response.status})`;
        try {
          const body = await response.json();
          message = body?.detail || body?.error || message;
        } catch {
          // couldn't parse body
        }
        setError(message);
        setIsStreaming(false);
        throw new Error(message); // stop fetchEventSource from retrying
      },
      onmessage(ev) {
        try {
          if (ev.event === "arc") {
            const data = JSON.parse(ev.data) as ArcOutline;
            setArcOutline(data);
            return;
          }
          if (ev.event === "status") {
            const data = JSON.parse(ev.data) as { status?: string; message?: string };
            if (data?.status === "complete") {
              setIsStreaming(false);
              setIsComplete(true);
              setProgressStep(null);
              setThinkingMessage(null);
            } else if (
              data?.status === "planning_arc" ||
              data?.status === "generating_narrative" ||
              data?.status === "generating_audio"
            ) {
              setProgressStep(data.status);
            } else if (data?.status === "thinking" || data?.status === "agent_message") {
              setThinkingMessage(data.message ?? null);
            }
            return;
          }
          if (ev.event === "error") {
            const data = JSON.parse(ev.data) as { error?: string };
            setError(data?.error || "Generation failed");
            setIsStreaming(false);
            setProgressStep(null);
            return;
          }
          if (["text", "image", "audio", "map"].includes(ev.event)) {
            const segment = JSON.parse(ev.data) as NarrativeSegment;
            setSegments((prev) => [...prev, segment]);
          }
        } catch {
          setError("Received malformed stream data");
          setIsStreaming(false);
          setProgressStep(null);
        }
      },
      onerror(err) {
        if (ctrl.signal.aborted) return;
        setError(err?.message || "Connection lost");
        setIsStreaming(false);
        setProgressStep(null);
        throw err; // prevent fetchEventSource from retrying
      },
      onclose() {
        setIsStreaming(false);
      },
    });
  }, []);

  return { segments, isStreaming, isComplete, error, progressStep, thinkingMessage, arcOutline, startStream, reset, abort };
}
