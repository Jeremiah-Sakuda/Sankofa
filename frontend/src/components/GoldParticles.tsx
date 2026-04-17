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
 * Uses fixed positioning so particles are always visible regardless of scroll.
 * Particles are distributed across the full viewport height so some are
 * immediately visible at the top of the page.
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
        : Array.from({ length: count }, (_, i) => {
            // Distribute initial positions across viewport height
            // Some start below (-5%), some start within viewport (0-100%)
            // This ensures particles are visible immediately at the top
            const startPosition = i % 4 === 0
              ? (i * 17) % 80 + 10  // 25% of particles start within viewport (10-90%)
              : -5;                  // 75% start below viewport (traditional behavior)

            return {
              id: i,
              x: (i * 37 + 13) % 100,
              size: 1 + (i % 3),
              duration: 12 + (i * 7) % 18,
              delay: startPosition > 0 ? 0 : (i * 1.3) % 10, // No delay for visible particles
              peakOpacity: 0.15 + (i % 5) * 0.06,
              drift: (i % 2 === 0 ? 1 : -1) * ((i * 3) % 20),
              startPosition,
            };
          }),
    [count, reducedMotion]
  );

  // Don't render anything if reduced motion is preferred
  if (reducedMotion) {
    return null;
  }

  return (
    <div className={`fixed inset-0 overflow-hidden pointer-events-none ${className}`} aria-hidden>
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute rounded-full bg-[var(--gold)] particle-float"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.x}%`,
            bottom: `${p.startPosition}%`,
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
