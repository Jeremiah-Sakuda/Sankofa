"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useRouter } from "next/navigation";
import { createSession, UserInput } from "../lib/api";
import SankofaBird from "./SankofaBird";

const STEPS = [
  {
    key: "family_name",
    question: "What is your family name?",
    placeholder: "Okonkwo, Baptiste, Chen…",
    required: true,
  },
  {
    key: "region_of_origin",
    question: "Where did your ancestors come from?",
    placeholder: "Ghana, coastal West Africa, Fujian province…",
    required: true,
  },
  {
    key: "time_period",
    question: "What era are you drawn to?",
    placeholder: "My grandmother's era, the 1940s, pre-independence…",
    required: true,
  },
  {
    key: "known_fragments",
    question: "Do you know any fragments of the story?",
    placeholder: "She was a trader… they came from the coast… (or press Enter to skip)",
    required: false,
  },
  {
    key: "specific_interests",
    question: "What would you most like to explore?",
    placeholder: "Daily life, music and art, the journey to America… (or press Enter to skip)",
    required: false,
  },
] as const;

type StepKey = (typeof STEPS)[number]["key"];

export default function IntakeFlow() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [inputValue, setInputValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const step = STEPS[currentStep];
  const progress = (currentStep + 1) / STEPS.length;

  const handleNext = async () => {
    const val = inputValue.trim();

    if (step.required && !val) {
      setError("This field is required to weave your narrative.");
      return;
    }

    const newAnswers = { ...answers, [step.key]: val };
    setAnswers(newAnswers);
    setInputValue("");
    setError("");

    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      setIsSubmitting(true);
      try {
        const userInput: UserInput = {
          family_name: newAnswers.family_name || "",
          region_of_origin: newAnswers.region_of_origin || "",
          time_period: newAnswers.time_period || "",
          known_fragments: newAnswers.known_fragments || undefined,
          specific_interests: newAnswers.specific_interests || undefined,
        };
        const { session_id } = await createSession(userInput);
        router.push(`/narrative/${session_id}`);
      } catch (e) {
        setError("Failed to begin your journey. Please try again.");
        setIsSubmitting(false);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleNext();
    }
  };

  if (isSubmitting) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-6">
        <SankofaBird className="w-20 h-20 text-[var(--gold)] animate-slow-rotate" />
        <p className="mt-8 font-[family-name:var(--font-display)] text-xl italic text-[var(--ivory)] animate-fade-pulse">
          Preparing your narrative…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      {/* Progress bar */}
      <div className="fixed top-0 left-0 right-0 h-[2px] bg-[var(--umber)] z-50">
        <motion.div
          className="h-full bg-[var(--gold)]"
          initial={{ scaleX: 0 }}
          animate={{ scaleX: progress }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{ transformOrigin: "left" }}
        />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -30 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center w-full max-w-2xl"
        >
          <p className="text-[var(--muted)] text-sm font-[family-name:var(--font-body)] mb-4 tracking-wider uppercase">
            {currentStep + 1} of {STEPS.length}
          </p>

          <h2 className="font-[family-name:var(--font-display)] text-3xl md:text-4xl text-[var(--ivory)] text-center leading-snug mb-12">
            {step.question}
          </h2>

          <input
            type="text"
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              setError("");
            }}
            onKeyDown={handleKeyDown}
            placeholder={step.placeholder}
            autoFocus
            className="w-full max-w-lg bg-transparent border-b-2 border-[var(--ochre)] text-[var(--ivory)] font-[family-name:var(--font-body)] text-xl md:text-2xl text-center pb-3 transition-colors focus:border-[var(--gold)] caret-[var(--gold)]"
          />

          {error && (
            <motion.p
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 text-[var(--terracotta)] text-sm font-[family-name:var(--font-body)]"
            >
              {error}
            </motion.p>
          )}

          <motion.button
            onClick={handleNext}
            className="mt-10 px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] text-base tracking-[0.08em] uppercase transition-all duration-400 hover:bg-[var(--gold)] hover:text-[var(--night)] cursor-pointer"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {currentStep < STEPS.length - 1
              ? "Continue"
              : "Weave My Narrative"}
          </motion.button>

          {!step.required && (
            <button
              onClick={() => {
                setInputValue("");
                handleNext();
              }}
              className="mt-4 text-[var(--muted)] text-sm font-[family-name:var(--font-body)] hover:text-[var(--ivory)] transition-colors cursor-pointer"
            >
              Skip this step
            </button>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
