"use client";

import { motion } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import TrustBadge from "./TrustBadge";
import AudioPlayer from "./AudioPlayer";

/** Renders segment content with simple markdown-style headings (### ACT 1 → styled h3). */
function SegmentContent({ content, isFirstInAct }: { content: string; isFirstInAct: boolean }) {
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
    if (h3) {
      flushPara();
      nodes.push({ type: "h3", text: h3[1] });
    } else if (h2) {
      flushPara();
      nodes.push({ type: "h2", text: h2[1] });
    } else if (h1) {
      flushPara();
      nodes.push({ type: "h1", text: h1[1] });
    } else {
      para.push(line);
    }
  }
  flushPara();

  return (
    <>
      {nodes.map((node, i) => {
        if (node.type === "h3") {
          return (
            <h3
              key={i}
              className="font-[family-name:var(--font-display)] text-[var(--gold)] text-lg md:text-xl tracking-wider uppercase mt-8 mb-3 first:mt-0"
            >
              {node.text}
            </h3>
          );
        }
        if (node.type === "h2") {
          return (
            <h2
              key={i}
              className="font-[family-name:var(--font-display)] text-[var(--gold)] text-xl md:text-2xl tracking-wider uppercase mt-10 mb-4 first:mt-0"
            >
              {node.text}
            </h2>
          );
        }
        if (node.type === "h1") {
          return (
            <h1
              key={i}
              className="font-[family-name:var(--font-display)] text-[var(--gold)] text-2xl md:text-3xl tracking-wider uppercase mt-10 mb-4 first:mt-0"
            >
              {node.text}
            </h1>
          );
        }
        return (
          <p
            key={i}
            className={
              isFirstInAct && i === 0
                ? "first-letter:text-[3.5rem] first-letter:font-[family-name:var(--font-display)] first-letter:text-[var(--gold)] first-letter:float-left first-letter:mr-3 first-letter:mt-1 first-letter:leading-[0.8]"
                : ""
            }
          >
            {node.text}
          </p>
        );
      })}
    </>
  );
}

interface Props {
  segment: SegmentType;
  index: number;
  isFirstInAct?: boolean;
}

export default function NarrativeSegment({
  segment,
  index,
  isFirstInAct = false,
}: Props) {
  if (segment.type === "text" && segment.content) {
    const hasAudio = segment.media_data && segment.media_type?.startsWith("audio");

    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut", delay: 0.1 }}
        className="relative mb-8 group"
      >
        <TrustBadge level={segment.trust_level} />
        <div className="font-[family-name:var(--font-body)] text-[var(--umber)] leading-[1.85] text-[1.1rem] md:text-[1.15rem]">
          <SegmentContent content={segment.content} isFirstInAct={isFirstInAct} />
        </div>
        {hasAudio && (
          <AudioPlayer
            audioData={segment.media_data}
            mediaType={segment.media_type}
          />
        )}
      </motion.div>
    );
  }

  if (segment.type === "image" && segment.media_data) {
    const isHero = segment.is_hero;

    return (
      <motion.figure
        initial={{ opacity: 0, scale: 0.98, filter: "blur(6px)" }}
        animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
        transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
        className={`my-10 ${isHero ? "-mx-8 md:-mx-16 lg:-mx-24" : "mx-auto"}`}
        style={{ maxWidth: isHero ? "none" : "85%" }}
      >
        <div
          className={`overflow-hidden ${
            isHero
              ? ""
              : "border-2 border-[var(--ochre)]/30 shadow-[0_4px_24px_rgba(59,35,20,0.15)]"
          }`}
        >
          <img
            src={`data:${segment.media_type || "image/png"};base64,${segment.media_data}`}
            alt={segment.content || "Heritage narrative illustration"}
            className="w-full h-auto block"
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

  if (segment.type === "audio" && segment.media_data) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="my-4"
      >
        <AudioPlayer audioData={segment.media_data} mediaType={segment.media_type} />
      </motion.div>
    );
  }

  return null;
}
