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

function ScrollIndicator() {
  return (
    <motion.div
      className="absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 cursor-pointer"
      initial={{ opacity: 0 }}
      animate={{ opacity: 0.6 }}
      transition={{ delay: 3, duration: 1 }}
      onClick={() => {
        document.getElementById("the-gap")?.scrollIntoView({ behavior: "smooth" });
      }}
    >
      <span className="font-[family-name:var(--font-body)] text-xs text-[var(--muted)] tracking-wider uppercase">
        Scroll
      </span>
      <motion.div
        animate={{ y: [0, 6, 0] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="text-[var(--gold)]/60"
        >
          <path d="M12 5v14M19 12l-7 7-7-7" />
        </svg>
      </motion.div>
    </motion.div>
  );
}

export default function Home() {
  const [showIntake, setShowIntake] = useState(false);
  const router = useRouter();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const { user, isLoading, isConfigured, signInWithGoogle, signOut } = useAuth();

  return (
    <div className="relative min-h-screen">
      {/* Fixed background */}
      <div className="fixed inset-0 bg-[var(--night)] animate-gradient-drift bg-gradient-to-br from-[var(--night)] via-[var(--indigo)] to-[#1a0f0a]" />
      <div className="fixed inset-0 noise-texture pointer-events-none" />
      <GoldParticles count={showIntake ? 40 : 25} />

      {/* Fixed header with navigation */}
      {!showIntake && (
        <motion.header
          className="fixed top-0 left-0 right-0 z-20 px-6 py-4 flex items-center justify-between"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 2 }}
        >
          <nav className="flex items-center gap-6">
            <Link
              href="/explore"
              className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
            >
              Explore
            </Link>
            <Link
              href="/about"
              className="text-sm text-[var(--muted)] hover:text-[var(--gold)] transition-colors"
            >
              About
            </Link>
          </nav>

          {isConfigured && !isLoading && (
            <div className="flex items-center gap-4">
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
            </div>
          )}
        </motion.header>
      )}

      <AnimatePresence mode="wait">
        {!showIntake ? (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="relative z-10"
          >
            {/* Hero Section */}
            <section className="relative min-h-screen flex flex-col items-center justify-center px-6">
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
                An AI griot that tells your ancestral story — with watercolor imagery,
                voice narration, and honesty about what&apos;s remembered versus imagined.
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

              <ScrollIndicator />
            </section>

            {/* The Gap Section */}
            <section id="the-gap" className="relative min-h-screen flex flex-col items-center justify-center px-6 py-24">
              <motion.div
                className="max-w-2xl text-center"
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.8 }}
              >
                <h2 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--gold)] tracking-wide mb-8">
                  The Gap
                </h2>
                <p className="font-[family-name:var(--font-body)] text-lg md:text-xl text-[var(--ivory)]/90 leading-relaxed mb-6">
                  For millions of people in the African, Caribbean, and South Asian diasporas,
                  heritage exists only as fragments. A family name. A region mentioned once by
                  a grandparent. A tradition no one can fully explain.
                </p>
                <p className="font-[family-name:var(--font-display)] text-xl md:text-2xl text-[var(--gold)]/80 italic">
                  Existing tools give data. Sankofa tells a story.
                </p>
              </motion.div>
            </section>

            {/* How It Works Section */}
            <section className="relative min-h-screen flex flex-col items-center justify-center px-6 py-24">
              <motion.div
                className="max-w-2xl text-center"
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.8 }}
              >
                <h2 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--gold)] tracking-wide mb-8">
                  How It Works
                </h2>
                <p className="font-[family-name:var(--font-body)] text-lg md:text-xl text-[var(--ivory)]/90 leading-relaxed mb-8">
                  You give the griot a few seeds — a surname, a region, an era. The griot
                  returns a multi-act narrative with AI-generated watercolor imagery, voice
                  narration, ambient soundscapes, and trust indicators marking what is
                  documented, what is cultural, and what is imagined.
                </p>

                <div className="flex flex-wrap justify-center gap-4 mb-8">
                  <div className="px-4 py-2 border border-[var(--gold)]/30 rounded">
                    <span className="font-[family-name:var(--font-body)] text-sm text-[var(--gold)]">Historical</span>
                    <p className="text-xs text-[var(--muted)] mt-1">Documented facts</p>
                  </div>
                  <div className="px-4 py-2 border border-[var(--ochre)]/30 rounded">
                    <span className="font-[family-name:var(--font-body)] text-sm text-[var(--ochre)]">Cultural</span>
                    <p className="text-xs text-[var(--muted)] mt-1">Known traditions</p>
                  </div>
                  <div className="px-4 py-2 border border-[var(--terracotta)]/30 rounded">
                    <span className="font-[family-name:var(--font-body)] text-sm text-[var(--terracotta)]">Reconstructed</span>
                    <p className="text-xs text-[var(--muted)] mt-1">Informed imagination</p>
                  </div>
                </div>

                <p className="font-[family-name:var(--font-body)] text-base text-[var(--muted)] leading-relaxed italic">
                  After the story, the griot stays. You can ask follow-up questions
                  about what was left out.
                </p>
              </motion.div>
            </section>

            {/* The Promise Section */}
            <section className="relative min-h-screen flex flex-col items-center justify-center px-6 py-24">
              <motion.div
                className="max-w-2xl text-center"
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.8 }}
              >
                <h2 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--gold)] tracking-wide mb-8">
                  The Promise
                </h2>
                <p className="font-[family-name:var(--font-body)] text-lg md:text-xl text-[var(--ivory)]/90 leading-relaxed mb-6">
                  The griot will never pretend to know what it doesn&apos;t. Every segment
                  is tagged so you know what is remembered versus what is imagined.
                </p>
                <p className="font-[family-name:var(--font-display)] text-xl md:text-2xl text-[var(--gold)]/80 italic mb-12">
                  Heritage deserves honesty, not confidence.
                </p>

                {/* Final CTA */}
                <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                  <motion.button
                    onClick={() => setShowIntake(true)}
                    className="px-10 py-4 border border-[var(--gold)] bg-[var(--gold)] text-[var(--night)] font-[family-name:var(--font-display)] text-lg tracking-[0.1em] uppercase transition-all duration-500 hover:bg-transparent hover:text-[var(--gold)] cursor-pointer"
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    Begin Your Journey
                  </motion.button>
                  <motion.button
                    onClick={() => router.push("/sample")}
                    className="px-8 py-4 flex items-center justify-center gap-2 border border-[var(--ivory)]/30 text-[var(--ivory)]/80 font-[family-name:var(--font-display)] text-base tracking-[0.05em] transition-all duration-300 hover:border-[var(--ivory)]/60 hover:text-[var(--ivory)] cursor-pointer"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="opacity-70">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                    See an Example
                  </motion.button>
                </div>
              </motion.div>

              {/* Proverb */}
              <motion.p
                className="absolute bottom-12 font-[family-name:var(--font-body)] text-xs text-[var(--muted)] italic text-center px-4"
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 0.5 }}
                viewport={{ once: true }}
                transition={{ duration: 1 }}
              >
                &ldquo;Se wo were fi na wosankofa a yenkyi&rdquo; — It is not
                wrong to go back for that which you have forgotten.
              </motion.p>
            </section>
          </motion.div>
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
