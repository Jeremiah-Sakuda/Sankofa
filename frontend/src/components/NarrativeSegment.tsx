"use client";

import { motion } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import TrustBadge from "./TrustBadge";
import AudioPlayer from "./AudioPlayer";

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
        <div
          className={`font-[family-name:var(--font-body)] text-[var(--umber)] leading-[1.85] text-[1.1rem] md:text-[1.15rem] ${
            isFirstInAct
              ? "first-letter:text-[3.5rem] first-letter:font-[family-name:var(--font-display)] first-letter:text-[var(--gold)] first-letter:float-left first-letter:mr-3 first-letter:mt-1 first-letter:leading-[0.8]"
              : ""
          }`}
        >
          {segment.content}
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
