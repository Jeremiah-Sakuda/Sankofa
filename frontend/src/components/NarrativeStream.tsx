"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import NarrativeSegment from "./NarrativeSegment";
import SankofaBird from "./SankofaBird";

interface Props {
  segments: SegmentType[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  familyName?: string;
  region?: string;
  era?: string;
  onFollowUp?: (question: string) => void;
}

function ActDivider() {
  return (
    <div className="flex items-center justify-center my-12 gap-4">
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[var(--ochre)]/30 to-transparent" />
      <SankofaBird className="w-6 h-6 text-[var(--ochre)] opacity-40" />
      <div className="h-px flex-1 bg-gradient-to-r from-transparent via-[var(--ochre)]/30 to-transparent" />
    </div>
  );
}

export default function NarrativeStream({
  segments,
  isStreaming,
  isComplete,
  error,
  familyName,
  region,
  era,
  onFollowUp,
}: Props) {
  const [followUpInput, setFollowUpInput] = useState("");

  let lastAct = 0;

  const handleFollowUp = () => {
    const q = followUpInput.trim();
    if (q && onFollowUp) {
      onFollowUp(q);
      setFollowUpInput("");
    }
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
        <h1 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl tracking-[0.3em] text-[var(--gold)] uppercase">
          Sankofa
        </h1>
        <div className="mt-3 h-px w-24 mx-auto bg-[var(--gold)]/40" />
      </header>

      {/* Narrative body */}
      <div className="relative pl-4 md:pl-28">
        <AnimatePresence>
          {segments.map((segment, i) => {
            const isNewAct = segment.act && segment.act !== lastAct;
            if (segment.act) lastAct = segment.act;
            const isFirstInAct = isNewAct && segment.type === "text";

            return (
              <div key={`seg-${segment.sequence}-${i}`}>
                {isNewAct && i > 0 && <ActDivider />}
                <NarrativeSegment
                  segment={segment}
                  index={i}
                  isFirstInAct={isFirstInAct || false}
                />
              </div>
            );
          })}
        </AnimatePresence>

        {isStreaming && (
          <div className="flex items-center gap-3 mt-8 mb-4">
            <div className="w-2 h-2 rounded-full bg-[var(--gold)] animate-gentle-pulse" />
            <span className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] italic">
              The story continues…
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      {(isComplete || (!isStreaming && segments.length > 0)) && (
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 0.8 }}
          className="mt-16 pt-8 border-t border-[var(--ochre)]/20"
        >
          <p className="text-center font-[family-name:var(--font-body)] text-sm text-[var(--muted)]">
            A narrative woven from: {familyName}, {region}, {era}
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
                  onChange={(e) => setFollowUpInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleFollowUp()}
                  placeholder="Tell me about the music of that era…"
                  className="flex-1 bg-transparent border-b-2 border-[var(--ochre)]/40 text-[var(--umber)] font-[family-name:var(--font-body)] text-base pb-2 transition-colors focus:border-[var(--gold)] caret-[var(--gold)]"
                />
                <button
                  onClick={handleFollowUp}
                  className="px-5 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                >
                  Ask
                </button>
              </div>
            </div>
          )}
        </motion.footer>
      )}

      {error && (
        <div className="mt-8 p-4 text-center text-[var(--terracotta)] font-[family-name:var(--font-body)] text-sm">
          {error}
        </div>
      )}
    </motion.div>
  );
}
