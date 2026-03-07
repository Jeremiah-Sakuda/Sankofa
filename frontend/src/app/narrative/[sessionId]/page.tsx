"use client";

import { useEffect, useCallback, useState } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { useSSEStream } from "../../../hooks/useSSEStream";
import { submitFollowUp, NarrativeSegment } from "../../../lib/api";
import NarrativeStream from "../../../components/NarrativeStream";
import SankofaBird from "../../../components/SankofaBird";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SessionInfo {
  family_name: string;
  region_of_origin: string;
  time_period: string;
}

export default function NarrativePage() {
  const params = useParams();
  const sessionId = params.sessionId as string;
  const { segments, isStreaming, isComplete, error, startStream, abort, reset } = useSSEStream();
  const [followUpSegments, setFollowUpSegments] = useState<NarrativeSegment[]>([]);
  const [isLoadingFollowUp, setIsLoadingFollowUp] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [enableAudio, setEnableAudio] = useState(false);

  useEffect(() => {
    if (sessionId) {
      fetch(`${API_BASE}/api/session/${sessionId}`)
        .then((r) => r.json())
        .then((data) => setSessionInfo(data.user_input))
        .catch(() => {});
    }
  }, [sessionId]);

  const handleBeginStream = useCallback(() => {
    if (!sessionId || hasStarted) return;
    setHasStarted(true);
    startStream(sessionId, enableAudio);
  }, [sessionId, hasStarted, startStream, enableAudio]);

  useEffect(() => {
    return () => abort();
  }, [abort]);

  const allSegments = [...segments, ...followUpSegments];

  const handleFollowUp = useCallback(
    async (question: string) => {
      setIsLoadingFollowUp(true);
      try {
        const result = await submitFollowUp(sessionId, question);
        setFollowUpSegments((prev) => [...prev, ...result.segments]);
      } catch {
        // silently handle
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
                <button
                  type="button"
                  onClick={handleBeginStream}
                  className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                >
                  Begin
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
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Narrative column */}
      <motion.div
        className="relative z-10 mx-auto max-w-[720px] min-h-screen"
        initial={{ opacity: 0, y: 30 }}
        animate={{
          opacity: allSegments.length > 0 ? 1 : 0,
          y: allSegments.length > 0 ? 0 : 30,
        }}
        transition={{ duration: 0.8, delay: 0.2 }}
      >
        <div className="bg-[var(--ivory)] noise-texture px-5 md:px-12 py-10 md:py-16 min-h-screen shadow-[0_0_80px_rgba(0,0,0,0.6)]">
          <NarrativeStream
            segments={allSegments}
            isStreaming={isStreaming || isLoadingFollowUp}
            isComplete={isComplete && !isLoadingFollowUp}
            error={error}
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
