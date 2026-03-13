"use client";

import { useRef, useMemo } from "react";
import { motion, AnimatePresence, useScroll, useSpring } from "motion/react";

interface ScrollProgressProps {
  totalActs: number;
  currentAct: number;
  isComplete: boolean;
}

export default function ScrollProgress({ totalActs, currentAct, isComplete }: ScrollProgressProps) {
  // Use framer-motion for butter-smooth, performant scroll tracking without React state thrashing
  const { scrollYProgress } = useScroll();
  
  // Add a spring physics smoothing layer to handle dynamic height changes during streaming
  const scaleY = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  // Calculate act markers based on a fixed 3 acts instead of dynamic totalActs
  // This prevents the markers from jumping around when new acts stream in
  const EXPECTED_ACTS = 3;
  const actMarkers = useMemo(() => Array.from({ length: EXPECTED_ACTS }, (_, i) => ({
    act: i + 1,
    position: i / (EXPECTED_ACTS - 1),
  })), [EXPECTED_ACTS]);

  return (
    <motion.div
      className="fixed left-3 md:left-6 top-1/2 -translate-y-1/2 z-40 hidden md:flex flex-col items-center gap-0"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.8, delay: 0.5 }}
    >
      {/* Track */}
      <div className="relative w-[2px] h-48 bg-[var(--ochre)]/15 rounded-full overflow-hidden">
        {/* Fill - hardware accelerated scaling instead of height manipulation */}
        <motion.div
          className="absolute inset-0 bg-[var(--gold)] rounded-full origin-top"
          style={{ scaleY }}
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
