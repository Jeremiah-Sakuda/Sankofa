"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "motion/react";
import IntakeFlow from "../components/IntakeFlow";
import SankofaBird from "../components/SankofaBird";
import GoldParticles from "../components/GoldParticles";
import SampleNarrativeButton from "../components/SampleNarrativeButton";
import AuthModal from "../components/AuthModal";
import { useAuth } from "../hooks/useAuth";

export default function Home() {
  const [showIntake, setShowIntake] = useState(false);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const router = useRouter();
  const { user, isLoading, isConfigured, signInWithGoogle, signOut } = useAuth();

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="fixed inset-0 bg-[var(--night)] animate-gradient-drift bg-gradient-to-br from-[var(--night)] via-[var(--indigo)] to-[#1a0f0a]" />
      <div className="fixed inset-0 noise-texture pointer-events-none" />
      <GoldParticles count={showIntake ? 40 : 25} />

      {/* Header with auth */}
      {!showIntake && isConfigured && (
        <motion.header
          className="fixed top-0 right-0 z-20 p-4 flex items-center gap-4"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 2 }}
        >
          {!isLoading && (
            <>
              {user ? (
                <>
                  <Link
                    href="/library"
                    className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
                  >
                    My Library
                  </Link>
                  <div className="flex items-center gap-2">
                    {user.photoURL && (
                      <img
                        src={user.photoURL}
                        alt={user.displayName || "User"}
                        className="w-7 h-7 rounded-full border border-[var(--gold)]/30"
                      />
                    )}
                    <button
                      onClick={signOut}
                      className="text-sm text-[var(--muted)] hover:text-[var(--ivory)] transition-colors cursor-pointer"
                    >
                      Sign out
                    </button>
                  </div>
                </>
              ) : (
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors cursor-pointer"
                >
                  Sign in
                </button>
              )}
            </>
          )}
        </motion.header>
      )}

      <AnimatePresence mode="wait">
        {!showIntake ? (
          <motion.main
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="relative z-10 flex min-h-screen flex-col items-center justify-center px-6"
          >
            {/* Radial glow behind bird */}
            <motion.div
              className="absolute w-64 h-64 md:w-80 md:h-80 rounded-full pointer-events-none"
              style={{
                background: "radial-gradient(circle, rgba(212,168,67,0.08) 0%, transparent 70%)",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -60%)",
              }}
              animate={{ scale: [1, 1.15, 1], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
            />

            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1.2, ease: "easeOut" }}
              className="mb-12 relative"
            >
              <SankofaBird className="w-28 h-28 text-[var(--gold)]" />
            </motion.div>

            <motion.h1
              className="font-[family-name:var(--font-display)] text-5xl md:text-7xl tracking-[0.15em] text-[var(--gold)] uppercase text-center"
              initial={{ opacity: 0, letterSpacing: "0.3em" }}
              animate={{ opacity: 1, letterSpacing: "0.15em" }}
              transition={{ duration: 1.4, delay: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              Sankofa
            </motion.h1>

            <motion.p
              className="mt-6 font-[family-name:var(--font-display)] text-xl md:text-2xl italic text-[var(--ivory)] opacity-80 text-center"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 0.8, y: 0 }}
              transition={{ duration: 0.8, delay: 1 }}
            >
              Go back and get it.
            </motion.p>

            <motion.p
              className="mt-3 font-[family-name:var(--font-body)] text-sm text-[var(--muted)] text-center max-w-md"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8, delay: 1.3 }}
            >
              An AI narrator that weaves your ancestral heritage into an
              immersive, living story — from a few seeds of memory.
            </motion.p>

            <motion.button
              onClick={() => setShowIntake(true)}
              className="mt-14 px-10 py-4 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-lg tracking-[0.1em] uppercase transition-all duration-500 hover:bg-[var(--gold)] hover:text-[var(--night)] hover:shadow-[0_0_40px_rgba(212,168,67,0.3)] cursor-pointer"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 1.6 }}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              Begin Your Journey
            </motion.button>

            <SampleNarrativeButton onClick={() => router.push("/sample")} />

            <motion.p
              className="absolute bottom-8 font-[family-name:var(--font-body)] text-xs text-[var(--muted)] italic text-center px-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              transition={{ delay: 2.5, duration: 1 }}
            >
              &ldquo;Se wo were fi na wosankofa a yenkyi&rdquo; — It is not
              wrong to go back for that which you have forgotten.
            </motion.p>
          </motion.main>
        ) : (
          <motion.div
            key="intake"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="relative z-10"
          >
            <IntakeFlow />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Auth modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        onSignIn={signInWithGoogle}
      />
    </div>
  );
}
