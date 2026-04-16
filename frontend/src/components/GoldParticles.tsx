"use client";

import { useMemo, useEffect, useState } from "react";

interface GoldParticlesProps {
  count?: number;
  className?: string;
}

/**
 * Floating gold particles using pure CSS animations.
 * All animations run on the compositor thread (GPU-accelerated via transform/opacity)
 * so they don't block the main thread or cause jank.
 *
 * Respects prefers-reduced-motion by rendering no particles when enabled.
 */
export default function GoldParticles({ count = 50, className = "" }: GoldParticlesProps) {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    // Check prefers-reduced-motion on mount and listen for changes
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  const particles = useMemo(
    () =>
      // Skip creating particles entirely if reduced motion is preferred
      reducedMotion
        ? []
        : Array.from({ length: count }, (_, i) => ({
            id: i,
            x: (i * 37 + 13) % 100,
            size: 1 + (i % 3),
            duration: 12 + (i * 7) % 18,
            delay: (i * 1.3) % 10,
            peakOpacity: 0.15 + (i % 5) * 0.06,
            drift: (i % 2 === 0 ? 1 : -1) * ((i * 3) % 20),
          })),
    [count, reducedMotion]
  );

  // Don't render anything if reduced motion is preferred
  if (reducedMotion) {
    return null;
  }

  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`} aria-hidden>
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute rounded-full bg-[var(--gold)] particle-float"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.x}%`,
            bottom: "-5%",
            "--p-drift": `${p.drift}px`,
            "--p-peak-opacity": p.peakOpacity,
            animationDuration: `${p.duration}s`,
            animationDelay: `${p.delay}s`,
            willChange: "transform, opacity",
          } as React.CSSProperties}
        />
      ))}
    </div>
  );
}
