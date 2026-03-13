"use client";

import { useRef, useState, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "motion/react";

export interface AudioTrack {
  id: string;
  label: string;
  audioData: string;
  mediaType: string;
  segmentSequence: number;
}

interface NarrationBarProps {
  tracks: AudioTrack[];
  onTrackChange?: (track: AudioTrack | null) => void;
  onPlayStateChange?: (playing: boolean) => void;
  autoPlay?: boolean;
}

function useBlobUrl(audioData: string | undefined, mediaType: string): string | null {
  const [src, setSrc] = useState<string | null>(null);
  const revokeRef = useRef<string | null>(null);

  useEffect(() => {
    if (!audioData) {
      setSrc(null);
      return;
    }
    const mime = mediaType?.startsWith("audio/") ? mediaType : "audio/wav";
    const trimmed = audioData.replace(/\s/g, "");
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
    };
  }, [audioData, mediaType]);

  return src;
}

export default function NarrationBar({ tracks, onTrackChange, onPlayStateChange, autoPlay = true }: NarrationBarProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loadError, setLoadError] = useState(false);
  const [hasUserPaused, setHasUserPaused] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const autoPlayedRef = useRef<Set<string>>(new Set());

  const currentTrack = tracks[currentIndex] ?? null;
  const src = useBlobUrl(currentTrack?.audioData, currentTrack?.mediaType ?? "audio/wav");

  const waveformBars = useMemo(
    () =>
      Array.from({ length: 24 }, (_, i) => ({
        height: [3, 6 + (i * 7) % 14, 3],
        duration: 0.35 + (i % 6) * 0.06,
        delay: i * 0.035,
        opacity: 0.4 + (i % 5) * 0.1,
      })),
    []
  );

  useEffect(() => {
    onTrackChange?.(currentTrack);
  }, [currentTrack, onTrackChange]);

  useEffect(() => {
    onPlayStateChange?.(isPlaying);
  }, [isPlaying, onPlayStateChange]);

  // Auto-play first track when it arrives, or newly arriving tracks if user hasn't paused
  useEffect(() => {
    if (!tracks.length || !autoPlay || hasUserPaused) return;
    if (currentTrack && !autoPlayedRef.current.has(currentTrack.id)) {
      autoPlayedRef.current.add(currentTrack.id);
    }
  }, [tracks.length, autoPlay, hasUserPaused, currentTrack]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !src) return;
    setLoadError(false);

    const onTimeUpdate = () => {
      if (audio.duration && Number.isFinite(audio.duration)) {
        setProgress(audio.currentTime / audio.duration);
        setDuration(audio.duration);
      }
    };
    const onEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      // Auto-advance to next track
      if (currentIndex < tracks.length - 1) {
        setCurrentIndex((i) => i + 1);
        setHasUserPaused(false);
      }
    };
    const onError = () => setLoadError(true);
    const onCanPlay = () => {
      setLoadError(false);
      setDuration(audio.duration);
      if (autoPlay && !hasUserPaused) {
        audio.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("ended", onEnded);
    audio.addEventListener("error", onError);
    audio.addEventListener("canplay", onCanPlay);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("error", onError);
      audio.removeEventListener("canplay", onCanPlay);
    };
  }, [src, autoPlay, hasUserPaused, currentIndex, tracks.length]);

  // When src changes (track change), reset state
  useEffect(() => {
    setProgress(0);
    setDuration(0);
    setLoadError(false);
  }, [src]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || !src) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
      setHasUserPaused(true);
    } else {
      audio.play().then(() => {
        setIsPlaying(true);
        setHasUserPaused(false);
      }).catch(() => setLoadError(true));
    }
  }, [isPlaying, src]);

  const skipTo = useCallback((index: number) => {
    if (index < 0 || index >= tracks.length) return;
    const audio = audioRef.current;
    if (audio) audio.pause();
    setIsPlaying(false);
    setProgress(0);
    setCurrentIndex(index);
    setHasUserPaused(false);
  }, [tracks.length]);

  const seekTo = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !src) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if (Number.isFinite(audio.duration)) {
      audio.currentTime = pct * audio.duration;
      setProgress(pct);
    }
  }, [src]);

  const formatTime = (s: number) => {
    if (!Number.isFinite(s) || s < 0) return "0:00";
    const min = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${min}:${sec.toString().padStart(2, "0")}`;
  };

  if (!tracks.length) return null;

  return (
    <motion.div
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 100, opacity: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="fixed bottom-0 inset-x-0 z-50"
    >
      {/* Frost backdrop */}
      <div className="absolute inset-0 bg-[var(--night)]/90 backdrop-blur-xl border-t border-[var(--gold)]/15" />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6">
        {/* Track list (expandable) */}
        <AnimatePresence>
          {isExpanded && tracks.length > 1 && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div className="pt-4 pb-2 max-h-48 overflow-y-auto scrollbar-thin">
                {tracks.map((track, i) => (
                  <button
                    key={track.id}
                    type="button"
                    onClick={() => { skipTo(i); setIsExpanded(false); }}
                    className={`w-full text-left px-3 py-2 rounded transition-colors text-sm font-[family-name:var(--font-body)] ${
                      i === currentIndex
                        ? "text-[var(--gold)] bg-[var(--gold)]/10"
                        : "text-[var(--ivory)]/60 hover:text-[var(--ivory)] hover:bg-[var(--ivory)]/5"
                    }`}
                  >
                    <span className="opacity-40 mr-2 text-xs">{i + 1}.</span>
                    {track.label}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main bar */}
        <div className="flex items-center gap-3 py-3 sm:py-4">
          {/* Hidden audio element */}
          {src && <audio ref={audioRef} src={src} preload="auto" className="hidden" />}

          {/* Previous */}
          <button
            type="button"
            onClick={() => skipTo(currentIndex - 1)}
            disabled={currentIndex === 0}
            className="shrink-0 text-[var(--ivory)]/40 hover:text-[var(--gold)] disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous track"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M3 2h2v12H3V2zm3 6l8-6v12L6 8z" />
            </svg>
          </button>

          {/* Play / Pause */}
          <button
            type="button"
            onClick={togglePlay}
            disabled={!src || loadError}
            className="shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-full border border-[var(--gold)]/50 flex items-center justify-center transition-all hover:border-[var(--gold)] hover:bg-[var(--gold)]/10 hover:shadow-[0_0_20px_rgba(212,168,67,0.15)] disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label={isPlaying ? "Pause narration" : "Play narration"}
          >
            {isPlaying ? (
              <svg width="14" height="14" viewBox="0 0 14 14" className="text-[var(--gold)]">
                <rect x="2" y="1" width="3.5" height="12" rx="0.5" fill="currentColor" />
                <rect x="8.5" y="1" width="3.5" height="12" rx="0.5" fill="currentColor" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 14 14" className="text-[var(--gold)] ml-0.5">
                <polygon points="2,0 14,7 2,14" fill="currentColor" />
              </svg>
            )}
          </button>

          {/* Next */}
          <button
            type="button"
            onClick={() => skipTo(currentIndex + 1)}
            disabled={currentIndex >= tracks.length - 1}
            className="shrink-0 text-[var(--ivory)]/40 hover:text-[var(--gold)] disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
            aria-label="Next track"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11 2h2v12h-2V2zM2 2l8 6-8 6V2z" />
            </svg>
          </button>

          {/* Center: progress + label */}
          <div className="flex-1 min-w-0 mx-2">
            {/* Track label */}
            <div className="flex items-center gap-2 mb-1.5">
              <button
                type="button"
                onClick={() => tracks.length > 1 && setIsExpanded(!isExpanded)}
                className="truncate text-[var(--ivory)] text-xs sm:text-sm font-[family-name:var(--font-body)] hover:text-[var(--gold)] transition-colors text-left"
              >
                {currentTrack?.label ?? "No audio loaded"}
              </button>
              {tracks.length > 1 && (
                <span className="shrink-0 text-[var(--muted)] text-[10px] font-[family-name:var(--font-body)]">
                  {currentIndex + 1}/{tracks.length}
                </span>
              )}
            </div>

            {/* Seekable progress bar */}
            <div
              className="group/seek relative h-1 bg-[var(--ivory)]/10 rounded-full cursor-pointer"
              onClick={seekTo}
              role="slider"
              aria-label="Seek"
              aria-valuenow={Math.round(progress * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="absolute inset-y-0 left-0 bg-[var(--gold)] rounded-full transition-[width] duration-100"
                style={{ width: `${progress * 100}%` }}
              />
              <div
                className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-[var(--gold)] opacity-0 group-hover/seek:opacity-100 transition-opacity shadow-[0_0_6px_rgba(212,168,67,0.4)]"
                style={{ left: `calc(${progress * 100}% - 5px)` }}
              />
            </div>

            {/* Time */}
            <div className="flex justify-between mt-1">
              <span className="text-[var(--muted)] text-[10px] font-[family-name:var(--font-body)] tabular-nums">
                {formatTime(progress * duration)}
              </span>
              <span className="text-[var(--muted)] text-[10px] font-[family-name:var(--font-body)] tabular-nums">
                {formatTime(duration)}
              </span>
            </div>
          </div>

          {/* Waveform */}
          <div className="hidden sm:flex items-center gap-[2px] h-5 shrink-0">
            {waveformBars.map((bar, i) => (
              <motion.div
                key={i}
                className="w-[2px] rounded-full"
                style={{
                  backgroundColor: isPlaying ? "var(--gold)" : "var(--muted)",
                  opacity: isPlaying ? bar.opacity : 0.2,
                }}
                animate={isPlaying ? { height: bar.height } : { height: 3 }}
                transition={
                  isPlaying
                    ? { duration: bar.duration, repeat: Infinity, delay: bar.delay }
                    : { duration: 0.3 }
                }
              />
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
