"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { NarrativeSegment as SegmentType } from "../lib/api";
import type { StreamProgressStep, ArcOutline } from "../hooks/useSSEStream";
import NarrativeSegment from "./NarrativeSegment";
import NarrationBar, { type AudioTrack } from "./NarrationBar";
import ScrollProgress from "./ScrollProgress";
import SankofaBird from "./SankofaBird";

const FOLLOW_UP_MAX_LENGTH = 500;

const ACT_LABELS: Record<number, { numeral: string; arcKey: keyof ArcOutline }> = {
  2: { numeral: "II", arcKey: "act2_people" },
  3: { numeral: "III", arcKey: "act3_thread" },
};

interface Props {
  segments: SegmentType[];
  isStreaming: boolean;
  isComplete: boolean;
  error: string | null;
  followUpError?: string | null;
  followUpThinking?: string | null;
  progressStep?: StreamProgressStep;
  familyName?: string;
  region?: string;
  era?: string;
  arcOutline?: ArcOutline | null;
  onFollowUp?: (question: string) => void;
  onTalkToGriot?: () => void;
  onRetry?: () => void;
}

function ActTransition({ actNumber, arcOutline }: { actNumber: number; arcOutline?: ArcOutline | null }) {
  const label = ACT_LABELS[actNumber];
  const actData = label && arcOutline ? arcOutline[label.arcKey] : null;
  const title = typeof actData === "object" && actData?.title ? actData.title : null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 1.0, ease: [0.22, 1, 0.36, 1] }}
      className="my-16 md:my-20 py-8 relative"
    >
      {/* Golden line expanding from center */}
      <motion.div
        className="h-px mx-auto bg-gradient-to-r from-transparent via-[var(--gold)]/50 to-transparent"
        initial={{ scaleX: 0 }}
        whileInView={{ scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
      />

      {/* Sankofa bird traveling along the line */}
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

      {/* Act numeral and title */}
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

      {/* Floating gold particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden>
        {Array.from({ length: 8 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 rounded-full bg-[var(--gold)]"
            style={{
              left: `${15 + (i * 10) % 70}%`,
              top: `${20 + (i * 13) % 60}%`,
            }}
            initial={{ opacity: 0, y: 10, x: 0 }}
            whileInView={{ 
              opacity: [0, 0.5, 0], 
              y: [10, -20, -35],
              x: [0, (i % 3 === 0 ? -15 : 15), (i % 2 === 0 ? 10 : -10)]
            }}
            viewport={{ once: true }}
            transition={{
              duration: 3 + (i % 3),
              delay: 0.2 + i * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}

function buildAudioTracks(segments: SegmentType[]): AudioTrack[] {
  const tracks: AudioTrack[] = [];

  let trackNum = 0;
  for (const seg of segments) {
    if (seg.type === "text" && seg.media_data && seg.media_type?.startsWith("audio")) {
      trackNum++;
      tracks.push({
        id: `text-${seg.sequence}`,
        label: `Narration ${trackNum}`,
        audioData: seg.media_data,
        mediaType: seg.media_type,
        segmentSequence: seg.sequence,
      });
    }
    if (seg.type === "audio" && seg.media_data) {
      trackNum++;
      tracks.push({
        id: `audio-${seg.sequence}`,
        label: `Narration ${trackNum}`,
        audioData: seg.media_data,
        mediaType: seg.media_type ?? "audio/wav",
        segmentSequence: seg.sequence,
      });
    }
  }

  return tracks;
}

export default function NarrativeStream({
  segments,
  isStreaming,
  isComplete,
  error,
  familyName,
  region,
  era,
  followUpError,
  followUpThinking,
  progressStep,
  arcOutline,
  onFollowUp,
  onTalkToGriot,
  onRetry,
}: Props) {
  const [followUpInput, setFollowUpInput] = useState("");
  const [followUpValidationError, setFollowUpValidationError] = useState<string | null>(null);
  const [activeSequence, setActiveSequence] = useState<number | null>(null);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [ambientMuted, setAmbientMuted] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const seenSequences = useRef<Set<number>>(new Set());
  const prevSegmentCountRef = useRef(0);

  const audioTracks = useMemo(() => buildAudioTracks(segments), [segments]);

  const totalActs = useMemo(() => {
    const acts = new Set(segments.map((s) => s.act).filter(Boolean));
    return Math.max(acts.size, 1);
  }, [segments]);

  const currentAct = useMemo(() => {
    const textSegs = segments.filter((s) => s.type === "text" && s.act);
    return textSegs.length > 0 ? (textSegs[textSegs.length - 1].act ?? 1) : 1;
  }, [segments]);

  const currentAmbientTrack = useMemo(() => {
    if (!arcOutline) return null;
    const actKey = currentAct === 1 ? "act1_setting" : currentAct === 2 ? "act2_people" : "act3_thread";
    // @ts-ignore
    return arcOutline[actKey]?.ambient_track || null;
  }, [arcOutline, currentAct]);

  const ambientAudioRef = useRef<HTMLAudioElement>(null);
  const ambientTargetVolume = 0.15;
  const fadeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Crossfade ambient audio when track changes
  useEffect(() => {
    const audio = ambientAudioRef.current;
    if (!audio) return;

    // Clear any running fade
    if (fadeTimerRef.current) {
      clearInterval(fadeTimerRef.current);
      fadeTimerRef.current = null;
    }

    if (!currentAmbientTrack) {
      // Fade out and pause
      fadeTimerRef.current = setInterval(() => {
        if (audio.volume > 0.01) {
          audio.volume = Math.max(0, audio.volume - 0.015);
        } else {
          audio.pause();
          audio.volume = 0;
          if (fadeTimerRef.current) clearInterval(fadeTimerRef.current);
          fadeTimerRef.current = null;
        }
      }, 50);
      return;
    }

    const newSrc = `/audio/${currentAmbientTrack}`;
    const needsSwitch = !audio.src.endsWith(newSrc);

    if (needsSwitch && audio.currentTime > 0) {
      // Fade out, switch, fade in
      fadeTimerRef.current = setInterval(() => {
        if (audio.volume > 0.01) {
          audio.volume = Math.max(0, audio.volume - 0.015);
        } else {
          if (fadeTimerRef.current) clearInterval(fadeTimerRef.current);
          fadeTimerRef.current = null;
          audio.src = newSrc;
          audio.volume = 0;
          audio.play().catch(() => {});
          // Fade in
          fadeTimerRef.current = setInterval(() => {
            const target = ambientMuted ? 0 : ambientTargetVolume;
            if (audio.volume < target - 0.01) {
              audio.volume = Math.min(target, audio.volume + 0.01);
            } else {
              audio.volume = target;
              if (fadeTimerRef.current) clearInterval(fadeTimerRef.current);
              fadeTimerRef.current = null;
            }
          }, 50);
        }
      }, 50);
    } else if (needsSwitch) {
      // First load — just set and play
      audio.src = newSrc;
      audio.volume = ambientMuted ? 0 : ambientTargetVolume;
      audio.play().catch(() => {});
    }

    return () => {
      if (fadeTimerRef.current) {
        clearInterval(fadeTimerRef.current);
        fadeTimerRef.current = null;
      }
    };
  }, [currentAmbientTrack]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle mute/unmute
  useEffect(() => {
    if (ambientAudioRef.current) {
      ambientAudioRef.current.volume = ambientMuted ? 0 : ambientTargetVolume;
    }
  }, [ambientMuted]);

  // Auto-scroll only during active streaming when the user is near the bottom
  useEffect(() => {
    const isNewSegment = segments.length > prevSegmentCountRef.current;
    prevSegmentCountRef.current = segments.length;

    if (!isStreaming || !isNewSegment || segments.length === 0) return;

    // Only auto-scroll if the user is near the bottom of the page
    const scrollBottom = window.innerHeight + window.scrollY;
    const docHeight = document.documentElement.scrollHeight;
    const isNearBottom = docHeight - scrollBottom < 400;

    if (isNearBottom) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [segments.length, isStreaming]);

  const isAudioPlayingRef = useRef(false);
  useEffect(() => { isAudioPlayingRef.current = isAudioPlaying; }, [isAudioPlaying]);

  const handleTrackChange = useCallback((track: AudioTrack | null) => {
    setActiveSequence(track?.segmentSequence ?? null);
    if (track && isAudioPlayingRef.current) {
      const el = document.querySelector(`[data-sequence="${track.segmentSequence}"]`);
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, []);

  const handlePlayStateChange = useCallback((playing: boolean) => {
    setIsAudioPlaying(playing);
  }, []);

  let lastAct = 0;

  const handleFollowUp = () => {
    const q = followUpInput.trim();
    if (!q || !onFollowUp) return;
    if (q.length > FOLLOW_UP_MAX_LENGTH) {
      setFollowUpValidationError(`Please keep your question to ${FOLLOW_UP_MAX_LENGTH} characters or fewer.`);
      return;
    }
    setFollowUpValidationError(null);
    onFollowUp(q);
    setFollowUpInput("");
  };

  const hasSpeechRecognition =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const toggleVoiceInput = useCallback(() => {
    if (!hasSpeechRecognition) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognitionAPI =
      (window as unknown as { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ??
      (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from(event.results)
        .map((r) => r[0].transcript)
        .join("");
      setFollowUpInput(transcript);
    };

    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [isListening, hasSpeechRecognition]);

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
      <ScrollProgress totalActs={totalActs} currentAct={currentAct} isComplete={isComplete} />
      {/* Header */}
      <header className="text-center mb-16">
        <div className="flex items-center justify-between mb-4">
          <Link
            href="/"
            className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
          >
            Begin new narrative
          </Link>
        </div>
        <h1 className="font-[family-name:var(--font-display)] text-2xl md:text-3xl tracking-[0.3em] text-[var(--gold)] uppercase">
          Sankofa
        </h1>
        <div className="mt-3 h-px w-24 mx-auto bg-[var(--gold)]/40" />
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
                <NarrativeSegment
                  segment={segment}
                  index={i}
                  isFirstInAct={isFirstInAct || false}
                  isNarrating={activeSequence === segment.sequence}
                  spotlightActive={isAudioPlaying && activeSequence !== null}
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
              {followUpThinking
                ? followUpThinking
                : progressStep === "generating_audio"
                  ? "Adding narration…"
                  : "The story continues…"}
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      {(isComplete || (!isStreaming && segments.length > 0)) && (
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
            {familyName != null && region != null && era != null
              ? `A narrative woven from: ${familyName}, ${region}, ${era}`
              : "A narrative woven from your heritage."}
          </motion.p>
          <p className="mt-2 text-center font-[family-name:var(--font-body)] text-xs text-[var(--muted)] opacity-60">
            Sankofa distinguishes historical record from narrative imagination.
            Look for the margin annotations.
          </p>

          {/* Follow-up input */}
          {onFollowUp && (
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
                Your story continues&hellip;
              </motion.p>

              {/* Talk to the Griot button */}
              {onTalkToGriot && (
                <motion.button
                  onClick={onTalkToGriot}
                  initial={{ opacity: 0, y: 8 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.5 }}
                  className="mb-8 px-6 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer flex items-center gap-3 mx-auto"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                    <line x1="12" x2="12" y1="19" y2="22" />
                  </svg>
                  Talk to the Griot
                </motion.button>
              )}
              <div className="flex items-center justify-center gap-3 max-w-lg mx-auto">
                <input
                  type="text"
                  value={followUpInput}
                  onChange={(e) => {
                    setFollowUpInput(e.target.value);
                    setFollowUpValidationError(null);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleFollowUp()}
                  placeholder={isListening ? "Listening…" : "Tell me about the music of that era…"}
                  maxLength={FOLLOW_UP_MAX_LENGTH}
                  className="flex-1 bg-transparent border-b-2 border-[var(--ochre)]/40 text-[var(--umber)] font-[family-name:var(--font-body)] text-base pb-2 transition-colors focus:border-[var(--gold)] caret-[var(--gold)]"
                />
                {hasSpeechRecognition && (
                  <button
                    onClick={toggleVoiceInput}
                    disabled={isStreaming}
                    className={`w-10 h-10 flex items-center justify-center border rounded-full transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                      isListening
                        ? "border-[var(--terracotta)] text-[var(--terracotta)] bg-[var(--terracotta)]/10 animate-gentle-pulse"
                        : "border-[var(--ochre)]/40 text-[var(--ochre)] hover:border-[var(--gold)] hover:text-[var(--gold)]"
                    }`}
                    title={isListening ? "Stop listening" : "Speak your question"}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                      <line x1="12" x2="12" y1="19" y2="22" />
                    </svg>
                  </button>
                )}
                <button
                  onClick={handleFollowUp}
                  disabled={isStreaming}
                  className="px-5 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Ask
                </button>
              </div>
              {(followUpError || followUpValidationError) && (
                <p className="mt-4 font-[family-name:var(--font-body)] text-sm text-[var(--terracotta)]" role="alert">
                  {followUpError ?? followUpValidationError}
                </p>
              )}
            </div>
          )}
        </motion.footer>
      )}

      {error && (
        <div className="mt-8 p-4 text-center font-[family-name:var(--font-body)] text-sm">
          <p className="text-[var(--terracotta)]">{error}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 px-4 py-2 border border-[var(--terracotta)] text-[var(--terracotta)] hover:bg-[var(--terracotta)] hover:text-[var(--ivory)] transition-all cursor-pointer"
            >
              Try again
            </button>
          )}
        </div>
      )}

      {/* Bottom padding so content doesn't hide behind the narration bar */}
      {audioTracks.length > 0 && <div className="h-28" />}

      {/* Persistent bottom narration bar */}
      <AnimatePresence>
        {audioTracks.length > 0 && (
          <NarrationBar
            tracks={audioTracks}
            onTrackChange={handleTrackChange}
            onPlayStateChange={handlePlayStateChange}
            autoPlay
          />
        )}
      </AnimatePresence>

      {/* Ambient background audio */}
      {currentAmbientTrack && (
        <audio
          ref={ambientAudioRef}
          src={`/audio/${currentAmbientTrack}`}
          loop
          autoPlay
        />
      )}

      {/* Ambient mute toggle */}
      {currentAmbientTrack && (
        <button
          onClick={() => setAmbientMuted((m) => !m)}
          className="fixed bottom-4 right-4 z-40 w-9 h-9 flex items-center justify-center rounded-full border border-[var(--ochre)]/30 bg-[var(--night)]/80 backdrop-blur text-[var(--gold)] hover:border-[var(--gold)] transition-all cursor-pointer"
          title={ambientMuted ? "Unmute ambient sound" : "Mute ambient sound"}
        >
          {ambientMuted ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 5 6 9H2v6h4l5 4V5Z" />
              <line x1="23" x2="17" y1="9" y2="15" />
              <line x1="17" x2="23" y1="9" y2="15" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 5 6 9H2v6h4l5 4V5Z" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            </svg>
          )}
        </button>
      )}
    </motion.div>
  );
}
