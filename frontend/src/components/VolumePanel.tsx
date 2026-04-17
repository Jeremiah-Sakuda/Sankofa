"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";

export interface VolumeChannel {
  id: string;
  label: string;
  icon: React.ReactNode;
  value: number; // 0-1
  onChange: (value: number) => void;
}

interface VolumePanelProps {
  channels: VolumeChannel[];
}

export default function VolumePanel({ channels }: VolumePanelProps) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  // Close on click-outside
  const handleClickOutside = useCallback(
    (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        btnRef.current &&
        !btnRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open, handleClickOutside]);

  const allMuted = channels.every((ch) => ch.value === 0);

  // Track previous values for unmuting
  const prevValues = useRef<Map<string, number>>(new Map());

  const toggleChannel = (ch: VolumeChannel) => {
    if (ch.value > 0) {
      // Mute: save current value and set to 0
      prevValues.current.set(ch.id, ch.value);
      ch.onChange(0);
    } else {
      // Unmute: restore previous value or default to 1
      const prev = prevValues.current.get(ch.id) ?? 1;
      ch.onChange(prev);
    }
  };

  return (
    <>
      {/* Toggle button */}
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-8 left-8 z-40 w-9 h-9 flex items-center justify-center rounded-full border border-[var(--gold)]/30 bg-[var(--night)]/80 backdrop-blur text-[var(--gold)] hover:border-[var(--gold)] transition-all cursor-pointer"
        title="Volume controls"
      >
        {allMuted ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 5L6 9H2v6h4l5 4V5z" />
            <line x1="23" x2="17" y1="9" y2="15" />
            <line x1="17" x2="23" y1="9" y2="15" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 5L6 9H2v6h4l5 4V5z" />
            <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
          </svg>
        )}
      </button>

      {/* Panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-20 left-8 z-40 min-w-[180px] rounded-lg border border-[var(--gold)]/20 bg-[var(--night)]/90 backdrop-blur-xl shadow-lg p-3 flex flex-col gap-2"
          >
            {channels.map((ch) => {
              const isOn = ch.value > 0;
              return (
                <button
                  key={ch.id}
                  type="button"
                  onClick={() => toggleChannel(ch)}
                  className={`flex items-center gap-3 px-2 py-2 rounded-md transition-all cursor-pointer ${
                    isOn
                      ? "bg-[var(--gold)]/10 text-[var(--gold)]"
                      : "text-[var(--ivory)]/40 hover:text-[var(--ivory)]/60"
                  }`}
                >
                  <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                    {ch.icon}
                  </span>
                  <span className="text-xs font-medium flex-1 text-left">
                    {ch.label}
                  </span>
                  {/* On/Off indicator */}
                  <span
                    className={`w-8 h-4 rounded-full flex items-center transition-colors ${
                      isOn ? "bg-[var(--gold)]/30" : "bg-[var(--ivory)]/10"
                    }`}
                  >
                    <span
                      className={`w-3 h-3 rounded-full transition-all ${
                        isOn
                          ? "bg-[var(--gold)] translate-x-4"
                          : "bg-[var(--ivory)]/30 translate-x-0.5"
                      }`}
                    />
                  </span>
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
