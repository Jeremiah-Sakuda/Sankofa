"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import type { StreamProgressStep } from "../hooks/useSSEStream";
import NarrativeSegment from "./NarrativeSegment";
import NarrationBar, { type AudioTrack } from "./NarrationBar";
import SankofaBird from "./SankofaBird";

const FOLLOW_UP_MAX_LENGTH = 500;

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
  onFollowUp?: (question: string) => void;
  onRetry?: () => void;
}

function ActDivider() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="flex items-center justify-center my-12 gap-4"
    >
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[var(--ochre)]/30 to-transparent" />
      <SankofaBird className="w-6 h-6 text-[var(--ochre)] opacity-40 shrink-0" />
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[var(--ochre)]/30 to-transparent" />
    </motion.div>
  );
}

function buildAudioTracks(segments: SegmentType[]): AudioTrack[] {
  const tracks: AudioTrack[] = [];

  for (const seg of segments) {
    // Text segments that have embedded audio
    if (seg.type === "text" && seg.media_data && seg.media_type?.startsWith("audio")) {
      tracks.push({
        id: `text-${seg.sequence}`,
        label: seg.content?.slice(0, 80)?.replace(/\[.*?\]/g, "").trim() || `Segment ${seg.sequence + 1}`,
        audioData: seg.media_data,
        mediaType: seg.media_type,
        segmentSequence: seg.sequence,
      });
    }
    // Standalone audio segments
    if (seg.type === "audio" && seg.media_data) {
      tracks.push({
        id: `audio-${seg.sequence}`,
        label: seg.content?.slice(0, 80) || `Narration ${seg.sequence + 1}`,
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
  onFollowUp,
  onRetry,
}: Props) {
  const [followUpInput, setFollowUpInput] = useState("");
  const [followUpValidationError, setFollowUpValidationError] = useState<string | null>(null);
  const [activeSequence, setActiveSequence] = useState<number | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const audioTracks = useMemo(() => buildAudioTracks(segments), [segments]);

  useEffect(() => {
    if (segments.length > 0) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [segments.length]);

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

            return (
              <div
                key={`seg-${segment.sequence}-${i}`}
                ref={i === segments.length - 1 ? endRef : undefined}
              >
                {isNewAct && i > 0 && <ActDivider />}
                <NarrativeSegment
                  segment={segment}
                  index={i}
                  isFirstInAct={isFirstInAct || false}
                  isNarrating={activeSequence === segment.sequence}
                  spotlightActive={isAudioPlaying && activeSequence !== null}
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
          <p className="text-center font-[family-name:var(--font-body)] text-sm text-[var(--muted)]">
            {familyName != null && region != null && era != null
              ? `A narrative woven from: ${familyName}, ${region}, ${era}`
              : "A narrative woven from your heritage."}
          </p>
          <p className="mt-2 text-center font-[family-name:var(--font-body)] text-xs text-[var(--muted)] opacity-60">
            Sankofa distinguishes historical record from narrative imagination.
            Look for the margin annotations.
          </p>

          {/* Follow-up input */}
          {onFollowUp && (
            <div className="mt-12 text-center">
              <div className="flex items-center justify-center gap-4 mb-6">
                <div className="h-px flex-1 max-w-[80px] bg-[var(--ochre)]/20" />
                <SankofaBird className="w-5 h-5 text-[var(--ochre)] opacity-30" />
                <div className="h-px flex-1 max-w-[80px] bg-[var(--ochre)]/20" />
              </div>
              <p className="font-[family-name:var(--font-display)] text-lg italic text-[var(--umber)] mb-6">
                Want to go deeper? Ask Sankofa…
              </p>
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
