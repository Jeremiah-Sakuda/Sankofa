"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import { GRIOT_BEATS } from "../lib/griotBeats";
import type { ArcOutline, StreamProgressStep } from "../hooks/useSSEStream";
import SankofaBird from "./SankofaBird";
import GoldParticles from "./GoldParticles";
import VolumePanel from "./VolumePanel";

/** Heritage fun facts shown during the waiting phase. */
const HERITAGE_FACTS = [
  "The Akan word \"Sankofa\" literally means \"go back and get it\" \u2014 wisdom is never left behind.",
  "West African griots are living libraries \u2014 some can recite genealogies spanning 800 years.",
  "The Djembe drum was originally carved from a single piece of lenke wood and goatskin.",
  "Timbuktu's Sankore University had the largest library in Africa by the 14th century, with over 700,000 manuscripts.",
  "The Kingdom of Ghana (not modern Ghana) flourished from the 6th to 13th century as the \"Land of Gold.\"",
  "Kente cloth patterns each carry specific meanings \u2014 \"Sika Futuro\" (gold dust) represents wealth and royalty.",
  "The Yoruba people have one of the world's highest rates of twin births \u2014 twins are considered sacred.",
  "Ancient Benin City had walls four times longer than the Great Wall of China before the British invasion of 1897.",
  "The Haitian Revolution (1791\u20131804) was the only successful large-scale slave revolt in history.",
  "Caribbean Junkanoo festivals preserve West African masquerade traditions brought across the Atlantic.",
  "The Adinkra symbol \"Gye Nyame\" \u2014 meaning \"except for God\" \u2014 represents the omnipotence of the divine.",
  "Mansa Musa of Mali gave away so much gold during his 1324 pilgrimage that he crashed the Egyptian economy.",
  "The Swahili coast traded with China, India, and Persia as early as the 1st century CE.",
  "Oral storytelling traditions across Africa use call-and-response to keep listeners engaged across generations.",
  "The baobab tree, called the \"Tree of Life,\" can store up to 32,000 gallons of water in its trunk.",
  "The Great Zimbabwe ruins were built without mortar \u2014 the stones fit together with remarkable precision.",
  "Anansi the spider, a West African trickster figure, traveled with enslaved people to become a Caribbean folk hero.",
  "Indigo dyeing in West Africa dates back over 1,000 years \u2014 the Tuareg are called \"Blue People\" for their dyed robes.",
  "The Ashanti Golden Stool is believed to house the spirit of the entire Ashanti nation.",
  "Trinidad's steelpan is the only acoustic musical instrument invented in the 20th century.",
];

const STUCK_TIMEOUT_MS = 360_000;

/* ── Background music timing constants ── */
const MUSIC_START_TIME = 3; // seconds into intro when music begins
const MUSIC_BEAT_DROP = 97; // seconds into intro when beat drop hits
const MUSIC_VOL_START = 0.03; // initial volume
const MUSIC_VOL_PEAK = 0.40; // volume at beat drop and beyond
const MUSIC_VOL_READY = 0.10; // volume when griot-ready plays

interface GriotIntroProps {
  isStoryReady: boolean;
  onComplete: () => void;
  error: string | null;
  onRetry: () => void;
  sessionInvalid: boolean;
  arcOutline: ArcOutline | null;
  thinkingMessage: string | null;
  progressStep: StreamProgressStep;
}

type IntroPhase = "playing" | "waiting" | "ready";

export default function GriotIntro({
  isStoryReady,
  onComplete,
  error,
  onRetry,
  sessionInvalid,
  arcOutline,
  thinkingMessage,
  progressStep,
}: GriotIntroProps) {
  const [phase, setPhase] = useState<IntroPhase>("playing");
  const [activeBeatIndex, setActiveBeatIndex] = useState(-1);
  const [prevBeatIndex, setPrevBeatIndex] = useState(-1);
  const introAudioRef = useRef<HTMLAudioElement | null>(null);
  const readyAudioRef = useRef<HTMLAudioElement | null>(null);
  const ambientAudioRef = useRef<HTMLAudioElement | null>(null);
  const [funFactIndex, setFunFactIndex] = useState(() => Math.floor(Math.random() * HERITAGE_FACTS.length));
  const [showStuckMessage, setShowStuckMessage] = useState(false);
  const stuckTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [stepElapsed, setStepElapsed] = useState(0);
  const stepStartRef = useRef<number | null>(null);
  const readyAudioPlayed = useRef(false);
  const ambientFadeRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const musicAudioRef = useRef<HTMLAudioElement | null>(null);
  const musicFadeRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const musicStartedRef = useRef(false);
  const [voiceVolume, setVoiceVolume] = useState(1.0);
  const [musicVolume, setMusicVolume] = useState(1.0);
  const [ambientVolume, setAmbientVolume] = useState(1.0);

  /** Stop all audio cleanly. */
  const stopAllAudio = useCallback(() => {
    introAudioRef.current?.pause();
    readyAudioRef.current?.pause();
    if (ambientFadeRef.current) {
      clearInterval(ambientFadeRef.current);
      ambientFadeRef.current = null;
    }
    ambientAudioRef.current?.pause();
    if (musicFadeRef.current) {
      clearInterval(musicFadeRef.current);
      musicFadeRef.current = null;
    }
    musicAudioRef.current?.pause();
  }, []);

  /** Fade out ambient audio over ~1s then pause. */
  const fadeOutAmbient = useCallback(() => {
    const ambient = ambientAudioRef.current;
    if (!ambient || ambient.paused) return;
    if (ambientFadeRef.current) clearInterval(ambientFadeRef.current);
    ambientFadeRef.current = setInterval(() => {
      if (ambient.volume > 0.02) {
        ambient.volume = Math.max(0, ambient.volume - 0.02);
      } else {
        ambient.pause();
        if (ambientFadeRef.current) {
          clearInterval(ambientFadeRef.current);
          ambientFadeRef.current = null;
        }
      }
    }, 100);
  }, []);

  /** Fade music to a target volume over ~1s, optionally pause when silent. */
  const fadeMusicTo = useCallback((target: number, pauseAtZero = false) => {
    const music = musicAudioRef.current;
    if (!music || music.paused) return;
    if (musicFadeRef.current) clearInterval(musicFadeRef.current);
    const step = music.volume > target ? -0.02 : 0.02;
    musicFadeRef.current = setInterval(() => {
      const diff = target - music.volume;
      if (Math.abs(diff) < 0.025) {
        music.volume = target;
        if (pauseAtZero && target === 0) music.pause();
        if (musicFadeRef.current) {
          clearInterval(musicFadeRef.current);
          musicFadeRef.current = null;
        }
      } else {
        music.volume = Math.max(0, Math.min(1, music.volume + step));
      }
    }, 100);
  }, []);

  // Apply voice volume
  useEffect(() => {
    if (introAudioRef.current) introAudioRef.current.volume = voiceVolume;
  }, [voiceVolume]);

  // Apply ambient volume
  useEffect(() => {
    if (ambientAudioRef.current && !ambientAudioRef.current.paused) {
      ambientAudioRef.current.volume = 0.15 * ambientVolume;
    }
  }, [ambientVolume]);

  // Handle music volume changes (pause when 0, resume when >0)
  useEffect(() => {
    const music = musicAudioRef.current;
    if (!music || !musicStartedRef.current) return;
    if (musicVolume === 0) {
      music.pause();
    } else if (phase === "playing" || phase === "waiting") {
      music.play().catch(() => {});
    }
  }, [musicVolume, phase]);

  // Transition to ready when story is ready and we're not playing the intro
  useEffect(() => {
    if (isStoryReady && phase === "waiting") {
      setPhase("ready");
    }
  }, [isStoryReady, phase]);

  // Play ready audio and fade ambient when entering ready phase
  useEffect(() => {
    if (phase === "ready" && !readyAudioPlayed.current) {
      readyAudioPlayed.current = true;
      readyAudioRef.current?.play().catch(() => {});
      fadeOutAmbient();
      fadeMusicTo(MUSIC_VOL_READY);
    }
  }, [phase, fadeOutAmbient, fadeMusicTo]);

  // Rotate fun facts during waiting phase
  useEffect(() => {
    if (phase !== "waiting") return;
    const interval = setInterval(() => {
      setFunFactIndex((prev) => (prev + 1) % HERITAGE_FACTS.length);
    }, 8000);
    return () => clearInterval(interval);
  }, [phase]);

  // Stuck timer during waiting phase
  useEffect(() => {
    if (phase === "waiting" && !isStoryReady && !error) {
      setShowStuckMessage(false);
      stuckTimerRef.current = setTimeout(() => {
        setShowStuckMessage(true);
      }, STUCK_TIMEOUT_MS);
    } else {
      if (stuckTimerRef.current) {
        clearTimeout(stuckTimerRef.current);
        stuckTimerRef.current = null;
      }
      setShowStuckMessage(false);
    }
    return () => {
      if (stuckTimerRef.current) {
        clearTimeout(stuckTimerRef.current);
        stuckTimerRef.current = null;
      }
    };
  }, [phase, isStoryReady, error]);

  // Step elapsed timer
  useEffect(() => {
    if (!progressStep) {
      stepStartRef.current = null;
      setStepElapsed(0);
      return;
    }
    stepStartRef.current = Date.now();
    setStepElapsed(0);
    const interval = setInterval(() => {
      if (stepStartRef.current != null) {
        setStepElapsed(Math.floor((Date.now() - stepStartRef.current) / 1000));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [progressStep]);

  const handleTimeUpdate = useCallback(() => {
    const audio = introAudioRef.current;
    if (!audio) return;
    const t = audio.currentTime;

    let newIndex = -1;
    for (let i = GRIOT_BEATS.length - 1; i >= 0; i--) {
      const beat = GRIOT_BEATS[i];
      if (t >= beat.time && t < beat.time + beat.duration) {
        newIndex = i;
        break;
      }
    }

    if (newIndex !== activeBeatIndex) {
      setPrevBeatIndex(activeBeatIndex);
      setActiveBeatIndex(newIndex);
    }

    /* ── Background music volume control ── */
    const music = musicAudioRef.current;
    if (!music) return;

    if (t >= MUSIC_START_TIME && !musicStartedRef.current) {
      musicStartedRef.current = true;
      music.volume = MUSIC_VOL_START * musicVolume;
      if (musicVolume > 0) music.play().catch(() => {});
    }

    if (musicStartedRef.current && !music.paused && musicVolume > 0) {
      let baseVol: number;
      if (t < MUSIC_BEAT_DROP) {
        const progress = (t - MUSIC_START_TIME) / (MUSIC_BEAT_DROP - MUSIC_START_TIME);
        baseVol = MUSIC_VOL_START + (MUSIC_VOL_PEAK - MUSIC_VOL_START) * Math.min(1, Math.max(0, progress));
      } else {
        baseVol = MUSIC_VOL_PEAK;
      }
      music.volume = baseVol * musicVolume;
    }
  }, [activeBeatIndex, musicVolume]);

  const handleIntroEnded = useCallback(() => {
    if (isStoryReady) {
      setPhase("ready");
    } else {
      setPhase("waiting");
    }
  }, [isStoryReady]);

  const handleSkipIntro = useCallback(() => {
    introAudioRef.current?.pause();
    musicAudioRef.current?.pause();
    if (musicFadeRef.current) {
      clearInterval(musicFadeRef.current);
      musicFadeRef.current = null;
    }
    fadeOutAmbient();
    if (isStoryReady) {
      setPhase("ready");
    } else {
      setPhase("waiting");
    }
  }, [isStoryReady, fadeOutAmbient]);

  /** Fade out intro ambient and stop narration before revealing the narrative. */
  const handleBegin = useCallback(() => {
    introAudioRef.current?.pause();
    readyAudioRef.current?.pause();
    fadeOutAmbient(); // smooth fade — NarrativeStream takes over ambient
    fadeMusicTo(0, true); // fade music out and pause
    onComplete();
  }, [onComplete, fadeOutAmbient, fadeMusicTo]);

  /** Retry: clear stuck message and local state before calling parent retry. */
  const handleRetry = useCallback(() => {
    setShowStuckMessage(false);
    onRetry();
  }, [onRetry]);

  // Auto-play ambient fire and griot voiceover simultaneously on mount.
  useEffect(() => {
    const audio = introAudioRef.current;
    const ambient = ambientAudioRef.current;
    if (ambient) {
      ambient.volume = 0.15 * ambientVolume;
      ambient.play().catch(() => {});
    }
    if (audio) {
      audio.play().catch(() => {
        handleSkipIntro();
      });
    }
    return () => {
      if (ambientFadeRef.current) {
        clearInterval(ambientFadeRef.current);
        ambientFadeRef.current = null;
      }
      if (musicFadeRef.current) {
        clearInterval(musicFadeRef.current);
        musicFadeRef.current = null;
      }
      musicAudioRef.current?.pause();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const activeBeat = activeBeatIndex >= 0 ? GRIOT_BEATS[activeBeatIndex] : null;

  return (
    <motion.div
      key="griot-intro"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.8 }}
      className="fixed inset-0 z-30 flex flex-col items-center justify-center bg-[var(--night)] overflow-hidden px-6"
    >
      {/* Audio elements */}
      <audio
        ref={introAudioRef}
        src="/audio/griot-intro.mp3"
        preload="auto"
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleIntroEnded}
      />
      <audio
        ref={readyAudioRef}
        src="/audio/griot-ready.mp3"
        preload="auto"
      />
      <audio
        ref={ambientAudioRef}
        src="/audio/fire.mp3"
        preload="auto"
        loop
      />
      <audio
        ref={musicAudioRef}
        src="/audio/intro-music.mp3"
        preload="metadata"
      />

      {/* Ambient gradient — CSS animated */}
      <div
        className="absolute inset-0 griot-bg-pulse"
        style={{
          background:
            "radial-gradient(ellipse at 50% 30%, #1a1520 0%, var(--night) 70%)",
        }}
      />

      <GoldParticles count={60} className="griot-sparks" />

      {/* === PLAYING PHASE === */}
      <AnimatePresence mode="wait">
        {phase === "playing" && (
          <motion.div
            key="playing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="relative z-10 flex flex-col items-center justify-center w-full max-w-2xl"
          >
            <SankofaBird className="w-20 h-20 text-[var(--gold)] animate-slow-rotate" />

            {/* Beat text */}
            <div className="mt-12 min-h-[120px] flex items-center justify-center">
              <AnimatePresence mode="wait">
                {activeBeat && (
                  <motion.p
                    key={activeBeatIndex}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="font-[family-name:var(--font-display)] text-2xl md:text-3xl text-[var(--gold)] text-center leading-relaxed whitespace-pre-line"
                    style={{ willChange: "transform, opacity" }}
                  >
                    {activeBeat.text}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>

            {/* Gold divider */}
            <div className="mt-8 w-32 h-px bg-[var(--gold)] griot-divider-expand" />

            {/* Skip intro */}
            <button
              type="button"
              onClick={handleSkipIntro}
              className="fixed bottom-8 right-8 font-[family-name:var(--font-body)] text-sm text-[var(--muted)]/60 hover:text-[var(--muted)] transition-colors cursor-pointer"
            >
              Skip intro
            </button>
          </motion.div>
        )}

        {/* === WAITING PHASE === */}
        {phase === "waiting" && (
          <motion.div
            key="waiting"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="relative z-10 flex flex-col items-center"
          >
            <SankofaBird className="w-24 h-24 text-[var(--gold)] animate-slow-rotate" />

            {sessionInvalid ? (
              <>
                <p className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)] text-center max-w-md">
                  This session is no longer valid. The server may have been restarted.
                </p>
                <p className="mt-4 font-[family-name:var(--font-body)] text-sm text-[var(--muted)] text-center">
                  Please start over from the beginning.
                </p>
                <Link
                  href="/"
                  className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                >
                  Start over
                </Link>
              </>
            ) : error ? (
              <>
                <p className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)]">
                  Something went wrong
                </p>
                <p className="mt-3 font-[family-name:var(--font-body)] text-sm text-[var(--terracotta)] max-w-md text-center">
                  {error}
                </p>
                <button
                  type="button"
                  onClick={handleRetry}
                  className="mt-8 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                >
                  Try again
                </button>
              </>
            ) : (
              <>
                <motion.p
                  className="mt-10 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)]"
                  animate={{ opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  Sankofa is reaching back…
                </motion.p>

                {/* Thinking/progress message */}
                <AnimatePresence mode="wait">
                  <motion.p
                    key={thinkingMessage || progressStep || "default"}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -6 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                    className="mt-4 font-[family-name:var(--font-body)] text-sm text-[var(--ochre)] italic text-center max-w-sm"
                    role="status"
                  >
                    {thinkingMessage
                      ? thinkingMessage
                      : progressStep === "planning_arc"
                        ? "Planning your story\u2026"
                        : progressStep === "generating_audio"
                          ? "Adding narration\u2026"
                          : progressStep === "generating_narrative"
                            ? "Generating narrative and images\u2026"
                            : "Weaving your ancestral narrative"}
                  </motion.p>
                </AnimatePresence>

                {stepElapsed > 0 && (
                  <p className="mt-1 font-[family-name:var(--font-body)] text-xs text-[var(--muted)]">
                    {stepElapsed}s
                  </p>
                )}

                {/* Arc chapter cards */}
                <AnimatePresence>
                  {arcOutline && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.8, delay: 0.3 }}
                      className="mt-10 w-full max-w-md"
                    >
                      <div className="h-px w-16 mx-auto bg-[var(--gold)]/40 mb-6" />
                      {[
                        { key: "act1_setting", num: "I" },
                        { key: "act2_people", num: "II" },
                        { key: "act3_thread", num: "III" },
                      ].map((act, i) => {
                        const actData = arcOutline[act.key as keyof typeof arcOutline];
                        const title = typeof actData === "object" && actData?.title ? actData.title : null;
                        if (!title) return null;
                        return (
                          <motion.div
                            key={act.key}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.6, delay: 0.5 + i * 0.4 }}
                            className="flex items-baseline gap-3 mb-3 arc-card"
                          >
                            <span className="font-[family-name:var(--font-display)] text-xs text-[var(--gold)]/60 tracking-widest shrink-0">
                              {act.num}
                            </span>
                            <span className="font-[family-name:var(--font-display)] text-sm text-[var(--ivory)]/70 italic">
                              {title}
                            </span>
                          </motion.div>
                        );
                      })}
                      <motion.div
                        className="mt-4 h-px bg-gradient-to-r from-transparent via-[var(--gold)]/30 to-transparent"
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ duration: 1.5, delay: 1.8 }}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Heritage fun facts */}
                <div className="mt-10 max-w-sm text-center">
                  <p className="font-[family-name:var(--font-body)] text-[10px] text-[var(--gold)]/50 uppercase tracking-[0.2em] mb-2">
                    Did you know?
                  </p>
                  <AnimatePresence mode="wait">
                    <motion.p
                      key={funFactIndex}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] italic leading-relaxed"
                    >
                      {HERITAGE_FACTS[funFactIndex]}
                    </motion.p>
                  </AnimatePresence>
                </div>

                {showStuckMessage && (
                  <div className="mt-8 text-center">
                    <p className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] max-w-sm">
                      This is taking longer than usual. Check that the backend is running and your
                      Google API key is set in <code className="text-[var(--ochre)]">backend/.env</code>.
                    </p>
                    <button
                      type="button"
                      onClick={handleRetry}
                      className="mt-4 px-6 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
                    >
                      Try again
                    </button>
                  </div>
                )}

              </>
            )}
          </motion.div>
        )}

        {/* === READY PHASE === */}
        {phase === "ready" && (
          <motion.div
            key="ready"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="relative z-10 flex flex-col items-center"
          >
            <SankofaBird className="w-20 h-20 text-[var(--gold)] animate-slow-rotate" />

            <motion.p
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="mt-12 font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--gold)] text-center"
            >
              Your story is ready.
            </motion.p>

            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.8 }}
              className="mt-4 font-[family-name:var(--font-body)] text-xl text-[var(--ivory)] italic text-center"
            >
              Come, let us begin.
            </motion.p>

            <motion.div
              initial={{ scaleX: 0, opacity: 0 }}
              animate={{ scaleX: 1, opacity: 0.4 }}
              transition={{ duration: 1.2, delay: 1.0 }}
              className="mt-8 w-32 h-px bg-[var(--gold)]"
              style={{ transformOrigin: "center" }}
            />

            <motion.button
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 1.4 }}
              onClick={handleBegin}
              className="mt-10 px-10 py-4 bg-[var(--gold)] text-[var(--night)] font-[family-name:var(--font-display)] text-lg tracking-[0.1em] uppercase hover:bg-[var(--ochre)] transition-colors cursor-pointer"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Begin
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Volume control panel */}
      <VolumePanel
        channels={[
          {
            id: "voice",
            label: "Voice",
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" x2="12" y1="19" y2="22" />
              </svg>
            ),
            value: voiceVolume,
            onChange: setVoiceVolume,
          },
          {
            id: "music",
            label: "Music",
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18V5l12-2v13" />
                <circle cx="6" cy="18" r="3" />
                <circle cx="18" cy="16" r="3" />
              </svg>
            ),
            value: musicVolume,
            onChange: setMusicVolume,
          },
          {
            id: "ambient",
            label: "Ambient",
            icon: (
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2" />
                <path d="M9.6 4.6A2 2 0 1 1 11 8H2" />
                <path d="M12.6 19.4A2 2 0 1 0 14 16H2" />
              </svg>
            ),
            value: ambientVolume,
            onChange: setAmbientVolume,
          },
        ]}
      />
    </motion.div>
  );
}
