"use client";

import { useMemo } from "react";
import { motion } from "motion/react";

interface GoldParticlesProps {
  count?: number;
  className?: string;
}

export default function GoldParticles({ count = 30, className = "" }: GoldParticlesProps) {
  const particles = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        id: i,
        x: (i * 37 + 13) % 100,
        startY: 80 + (i * 17) % 30,
        endY: -10 - (i * 11) % 20,
        size: 1 + (i % 3),
        duration: 12 + (i * 7) % 18,
        delay: (i * 1.3) % 8,
        opacity: 0.15 + (i % 5) * 0.06,
        drift: ((i % 2 === 0 ? 1 : -1) * ((i * 3) % 20)),
      })),
    [count]
  );

  return (
    <div className={`absolute inset-0 overflow-hidden pointer-events-none ${className}`} aria-hidden>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          className="absolute rounded-full bg-[var(--gold)]"
          style={{
            width: p.size,
            height: p.size,
            left: `${p.x}%`,
          }}
          animate={{
            y: [`${p.startY}vh`, `${p.endY}vh`],
            x: [0, p.drift, 0],
            opacity: [0, p.opacity, p.opacity, 0],
          }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      ))}
    </div>
  );
}
