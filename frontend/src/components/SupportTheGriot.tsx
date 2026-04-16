"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { createContributionCheckout, trackContributionEvent } from "../lib/api";
import SankofaBird from "./SankofaBird";

interface SupportTheGriotProps {
  sessionId: string;
  region?: string;
  contributed: boolean;
  onDismiss: () => void;
}

interface AmountOption {
  cents: number;
  label: string;
  description: string;
}

const AMOUNT_OPTIONS: AmountOption[] = [
  { cents: 500, label: "$5", description: "A seed" },
  { cents: 1000, label: "$10", description: "A story" },
  { cents: 2500, label: "$25", description: "A legacy" },
];

export default function SupportTheGriot({
  sessionId,
  region,
  contributed,
  onDismiss,
}: SupportTheGriotProps) {
  const [selectedAmount, setSelectedAmount] = useState<number | null>(null);
  const [customAmount, setCustomAmount] = useState("");
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCustomInput, setShowCustomInput] = useState(false);

  // Track card shown on mount
  useEffect(() => {
    if (!contributed) {
      trackContributionEvent("tip_card_shown", sessionId);
    }
  }, [sessionId, contributed]);

  const handleAmountSelect = async (cents: number) => {
    setSelectedAmount(cents);
    setError(null);
    trackContributionEvent("tip_amount_selected", sessionId, cents);
    await handleCheckout(cents);
  };

  const handleCustomAmountSubmit = async () => {
    const dollars = parseFloat(customAmount);
    if (isNaN(dollars) || dollars < 1 || dollars > 500) {
      setError("Please enter an amount between $1 and $500");
      return;
    }
    const cents = Math.round(dollars * 100);
    setSelectedAmount(cents);
    setError(null);
    trackContributionEvent("tip_amount_selected", sessionId, cents);
    await handleCheckout(cents);
  };

  const handleCheckout = async (cents: number) => {
    setIsRedirecting(true);
    setError(null);

    try {
      const { checkout_url } = await createContributionCheckout(sessionId, cents);
      // Redirect to Stripe
      window.location.href = checkout_url;
    } catch (e) {
      setIsRedirecting(false);
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    }
  };

  const handleDismiss = () => {
    trackContributionEvent("tip_card_dismissed", sessionId);
    onDismiss();
  };

  // Thank you state after contribution
  if (contributed) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="my-12 mx-auto max-w-md"
      >
        <div className="relative rounded-xl overflow-hidden">
          {/* Warm gradient background */}
          <div className="absolute inset-0 bg-gradient-to-br from-[var(--gold)]/10 via-[var(--ochre)]/5 to-[var(--terracotta)]/10" />
          <div className="absolute inset-0 border border-[var(--gold)]/30 rounded-xl" />

          <div className="relative p-8 text-center">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.5, type: "spring", stiffness: 200 }}
              className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--gold)]/20 flex items-center justify-center"
            >
              <SankofaBird className="w-8 h-8 text-[var(--gold)]" />
            </motion.div>

            <h3 className="font-[family-name:var(--font-display)] text-xl text-[var(--umber)] mb-2">
              Thank you, kindred spirit
            </h3>
            <p className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] leading-relaxed">
              Your contribution helps preserve the stories that connect us to our ancestors.
              The griot honors your generosity.
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.5 }}
      className="my-12 mx-auto max-w-lg"
    >
      <div className="relative rounded-xl overflow-hidden">
        {/* Warm gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[var(--gold)]/8 via-[var(--ochre)]/5 to-[var(--terracotta)]/8" />
        <div className="absolute inset-0 border border-[var(--gold)]/30 rounded-xl" />

        <div className="relative p-6 md:p-8">
          {/* Header */}
          <div className="text-center mb-6">
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="inline-flex items-center gap-2 mb-3"
            >
              <SankofaBird className="w-5 h-5 text-[var(--gold)] opacity-70" />
              <span className="font-[family-name:var(--font-display)] text-xs tracking-[0.2em] text-[var(--gold)]/70 uppercase">
                Support the Griot
              </span>
              <SankofaBird className="w-5 h-5 text-[var(--gold)] opacity-70 transform scale-x-[-1]" />
            </motion.div>

            <h3 className="font-[family-name:var(--font-display)] text-lg md:text-xl text-[var(--umber)] mb-2">
              Help preserve ancestral stories
            </h3>
            <p className="font-[family-name:var(--font-body)] text-sm text-[var(--muted)] leading-relaxed max-w-sm mx-auto">
              Your contribution helps keep the griot&apos;s fire burning, preserving and sharing
              the narratives that connect us to our heritage.
            </p>
          </div>

          {/* Amount buttons */}
          <div className="flex flex-wrap justify-center gap-3 mb-6">
            {AMOUNT_OPTIONS.map((option, i) => (
              <motion.button
                key={option.cents}
                onClick={() => handleAmountSelect(option.cents)}
                disabled={isRedirecting}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.8 + i * 0.1 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`
                  relative px-5 py-3 rounded-lg border-2 transition-all cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${selectedAmount === option.cents
                    ? "border-[var(--gold)] bg-[var(--gold)]/10"
                    : "border-[var(--gold)]/40 hover:border-[var(--gold)] hover:bg-[var(--gold)]/5"
                  }
                `}
              >
                <span className="font-[family-name:var(--font-display)] text-lg text-[var(--umber)] block">
                  {option.label}
                </span>
                <span className="font-[family-name:var(--font-body)] text-xs text-[var(--muted)]">
                  {option.description}
                </span>
              </motion.button>
            ))}
          </div>

          {/* Custom amount toggle/input */}
          <AnimatePresence mode="wait">
            {!showCustomInput ? (
              <motion.div
                key="toggle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-center mb-4"
              >
                <button
                  onClick={() => setShowCustomInput(true)}
                  disabled={isRedirecting}
                  className="font-[family-name:var(--font-body)] text-sm text-[var(--gold)]/70 hover:text-[var(--gold)] transition-colors cursor-pointer underline underline-offset-2"
                >
                  Enter a custom amount
                </button>
              </motion.div>
            ) : (
              <motion.div
                key="input"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4"
              >
                <div className="flex items-center justify-center gap-3 max-w-xs mx-auto">
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]">$</span>
                    <input
                      type="number"
                      min="1"
                      max="500"
                      step="1"
                      value={customAmount}
                      onChange={(e) => {
                        setCustomAmount(e.target.value);
                        setError(null);
                      }}
                      onKeyDown={(e) => e.key === "Enter" && handleCustomAmountSubmit()}
                      placeholder="1-500"
                      disabled={isRedirecting}
                      className="w-full pl-7 pr-3 py-2 bg-transparent border-b-2 border-[var(--ochre)]/40 text-[var(--umber)] font-[family-name:var(--font-body)] transition-colors focus:border-[var(--gold)] caret-[var(--gold)] disabled:opacity-50"
                    />
                  </div>
                  <button
                    onClick={handleCustomAmountSubmit}
                    disabled={isRedirecting || !customAmount}
                    className="px-4 py-2 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-sm tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Go
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error message */}
          {error && (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center font-[family-name:var(--font-body)] text-sm text-[var(--terracotta)] mb-4"
              role="alert"
            >
              {error}
            </motion.p>
          )}

          {/* Loading indicator */}
          {isRedirecting && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center mb-4"
            >
              <div className="inline-flex items-center gap-2 text-[var(--gold)]">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <SankofaBird className="w-4 h-4" />
                </motion.div>
                <span className="font-[family-name:var(--font-body)] text-sm">
                  Preparing secure checkout...
                </span>
              </div>
            </motion.div>
          )}

          {/* Dismiss link */}
          <div className="text-center">
            <button
              onClick={handleDismiss}
              disabled={isRedirecting}
              className="font-[family-name:var(--font-body)] text-xs text-[var(--muted)] hover:text-[var(--umber)] transition-colors cursor-pointer disabled:opacity-50"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
