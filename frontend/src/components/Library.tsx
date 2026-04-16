"use client";

import { motion } from "motion/react";
import Link from "next/link";
import SankofaBird from "./SankofaBird";

export interface NarrativeSummary {
  session_id: string;
  family_name: string;
  region: string;
  era: string;
  created_at: number;
  segment_count: number;
  first_image_data: string | null;
  first_image_type: string | null;
  arc_title: string | null;
}

interface LibraryProps {
  narratives: NarrativeSummary[];
  isLoading: boolean;
  onRefresh: () => void;
}

function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function Library({ narratives, isLoading, onRefresh }: LibraryProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <SankofaBird className="w-12 h-12 text-[var(--gold)] animate-slow-rotate" />
        <p className="mt-4 font-[family-name:var(--font-body)] text-[var(--muted)] text-sm">
          Loading your library...
        </p>
      </div>
    );
  }

  if (narratives.length === 0) {
    return (
      <div className="text-center py-20">
        <SankofaBird className="w-16 h-16 text-[var(--gold)]/40 mx-auto mb-4" />
        <h2 className="font-[family-name:var(--font-display)] text-xl text-[var(--ivory)] mb-2">
          No stories yet
        </h2>
        <p className="font-[family-name:var(--font-body)] text-[var(--muted)] text-sm mb-6">
          Your saved narratives will appear here.
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all"
        >
          Begin Your First Journey
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {narratives.map((narrative, index) => (
        <motion.div
          key={narrative.session_id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: index * 0.1 }}
        >
          <Link
            href={`/narrative/${narrative.session_id}`}
            className="block group"
          >
            <div className="bg-[var(--night)]/50 border border-[var(--gold)]/20 rounded-lg overflow-hidden hover:border-[var(--gold)]/50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(212,168,67,0.1)]">
              {/* Thumbnail */}
              <div className="aspect-video bg-[var(--night)] relative overflow-hidden">
                {narrative.first_image_data ? (
                  <img
                    src={`data:${narrative.first_image_type || "image/png"};base64,${narrative.first_image_data}`}
                    alt={`${narrative.family_name} family narrative`}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <SankofaBird className="w-12 h-12 text-[var(--gold)]/30" />
                  </div>
                )}
                {/* Gradient overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-[var(--night)] via-transparent to-transparent opacity-60" />
              </div>

              {/* Content */}
              <div className="p-4">
                <h3 className="font-[family-name:var(--font-display)] text-lg text-[var(--gold)] mb-1 truncate">
                  {narrative.arc_title || `The ${narrative.family_name} Family`}
                </h3>
                <p className="font-[family-name:var(--font-body)] text-sm text-[var(--ivory)]/80 mb-2">
                  {narrative.region}, {narrative.era}
                </p>
                <div className="flex items-center justify-between text-xs text-[var(--muted)]">
                  <span>{formatDate(narrative.created_at)}</span>
                  <span>{narrative.segment_count} segments</span>
                </div>
              </div>

              {/* Replay button overlay */}
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-black/40">
                <div className="px-4 py-2 bg-[var(--gold)] text-[var(--night)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase rounded">
                  Replay Story
                </div>
              </div>
            </div>
          </Link>
        </motion.div>
      ))}
    </div>
  );
}
