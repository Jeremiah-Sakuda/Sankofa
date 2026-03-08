"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { useSSEStream } from "../../../hooks/useSSEStream";
import { submitFollowUp, NarrativeSegment, checkBackendHealth } from "../../../lib/api";
import NarrativeStream from "../../../components/NarrativeStream";
import SankofaBird from "../../../components/SankofaBird";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const STUCK_TIMEOUT_MS = 90_000; // show "taking longer" after 90s with no segments

interface SessionInfo {
  family_name: string;
  region_of_origin: string;
  time_period: string;
}

export default function NarrativePage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const { segments, isStreaming, isComplete, error, progressStep, startStream, abort, reset } = useSSEStream();
  const [followUpSegments, setFollowUpSegments] = useState<NarrativeSegment[]>([]);
  const [isLoadingFollowUp, setIsLoadingFollowUp] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [enableAudio, setEnableAudio] = useState(false);
  const [showStuckMessage, setShowStuckMessage] = useState(false);
  const stuckTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [connectionTest, setConnectionTest] = useState<"idle" | "checking" | "ok" | "fail">("idle");
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const [stepElapsed, setStepElapsed] = useState(0);
  const stepStartRef = useRef<number | null>(null);
  const [sessionInvalid, setSessionInvalid] = useState(false);
  const [followUpError, setFollowUpError] = useState<string | null>(null);

  useEffect(() => {
    if (sessionId) {
      fetch(`${API_BASE}/api/session/${sessionId}`)
        .then((r) => {
          if (r.status === 404) setSessionInvalid(true);
          return r.json();
        })
        .then((data) => {
          if (data?.user_input) setSessionInfo(data.user_input);
        })
        .catch(() => setSessionInvalid(true));
    }
  }, [sessionId]);

  const handleBeginStream = useCallback(async () => {
    if (!sessionId || hasStarted) return;
    // Confirm session still exists before starting stream (avoids 404 after backend restart)
    try {
      const r = await fetch(`${API_BASE}/api/session/${sessionId}`);
      if (r.status === 404) {
        setSessionInvalid(true);
        return;
      }
    } catch {
      setSessionInvalid(true);
      return;
    }
    setHasStarted(true);
    startStream(sessionId, enableAudio);
  }, [sessionId, hasStarted, startStream, enableAudio]);

  const handleTestConnection = useCallback(async () => {
    setConnectionTest("checking");
    setConnectionMessage(null);
    const result = await checkBackendHealth();
    if (result.ok) {
      setConnectionTest("ok");
      setConnectionMessage("Backend connected.");
    } else {
      setConnectionTest("fail");
      setConnectionMessage(result.message || "Could not reach backend.");
    }
  }, []);

  useEffect(() => {
    return () => abort();
  }, [abort]);

  const allSegments = [...segments, ...followUpSegments];

  // If we're waiting for the first segment for too long, show "taking longer" + retry
  useEffect(() => {
    if (hasStarted && allSegments.length === 0 && !error) {
      setShowStuckMessage(false);
      stuckTimerRef.current = setTimeout(() => {
        setShowStuckMessage(true);
      }, STUCK_TIMEOUT_MS);
    } else {
      if (stuckTimerRef.current) {
        clearTimeout(stuckTimerRef.current);
        stuckTimerRef.current = null;
      }
      setShowStuckMessage(false);
    }
    return () => {
      if (stuckTimerRef.current) {
        clearTimeout(stuckTimerRef.current);
        stuckTimerRef.current = null;
      }
    };
  }, [hasStarted, allSegments.length, error]);

  // Show elapsed seconds while on planning_arc or generating_narrative
  useEffect(() => {
    if (!progressStep) {
      stepStartRef.current = null;
      setStepElapsed(0);
      return;
    }
    stepStartRef.current = Date.now();
    setStepElapsed(0);
    const interval = setInterval(() => {
      if (stepStartRef.current != null) {
        setStepElapsed(Math.floor((Date.now() - stepStartRef.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [progressStep]);

  const handleFollowUp = useCallback(
    async (question: string) => {
      setFollowUpError(null);
      setIsLoadingFollowUp(true);
      try {
        const result = await submitFollowUp(sessionId, question);
        if (!result.segments?.length) {
          setFollowUpError("Sankofa couldn't add to the story this time. Try another question.");
        } else {
          setFollowUpSegments((prev) => [...prev, ...result.segments]);
        }
      } catch (e) {
        setFollowUpError(e instanceof Error ? e.message : "Something went wrong. Try again.");
      } finally {
        setIsLoadingFollowUp(false);
      }
    },
    [sessionId]
  );

  return (
    <div className="min-h-screen relative">
      {/* Dark outer background with warm radial gradient */}
      <div className="fixed inset-0 bg-[var(--night)]">
        <div
          className="absolute inset-0 opacity-40"
          style={{
            background: "radial-gradient(ellipse at 50% 30%, #1a1520 0%, var(--night) 70%)",
          }}
        />
      </div>

      {/* Pre-start: audio option + Begin. Or loading overlay. */}
      <AnimatePresence>
        {allSegments.length === 0 && (
          <motion.div
            key="loader"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="fixed inset-0 z-30 flex flex-col items-center justify-center bg-[var(--night)] overflow-hidden px-6"
          >
            <div className="absolute inset-0 pointer-events-none" aria-hidden>
              {Array.from({ length: 20 }).map((_, i) => (
                <div
                  key={i}
                  className="absolute w-1 h-1 rounded-full bg-[var(--gold)]"
                  style={{
                    left: `${10 + (i * 4) % 80}%`,
                    top: `${10 + (i * 7) % 80}%`,
                    opacity: 0.2 + (i % 3) * 0.15,
                    animation: "gentle-pulse 2.5s ease-in-out infinite",
                    animationDelay: `${i * 0.2}s`,
                  }}
                />
              ))}
            </div>

            <SankofaBird className="w-24 h-24 text-[var(--gold)] animate-slow-rotate" />
            {!hasStarted ? (
              sessionInvalid ? (
                <>
                  <p className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)] text-center max-w-md">
                    This session is no longer valid. The server may have been restarted.
                  </p>
                  <p className="mt-4 font-[family-name:var(--font-body)] text-sm text-[var(--muted)] text-center">
                    Please start over from the beginning.
                  </p>
                  <Link
                    href="/intake"
                    className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                  >
                    Start over
                  </Link>
                </>
              ) : (
              <>
                <p className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)]">
                  Ready to weave your narrative.
                </p>
                <label className="mt-6 flex items-center gap-3 font-[family-name:var(--font-body)] text-[var(--ivory)] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableAudio}
                    onChange={(e) => setEnableAudio(e.target.checked)}
                    className="w-4 h-4 accent-[var(--gold)]"
                  />
                  Include audio narration
                </label>
                <div className="mt-6 flex flex-col items-center gap-2">
                  <button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={connectionTest === "checking"}
                    className="px-5 py-2 font-[family-name:var(--font-body)] text-sm text-[var(--muted)] border border-[var(--ochre)]/40 hover:border-[var(--ochre)] hover:text-[var(--ivory)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {connectionTest === "checking" ? "Checking…" : "Test API connection"}
                  </button>
                  {connectionTest === "ok" && (
                    <p className="text-sm text-[var(--gold)]" role="status">
                      {connectionMessage}
                    </p>
                  )}
                  {connectionTest === "fail" && (
                    <p className="text-sm text-[var(--terracotta)] max-w-xs text-center" role="alert">
                      {connectionMessage}
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleBeginStream}
                  className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                >
                  Begin
                </button>
              </>
              )
            ) : error ? (
              <>
                <p className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)]">
                  Something went wrong
                </p>
                <p className="mt-3 font-[family-name:var(--font-body)] text-sm text-[var(--terracotta)] max-w-md text-center">
                  {error}
                </p>
                <button
                  type="button"
                  onClick={() => {
                    reset();
                    setHasStarted(false);
                    setFollowUpSegments([]);
                  }}
                  className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                >
                  Try again
                </button>
              </>
            ) : (
              <>
                <p className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)] animate-fade-pulse">
                  Sankofa is reaching back…
                </p>
                <p className="mt-3 font-[family-name:var(--font-body)] text-sm text-[var(--muted)]">
                  Weaving your ancestral narrative
                </p>
                {progressStep && (
                  <p className="mt-2 font-[family-name:var(--font-body)] text-xs text-[var(--ochre)]/80" role="status">
                    {progressStep === "planning_arc"
                      ? "Planning your story…"
                      : "Generating narrative and images…"}
                    {stepElapsed > 0 && (
                      <span className="ml-1 text-[var(--muted)]">({stepElapsed}s)</span>
                    )}
                  </p>
                )}
                {showStuckMessage && (
                  <div className="mt-8 text-center">
                    <p className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] max-w-sm">
                      This is taking longer than usual. Check that the backend is running and your
                      Google API key is set in <code className="text-[var(--ochre)]">backend/.env</code>.
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        abort();
                        reset();
                        setHasStarted(false);
                        setFollowUpSegments([]);
                        setShowStuckMessage(false);
                      }}
                      className="mt-4 px-6 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                    >
                      Try again
                    </button>
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Narrative column */}
      <motion.div
        className="relative z-10 mx-auto w-full max-w-[min(1280px,94vw)] min-h-screen px-3 sm:px-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{
          opacity: allSegments.length > 0 ? 1 : 0,
          y: allSegments.length > 0 ? 0 : 30,
        }}
        transition={{ duration: 0.8, delay: 0.2 }}
      >
        <div className="bg-[var(--ivory)] noise-texture px-6 md:px-14 py-10 md:py-16 min-h-screen shadow-[0_0_80px_rgba(0,0,0,0.6)]">
          <NarrativeStream
            segments={allSegments}
            isStreaming={isStreaming || isLoadingFollowUp}
            isComplete={isComplete && !isLoadingFollowUp}
            error={error}
            followUpError={followUpError}
            progressStep={progressStep}
            familyName={sessionInfo?.family_name}
            region={sessionInfo?.region_of_origin}
            era={sessionInfo?.time_period}
            onFollowUp={handleFollowUp}
            onRetry={() => {
              reset();
              setHasStarted(false);
              setFollowUpSegments([]);
            }}
          />
        </div>
      </motion.div>
    </div>
  );
}
