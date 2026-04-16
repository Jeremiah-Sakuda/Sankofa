"use client";

import { motion } from "motion/react";
import SankofaBird from "./SankofaBird";

interface DiscoveryPromptsProps {
  familyName?: string;
  region?: string;
  era?: string;
  onExploreEra: () => void;
  onExploreCulture: () => void;
  onTraceMigration: () => void;
  onShare: () => void;
}

interface PromptCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  onClick: () => void;
  delay: number;
}

function PromptCard({ icon, title, description, onClick, delay }: PromptCardProps) {
  return (
    <motion.button
      onClick={onClick}
      className="group relative bg-[var(--ivory)]/5 border border-[var(--ochre)]/30 rounded-lg p-5 text-left transition-all hover:border-[var(--gold)]/60 hover:bg-[var(--gold)]/5 cursor-pointer"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[var(--gold)]/10 flex items-center justify-center text-[var(--gold)] group-hover:bg-[var(--gold)]/20 transition-colors">
          {icon}
        </div>
        <div>
          <h4 className="font-[family-name:var(--font-display)] text-base text-[var(--umber)] mb-1 group-hover:text-[var(--gold)] transition-colors">
            {title}
          </h4>
          <p className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] leading-relaxed">
            {description}
          </p>
        </div>
      </div>
      {/* Hover arrow */}
      <motion.div
        className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--gold)] opacity-0 group-hover:opacity-100 transition-opacity"
        initial={{ x: -5 }}
        whileHover={{ x: 0 }}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </motion.div>
    </motion.button>
  );
}

export default function DiscoveryPrompts({
  familyName,
  region,
  era,
  onExploreEra,
  onExploreCulture,
  onTraceMigration,
  onShare,
}: DiscoveryPromptsProps) {
  return (
    <motion.div
      className="mt-12 mb-8"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6 }}
    >
      {/* Decorative header */}
      <div className="flex items-center justify-center gap-4 mb-8">
        <motion.div
          className="h-px flex-1 max-w-[100px] bg-gradient-to-r from-transparent to-[var(--ochre)]/30"
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
          <SankofaBird className="w-6 h-6 text-[var(--gold)] opacity-60" />
        </motion.div>
        <motion.div
          className="h-px flex-1 max-w-[100px] bg-gradient-to-l from-transparent to-[var(--ochre)]/30"
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          style={{ transformOrigin: "left" }}
        />
      </div>

      <motion.h3
        className="text-center font-[family-name:var(--font-display)] text-xl italic text-[var(--umber)] mb-8"
        initial={{ opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        Continue the journey&hellip;
      </motion.h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto">
        <PromptCard
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          }
          title="Explore an earlier era"
          description={`What was life like for the ${familyName || "family"} before ${era || "this time"}?`}
          onClick={onExploreEra}
          delay={0.3}
        />

        <PromptCard
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z" />
              <path d="M12 2v2" />
              <path d="M12 20v2" />
              <path d="m4.93 4.93 1.41 1.41" />
              <path d="m17.66 17.66 1.41 1.41" />
              <path d="M2 12h2" />
              <path d="M20 12h2" />
              <path d="m6.34 17.66-1.41 1.41" />
              <path d="m19.07 4.93-1.41 1.41" />
            </svg>
          }
          title="What was the music of this region?"
          description={`Discover the rhythms, instruments, and songs of ${region || "the homeland"}.`}
          onClick={onExploreCulture}
          delay={0.4}
        />

        <PromptCard
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
          }
          title="Trace the migration"
          description="Follow the paths your ancestors may have traveled across generations."
          onClick={onTraceMigration}
          delay={0.5}
        />

        <PromptCard
          icon={
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
              <polyline points="16 6 12 2 8 6" />
              <line x1="12" y1="2" x2="12" y2="15" />
            </svg>
          }
          title="Share with family"
          description="Send this story to loved ones and discover your heritage together."
          onClick={onShare}
          delay={0.6}
        />
      </div>
    </motion.div>
  );
}
