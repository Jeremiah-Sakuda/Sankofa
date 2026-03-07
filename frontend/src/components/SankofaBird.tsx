interface SankofaBirdProps {
  className?: string;
}

export default function SankofaBird({ className = "" }: SankofaBirdProps) {
  return (
    <svg
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Sankofa bird — stylized Adinkra symbol: a bird looking backward with an egg on its back */}
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {/* Body */}
        <path d="M60 95 C40 90, 25 75, 28 55 C30 40, 40 30, 55 28 C65 26, 72 30, 75 38" fill="none" />
        {/* Neck curving backward */}
        <path d="M75 38 C78 30, 82 22, 78 16 C74 10, 66 12, 62 18 C58 24, 60 32, 65 35" fill="none" />
        {/* Head / eye area */}
        <circle cx="70" cy="16" r="3" fill="currentColor" opacity="0.6" />
        {/* Beak pointing backward */}
        <path d="M66 14 L58 10 L64 16" fill="none" />
        {/* Egg on back */}
        <ellipse cx="52" cy="42" rx="8" ry="10" fill="none" strokeWidth="2.5" />
        {/* Tail feathers */}
        <path d="M60 95 C55 100, 48 105, 40 102" fill="none" />
        <path d="M60 95 C58 102, 55 108, 48 108" fill="none" />
        <path d="M60 95 C62 102, 60 110, 55 112" fill="none" />
        {/* Feet */}
        <path d="M45 88 L40 100 M40 100 L35 98 M40 100 L42 103" fill="none" />
        <path d="M55 92 L52 104 M52 104 L47 102 M52 104 L54 107" fill="none" />
        {/* Wing detail */}
        <path d="M35 60 C32 68, 38 78, 48 82" fill="none" opacity="0.5" />
        <path d="M40 55 C37 63, 42 73, 50 76" fill="none" opacity="0.5" />
      </g>
    </svg>
  );
}
