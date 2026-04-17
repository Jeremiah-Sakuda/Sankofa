"use client";

import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[Sankofa Error]", error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--night)] px-6">
      <h1 className="font-[family-name:var(--font-display)] text-2xl text-[var(--gold)] tracking-wider uppercase">
        Something went wrong
      </h1>
      <p className="mt-4 font-[family-name:var(--font-body)] text-[var(--muted)] text-center max-w-md">
        Sankofa encountered an unexpected error. Please try again.
      </p>
      {/* Error details logged to console, not exposed to users */}
      <div className="flex gap-4 mt-8">
        <button
          type="button"
          onClick={reset}
          className="px-8 py-3 border border-[var(--gold)] text-[var(--gold)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:bg-[var(--gold)] hover:text-[var(--night)] transition-all cursor-pointer"
        >
          Try Again
        </button>
        <a
          href="/"
          className="px-8 py-3 border border-[var(--muted)]/40 text-[var(--muted)] font-[family-name:var(--font-display)] tracking-wider uppercase hover:border-[var(--ivory)] hover:text-[var(--ivory)] transition-all"
        >
          Start Over
        </a>
      </div>
    </div>
  );
}
