"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import type { ResearchBundle, ResearchFact } from "../hooks/useSSEStream";

const CATEGORY_ICONS: Record<ResearchFact["category"], React.ReactNode> = {
  geography: (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  ),
  culture: (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </svg>
  ),
  history: (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  ),
  diaspora: (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  daily_life: (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
};

const CATEGORY_LABELS: Record<ResearchFact["category"], string> = {
  geography: "Geography",
  culture: "Culture",
  history: "History",
  diaspora: "Diaspora",
  daily_life: "Daily Life",
};

interface ResearchCardProps {
  bundle: ResearchBundle;
}

export default function ResearchCard({ bundle }: ResearchCardProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const facts = bundle.facts;

  // Rotate through facts every 6 seconds in collapsed mode
  useEffect(() => {
    if (isExpanded || facts.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % facts.length);
    }, 6000);
    return () => clearInterval(interval);
  }, [isExpanded, facts.length]);

  const toggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  if (facts.length === 0) return null;

  const currentFact = facts[currentIndex];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="mt-8 w-full max-w-md"
    >
      <button
        type="button"
        onClick={toggleExpand}
        className="w-full text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--gold)]/50 rounded-lg"
      >
        <div className="border border-[var(--gold)]/20 rounded-lg bg-[var(--night)]/50 backdrop-blur-sm p-4 hover:border-[var(--gold)]/40 transition-colors">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <span className="font-[family-name:var(--font-body)] text-[10px] text-[var(--gold)]/60 uppercase tracking-[0.2em]">
              About {bundle.region}
            </span>
            <motion.svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-[var(--gold)]/40"
              animate={{ rotate: isExpanded ? 180 : 0 }}
              transition={{ duration: 0.3 }}
            >
              <polyline points="6 9 12 15 18 9" />
            </motion.svg>
          </div>

          <AnimatePresence mode="wait">
            {isExpanded ? (
              // Expanded view: show all facts grouped by category
              <motion.div
                key="expanded"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-3"
              >
                {facts.map((fact, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.05 }}
                    className="flex gap-3"
                  >
                    <div className="flex-shrink-0 mt-1 text-[var(--gold)]/50">
                      {CATEGORY_ICONS[fact.category]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-[family-name:var(--font-body)] text-sm text-[var(--ivory)]/80 leading-relaxed">
                        {fact.fact}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="font-[family-name:var(--font-body)] text-[9px] text-[var(--muted)]/60 uppercase">
                          {CATEGORY_LABELS[fact.category]}
                        </span>
                        {fact.confidence === "grounded_search" && (
                          <span className="px-1.5 py-0.5 text-[8px] uppercase tracking-wider bg-[var(--gold)]/10 text-[var(--gold)]/70 rounded">
                            Web
                          </span>
                        )}
                        {fact.source && (
                          <a
                            href={fact.source}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[8px] text-[var(--gold)]/50 hover:text-[var(--gold)] transition-colors underline"
                          >
                            Source
                          </a>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            ) : (
              // Collapsed view: single rotating fact
              <motion.div
                key={`collapsed-${currentIndex}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.4 }}
              >
                <div className="flex gap-3">
                  <div className="flex-shrink-0 mt-0.5 text-[var(--gold)]/50">
                    {CATEGORY_ICONS[currentFact.category]}
                  </div>
                  <p className="font-[family-name:var(--font-body)] text-sm text-[var(--ivory)]/80 leading-relaxed">
                    {currentFact.fact}
                  </p>
                </div>
                {/* Progress dots */}
                {facts.length > 1 && (
                  <div className="flex justify-center gap-1.5 mt-3">
                    {facts.map((_, i) => (
                      <div
                        key={i}
                        className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
                          i === currentIndex
                            ? "bg-[var(--gold)]/70"
                            : "bg-[var(--gold)]/20"
                        }`}
                      />
                    ))}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </button>
    </motion.div>
  );
}
