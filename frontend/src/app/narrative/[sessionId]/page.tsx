"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { useSSEStream } from "../../../hooks/useSSEStream";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { submitFollowUp, NarrativeSegment, checkBackendHealth, getSession, getFollowUpStreamUrl, type SessionInfo } from "../../../lib/api";
import NarrativeStream from "../../../components/NarrativeStream";
import SankofaBird from "../../../components/SankofaBird";
import GoldParticles from "../../../components/GoldParticles";

const STUCK_TIMEOUT_MS = 90_000; // show "taking longer" after 90s with no segments

export default function NarrativePage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const { segments, isStreaming, isComplete, error, progressStep, thinkingMessage, arcOutline, startStream, abort, reset } = useSSEStream();
  const [followUpSegments, setFollowUpSegments] = useState<NarrativeSegment[]>([]);
  const [isLoadingFollowUp, setIsLoadingFollowUp] = useState(false);
  const [followUpThinking, setFollowUpThinking] = useState<string | null>(null);
  const followUpAbortRef = useRef<AbortController | null>(null);
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
    if (!sessionId) return;
    getSession(sessionId).then((data) => {
      if (data === null) setSessionInvalid(true);
      else setSessionInfo(data.user_input);
    });
  }, [sessionId]);

  const handleBeginStream = useCallback(async () => {
    if (!sessionId || hasStarted) return;
    const data = await getSession(sessionId);
    if (data === null) {
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
      setFollowUpThinking(null);

      // Abort any previous follow-up stream
      followUpAbortRef.current?.abort();
      const ctrl = new AbortController();
      followUpAbortRef.current = ctrl;

      let receivedSegments = false;

      try {
        await fetchEventSource(getFollowUpStreamUrl(sessionId, question, enableAudio), {
          signal: ctrl.signal,
          onmessage(ev) {
            try {
              if (ev.event === "status") {
                const data = JSON.parse(ev.data) as { status?: string; message?: string };
                if (data?.status === "complete") {
                  setIsLoadingFollowUp(false);
                  setFollowUpThinking(null);
                  if (!receivedSegments) {
                    setFollowUpError("Sankofa couldn't add to the story this time. Try another question.");
                  }
                } else if (data?.status === "thinking" || data?.status === "agent_message") {
                  setFollowUpThinking(data.message ?? null);
                }
                return;
              }
              if (ev.event === "error") {
                const data = JSON.parse(ev.data) as { error?: string };
                setFollowUpError(data?.error || "Follow-up generation failed");
                setIsLoadingFollowUp(false);
                setFollowUpThinking(null);
                return;
              }
              if (["text", "image", "audio", "map"].includes(ev.event)) {
                const segment = JSON.parse(ev.data) as NarrativeSegment;
                receivedSegments = true;
                setFollowUpSegments((prev) => [...prev, segment]);
              }
            } catch {
              // Ignore malformed events
            }
          },
          onerror(err) {
            if (ctrl.signal.aborted) return;
            setFollowUpError(err?.message || "Connection lost during follow-up");
            setIsLoadingFollowUp(false);
            setFollowUpThinking(null);
          },
          onclose() {
            setIsLoadingFollowUp(false);
            setFollowUpThinking(null);
          },
        });
      } catch (e) {
        if (!ctrl.signal.aborted) {
          setFollowUpError(e instanceof Error ? e.message : "Something went wrong. Try again.");
          setIsLoadingFollowUp(false);
          setFollowUpThinking(null);
        }
      }
    },
    [sessionId, enableAudio]
  );

  const currentAct = allSegments.length > 0
    ? (allSegments[allSegments.length - 1].act ?? 1)
    : 1;

  const actGradients: Record<number, string> = {
    1: "radial-gradient(ellipse at 50% 30%, #1a1520 0%, var(--night) 70%)",
    2: "radial-gradient(ellipse at 50% 40%, #1c1210 0%, var(--night) 70%)",
    3: "radial-gradient(ellipse at 50% 50%, #1a1815 0%, #0d0d0d 70%)",
  };

  return (
    <div className="min-h-screen relative">
      {/* Dark outer background with warm per-act gradient */}
      <div className="fixed inset-0 bg-[var(--night)]">
        <motion.div
          className="absolute inset-0"
          animate={{ opacity: 0.4 }}
          transition={{ duration: 2 }}
          style={{
            background: actGradients[currentAct] ?? actGradients[1],
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
            <GoldParticles count={hasStarted ? 35 : 20} />

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
                    href="/"
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
                <motion.p
                  className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)]"
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  Sankofa is reaching back…
                </motion.p>
                <p className="mt-3 font-[family-name:var(--font-body)] text-sm text-[var(--muted)]">
                  Weaving your ancestral narrative
                </p>
                {(progressStep || thinkingMessage) && (
                  <p className="mt-2 font-[family-name:var(--font-body)] text-xs text-[var(--ochre)]/80" role="status">
                    {thinkingMessage
                      ? thinkingMessage
                      : progressStep === "planning_arc"
                        ? "Planning your story…"
                        : "Generating narrative and images…"}
                    {stepElapsed > 0 && (
                      <span className="ml-1 text-[var(--muted)]">({stepElapsed}s)</span>
                    )}
                  </p>
                )}

                {/* Arc chapter cards -- shown while Gemini generates the narrative */}
                <AnimatePresence>
                  {arcOutline && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.8, delay: 0.3 }}
                      className="mt-10 w-full max-w-md"
                    >
                      <div className="h-px w-16 mx-auto bg-[var(--gold)]/40 mb-6" />
                      {[
                        { key: "act1_setting", num: "I" },
                        { key: "act2_people", num: "II" },
                        { key: "act3_thread", num: "III" },
                      ].map((act, i) => {
                        const actData = arcOutline[act.key as keyof typeof arcOutline];
                        const title = typeof actData === "object" && actData?.title ? actData.title : null;
                        if (!title) return null;
                        return (
                          <motion.div
                            key={act.key}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.6, delay: 0.5 + i * 0.4 }}
                            className="flex items-baseline gap-3 mb-3"
                          >
                            <span className="font-[family-name:var(--font-display)] text-xs text-[var(--gold)]/60 tracking-widest shrink-0">
                              {act.num}
                            </span>
                            <span className="font-[family-name:var(--font-display)] text-sm text-[var(--ivory)]/70 italic">
                              {title}
                            </span>
                          </motion.div>
                        );
                      })}
                      <motion.div
                        className="mt-4 h-px bg-gradient-to-r from-transparent via-[var(--gold)]/30 to-transparent"
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ duration: 1.5, delay: 1.8 }}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>

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
            followUpThinking={followUpThinking}
            progressStep={progressStep}
            familyName={sessionInfo?.family_name}
            region={sessionInfo?.region_of_origin}
            era={sessionInfo?.time_period}
            arcOutline={arcOutline}
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
