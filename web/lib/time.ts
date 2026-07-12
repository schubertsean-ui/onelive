// Time formatting for the public feed. All functions are null-safe and never
// throw on malformed input — a bad timestamp degrades to a readable fallback,
// it does not crash the feed.

export function parseIso(raw: string | null | undefined): Date | null {
  if (!raw) return null;
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? null : d;
}

// e.g. "8:30 PM" (local time). Fallback: "Time TBA".
export function formatTime(raw: string | null | undefined, locale?: string): string {
  const d = parseIso(raw);
  if (!d) return "Time TBA";
  try {
    return d.toLocaleTimeString(locale, { hour: "numeric", minute: "2-digit" });
  } catch {
    return "Time TBA";
  }
}

// e.g. "Tonight" if same calendar day as `now`, else "Sat, Jul 11".
export function formatDayLabel(
  raw: string | null | undefined,
  now: Date = new Date(),
  locale?: string
): string {
  const d = parseIso(raw);
  if (!d) return "Date TBA";
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  if (sameDay) return "Tonight";
  try {
    return d.toLocaleDateString(locale, { weekday: "short", month: "short", day: "numeric" });
  } catch {
    return "Date TBA";
  }
}
