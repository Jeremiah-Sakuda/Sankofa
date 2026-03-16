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
            className="fixed bottom-20 left-8 z-40 min-w-[200px] rounded-lg border border-[var(--gold)]/20 bg-[var(--night)]/90 backdrop-blur-xl shadow-lg p-3 flex flex-col gap-3"
          >
            {channels.map((ch) => (
              <div key={ch.id} className="flex items-center gap-2.5">
                <span className="text-[var(--gold)] w-4 h-4 flex-shrink-0 flex items-center justify-center">
                  {ch.icon}
                </span>
                <span className="text-[var(--ivory)]/70 text-xs font-medium w-16 flex-shrink-0">
                  {ch.label}
                </span>
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={Math.round(ch.value * 100)}
                  onChange={(e) => ch.onChange(Number(e.target.value) / 100)}
                  className="volume-slider flex-1 h-1 cursor-pointer"
                />
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
