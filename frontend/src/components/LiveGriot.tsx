"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { API_BASE } from "../lib/api";
import SankofaBird from "./SankofaBird";
import GoldParticles from "./GoldParticles";

interface Props {
  sessionId: string;
  onClose: () => void;
  hasNarrative?: boolean;
  latestImageSrc?: string | null;
}

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

/**
 * LiveGriot — Real-time voice conversation with the Sankofa Griot
 * using the Gemini Live API via WebSocket.
 *
 * Two modes:
 *   A) hasNarrative=true  → Glassmorphism bottom dock (narrative stays visible)
 *   B) hasNarrative=false → Ambient full-screen with warm gradient + particles
 */
export default function LiveGriot({ sessionId, onClose, hasNarrative = false, latestImageSrc }: Props) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [isGriotSpeaking, setIsGriotSpeaking] = useState(false);
  const [userTranscript, setUserTranscript] = useState("");
  const [griotTranscript, setGriotTranscript] = useState("");
  const [toolMessage, setToolMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const nextPlayTimeRef = useRef(0);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll transcript to bottom
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [userTranscript, griotTranscript, toolMessage]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const disconnect = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: "close" }));
      } catch { /* ignore */ }
      wsRef.current.close();
      wsRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setConnectionState("disconnected");
    setIsUserSpeaking(false);
    setIsGriotSpeaking(false);
  }, []);

  const connect = useCallback(async () => {
    if (connectionState === "connecting" || connectionState === "connected") return;

    setConnectionState("connecting");
    setErrorMessage(null);
    setUserTranscript("");
    setGriotTranscript("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      mediaStreamRef.current = stream;

      const audioCtx = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioCtx;
      nextPlayTimeRef.current = audioCtx.currentTime;

      const wsUrl = `${API_BASE.replace(/^http/, "ws")}/api/narrative/${sessionId}/live`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionState("connected");

        const captureCtx = new AudioContext({ sampleRate: 16000 });
        const source = captureCtx.createMediaStreamSource(stream);
        const processor = captureCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;

          const float32 = e.inputBuffer.getChannelData(0);
          const int16 = new Int16Array(float32.length);
          for (let i = 0; i < float32.length; i++) {
            const s = Math.max(-1, Math.min(1, float32[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }

          const bytes = new Uint8Array(int16.buffer);
          const b64 = btoa(String.fromCharCode(...bytes));
          ws.send(JSON.stringify({ type: "audio", data: b64 }));
        };

        source.connect(processor);
        processor.connect(captureCtx.destination);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === "audio" && msg.data) {
            setIsGriotSpeaking(true);
            playAudioChunk(msg.data, msg.mime_type || "audio/pcm;rate=24000");
          } else if (msg.type === "transcript_in") {
            setUserTranscript(msg.text || "");
          } else if (msg.type === "transcript_out") {
            setIsGriotSpeaking(true);
            // Replace (not append) — Gemini Live API sends cumulative transcriptions
            setGriotTranscript(msg.text || "");
          } else if (msg.type === "tool_call") {
            setToolMessage(msg.message || null);
          } else if (msg.type === "turn_complete") {
            setIsGriotSpeaking(false);
            setToolMessage(null);
          } else if (msg.type === "error") {
            setErrorMessage(msg.message || "Something went wrong");
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        setConnectionState("error");
        setErrorMessage("WebSocket connection failed");
      };

      ws.onclose = () => {
        setConnectionState("disconnected");
      };
    } catch (e) {
      setConnectionState("error");
      setErrorMessage(
        e instanceof Error
          ? e.message.includes("Permission denied") || e.message.includes("NotAllowed")
            ? "Microphone access denied. Please allow mic access and try again."
            : e.message
          : "Failed to start voice conversation"
      );
    }
  }, [connectionState, sessionId]);

  const playAudioChunk = useCallback((b64Data: string, mimeType: string) => {
    const audioCtx = audioContextRef.current;
    if (!audioCtx) return;

    // Resume AudioContext if suspended (browsers require user gesture)
    if (audioCtx.state === "suspended") {
      audioCtx.resume().catch(() => {});
    }

    try {
      const raw = atob(b64Data);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) {
        bytes[i] = raw.charCodeAt(i);
      }

      const rateMatch = mimeType.match(/rate=(\d+)/);
      const sampleRate = rateMatch ? parseInt(rateMatch[1], 10) : 24000;

      const int16 = new Int16Array(bytes.buffer);
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) {
        float32[i] = int16[i] / 32768;
      }

      const buffer = audioCtx.createBuffer(1, float32.length, sampleRate);
      buffer.copyToChannel(float32, 0);

      const source = audioCtx.createBufferSource();
      source.buffer = buffer;
      source.connect(audioCtx.destination);

      const now = audioCtx.currentTime;
      const startTime = Math.max(now, nextPlayTimeRef.current);
      source.start(startTime);
      nextPlayTimeRef.current = startTime + buffer.duration;
    } catch (e) {
      console.warn("Audio playback error:", e);
    }
  }, []);

  const isActive = connectionState === "connected";

  const statusText =
    connectionState === "connected"
      ? isGriotSpeaking
        ? "Griot is speaking\u2026"
        : "Listening\u2026 speak naturally"
      : connectionState === "connecting"
        ? "Connecting\u2026"
        : "Start a voice conversation about your heritage";

  /* ── Shared UI pieces ── */

  const closeButton = (
    <button
      onClick={() => { disconnect(); onClose(); }}
      className="text-[var(--muted)] hover:text-[var(--ivory)] transition-colors shrink-0 cursor-pointer"
    >
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" x2="6" y1="6" y2="18" /><line x1="6" x2="18" y1="6" y2="18" />
      </svg>
    </button>
  );

  const micRing = (size: string) => (
    <motion.div
      className={`${size} rounded-full border-2 flex items-center justify-center transition-colors shrink-0 ${
        isGriotSpeaking
          ? "border-[var(--gold)] bg-[var(--gold)]/10"
          : isActive
            ? "border-[var(--ochre)]/60 bg-transparent"
            : "border-[var(--muted)]/30 bg-transparent"
      }`}
      animate={
        isGriotSpeaking
          ? { scale: [1, 1.05, 1], borderColor: ["var(--gold)", "var(--ochre)", "var(--gold)"] }
          : isActive
            ? { scale: [1, 1.02, 1] }
            : {}
      }
      transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width={size === "w-14 h-14" ? "20" : "28"}
        height={size === "w-14 h-14" ? "20" : "28"}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={isActive ? "text-[var(--gold)]" : "text-[var(--muted)]"}
      >
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" x2="12" y1="19" y2="22" />
      </svg>
    </motion.div>
  );

  const actionButton = (
    <>
      {connectionState === "disconnected" || connectionState === "error" ? (
        <button
          onClick={connect}
          className="px-6 py-2.5 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
        >
          Start Conversation
        </button>
      ) : (
        <button
          onClick={disconnect}
          className="px-6 py-2.5 border border-[var(--terracotta)]/60 text-[var(--terracotta)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--terracotta)] hover:text-[var(--ivory)] transition-all cursor-pointer"
        >
          End Conversation
        </button>
      )}
    </>
  );

  const transcriptArea = (className: string) => (
    <div className={className}>
      <AnimatePresence mode="popLayout">
        {userTranscript && (
          <motion.div
            key="user"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-right"
          >
            <span className="font-[family-name:var(--font-body)] text-xs text-[var(--muted)] uppercase tracking-wider">You</span>
            <p className="mt-1 font-[family-name:var(--font-body)] text-sm text-[var(--ivory)]/80 italic">
              {userTranscript}
            </p>
          </motion.div>
        )}
        {toolMessage && (
          <motion.div
            key="tool"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center"
          >
            <p className="font-[family-name:var(--font-body)] text-xs text-[var(--ochre)] italic">
              {toolMessage}
            </p>
          </motion.div>
        )}
        {griotTranscript && (
          <motion.div
            key="griot"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <span className="font-[family-name:var(--font-body)] text-xs text-[var(--gold)]/60 uppercase tracking-wider">Griot</span>
            <p className="mt-1 font-[family-name:var(--font-body)] text-sm text-[var(--ivory)] leading-relaxed">
              {griotTranscript}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
      <div ref={transcriptEndRef} />
    </div>
  );

  const errorDisplay = errorMessage && (
    <p className="mt-2 text-center font-[family-name:var(--font-body)] text-xs text-[var(--terracotta)]">
      {errorMessage}
    </p>
  );

  /* ── Mode A: Glassmorphism Bottom Dock ── */
  if (hasNarrative) {
    return (
      <motion.div
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        exit={{ y: "100%" }}
        transition={{ type: "spring", damping: 30, stiffness: 300 }}
        className="fixed bottom-0 inset-x-0 z-50 max-h-[45vh] flex flex-col bg-[var(--night)]/60 backdrop-blur-xl border-t border-[var(--gold)]/20 shadow-[0_-8px_40px_rgba(0,0,0,0.5)]"
      >
        {/* Header bar */}
        <div className="flex items-center justify-between py-3 px-6 border-b border-[var(--gold)]/10 shrink-0">
          <div className="flex items-center gap-3">
            <motion.div
              animate={isGriotSpeaking ? { scale: [1, 1.1, 1] } : {}}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
            >
              <SankofaBird className={`w-6 h-6 ${isActive ? "text-[var(--gold)]" : "text-[var(--gold)]/40"}`} />
            </motion.div>
            <h2 className="font-[family-name:var(--font-display)] text-sm tracking-wider text-[var(--gold)] uppercase">
              Talk to the Griot
            </h2>
            <span className="font-[family-name:var(--font-body)] text-xs text-[var(--muted)]">
              &middot;&nbsp;{statusText}
            </span>
          </div>
          {closeButton}
        </div>

        {/* Transcript area — scrollable */}
        {transcriptArea("flex-1 overflow-y-auto px-6 py-3 space-y-3 min-h-0")}

        {/* Action bar */}
        <div className="flex items-center justify-center gap-6 py-4 px-6 border-t border-[var(--gold)]/10 shrink-0">
          {micRing("w-14 h-14")}
          {actionButton}
        </div>

        {errorDisplay}
      </motion.div>
    );
  }

  /* ── Mode B: Ambient Full-Screen ── */
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.5 }}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
    >
      {/* Warm radial gradient background */}
      <div
        className="absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at 50% 40%, #1c1210 0%, #1a1520 40%, var(--night) 100%)",
        }}
      />

      {/* Ambient image with Ken Burns */}
      {latestImageSrc && (
        <motion.img
          src={latestImageSrc}
          className="absolute inset-0 w-full h-full object-cover opacity-20"
          animate={{ scale: [1, 1.15] }}
          transition={{ duration: 30, repeat: Infinity, repeatType: "reverse", ease: "linear" }}
          alt=""
        />
      )}

      {/* Gold particles overlay */}
      <GoldParticles count={25} />

      {/* Content card */}
      <div className="relative z-10 w-full max-w-md mx-4 p-8 rounded-lg bg-gradient-to-b from-[#1a1520]/80 to-[var(--night)]/80 backdrop-blur-md border border-[var(--gold)]/20 shadow-2xl">
        {/* Close button */}
        <div className="absolute top-4 right-4">
          {closeButton}
        </div>

        {/* Header */}
        <div className="text-center mb-8">
          <motion.div
            animate={isGriotSpeaking ? { scale: [1, 1.1, 1] } : {}}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          >
            <SankofaBird className={`w-12 h-12 mx-auto ${isActive ? "text-[var(--gold)]" : "text-[var(--gold)]/40"}`} />
          </motion.div>
          <h2 className="mt-3 font-[family-name:var(--font-display)] text-lg tracking-wider text-[var(--gold)] uppercase">
            Talk to the Griot
          </h2>
          <p className="mt-1 font-[family-name:var(--font-body)] text-xs text-[var(--muted)]">
            {statusText}
          </p>
        </div>

        {/* Transcript area */}
        {transcriptArea("min-h-[120px] mb-6 space-y-3")}

        {/* Mic ring */}
        <div className="flex justify-center mb-6">
          {micRing("w-20 h-20")}
        </div>

        {/* Connect / Disconnect */}
        <div className="flex justify-center">
          {actionButton}
        </div>

        {errorDisplay}
      </div>
    </motion.div>
  );
}
