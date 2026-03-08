import { useState, useCallback, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getStreamUrl } from "../lib/api";

/** Progress step from backend: planning_arc | generating_narrative | generating_audio */
export type StreamProgressStep = "planning_arc" | "generating_narrative" | "generating_audio" | null;

interface UseSSEStreamReturn {
  segments: NarrativeSegment[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  progressStep: StreamProgressStep;
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
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSegments([]);
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
    setProgressStep(null);
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

    fetchEventSource(getStreamUrl(sessionId, enableAudio), {
      signal: ctrl.signal,
      onmessage(ev) {
        if (ev.event === "status") {
          const data = JSON.parse(ev.data);
          if (data.status === "complete") {
            setIsStreaming(false);
            setIsComplete(true);
            setProgressStep(null);
          } else if (
            data.status === "planning_arc" ||
            data.status === "generating_narrative" ||
            data.status === "generating_audio"
          ) {
            setProgressStep(data.status);
          }
          return;
        }
        if (ev.event === "error") {
          const data = JSON.parse(ev.data);
          setError(data.error || "Generation failed");
          setIsStreaming(false);
          setProgressStep(null);
          return;
        }
        if (["text", "image", "audio", "map"].includes(ev.event)) {
          const segment: NarrativeSegment = JSON.parse(ev.data);
          setSegments((prev) => [...prev, segment]);
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

  return { segments, isStreaming, isComplete, error, progressStep, startStream, reset, abort };
}
