import { useState, useCallback, useRef } from "react";
import { fetchEventSource, EventStreamContentType } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getStreamUrl, getSessionState } from "../lib/api";

/** Progress step from backend: planning_arc | generating_narrative | generating_audio */
export type StreamProgressStep = "planning_arc" | "generating_narrative" | "generating_audio" | null;

export interface ArcOutline {
  act1_setting?: { title?: string; focus?: string; image_prompt?: string; ambient_track?: string };
  act2_people?: { title?: string; focus?: string; image_prompt?: string; ambient_track?: string };
  act3_thread?: { title?: string; focus?: string; image_prompt?: string; ambient_track?: string };
  tone?: string;
  narrative_voice?: string;
}

export interface ResearchFact {
  fact: string;
  category: "geography" | "culture" | "history" | "diaspora" | "daily_life";
  source?: string;
  source_title?: string;
  confidence: "knowledge_base" | "grounded_search";
}

export interface ResearchBundle {
  region: string;
  time_period: string;
  facts: ResearchFact[];
}

interface UseSSEStreamReturn {
  segments: NarrativeSegment[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  progressStep: StreamProgressStep;
  thinkingMessage: string | null;
  arcOutline: ArcOutline | null;
  researchBundle: ResearchBundle | null;
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
  const [researchBundle, setResearchBundle] = useState<ResearchBundle | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const clearInactivityTimeout = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const resetInactivityTimeout = useCallback(() => {
    clearInactivityTimeout();
    timeoutRef.current = setTimeout(() => {
      setError("Request timed out");
      setIsStreaming(false);
      abortRef.current?.abort();
    }, 480_000); // 8 minutes — audio generation can take a while
  }, [clearInactivityTimeout]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    clearInactivityTimeout();
    setSegments([]);
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
    setProgressStep(null);
    setThinkingMessage(null);
    setArcOutline(null);
    setResearchBundle(null);
  }, [clearInactivityTimeout]);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    clearInactivityTimeout();
  }, [clearInactivityTimeout]);

  // Poll for existing segments when generation is already in progress
  const pollForExistingSegments = useCallback(async (sessionId: string, signal: AbortSignal) => {
    setThinkingMessage("Your story is being generated...");
    setProgressStep("generating_narrative");

    const POLL_INTERVAL = 3000; // 3 seconds
    const MAX_POLLS = 120; // 6 minutes max

    for (let i = 0; i < MAX_POLLS; i++) {
      if (signal.aborted) return;

      await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));
      if (signal.aborted) return;

      const state = await getSessionState(sessionId, true);
      if (!state) continue;

      // Update arc outline if available
      if (state.arc_outline) {
        setArcOutline(state.arc_outline as ArcOutline);
      }

      // If generation completed (or stale), load segments
      const isComplete = !state.is_generating || state.is_generating_stale;
      if (isComplete && state.segments && state.segments.length > 0) {
        if (state.is_generating_stale) {
          console.warn("[SSE] Detected stale generation, loading available segments");
        }
        setSegments(state.segments);
        setIsStreaming(false);
        setIsComplete(true);
        setProgressStep(null);
        setThinkingMessage(null);
        clearInactivityTimeout();
        return;
      }

      // Update progress message with segment count
      if (state.segment_count > 0) {
        setThinkingMessage(`Your story is being generated... (${state.segment_count} parts ready)`);
      }
    }

    // Timed out waiting
    setError("Story generation is taking too long. Please refresh the page.");
    setIsStreaming(false);
    setProgressStep(null);
    setThinkingMessage(null);
    clearInactivityTimeout();
  }, [clearInactivityTimeout]);

  const startStream = useCallback((sessionId: string, enableAudio: boolean = false) => {
    abortRef.current?.abort();
    clearInactivityTimeout();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    resetInactivityTimeout();
    setIsStreaming(true);
    setError(null);
    setSegments([]);
    setIsComplete(false);
    setProgressStep(null);
    setThinkingMessage(null);
    setArcOutline(null);
    setResearchBundle(null);

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

        // Handle 409 "already generating" by polling for existing segments
        if (response.status === 409 && message.toLowerCase().includes("already generating")) {
          pollForExistingSegments(sessionId, ctrl.signal);
          throw new Error("__polling__"); // Stop fetchEventSource, polling handles the rest
        }

        setError(message);
        setIsStreaming(false);
        clearInactivityTimeout();
        throw new Error(message); // stop fetchEventSource from retrying
      },
      onmessage(ev) {
        resetInactivityTimeout();
        try {
          if (ev.event === "arc") {
            const data = JSON.parse(ev.data) as ArcOutline;
            setArcOutline(data);
            return;
          }
          if (ev.event === "research") {
            const data = JSON.parse(ev.data) as ResearchBundle;
            setResearchBundle(data);
            return;
          }
          if (ev.event === "status") {
            const data = JSON.parse(ev.data) as { status?: string; message?: string };
            if (data?.status === "complete") {
              setIsStreaming(false);
              setIsComplete(true);
              setProgressStep(null);
              setThinkingMessage(null);
              clearInactivityTimeout();
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
            clearInactivityTimeout();
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
          clearInactivityTimeout();
        }
      },
      onerror(err) {
        if (ctrl.signal.aborted) return;
        // Don't show error if we're polling for existing segments
        if (err?.message === "__polling__") {
          throw err;
        }
        setError(err?.message || "Connection lost");
        setIsStreaming(false);
        setProgressStep(null);
        clearInactivityTimeout();
        throw err; // prevent fetchEventSource from retrying
      },
      onclose() {
        setIsStreaming(false);
        clearInactivityTimeout();
      },
    });
  }, [clearInactivityTimeout, resetInactivityTimeout, pollForExistingSegments]);

  return { segments, isStreaming, isComplete, error, progressStep, thinkingMessage, arcOutline, researchBundle, startStream, reset, abort };
}
