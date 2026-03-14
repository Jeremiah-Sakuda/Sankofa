"use client";

import { useRef, useState, useEffect } from "react";
import { motion, useScroll, useTransform, useInView, Variants } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import TrustBadge from "./TrustBadge";

const WORD_STAGGER = 0.018;
const LINE_STAGGER = 0.12;

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: WORD_STAGGER,
      delayChildren: 0.1,
    },
  },
};

const wordVariants: Variants = {
  hidden: { opacity: 0, y: 6 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] },
  },
};

function RevealWords({ text, isNarrating, isNarrationPaused, totalWordsInSegment, cumulativeWordOffset }: { text: string; isNarrating: boolean; isNarrationPaused?: boolean; totalWordsInSegment: number; cumulativeWordOffset: number }) {
  const words = text.split(/(\s+)/);
  let localWordIdx = 0;
  
  return (
    <>
      {words.map((token, i) => {
        if (/^\s+$/.test(token)) return token;
        
        const globalWordIdx = cumulativeWordOffset + localWordIdx;
        localWordIdx++;

        // Calculate staggered delay for audio sync highlighting 
        // We know the total duration is CSS variable --narrate-duration (in seconds)
        // We approximate start time as a fraction of total words
        const syncDelayPct = totalWordsInSegment > 0 ? (globalWordIdx / totalWordsInSegment) : 0;
        
        return (
          <motion.span
            key={i}
            variants={wordVariants}
            className={`inline ${isNarrating || isNarrationPaused ? "sync-highlight" : ""}`}
            style={isNarrating || isNarrationPaused ? { "--sync-delay": syncDelayPct } as React.CSSProperties : undefined}
          >
            {token}
          </motion.span>
        );
      })}
    </>
  );
}

function parseNodes(content: string) {
  const lines = content.split(/\n/);
  const nodes: { type: "h1" | "h2" | "h3" | "p"; text: string }[] = [];
  let para: string[] = [];

  const flushPara = () => {
    if (para.length) {
      nodes.push({ type: "p", text: para.join("\n").trim() });
      para = [];
    }
  };

  for (const line of lines) {
    const h3 = line.match(/^###\s+(.+)$/);
    const h2 = line.match(/^##\s+(.+)$/);
    const h1 = line.match(/^#\s+(.+)$/);
    if (h3) { flushPara(); nodes.push({ type: "h3", text: h3[1] }); }
    else if (h2) { flushPara(); nodes.push({ type: "h2", text: h2[1] }); }
    else if (h1) { flushPara(); nodes.push({ type: "h1", text: h1[1] }); }
    else { para.push(line); }
  }
  flushPara();
  return nodes;
}

function SegmentContent({ content, isFirstInAct, animate, isNarrating, isNarrationPaused }: { content: string; isFirstInAct: boolean; animate: boolean; isNarrating: boolean; isNarrationPaused?: boolean }) {
  const nodes = parseNodes(content);

  // Calculate total words for audio sync timing
  const totalWordsInSegment = content.split(/\s+/).filter(w => w.length > 0).length;
  let cumulativeWords = 0;

  // We wrap the whole content in a motion.div to orchestrate staggerChildren
  const Wrapper = animate ? motion.div : "div";
  const wrapperProps = animate ? {
    variants: containerVariants,
    initial: "hidden",
    whileInView: "visible",
    viewport: { once: true, amount: 0.2 }
  } : {};

  return (
    <Wrapper {...wrapperProps}>
      {nodes.map((node, i) => {
        const wordCount = node.text.split(/\s+/).filter(w => w.length > 0).length;
        const currentCumulative = cumulativeWords;
        cumulativeWords += wordCount;

        const headingClasses: Record<string, string> = {
          h1: "font-[family-name:var(--font-display)] text-[var(--gold)] text-2xl md:text-3xl tracking-wider uppercase mt-10 mb-4 first:mt-0",
          h2: "font-[family-name:var(--font-display)] text-[var(--gold)] text-xl md:text-2xl tracking-wider uppercase mt-10 mb-4 first:mt-0",
          h3: "font-[family-name:var(--font-display)] text-[var(--gold)] text-lg md:text-xl tracking-wider uppercase mt-8 mb-3 first:mt-0",
        };

        const renderText = () => {
          if (animate) {
             return <RevealWords
                text={node.text}
                isNarrating={isNarrating}
                isNarrationPaused={isNarrationPaused}
                totalWordsInSegment={totalWordsInSegment}
                cumulativeWordOffset={currentCumulative}
              />;
          }
          if (isNarrating || isNarrationPaused) {
            return <RevealWords
              text={node.text}
              isNarrating={isNarrating}
              isNarrationPaused={isNarrationPaused}
              totalWordsInSegment={totalWordsInSegment}
              cumulativeWordOffset={currentCumulative}
            />;
          }
          return node.text;
        };

        if (node.type !== "p") {
          const Tag = node.type as "h1" | "h2" | "h3";
          return (
            <Tag key={i} className={headingClasses[node.type]}>
              {renderText()}
            </Tag>
          );
        }

        const dropCap = isFirstInAct && i === 0;
        const cls = dropCap
          ? "first-letter:text-[3.5rem] first-letter:font-[family-name:var(--font-display)] first-letter:text-[var(--gold)] first-letter:float-left first-letter:mr-3 first-letter:mt-1 first-letter:leading-[0.8]"
          : "";

        return (
          <p key={i} className={cls}>
            {renderText()}
          </p>
        );
      })}
    </Wrapper>
  );
}

interface Props {
  segment: SegmentType;
  index: number;
  isFirstInAct?: boolean;
  isNarrating?: boolean;
  isNarrationPaused?: boolean;
  audioDuration?: number;
  spotlightActive?: boolean;
  isNew?: boolean;
}

const revealTransition = { duration: 0.65, ease: [0.22, 1, 0.36, 1] as const };


function CinematicImage({ src, alt, isHero, isNew }: { src: string; alt: string; isHero: boolean; isNew: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [isHero ? -50 : -30, isHero ? 50 : 30]);
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [1.08, 1, 1.08]);

  return (
    <div ref={ref} className="overflow-hidden relative">
      <motion.img
        src={src}
        alt={alt}
        className="w-full h-auto block will-change-transform"
        style={{ y, scale }}
        initial={isNew ? { filter: "sepia(100%) brightness(0.8)" } : false}
        whileInView={isNew ? { filter: "sepia(0%) brightness(1)" } : undefined}
        viewport={{ once: true, amount: 0.15 }}
        transition={{ duration: 2.5, ease: "easeOut" }}
      />
      {/* Warm vignette overlay for hero images */}
      {isHero && (
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: "radial-gradient(ellipse at center, transparent 50%, rgba(59,35,20,0.25) 100%)",
          }}
        />
      )}
      {/* Golden shimmer that sweeps and fades out on reveal */}
      {isNew && (
        <motion.div
          className="absolute inset-0 pointer-events-none"
          initial={{ opacity: 0.8, backgroundPosition: "200% 0%" }}
          whileInView={{ opacity: 0, backgroundPosition: "-100% 0%" }}
          viewport={{ once: true, amount: 0.15 }}
          transition={{ 
            opacity: { duration: 3, ease: "easeOut" },
            backgroundPosition: { duration: 2.5, ease: "easeOut" }
          }}
          style={{
            background: "linear-gradient(110deg, transparent 20%, rgba(212,168,67,0.3) 40%, rgba(212,168,67,0.6) 50%, rgba(212,168,67,0.3) 60%, transparent 80%)",
            backgroundSize: "200% 100%",
          }}
        />
      )}
    </div>
  );
}

export default function NarrativeSegment({
  segment,
  index,
  isFirstInAct = false,
  isNarrating = false,
  isNarrationPaused = false,
  audioDuration,
  spotlightActive = false,
  isNew = false,
}: Props) {
  const isDimmed = spotlightActive && !isNarrating;
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, amount: 0.12 });
  const [hasRevealed, setHasRevealed] = useState(!isNew);

  useEffect(() => {
    if (isInView && !hasRevealed) setHasRevealed(true);
  }, [isInView, hasRevealed]);

  if (segment.type === "text" && segment.content) {
    const wordCount = segment.content.split(/\s+/).length;
    const estimatedDuration = Math.max(8, wordCount / 2.5);
    const narrateDuration = audioDuration && (isNarrating || isNarrationPaused) ? audioDuration : estimatedDuration;

    const segmentClasses = [
      "relative mb-8 group",
      isNarrating ? "narrating-segment" : "",
      isNarrationPaused ? "narrating-segment narrating-paused" : "",
    ].filter(Boolean).join(" ");

    return (
      <motion.div
        ref={containerRef}
        initial={isNew ? { opacity: 0, y: 28 } : false}
        animate={hasRevealed ? {
          opacity: isDimmed ? 0.3 : 1,
          y: 0,
          filter: isDimmed ? "blur(0.5px)" : "blur(0px)",
        } : undefined}
        transition={revealTransition}
        className={segmentClasses}
        style={{
          "--narrate-duration": `${narrateDuration}s`,
        } as React.CSSProperties}
        data-sequence={segment.sequence}
      >
        <TrustBadge level={segment.trust_level} />
        <div className="font-[family-name:var(--font-body)] text-[var(--umber)] leading-[1.85] text-[1.1rem] md:text-[1.15rem]">
          <SegmentContent
            content={segment.content}
            isFirstInAct={isFirstInAct}
            animate={isNew}
            isNarrating={isNarrating}
            isNarrationPaused={isNarrationPaused}
          />
        </div>
      </motion.div>
    );
  }

  if (segment.type === "image" && segment.media_data) {
    const isHero = segment.is_hero ?? false;
    const imgSrc = `data:${segment.media_type || "image/png"};base64,${segment.media_data}`;

    return (
      <motion.figure
        ref={containerRef}
        initial={isNew ? { opacity: 0, scale: 0.94, filter: "blur(12px)" } : false}
        animate={hasRevealed ? {
          opacity: isDimmed ? 0.4 : 1,
          scale: 1,
          filter: "blur(0px)",
        } : undefined}
        transition={{
          duration: isNew ? 1.4 : 0.85,
          ease: [0.22, 1, 0.36, 1],
        }}
        className={`my-10 ${isHero ? "-mx-8 md:-mx-16 lg:-mx-24" : "mx-auto"}`}
        style={{ maxWidth: isHero ? "none" : "85%" }}
        data-sequence={segment.sequence}
      >
        <div
          className={`overflow-hidden ${
            isHero
              ? "shadow-[0_8px_60px_rgba(59,35,20,0.3)]"
              : "border-2 border-[var(--ochre)]/30 shadow-[0_4px_24px_rgba(59,35,20,0.15)]"
          }`}
        >
          <CinematicImage
            src={imgSrc}
            alt={segment.content || "Heritage narrative illustration"}
            isHero={isHero}
            isNew={isNew}
          />
        </div>
        {segment.content && (
          <motion.figcaption
            className="mt-3 text-center font-[family-name:var(--font-body)] text-sm italic text-[var(--muted)]"
            initial={isNew ? { opacity: 0, y: 8 } : undefined}
            animate={isNew && isInView ? { opacity: 1, y: 0 } : undefined}
            transition={{ duration: 0.6, delay: 1.0 }}
          >
            {segment.content}
          </motion.figcaption>
        )}
      </motion.figure>
    );
  }

  return null;
}
