interface TrustBadgeProps {
  level: "historical" | "cultural" | "reconstructed";
}

const BADGE_CONFIG = {
  historical: {
    color: "var(--indigo)",
    label: "Historical",
    description: "Based on documented historical facts about this region and era.",
  },
  cultural: {
    color: "var(--ochre)",
    label: "Cultural",
    description: "Based on well-documented cultural practices of this community.",
  },
  reconstructed: {
    color: "var(--terracotta)",
    label: "Imagined",
    description: "An imaginative reconstruction informed by historical and cultural context.",
  },
};

export default function TrustBadge({ level }: TrustBadgeProps) {
  const config = BADGE_CONFIG[level];

  return (
    <div className="absolute -left-4 md:-left-28 top-1 group/badge">
      {/* Desktop: full label */}
      <div
        className="hidden md:flex items-center gap-2 cursor-help"
        style={{ borderLeft: `2px solid ${config.color}` }}
      >
        <span
          className="pl-2 font-[family-name:var(--font-display)] text-[0.65rem] uppercase tracking-[0.1em] opacity-50 group-hover/badge:opacity-100 transition-opacity duration-300"
          style={{ color: config.color }}
        >
          {config.label}
        </span>
      </div>

      {/* Mobile: colored dot */}
      <div className="md:hidden">
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: config.color }}
        />
      </div>

      {/* Tooltip */}
      <div className="absolute left-0 md:-left-2 top-6 w-56 p-3 bg-[var(--night)] text-[var(--ivory)] text-xs font-[family-name:var(--font-body)] leading-relaxed rounded shadow-lg opacity-0 pointer-events-none group-hover/badge:opacity-100 group-hover/badge:pointer-events-auto transition-opacity duration-300 z-20">
        {config.description}
      </div>
    </div>
  );
}
