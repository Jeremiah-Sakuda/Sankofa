"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "motion/react";
import Link from "next/link";
import { NarrativeSegment, API_BASE } from "../../../lib/api";
import SegmentComponent from "../../../components/NarrativeSegment";
import SankofaBird from "../../../components/SankofaBird";
import ScrollProgress from "../../../components/ScrollProgress";
import GoldParticles from "../../../components/GoldParticles";

interface PublicStory {
  session_id: string;
  family_name: string;
  region: string;
  era: string;
  arc_title: string | null;
  arc_outline: {
    acts?: Array<{
      act_number: number;
      title: string;
    }>;
  } | null;
  segments: NarrativeSegment[];
}

const ACT_LABELS: Record<number, { numeral: string }> = {
  2: { numeral: "II" },
  3: { numeral: "III" },
};

function ActTransition({ actNumber, arcOutline }: { actNumber: number; arcOutline: PublicStory["arc_outline"] }) {
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

export default function PublicStoryPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [story, setStory] = useState<PublicStory | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const seenSequences = useRef<Set<number>>(new Set());

  useEffect(() => {
    const fetchStory = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/story/${sessionId}`);
        if (res.status === 404) {
          setError("This story doesn't exist or is no longer public.");
          return;
        }
        if (!res.ok) {
          setError("Failed to load story");
          return;
        }
        const data = await res.json();
        setStory(data);
      } catch (e) {
        setError("Failed to load story");
      } finally {
        setIsLoading(false);
      }
    };

    fetchStory();
  }, [sessionId]);

  const totalActs = useMemo(() => {
    if (!story) return 1;
    const acts = new Set(story.segments.map((s) => s.act).filter(Boolean));
    return Math.max(acts.size, 1);
  }, [story]);

  const currentAct = useMemo(() => {
    if (!story) return 1;
    const textSegs = story.segments.filter((s) => s.type === "text" && s.act);
    return textSegs.length > 0 ? (textSegs[textSegs.length - 1].act ?? 1) : 1;
  }, [story]);

  const actGradients: Record<number, string> = {
    1: "radial-gradient(ellipse at 50% 30%, #1a1520 0%, var(--night) 70%)",
    2: "radial-gradient(ellipse at 50% 40%, #1c1210 0%, var(--night) 70%)",
    3: "radial-gradient(ellipse at 50% 50%, #1a1815 0%, #0d0d0d 70%)",
  };

  if (isLoading) {
    return (
      <div className="min-h-screen relative">
        <div className="fixed inset-0 bg-[var(--night)]" />
        <div className="flex min-h-screen flex-col items-center justify-center relative z-10">
          <SankofaBird className="w-12 h-12 text-[var(--gold)] animate-slow-rotate" />
          <p className="mt-6 font-[family-name:var(--font-display)] text-lg italic text-[var(--ivory)] animate-fade-pulse">
            Loading story&hellip;
          </p>
        </div>
      </div>
    );
  }

  if (error || !story) {
    return (
      <div className="min-h-screen relative">
        <div className="fixed inset-0 bg-[var(--night)]" />
        <GoldParticles count={15} />
        <div className="flex min-h-screen flex-col items-center justify-center relative z-10 px-4">
          <SankofaBird className="w-16 h-16 text-[var(--gold)]/40 mb-6" />
          <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--ivory)] mb-3 text-center">
            Story Not Found
          </h1>
          <p className="font-[family-name:var(--font-body)] text-[var(--muted)] text-center mb-8 max-w-md">
            {error || "This story doesn't exist or is no longer public."}
          </p>
          <Link
            href="/"
            className="px-6 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all"
          >
            Create Your Own Story
          </Link>
        </div>
      </div>
    );
  }

  let lastAct = 0;

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
          <ScrollProgress totalActs={totalActs} currentAct={currentAct} isComplete={true} />

          {/* Shared story banner */}
          <motion.div
            className="mb-8 p-4 bg-[var(--gold)]/10 border border-[var(--gold)]/30 rounded text-center"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <p className="font-[family-name:var(--font-body)] text-sm text-[var(--umber)]">
              A heritage narrative shared with you.{" "}
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
            <Link
              href="/"
              className="inline-flex items-center gap-2 mb-6"
            >
              <SankofaBird className="w-8 h-8 text-[var(--gold)]" />
            </Link>
            <h1 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl tracking-[0.3em] text-[var(--gold)] uppercase">
              Sankofa
            </h1>
            <div className="mt-3 h-px w-24 mx-auto bg-[var(--gold)]/40" />
            {story.arc_title && (
              <p className="mt-4 font-[family-name:var(--font-display)] text-lg italic text-[var(--umber)]/80">
                {story.arc_title}
              </p>
            )}
          </header>

          {/* Narrative body */}
          <div className="relative pl-4 md:pl-28">
            <AnimatePresence>
              {story.segments.map((segment, i) => {
                if (segment.type === "audio") return null;

                const isNewAct = segment.act && segment.act !== lastAct;
                if (segment.act) lastAct = segment.act;
                const isFirstInAct = isNewAct && segment.type === "text";

                const isNew = !seenSequences.current.has(segment.sequence);
                if (isNew) seenSequences.current.add(segment.sequence);

                return (
                  <div key={`seg-${segment.sequence}-${i}`}>
                    {isNewAct && i > 0 && <ActTransition actNumber={segment.act!} arcOutline={story.arc_outline} />}
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
          </div>

          {/* Footer */}
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
              A narrative woven from: {story.family_name}, {story.region}, {story.era}
            </motion.p>
            <p className="mt-2 text-center font-[family-name:var(--font-body)] text-xs text-[var(--muted)] opacity-60">
              Sankofa distinguishes historical record from narrative imagination.
            </p>

            {/* CTA to create own story */}
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
                <SankofaBird className="w-5 h-5 text-[var(--gold)] opacity-50" />
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
                Discover your own heritage
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
        </div>
      </motion.div>
    </div>
  );
}
