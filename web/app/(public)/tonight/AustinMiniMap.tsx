"use client";

/** Austin outline + river + mark. Mark only when lat/lng are already stored. */
export function AustinMiniMap({
  lat,
  lng,
  href,
}: {
  lat: number;
  lng: number;
  href: string | null;
}) {
  const W = 160;
  const H = 90;
  const x = ((lng - -98.0) / (-97.56 - -98.0)) * W;
  const y = ((30.52 - lat) / (30.52 - 30.12)) * H;
  const cx = Math.max(6, Math.min(W - 6, x));
  const cy = Math.max(6, Math.min(H - 6, y));
  const svg = (
    <svg viewBox={`0 0 ${W} ${H}`} className="minmap" aria-hidden>
      <path
        d="M28 12 L132 10 L148 28 L150 70 L120 82 L40 84 L12 60 L16 24 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <path
        d="M18 48 C50 42, 80 52, 110 40 C130 34, 148 38, 152 36"
        fill="none"
        stroke="#3b82f6"
        strokeWidth="2.5"
      />
      <circle cx={cx} cy={cy} r="4" fill="currentColor" />
    </svg>
  );
  if (href) {
    return (
      <a className="minmapwrap" href={href} target="_blank" rel="noopener noreferrer">
        {svg}
      </a>
    );
  }
  return <div className="minmapwrap">{svg}</div>;
}
