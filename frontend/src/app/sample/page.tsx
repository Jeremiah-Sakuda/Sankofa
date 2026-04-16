"use client";

import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import { fetchEventSource, EventStreamContentType } from "@microsoft/fetch-event-source";
import { NarrativeSegment, getSampleStreamUrl } from "../../lib/api";
import SegmentComponent from "../../components/NarrativeSegment";
import SankofaBird from "../../components/SankofaBird";
import ScrollProgress from "../../components/ScrollProgress";
import Link from "next/link";

interface ArcOutline {
  title: string;
  acts: Array<{
    act_number: number;
    title: string;
    summary: string;
    ambient_track: string;
  }>;
}

const ACT_LABELS: Record<number, { numeral: string }> = {
  2: { numeral: "II" },
  3: { numeral: "III" },
};

function ActTransition({ actNumber, arcOutline }: { actNumber: number; arcOutline?: ArcOutline | null }) {
  const label = ACT_LABELS[actNumber];
  const actData = arcOutline?.acts?.find((a) => a.act_number === actNumber);
  const title = actData?.title ?? null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 1.0, ease: [0.22, 1, 0.36, 1] }}
      className="my-16 md:my-20 py-8 relative"
    >
      <motion.div
        className="h-px mx-auto bg-gradient-to-r from-transparent via-[var(--gold)]/50 to-transparent"
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      />

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
    </motion.div>
  );
}

export default function SampleNarrativePage() {
  const router = useRouter();
  const [segments, setSegments] = useState<NarrativeSegment[]>([]);
  const [arcOutline, setArcOutline] = useState<ArcOutline | null>(null);
  const [isStreaming, setIsStreaming] = useState(true);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seenSequences = useRef<Set<number>>(new Set());
  const endRef = useRef<HTMLDivElement>(null);
  const prevSegmentCount = useRef(0);

  useEffect(() => {
    const ctrl = new AbortController();

    fetchEventSource(getSampleStreamUrl(), {
      signal: ctrl.signal,
      async onopen(response) {
        const ct = response.headers.get("content-type") || "";
        if (response.ok && ct.includes(EventStreamContentType)) return;
        setError("Failed to load sample narrative");
        setIsStreaming(false);
        throw new Error("Failed to connect");
      },
      onmessage(ev) {
        try {
          if (ev.event === "arc") {
            const arc = JSON.parse(ev.data) as ArcOutline;
            setArcOutline(arc);
            return;
          }
          if (ev.event === "status") {
            const data = JSON.parse(ev.data) as { status?: string };
            if (data?.status === "complete") {
              setIsStreaming(false);
              setIsComplete(true);
            }
            return;
          }
          if (ev.event === "error") {
            const data = JSON.parse(ev.data) as { error?: string };
            setError(data?.error || "Something went wrong");
            setIsStreaming(false);
            return;
          }
          if (["text", "image"].includes(ev.event)) {
            const segment = JSON.parse(ev.data) as NarrativeSegment;
            setSegments((prev) => [...prev, segment]);
          }
        } catch {
          // Ignore malformed events
        }
      },
      onerror(err) {
        if (ctrl.signal.aborted) return;
        setError("Connection lost");
        setIsStreaming(false);
        throw err;
      },
      onclose() {
        setIsStreaming(false);
      },
    });

    return () => ctrl.abort();
  }, []);

  // Auto-scroll during streaming
  useEffect(() => {
    const isNewSegment = segments.length > prevSegmentCount.current;
    prevSegmentCount.current = segments.length;

    if (!isStreaming || !isNewSegment || segments.length === 0) return;

    const scrollBottom = window.innerHeight + window.scrollY;
    const docHeight = document.documentElement.scrollHeight;
    const isNearBottom = docHeight - scrollBottom < 400;

    if (isNearBottom) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [segments.length, isStreaming]);

  const totalActs = useMemo(() => {
    const acts = new Set(segments.map((s) => s.act).filter(Boolean));
    return Math.max(acts.size, 1);
  }, [segments]);

  const currentAct = useMemo(() => {
    const textSegs = segments.filter((s) => s.type === "text" && s.act);
    return textSegs.length > 0 ? (textSegs[textSegs.length - 1].act ?? 1) : 1;
  }, [segments]);

  const actGradients: Record<number, string> = {
    1: "radial-gradient(ellipse at 50% 30%, #1a1520 0%, var(--night) 70%)",
    2: "radial-gradient(ellipse at 50% 40%, #1c1210 0%, var(--night) 70%)",
    3: "radial-gradient(ellipse at 50% 50%, #1a1815 0%, #0d0d0d 70%)",
  };

  let lastAct = 0;

  if (segments.length === 0 && isStreaming) {
    return (
      <div className="min-h-screen relative">
        <div className="fixed inset-0 bg-[var(--night)]" />
        <div className="flex min-h-screen flex-col items-center justify-center relative z-10">
          <SankofaBird className="w-16 h-16 text-[var(--gold)] animate-slow-rotate" />
          <p className="mt-8 font-[family-name:var(--font-display)] text-lg italic text-[var(--ivory)] animate-fade-pulse">
            Preparing a sample journey&hellip;
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative">
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

      <motion.div
        className="relative z-10 mx-auto w-full max-w-[min(1280px,94vw)] min-h-screen px-3 sm:px-4"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
      >
        <div className="bg-[var(--ivory)] noise-texture px-6 md:px-14 py-10 md:py-16 min-h-screen shadow-[0_0_80px_rgba(0,0,0,0.6)]">
          <ScrollProgress totalActs={totalActs} currentAct={currentAct} isComplete={isComplete} />

          {/* Sample narrative banner */}
          <motion.div
            className="mb-8 p-4 bg-[var(--gold)]/10 border border-[var(--gold)]/30 rounded text-center"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <p className="font-[family-name:var(--font-body)] text-sm text-[var(--umber)]">
              This is a sample narrative to show you what Sankofa creates.{" "}
              <button
                onClick={() => router.push("/")}
                className="text-[var(--gold)] hover:underline cursor-pointer font-medium"
              >
                Create your own story
              </button>
            </p>
          </motion.div>

          {/* Header */}
          <header className="text-center mb-16">
            <div className="flex items-center justify-between mb-4">
              <Link
                href="/"
                className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
              >
                Create your own narrative
              </Link>
            </div>
            <h1 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl tracking-[0.3em] text-[var(--gold)] uppercase">
              Sankofa
            </h1>
            <div className="mt-3 h-px w-24 mx-auto bg-[var(--gold)]/40" />
            {arcOutline && (
              <p className="mt-4 font-[family-name:var(--font-display)] text-lg italic text-[var(--umber)]/80">
                {arcOutline.title}
              </p>
            )}
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
                    <SegmentComponent
                      segment={segment}
                      index={i}
                      isFirstInAct={isFirstInAct || false}
                      isNarrating={false}
                      isNarrationPaused={false}
                      spotlightActive={false}
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
                  The story continues&hellip;
                </span>
              </div>
            )}
          </div>

          {/* Footer */}
          {isComplete && (
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
                A sample narrative: The Mwangi Family, Kenya, 1940s
              </motion.p>
              <p className="mt-2 text-center font-[family-name:var(--font-body)] text-xs text-[var(--muted)] opacity-60">
                Sankofa distinguishes historical record from narrative imagination.
                Look for the margin annotations.
              </p>

              {/* CTA to create own narrative */}
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
                  Ready to discover your own heritage?
                </motion.p>

                <motion.button
                  onClick={() => router.push("/")}
                  initial={{ opacity: 0, y: 8 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.5 }}
                  className="px-8 py-3 border border-[var(--gold)] bg-[var(--gold)] text-[var(--night)] font-[family-name:var(--font-display)] text-base tracking-wider uppercase hover:bg-transparent hover:text-[var(--gold)] transition-all cursor-pointer"
                >
                  Begin Your Journey
                </motion.button>
              </div>
            </motion.footer>
          )}

          {error && (
            <div className="mt-8 p-4 text-center font-[family-name:var(--font-body)] text-sm">
              <p className="text-[var(--terracotta)]">{error}</p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="mt-3 px-4 py-2 border border-[var(--terracotta)] text-[var(--terracotta)] hover:bg-[var(--terracotta)] hover:text-[var(--ivory)] transition-all cursor-pointer"
              >
                Try again
              </button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
