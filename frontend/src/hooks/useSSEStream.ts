import { useState, useCallback, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getStreamUrl } from "../lib/api";

/** Progress step from backend: planning_arc | generating_narrative | generating_audio */
export type StreamProgressStep = "planning_arc" | "generating_narrative" | "generating_audio" | null;

export interface ArcOutline {
  act1_setting?: { title?: string; focus?: string; image_prompt?: string };
  act2_people?: { title?: string; focus?: string; image_prompt?: string };
  act3_thread?: { title?: string; focus?: string; image_prompt?: string };
  tone?: string;
  narrative_voice?: string;
}

interface UseSSEStreamReturn {
  segments: NarrativeSegment[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  progressStep: StreamProgressStep;
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
  const [arcOutline, setArcOutline] = useState<ArcOutline | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSegments([]);
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
    setProgressStep(null);
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
    setArcOutline(null);

    fetchEventSource(getStreamUrl(sessionId, enableAudio), {
      signal: ctrl.signal,
      onmessage(ev) {
        try {
          if (ev.event === "arc") {
            const data = JSON.parse(ev.data) as ArcOutline;
            setArcOutline(data);
            return;
          }
          if (ev.event === "status") {
            const data = JSON.parse(ev.data) as { status?: string };
            if (data?.status === "complete") {
              setIsStreaming(false);
              setIsComplete(true);
              setProgressStep(null);
            } else if (
              data?.status === "planning_arc" ||
              data?.status === "generating_narrative" ||
              data?.status === "generating_audio"
            ) {
              setProgressStep(data.status);
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
      },
      onclose() {
        setIsStreaming(false);
      },
    });
  }, []);

  return { segments, isStreaming, isComplete, error, progressStep, arcOutline, startStream, reset, abort };
}
