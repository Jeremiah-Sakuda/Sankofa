"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import Link from "next/link";
import Library, { NarrativeSummary } from "../../components/Library";
import SankofaBird from "../../components/SankofaBird";
import GoldParticles from "../../components/GoldParticles";
import { useAuth } from "../../hooks/useAuth";
import { API_BASE } from "../../lib/api";

export default function LibraryPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, signOut } = useAuth();
  const [narratives, setNarratives] = useState<NarrativeSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push("/");
      return;
    }

    // Fetch user's narratives
    const fetchNarratives = async () => {
      try {
        const token = await user.getIdToken();
        const res = await fetch(`${API_BASE}/api/narratives`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          setNarratives(data.narratives || []);
        }
      } catch (e) {
        console.error("Failed to fetch narratives:", e);
      } finally {
        setIsLoading(false);
      }
    };

    fetchNarratives();
  }, [user, authLoading, router]);

  const handleRefresh = async () => {
    if (!user) return;
    setIsLoading(true);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${API_BASE}/api/narratives`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setNarratives(data.narratives || []);
      }
    } catch (e) {
      console.error("Failed to refresh narratives:", e);
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[var(--night)] flex items-center justify-center">
        <SankofaBird className="w-12 h-12 text-[var(--gold)] animate-slow-rotate" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen relative">
      {/* Background */}
      <div className="fixed inset-0 bg-[var(--night)] animate-gradient-drift bg-gradient-to-br from-[var(--night)] via-[var(--indigo)] to-[#1a0f0a]" />
      <div className="fixed inset-0 noise-texture pointer-events-none" />
      <GoldParticles count={15} />

      {/* Content */}
      <div className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        {/* Header */}
        <header className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-3 group">
              <SankofaBird className="w-8 h-8 text-[var(--gold)]" />
              <span className="font-[family-name:var(--font-display)] text-xl text-[var(--gold)] tracking-wider hidden sm:inline group-hover:tracking-[0.2em] transition-all">
                Sankofa
              </span>
            </Link>
            <span className="text-[var(--muted)]/40">|</span>
            <h1 className="font-[family-name:var(--font-display)] text-lg text-[var(--ivory)] tracking-wide">
              My Library
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="px-4 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all hidden sm:block"
            >
              New Story
            </Link>
            <div className="flex items-center gap-3">
              {user.photoURL && (
                <img
                  src={user.photoURL}
                  alt={user.displayName || "User"}
                  className="w-8 h-8 rounded-full border border-[var(--gold)]/30"
                />
              )}
              <button
                onClick={signOut}
                className="text-sm text-[var(--muted)] hover:text-[var(--ivory)] transition-colors cursor-pointer"
              >
                Sign out
              </button>
            </div>
          </div>
        </header>

        {/* Library content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Library
            narratives={narratives}
            isLoading={isLoading}
            onRefresh={handleRefresh}
          />
        </motion.div>
      </div>
    </div>
  );
}
