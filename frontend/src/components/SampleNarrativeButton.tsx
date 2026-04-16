"use client";

import { motion } from "motion/react";

interface SampleNarrativeButtonProps {
  onClick: () => void;
}

export default function SampleNarrativeButton({ onClick }: SampleNarrativeButtonProps) {
  return (
    <motion.button
      onClick={onClick}
      className="mt-5 px-8 py-3 flex items-center justify-center gap-2 border border-[var(--ivory)]/30 text-[var(--ivory)]/80 font-[family-name:var(--font-display)] text-base tracking-[0.05em] transition-all duration-300 hover:border-[var(--ivory)]/60 hover:text-[var(--ivory)] hover:bg-[var(--ivory)]/5 cursor-pointer"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 1.9 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="currentColor"
        className="opacity-70"
      >
        <path d="M8 5v14l11-7z" />
      </svg>
      See an Example
    </motion.button>
  );
}
