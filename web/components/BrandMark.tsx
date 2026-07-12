// OneLive logo: a single live "pulse" — one bar rising among a beat, capped by
// a stage-light dot. Geometric, works small, uses currentColor + amber accent.
export function BrandMark({ size = 26 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      role="img"
      aria-label="OneLive"
    >
      <rect x="3" y="18" width="4" height="8" rx="2" fill="currentColor" opacity="0.55" />
      <rect x="10" y="12" width="4" height="14" rx="2" fill="currentColor" opacity="0.75" />
      <rect x="17" y="6" width="4" height="20" rx="2" fill="#ffb23e" />
      <rect x="24" y="14" width="4" height="12" rx="2" fill="currentColor" opacity="0.55" />
      <circle cx="19" cy="4" r="2.6" fill="#ffb23e" />
    </svg>
  );
}
