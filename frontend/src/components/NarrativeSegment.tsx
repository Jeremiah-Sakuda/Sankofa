"use client";

import { useRef, useState, useEffect } from "react";
import { motion, useScroll, useTransform, useInView } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import TrustBadge from "./TrustBadge";

const WORD_STAGGER = 0.018;
const LINE_STAGGER = 0.12;

function RevealWords({ text, baseDelay = 0 }: { text: string; baseDelay?: number }) {
  const words = text.split(/(\s+)/);
  let wordIdx = 0;
  return (
    <>
      {words.map((token, i) => {
        if (/^\s+$/.test(token)) return token;
        const delay = baseDelay + wordIdx * WORD_STAGGER;
        wordIdx++;
        return (
          <motion.span
            key={i}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay, ease: [0.22, 1, 0.36, 1] }}
            className="inline"
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

function SegmentContent({ content, isFirstInAct, animate }: { content: string; isFirstInAct: boolean; animate: boolean }) {
  const nodes = parseNodes(content);

  let cumulativeWords = 0;

  return (
    <>
      {nodes.map((node, i) => {
        const wordCount = node.text.split(/\s+/).length;
        const baseDelay = i * LINE_STAGGER;

        const headingClasses: Record<string, string> = {
          h1: "font-[family-name:var(--font-display)] text-[var(--gold)] text-2xl md:text-3xl tracking-wider uppercase mt-10 mb-4 first:mt-0",
          h2: "font-[family-name:var(--font-display)] text-[var(--gold)] text-xl md:text-2xl tracking-wider uppercase mt-10 mb-4 first:mt-0",
          h3: "font-[family-name:var(--font-display)] text-[var(--gold)] text-lg md:text-xl tracking-wider uppercase mt-8 mb-3 first:mt-0",
        };

        if (node.type !== "p") {
          const Tag = node.type as "h1" | "h2" | "h3";
          const el = animate ? (
            <Tag key={i} className={headingClasses[node.type]}>
              <RevealWords text={node.text} baseDelay={baseDelay} />
            </Tag>
          ) : (
            <Tag key={i} className={headingClasses[node.type]}>{node.text}</Tag>
          );
          cumulativeWords += wordCount;
          return el;
        }

        const delay = cumulativeWords * WORD_STAGGER + i * LINE_STAGGER;
        cumulativeWords += wordCount;

        const dropCap = isFirstInAct && i === 0;
        const cls = dropCap
          ? "first-letter:text-[3.5rem] first-letter:font-[family-name:var(--font-display)] first-letter:text-[var(--gold)] first-letter:float-left first-letter:mr-3 first-letter:mt-1 first-letter:leading-[0.8]"
          : "";

        if (!animate) {
          return <p key={i} className={cls}>{node.text}</p>;
        }

        return (
          <motion.p
            key={i}
            className={cls}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: baseDelay }}
          >
            <RevealWords text={node.text} baseDelay={delay} />
          </motion.p>
        );
      })}
    </>
  );
}

interface Props {
  segment: SegmentType;
  index: number;
  isFirstInAct?: boolean;
  isNarrating?: boolean;
  spotlightActive?: boolean;
  isNew?: boolean;
}

const revealTransition = { duration: 0.65, ease: [0.22, 1, 0.36, 1] };
const revealViewport = { once: true, amount: 0.12, margin: "-40px 0px 0px 0px" };

function ParallaxImage({ src, alt, isHero }: { src: string; alt: string; isHero: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  // Shift the image 40px over the scroll range of the container
  const y = useTransform(scrollYProgress, [0, 1], [isHero ? -50 : -30, isHero ? 50 : 30]);
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [1.08, 1, 1.08]);

  return (
    <div ref={ref} className="overflow-hidden">
      <motion.img
        src={src}
        alt={alt}
        className="w-full h-auto block will-change-transform"
        style={{ y, scale }}
      />
    </div>
  );
}

export default function NarrativeSegment({
  segment,
  index,
  isFirstInAct = false,
  isNarrating = false,
  spotlightActive = false,
  isNew = false,
}: Props) {
  const isDimmed = spotlightActive && !isNarrating;
  const containerRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(containerRef, { once: true, amount: 0.12 });
  const [hasRevealed, setHasRevealed] = useState(false);

  useEffect(() => {
    if (isInView && isNew && !hasRevealed) setHasRevealed(true);
  }, [isInView, isNew, hasRevealed]);

  if (segment.type === "text" && segment.content) {
    return (
      <motion.div
        ref={containerRef}
        initial={{ opacity: 0, y: 28 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={revealViewport}
        transition={{ ...revealTransition, delay: 0.05 }}
        className={`relative mb-8 group transition-all duration-700 ${
          isNarrating ? "narrating-segment" : ""
        }`}
        style={{
          opacity: isDimmed ? 0.3 : undefined,
          filter: isDimmed ? "blur(0.5px)" : undefined,
          transition: "opacity 0.7s ease, filter 0.7s ease",
        }}
        data-sequence={segment.sequence}
      >
        <TrustBadge level={segment.trust_level} />
        <div className="font-[family-name:var(--font-body)] text-[var(--umber)] leading-[1.85] text-[1.1rem] md:text-[1.15rem]">
          <SegmentContent
            content={segment.content}
            isFirstInAct={isFirstInAct}
            animate={isNew && isInView}
          />
        </div>
      </motion.div>
    );
  }

  if (segment.type === "image" && segment.media_data) {
    const isHero = segment.is_hero;
    const imgSrc = `data:${segment.media_type || "image/png"};base64,${segment.media_data}`;

    return (
      <motion.figure
        initial={{ opacity: 0, scale: 0.96, filter: "blur(8px)" }}
        whileInView={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
        viewport={revealViewport}
        transition={{ ...revealTransition, duration: 0.85 }}
        className={`my-10 ${isHero ? "-mx-8 md:-mx-16 lg:-mx-24" : "mx-auto"}`}
        style={{
          maxWidth: isHero ? "none" : "85%",
          opacity: isDimmed ? 0.4 : undefined,
          transition: "opacity 0.7s ease",
        }}
        data-sequence={segment.sequence}
      >
        <div
          className={`overflow-hidden ${
            isHero
              ? ""
              : "border-2 border-[var(--ochre)]/30 shadow-[0_4px_24px_rgba(59,35,20,0.15)]"
          }`}
        >
          <ParallaxImage
            src={imgSrc}
            alt={segment.content || "Heritage narrative illustration"}
            isHero={isHero}
          />
        </div>
        {segment.content && (
          <figcaption className="mt-3 text-center font-[family-name:var(--font-body)] text-sm italic text-[var(--muted)]">
            {segment.content}
          </figcaption>
        )}
      </motion.figure>
    );
  }

  return null;
}
