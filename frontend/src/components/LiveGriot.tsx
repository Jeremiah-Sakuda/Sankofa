"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { API_BASE } from "../lib/api";
import SankofaBird from "./SankofaBird";

interface Props {
  sessionId: string;
  onClose: () => void;
}

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

/**
 * LiveGriot — Real-time voice conversation with the Sankofa Griot
 * using the Gemini Live API via WebSocket.
 *
 * Captures mic audio as PCM 16-bit 16kHz, streams to backend,
 * receives audio back and plays it through AudioContext.
 */
export default function LiveGriot({ sessionId, onClose }: Props) {
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

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const disconnect = useCallback(() => {
    // Stop mic
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      try {
        wsRef.current.send(JSON.stringify({ type: "close" }));
      } catch { /* ignore */ }
      wsRef.current.close();
      wsRef.current = null;
    }

    // Close audio context
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
      // Request mic access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      mediaStreamRef.current = stream;

      // Set up AudioContext for playback and capture
      const audioCtx = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioCtx;
      nextPlayTimeRef.current = audioCtx.currentTime;

      // Connect to WebSocket
      const wsUrl = `${API_BASE.replace(/^http/, "ws")}/api/narrative/${sessionId}/live`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionState("connected");

        // Start capturing mic audio
        const captureCtx = new AudioContext({ sampleRate: 16000 });
        const source = captureCtx.createMediaStreamSource(stream);
        const processor = captureCtx.createScriptProcessor(4096, 1, 1);
        processorRef.current = processor;

        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;

          const float32 = e.inputBuffer.getChannelData(0);
          // Convert float32 to int16 PCM
          const int16 = new Int16Array(float32.length);
          for (let i = 0; i < float32.length; i++) {
            const s = Math.max(-1, Math.min(1, float32[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }

          // Send as base64
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
            setGriotTranscript((prev) => (prev ? prev + " " : "") + (msg.text || ""));
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

    try {
      const raw = atob(b64Data);
      const bytes = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) {
        bytes[i] = raw.charCodeAt(i);
      }

      // Determine sample rate from mime type
      const rateMatch = mimeType.match(/rate=(\d+)/);
      const sampleRate = rateMatch ? parseInt(rateMatch[1], 10) : 24000;

      // Convert PCM int16 to float32
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

      // Schedule playback sequentially to avoid gaps
      const now = audioCtx.currentTime;
      const startTime = Math.max(now, nextPlayTimeRef.current);
      source.start(startTime);
      nextPlayTimeRef.current = startTime + buffer.duration;
    } catch (e) {
      console.warn("Audio playback error:", e);
    }
  }, []);

  const isActive = connectionState === "connected";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--night)]/90 backdrop-blur-sm"
    >
      <div className="relative w-full max-w-md mx-4 p-8 rounded-lg bg-gradient-to-b from-[#1a1520] to-[var(--night)] border border-[var(--gold)]/20 shadow-2xl">
        {/* Close button */}
        <button
          onClick={() => { disconnect(); onClose(); }}
          className="absolute top-4 right-4 text-[var(--muted)] hover:text-[var(--ivory)] transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" x2="6" y1="6" y2="18" /><line x1="6" x2="18" y1="6" y2="18" />
          </svg>
        </button>

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
            {connectionState === "connected"
              ? "Listening… speak naturally"
              : connectionState === "connecting"
                ? "Connecting…"
                : "Start a voice conversation about your heritage"}
          </p>
        </div>

        {/* Transcription area */}
        <div className="min-h-[120px] mb-6 space-y-3">
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
        </div>

        {/* Audio visualizer / status ring */}
        <div className="flex justify-center mb-6">
          <motion.div
            className={`w-20 h-20 rounded-full border-2 flex items-center justify-center transition-colors ${
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
            {/* Mic icon */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="28"
              height="28"
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
        </div>

        {/* Connect / Disconnect button */}
        <div className="flex justify-center">
          {connectionState === "disconnected" || connectionState === "error" ? (
            <button
              onClick={connect}
              className="px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
            >
              Start Conversation
            </button>
          ) : (
            <button
              onClick={disconnect}
              className="px-8 py-3 border border-[var(--terracotta)]/60 text-[var(--terracotta)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--terracotta)] hover:text-[var(--ivory)] transition-all cursor-pointer"
            >
              End Conversation
            </button>
          )}
        </div>

        {/* Error message */}
        {errorMessage && (
          <p className="mt-4 text-center font-[family-name:var(--font-body)] text-xs text-[var(--terracotta)]">
            {errorMessage}
          </p>
        )}
      </div>
    </motion.div>
  );
}
