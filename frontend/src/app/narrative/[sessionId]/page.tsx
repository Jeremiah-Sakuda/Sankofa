"use client";

import { useEffect, useCallback, useState, useRef, useMemo } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { useSSEStream } from "../../../hooks/useSSEStream";
import { fetchEventSource, EventStreamContentType } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getSession, getFollowUpStreamUrl, getFollowUpStreamOptions, type SessionInfo } from "../../../lib/api";
import NarrativeStream from "../../../components/NarrativeStream";
// import LiveGriot from "../../../components/LiveGriot";  // Live Griot feature disabled for now
import GriotIntro from "../../../components/GriotIntro";
import ShareModal from "../../../components/ShareModal";
import GoldParticles from "../../../components/GoldParticles";

export default function NarrativePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.sessionId as string;
  const contributed = searchParams.get("contributed") === "true";
  const { segments, isStreaming, isComplete, error, progressStep, thinkingMessage, arcOutline, startStream, abort, reset } = useSSEStream();
  const [followUpSegments, setFollowUpSegments] = useState<NarrativeSegment[]>([]);
  const [isLoadingFollowUp, setIsLoadingFollowUp] = useState(false);
  const [followUpThinking, setFollowUpThinking] = useState<string | null>(null);
  const followUpAbortRef = useRef<AbortController | null>(null);
  const [hasStarted, setHasStarted] = useState(false);
  const [sessionInfo, setSessionInfo] = useState<SessionInfo | null>(null);
  const [sessionInvalid, setSessionInvalid] = useState(false);
  const [followUpError, setFollowUpError] = useState<string | null>(null);
  // const [showLiveGriot, setShowLiveGriot] = useState(false);  // Live Griot feature disabled for now
  const [showShareModal, setShowShareModal] = useState(false);
  const [userDismissedIntro, setUserDismissedIntro] = useState(false);
  const autoStartedRef = useRef(false);

  useEffect(() => {
    if (!sessionId) return;
    getSession(sessionId).then((data) => {
      if (data === null) setSessionInvalid(true);
      else setSessionInfo(data.user_input);
    });
  }, [sessionId]);

  // Auto-start stream on mount — always with audio enabled
  useEffect(() => {
    if (!sessionId || hasStarted || sessionInvalid || autoStartedRef.current) return;
    autoStartedRef.current = true;
    getSession(sessionId).then((data) => {
      if (data === null) {
        setSessionInvalid(true);
        return;
      }
      setHasStarted(true);
      startStream(sessionId, true);
    });
  }, [sessionId, hasStarted, sessionInvalid, startStream]);

  useEffect(() => {
    return () => abort();
  }, [abort]);

  const allSegments = [...segments, ...followUpSegments];

  // Ready once the first text segment's audio has arrived so narration starts
  // on the correct paragraph (not a later one whose TTS finished faster).
  // Audio can be either: (1) a separate "audio" segment with matching sequence, or
  // (2) embedded in the text segment itself as media_data (when loaded via polling).
  const hasTextSegment = segments.some((s) => s.type === "text");
  const firstTextSeg = segments.find((s) => s.type === "text" && s.content);
  const firstTextSeq = firstTextSeg?.sequence ?? null;
  const hasFirstAudio = firstTextSeq !== null && (
    // Case 1: Separate audio segment with matching sequence (streaming)
    segments.some((s) => s.type === "audio" && s.sequence === firstTextSeq) ||
    // Case 2: Audio embedded in text segment (polling/reconnect)
    !!(firstTextSeg?.media_data && firstTextSeg?.media_type?.startsWith("audio"))
  );
  const isReadyToShow = hasTextSegment && hasFirstAudio;

  // Live Griot feature disabled for now
  // const latestImageSrc = useMemo(() => {
  //   const imgs = allSegments.filter(s => s.type === "image" && s.media_data);
  //   if (imgs.length === 0) return null;
  //   const last = imgs[imgs.length - 1];
  //   return `data:${last.media_type || "image/png"};base64,${last.media_data}`;
  // }, [allSegments]);

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
        await fetchEventSource(getFollowUpStreamUrl(sessionId), {
          ...getFollowUpStreamOptions(question, true),
          signal: ctrl.signal,
          async onopen(response) {
            const ct = response.headers.get("content-type") || "";
            if (response.ok && ct.includes(EventStreamContentType)) return;
            let message = `Follow-up failed (${response.status})`;
            try {
              const body = await response.json();
              message = body?.detail || body?.error || message;
            } catch { /* ignore */ }
            setFollowUpError(message);
            setIsLoadingFollowUp(false);
            setFollowUpThinking(null);
            throw new Error(message);
          },
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
            throw err; // prevent fetchEventSource from retrying
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
    [sessionId]
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
        {/* Vignette overlay - draws eye inward */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: "linear-gradient(to right, rgba(0,0,0,0.4) 0%, transparent 15%, transparent 85%, rgba(0,0,0,0.4) 100%)",
          }}
        />
      </div>

      {/* Subtle gold particles in gutters */}
      <GoldParticles count={30} />

      {/* Cinematic griot intro overlay */}
      <AnimatePresence>
        {!userDismissedIntro && (
          <GriotIntro
            isStoryReady={isReadyToShow}
            onComplete={() => setUserDismissedIntro(true)}
            error={error}
            onRetry={() => {
              autoStartedRef.current = false;
              reset();
              setHasStarted(false);
              setFollowUpSegments([]);
            }}
            sessionInvalid={sessionInvalid}
            arcOutline={arcOutline}
            thinkingMessage={thinkingMessage}
            progressStep={progressStep}
          />
        )}
      </AnimatePresence>

      {/* Narrative column - wider for immersion */}
      <motion.div
        className="relative z-10 mx-auto w-full max-w-[min(1400px,82vw)] min-h-screen px-3 sm:px-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{
          opacity: userDismissedIntro ? 1 : 0,
          y: userDismissedIntro ? 0 : 30,
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
            autoPlay={userDismissedIntro}
            sessionId={sessionId}
            contributed={contributed}
            onFollowUp={handleFollowUp}
            // onTalkToGriot={() => setShowLiveGriot(true)}  // Live Griot feature disabled for now
            onShare={() => setShowShareModal(true)}
            onRetry={() => {
              reset();
              setHasStarted(false);
              setFollowUpSegments([]);
            }}
          />
        </div>
      </motion.div>

      {/* Live Griot voice conversation overlay - disabled for now
      <AnimatePresence>
        {showLiveGriot && (
          <LiveGriot
            sessionId={sessionId}
            onClose={() => setShowLiveGriot(false)}
            hasNarrative={allSegments.length > 0}
            latestImageSrc={latestImageSrc}
          />
        )}
      </AnimatePresence>
      */}

      {/* Share modal */}
      <ShareModal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        sessionId={sessionId}
        familyName={sessionInfo?.family_name}
        region={sessionInfo?.region_of_origin}
      />
    </div>
  );
}
