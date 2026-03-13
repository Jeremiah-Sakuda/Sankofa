"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";

interface ScrollProgressProps {
  totalActs: number;
  currentAct: number;
  isComplete: boolean;
}

export default function ScrollProgress({ totalActs, currentAct, isComplete }: ScrollProgressProps) {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (scrollHeight <= 0) { setScrollProgress(0); return; }
      setScrollProgress(Math.min(1, window.scrollY / scrollHeight));
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const actMarkers = Array.from({ length: totalActs }, (_, i) => ({
    act: i + 1,
    position: totalActs <= 1 ? 0 : i / (totalActs - 1),
  }));

  return (
    <motion.div
      className="fixed left-3 md:left-6 top-1/2 -translate-y-1/2 z-40 hidden md:flex flex-col items-center gap-0"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.8, delay: 0.5 }}
    >
      {/* Track */}
      <div className="relative w-[2px] h-48 bg-[var(--ochre)]/15 rounded-full overflow-hidden">
        {/* Fill */}
        <motion.div
          className="absolute top-0 left-0 w-full bg-[var(--gold)] rounded-full origin-top"
          style={{ height: `${scrollProgress * 100}%` }}
          transition={{ duration: 0.1 }}
        />

        {/* Act markers */}
        {actMarkers.map((marker) => (
          <div
            key={marker.act}
            className="absolute left-1/2 -translate-x-1/2"
            style={{ top: `${marker.position * 100}%` }}
          >
            <div
              className={`w-2 h-2 rounded-full border transition-all duration-500 ${
                currentAct >= marker.act
                  ? "bg-[var(--gold)] border-[var(--gold)] shadow-[0_0_8px_rgba(212,168,67,0.4)]"
                  : "bg-transparent border-[var(--ochre)]/30"
              }`}
            />
          </div>
        ))}
      </div>

      {/* Chapter label */}
      <AnimatePresence mode="wait">
        <motion.span
          key={currentAct}
          className="mt-3 font-[family-name:var(--font-display)] text-[9px] tracking-[0.2em] text-[var(--gold)]/60 uppercase whitespace-nowrap"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.3 }}
        >
          {isComplete ? "Fin" : `Act ${currentAct}`}
        </motion.span>
      </AnimatePresence>
    </motion.div>
  );
}
