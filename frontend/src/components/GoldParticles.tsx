"use client";

import { useMemo } from "react";

interface GoldParticlesProps {
  count?: number;
  className?: string;
}

/**
 * Floating gold particles using pure CSS animations.
 * All animations run on the compositor thread (GPU-accelerated via transform/opacity)
 * so they don't block the main thread or cause jank.
 */
export default function GoldParticles({ count = 50, className = "" }: GoldParticlesProps) {
  const particles = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        x: (i * 37 + 13) % 100,
        size: 1 + (i % 3),
        duration: 12 + (i * 7) % 18,
        delay: (i * 1.3) % 10,
        peakOpacity: 0.15 + (i % 5) * 0.06,
        drift: (i % 2 === 0 ? 1 : -1) * ((i * 3) % 20),
      })),
    [count]
  );

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
