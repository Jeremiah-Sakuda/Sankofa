"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { motion } from "motion/react";

interface AudioPlayerProps {
  audioData?: string;
  mediaType?: string;
  autoPlay?: boolean;
  onPlayStateChange?: (playing: boolean) => void;
}

export default function AudioPlayer({
  audioData,
  mediaType = "audio/wav",
  autoPlay = false,
  onPlayStateChange,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!audioData) return;

    const audio = new Audio(`data:${mediaType};base64,${audioData}`);
    audioRef.current = audio;

    audio.addEventListener("timeupdate", () => {
      if (audio.duration) {
        setProgress(audio.currentTime / audio.duration);
      }
    });

    audio.addEventListener("ended", () => {
      setIsPlaying(false);
      setProgress(0);
      onPlayStateChange?.(false);
    });

    if (autoPlay) {
      audio.play().catch(() => {});
      setIsPlaying(true);
      onPlayStateChange?.(true);
    }

    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", () => {});
      audio.removeEventListener("ended", () => {});
    };
  }, [audioData, mediaType, autoPlay, onPlayStateChange]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
      onPlayStateChange?.(false);
    } else {
      audio.play().catch(() => {});
      setIsPlaying(true);
      onPlayStateChange?.(true);
    }
  }, [isPlaying, onPlayStateChange]);

  if (!audioData) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="inline-flex items-center gap-3 mt-2 mb-1"
    >
      <button
        onClick={togglePlay}
        className="relative w-8 h-8 rounded-full border border-[var(--gold)]/60 flex items-center justify-center transition-all duration-300 hover:border-[var(--gold)] hover:shadow-[0_0_12px_rgba(212,168,67,0.2)] cursor-pointer group"
        aria-label={isPlaying ? "Pause narration" : "Play narration"}
      >
        {isPlaying ? (
          <svg width="10" height="10" viewBox="0 0 10 10" className="text-[var(--gold)]">
            <rect x="1" y="1" width="3" height="8" fill="currentColor" />
            <rect x="6" y="1" width="3" height="8" fill="currentColor" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 10 10" className="text-[var(--gold)] ml-0.5">
            <polygon points="1,0 10,5 1,10" fill="currentColor" />
          </svg>
        )}

        {/* Progress ring */}
        {isPlaying && (
          <svg
            className="absolute inset-0 w-full h-full -rotate-90"
            viewBox="0 0 32 32"
          >
            <circle
              cx="16"
              cy="16"
              r="14"
              fill="none"
              stroke="var(--gold)"
              strokeWidth="1.5"
              strokeDasharray={`${progress * 88} 88`}
              opacity="0.6"
            />
          </svg>
        )}
      </button>

      {/* Waveform visualization */}
      {isPlaying && (
        <div className="flex items-center gap-[2px] h-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <motion.div
              key={i}
              className="w-[2px] bg-[var(--gold)] rounded-full"
              animate={{
                height: [4, 8 + Math.random() * 8, 4],
              }}
              transition={{
                duration: 0.4 + Math.random() * 0.4,
                repeat: Infinity,
                delay: i * 0.05,
              }}
              style={{ opacity: 0.5 + Math.random() * 0.3 }}
            />
          ))}
        </div>
      )}

      {!isPlaying && (
        <span className="text-[var(--muted)] text-xs font-[family-name:var(--font-body)] opacity-60 group-hover:opacity-100 transition-opacity">
          Listen
        </span>
      )}
    </motion.div>
  );
}
