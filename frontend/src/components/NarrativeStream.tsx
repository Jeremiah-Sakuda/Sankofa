"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import type { StreamProgressStep, ArcOutline } from "../hooks/useSSEStream";
import NarrativeSegment from "./NarrativeSegment";
import NarrationBar, { type AudioTrack } from "./NarrationBar";
import ScrollProgress from "./ScrollProgress";
import SankofaBird from "./SankofaBird";

const FOLLOW_UP_MAX_LENGTH = 500;

const ACT_LABELS: Record<number, { numeral: string; arcKey: keyof ArcOutline }> = {
  2: { numeral: "II", arcKey: "act2_people" },
  3: { numeral: "III", arcKey: "act3_thread" },
};

interface Props {
  segments: SegmentType[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  followUpError?: string | null;
  progressStep?: StreamProgressStep;
  familyName?: string;
  region?: string;
  era?: string;
  arcOutline?: ArcOutline | null;
  onFollowUp?: (question: string) => void;
  onRetry?: () => void;
}

function ActTransition({ actNumber, arcOutline }: { actNumber: number; arcOutline?: ArcOutline | null }) {
  const label = ACT_LABELS[actNumber];
  const actData = label && arcOutline ? arcOutline[label.arcKey] : null;
  const title = typeof actData === "object" && actData?.title ? actData.title : null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 1.0, ease: [0.22, 1, 0.36, 1] }}
      className="my-16 md:my-20 py-8 relative"
    >
      {/* Golden line expanding from center */}
      <motion.div
        className="h-px mx-auto bg-gradient-to-r from-transparent via-[var(--gold)]/50 to-transparent"
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      />

      {/* Sankofa bird traveling along the line */}
      <div className="flex justify-center -mt-3">
        <motion.div
          initial={{ opacity: 0, scale: 0.5, rotate: -20 }}
          whileInView={{ opacity: 1, scale: 1, rotate: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        >
          <SankofaBird className="w-7 h-7 text-[var(--gold)] opacity-60" />
        </motion.div>
      </div>

      {/* Act numeral and title */}
      {label && (
        <motion.div
          className="text-center mt-4"
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.6 }}
        >
          <span className="font-[family-name:var(--font-display)] text-xs tracking-[0.3em] text-[var(--gold)]/50 uppercase">
            Act {label.numeral}
          </span>
          {title && (
            <motion.p
              className="mt-2 font-[family-name:var(--font-display)] text-base md:text-lg italic text-[var(--umber)]/70"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 1.0 }}
            >
              {title}
            </motion.p>
          )}
        </motion.div>
      )}

      {/* Floating gold particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden>
        {Array.from({ length: 8 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-[var(--gold)]"
            style={{
              left: `${15 + (i * 10) % 70}%`,
              top: `${20 + (i * 13) % 60}%`,
            }}
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: [0, 0.4, 0], y: [10, -15, -25] }}
            viewport={{ once: true }}
            transition={{
              duration: 2.5,
              delay: 0.4 + i * 0.15,
              ease: "easeOut",
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}

function buildAudioTracks(segments: SegmentType[]): AudioTrack[] {
  const tracks: AudioTrack[] = [];

  let trackNum = 0;
  for (const seg of segments) {
    if (seg.type === "text" && seg.media_data && seg.media_type?.startsWith("audio")) {
      trackNum++;
      tracks.push({
        id: `text-${seg.sequence}`,
        label: `Narration ${trackNum}`,
        audioData: seg.media_data,
        mediaType: seg.media_type,
        segmentSequence: seg.sequence,
      });
    }
    if (seg.type === "audio" && seg.media_data) {
      trackNum++;
      tracks.push({
        id: `audio-${seg.sequence}`,
        label: `Narration ${trackNum}`,
        audioData: seg.media_data,
        mediaType: seg.media_type ?? "audio/wav",
        segmentSequence: seg.sequence,
      });
    }
  }

  return tracks;
}

export default function NarrativeStream({
  segments,
  isStreaming,
  isComplete,
  error,
  familyName,
  region,
  era,
  followUpError,
  progressStep,
  arcOutline,
  onFollowUp,
  onRetry,
}: Props) {
  const [followUpInput, setFollowUpInput] = useState("");
  const [followUpValidationError, setFollowUpValidationError] = useState<string | null>(null);
  const [activeSequence, setActiveSequence] = useState<number | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const seenSequences = useRef<Set<number>>(new Set());
  const prevSegmentCountRef = useRef(0);

  const audioTracks = useMemo(() => buildAudioTracks(segments), [segments]);

  const totalActs = useMemo(() => {
    const acts = new Set(segments.map((s) => s.act).filter(Boolean));
    return Math.max(acts.size, 1);
  }, [segments]);

  const currentAct = useMemo(() => {
    const textSegs = segments.filter((s) => s.type === "text" && s.act);
    return textSegs.length > 0 ? (textSegs[textSegs.length - 1].act ?? 1) : 1;
  }, [segments]);

  // Auto-scroll only during active streaming when the user is near the bottom
  useEffect(() => {
    const isNewSegment = segments.length > prevSegmentCountRef.current;
    prevSegmentCountRef.current = segments.length;

    if (!isStreaming || !isNewSegment || segments.length === 0) return;

    // Only auto-scroll if the user is near the bottom of the page
    const scrollBottom = window.innerHeight + window.scrollY;
    const docHeight = document.documentElement.scrollHeight;
    const isNearBottom = docHeight - scrollBottom < 400;

    if (isNearBottom) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [segments.length, isStreaming]);

  const handleTrackChange = useCallback((track: AudioTrack | null) => {
    setActiveSequence(track?.segmentSequence ?? null);
    if (track) {
      const el = document.querySelector(`[data-sequence="${track.segmentSequence}"]`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  const handlePlayStateChange = useCallback((playing: boolean) => {
    setIsAudioPlaying(playing);
  }, []);

  let lastAct = 0;

  const handleFollowUp = () => {
    const q = followUpInput.trim();
    if (!q || !onFollowUp) return;
    if (q.length > FOLLOW_UP_MAX_LENGTH) {
      setFollowUpValidationError(`Please keep your question to ${FOLLOW_UP_MAX_LENGTH} characters or fewer.`);
      return;
    }
    setFollowUpValidationError(null);
    onFollowUp(q);
    setFollowUpInput("");
  };

  if (segments.length === 0 && !isStreaming) {
    return null;
  }

  if (segments.length === 0 && isStreaming) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <SankofaBird className="w-16 h-16 text-[var(--gold)] animate-slow-rotate" />
        <p className="mt-8 font-[family-name:var(--font-display)] text-lg italic text-[var(--ivory)] animate-fade-pulse">
          Sankofa is reaching back…
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
    >
      <ScrollProgress totalActs={totalActs} currentAct={currentAct} isComplete={isComplete} />
      {/* Header */}
      <header className="text-center mb-16">
        <div className="flex items-center justify-between mb-4">
          <Link
            href="/"
            className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
          >
            Begin new narrative
          </Link>
        </div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl tracking-[0.3em] text-[var(--gold)] uppercase">
          Sankofa
        </h1>
        <div className="mt-3 h-px w-24 mx-auto bg-[var(--gold)]/40" />
      </header>

      {/* Narrative body */}
      <div className="relative pl-4 md:pl-28">
        <AnimatePresence>
          {segments.map((segment, i) => {
            if (segment.type === "audio") return null;

            const isNewAct = segment.act && segment.act !== lastAct;
            if (segment.act) lastAct = segment.act;
            const isFirstInAct = isNewAct && segment.type === "text";

            const isNew = !seenSequences.current.has(segment.sequence);
            if (isNew) seenSequences.current.add(segment.sequence);

            return (
              <div
                key={`seg-${segment.sequence}-${i}`}
                ref={i === segments.length - 1 ? endRef : undefined}
              >
                {isNewAct && i > 0 && <ActTransition actNumber={segment.act!} arcOutline={arcOutline} />}
                <NarrativeSegment
                  segment={segment}
                  index={i}
                  isFirstInAct={isFirstInAct || false}
                  isNarrating={activeSequence === segment.sequence}
                  spotlightActive={isAudioPlaying && activeSequence !== null}
                  isNew={isNew}
                />
              </div>
            );
          })}
        </AnimatePresence>

        {isStreaming && (
          <div className="flex items-center gap-3 mt-8 mb-4" ref={endRef}>
            <div className="w-2 h-2 rounded-full bg-[var(--gold)] animate-gentle-pulse" />
            <span className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] italic">
              {progressStep === "generating_audio" ? "Adding narration…" : "The story continues…"}
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      {(isComplete || (!isStreaming && segments.length > 0)) && (
        <motion.footer
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.1 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="mt-16 pt-8 border-t border-[var(--ochre)]/20"
        >
          <motion.p
            className="text-center font-[family-name:var(--font-display)] text-sm tracking-wider text-[var(--gold)]/60 uppercase"
            animate={{ opacity: [0.4, 0.7, 0.4] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          >
            {familyName != null && region != null && era != null
              ? `A narrative woven from: ${familyName}, ${region}, ${era}`
              : "A narrative woven from your heritage."}
          </motion.p>
          <p className="mt-2 text-center font-[family-name:var(--font-body)] text-xs text-[var(--muted)] opacity-60">
            Sankofa distinguishes historical record from narrative imagination.
            Look for the margin annotations.
          </p>

          {/* Follow-up input */}
          {onFollowUp && (
            <div className="mt-12 text-center">
              <div className="flex items-center justify-center gap-4 mb-6">
                <motion.div
                  className="h-px flex-1 max-w-[80px] bg-gradient-to-r from-transparent to-[var(--ochre)]/30"
                  initial={{ scaleX: 0 }}
                  whileInView={{ scaleX: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8 }}
                  style={{ transformOrigin: "right" }}
                />
                <motion.div
                  whileInView={{ rotate: [0, 10, -10, 0] }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.5, delay: 0.5 }}
                >
                  <SankofaBird className="w-5 h-5 text-[var(--gold)] opacity-50" />
                </motion.div>
                <motion.div
                  className="h-px flex-1 max-w-[80px] bg-gradient-to-l from-transparent to-[var(--ochre)]/30"
                  initial={{ scaleX: 0 }}
                  whileInView={{ scaleX: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.8 }}
                  style={{ transformOrigin: "left" }}
                />
              </div>
              <motion.p
                className="font-[family-name:var(--font-display)] text-lg italic text-[var(--umber)] mb-6"
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.3 }}
              >
                Your story continues&hellip;
              </motion.p>
              <div className="flex items-center justify-center gap-3 max-w-lg mx-auto">
                <input
                  type="text"
                  value={followUpInput}
                  onChange={(e) => {
                    setFollowUpInput(e.target.value);
                    setFollowUpValidationError(null);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleFollowUp()}
                  placeholder="Tell me about the music of that era…"
                  maxLength={FOLLOW_UP_MAX_LENGTH}
                  className="flex-1 bg-transparent border-b-2 border-[var(--ochre)]/40 text-[var(--umber)] font-[family-name:var(--font-body)] text-base pb-2 transition-colors focus:border-[var(--gold)] caret-[var(--gold)]"
                />
                <button
                  onClick={handleFollowUp}
                  disabled={isStreaming}
                  className="px-5 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Ask
                </button>
              </div>
              {(followUpError || followUpValidationError) && (
                <p className="mt-4 font-[family-name:var(--font-body)] text-sm text-[var(--terracotta)]" role="alert">
                  {followUpError ?? followUpValidationError}
                </p>
              )}
            </div>
          )}
        </motion.footer>
      )}

      {error && (
        <div className="mt-8 p-4 text-center font-[family-name:var(--font-body)] text-sm">
          <p className="text-[var(--terracotta)]">{error}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 px-4 py-2 border border-[var(--terracotta)] text-[var(--terracotta)] hover:bg-[var(--terracotta)] hover:text-[var(--ivory)] transition-all cursor-pointer"
            >
              Try again
            </button>
          )}
        </div>
      )}

      {/* Bottom padding so content doesn't hide behind the narration bar */}
      {audioTracks.length > 0 && <div className="h-28" />}

      {/* Persistent bottom narration bar */}
      <AnimatePresence>
        {audioTracks.length > 0 && (
          <NarrationBar
            tracks={audioTracks}
            onTrackChange={handleTrackChange}
            onPlayStateChange={handlePlayStateChange}
            autoPlay
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
