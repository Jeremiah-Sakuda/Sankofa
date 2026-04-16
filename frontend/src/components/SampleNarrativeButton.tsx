"use client";

import { motion } from "motion/react";

interface SampleNarrativeButtonProps {
  onClick: () => void;
}

export default function SampleNarrativeButton({ onClick }: SampleNarrativeButtonProps) {
  return (
    <motion.button
      onClick={onClick}
      className="px-6 py-2 text-[var(--muted)] font-[family-name:var(--font-body)] text-sm tracking-wide transition-all duration-300 hover:text-[var(--gold)] cursor-pointer underline underline-offset-4 decoration-[var(--muted)]/30 hover:decoration-[var(--gold)]/50"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay: 2 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      See an example first
    </motion.button>
  );
}
