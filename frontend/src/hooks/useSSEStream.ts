import { useState, useCallback, useRef } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getStreamUrl } from "../lib/api";

interface UseSSEStreamReturn {
  segments: NarrativeSegment[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  startStream: (sessionId: string) => void;
  reset: () => void;
}

export function useSSEStream(): UseSSEStreamReturn {
  const [segments, setSegments] = useState<NarrativeSegment[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setSegments([]);
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
  }, []);

  const startStream = useCallback((sessionId: string, enableAudio: boolean = false) => {
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setIsStreaming(true);
    setError(null);
    setSegments([]);
    setIsComplete(false);

    fetchEventSource(getStreamUrl(sessionId, enableAudio), {
      signal: ctrl.signal,
      onmessage(ev) {
        if (ev.event === "status") {
          const data = JSON.parse(ev.data);
          if (data.status === "complete") {
            setIsStreaming(false);
            setIsComplete(true);
          }
          return;
        }
        if (ev.event === "error") {
          const data = JSON.parse(ev.data);
          setError(data.error || "Generation failed");
          setIsStreaming(false);
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
      },
      onclose() {
        setIsStreaming(false);
      },
    });
  }, []);

  return { segments, isStreaming, isComplete, error, startStream, reset };
}
