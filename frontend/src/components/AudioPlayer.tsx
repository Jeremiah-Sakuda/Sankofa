"use client";

import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import { motion } from "motion/react";

interface AudioPlayerProps {
  audioData?: string;
  mediaType?: string;
  autoPlay?: boolean;
  onPlayStateChange?: (playing: boolean) => void;
}

/** Build a playable blob URL from base64 audio. Trims whitespace for compatibility. */
function useAudioSrc(audioData: string | undefined, mediaType: string): string | null {
  const [src, setSrc] = useState<string | null>(null);
  const revokeRef = useRef<string | null>(null);

  useEffect(() => {
    if (!audioData) {
      setSrc(null);
      return;
    }
    const mime = mediaType?.startsWith("audio/") ? mediaType : "audio/wav";
    const trimmed = audioData.replace(/\s/g, "").trim();
    if (!trimmed) {
      setSrc(null);
      return;
    }
    try {
      const binary = atob(trimmed);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: mime });
      const url = URL.createObjectURL(blob);
      if (revokeRef.current) URL.revokeObjectURL(revokeRef.current);
      revokeRef.current = url;
      setSrc(url);
    } catch {
      setSrc(null);
    }
    return () => {
      if (revokeRef.current) {
        URL.revokeObjectURL(revokeRef.current);
        revokeRef.current = null;
      }
      setSrc(null);
    };
  }, [audioData, mediaType]);

  return src;
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
  const [loadError, setLoadError] = useState(false);
  const src = useAudioSrc(audioData, mediaType);

  // Deterministic waveform bar config (stable across renders for hydration)
  const waveformBars = useMemo(
    () =>
      Array.from({ length: 12 }, (_, i) => ({
        height: [4, 8 + (i * 7) % 13, 4],
        duration: 0.4 + (i % 5) * 0.08,
        delay: i * 0.05,
        opacity: 0.5 + (i % 4) * 0.08,
      })),
    []
  );

  useEffect(() => {
    if (!src || !audioRef.current) return;
    setLoadError(false);
  }, [src]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !src) return;

    const onTimeUpdate = () => {
      if (audio.duration && Number.isFinite(audio.duration)) setProgress(audio.currentTime / audio.duration);
    };
    const onEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      onPlayStateChange?.(false);
    };
    const onError = () => setLoadError(true);
    const onCanPlay = () => setLoadError(false);

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);
    audio.addEventListener("canplay", onCanPlay);

    if (autoPlay) {
      audio.play().catch(() => {});
      setIsPlaying(true);
      onPlayStateChange?.(true);
    }

    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
      audio.removeEventListener("canplay", onCanPlay);
    };
  }, [src, autoPlay, onPlayStateChange]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !src) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
      onPlayStateChange?.(false);
    } else {
      const p = audio.play();
      if (p && typeof p.then === "function") {
        p.then(() => {
          setIsPlaying(true);
          onPlayStateChange?.(true);
        }).catch(() => setLoadError(true));
      } else {
        setIsPlaying(true);
        onPlayStateChange?.(true);
      }
    }
  }, [isPlaying, onPlayStateChange, src]);

  if (!audioData) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="inline-flex items-center gap-3 mt-2 mb-1"
    >
      {src && (
        <audio ref={audioRef} src={src} preload="metadata" className="hidden" />
      )}
      <button
        type="button"
        onClick={togglePlay}
        disabled={!src || loadError}
        className="relative w-8 h-8 rounded-full border border-[var(--gold)]/60 flex items-center justify-center transition-all duration-300 hover:border-[var(--gold)] hover:shadow-[0_0_12px_rgba(212,168,67,0.2)] cursor-pointer group disabled:opacity-50 disabled:cursor-not-allowed"
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

      {/* Waveform visualization - deterministic for hydration safety */}
      {isPlaying && (
        <div className="flex items-center gap-[2px] h-4">
          {waveformBars.map((bar, i) => (
            <motion.div
              key={i}
              className="w-[2px] bg-[var(--gold)] rounded-full"
              animate={{ height: bar.height }}
              transition={{
                duration: bar.duration,
                repeat: Infinity,
                delay: bar.delay,
              }}
              style={{ opacity: bar.opacity }}
            />
          ))}
        </div>
      )}

      {!isPlaying && (
        <span className="text-[var(--muted)] text-xs font-[family-name:var(--font-body)] opacity-60 group-hover:opacity-100 transition-opacity">
          {loadError ? "Audio unavailable" : "Listen"}
        </span>
      )}
    </motion.div>
  );
}
