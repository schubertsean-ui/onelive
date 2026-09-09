/** 1Live when: two facts, one happening.
 *  start date = the calendar day they printed (enough to list).
 *  start time = the clock they printed (optional).
 *  Never invent 17:00. Never treat YYYY-MM-DD as UTC midnight.
 */

const MARKET_TZ = "America/Chicago";

export function isDateOnly(raw: string | null | undefined): boolean {
  return typeof raw === "string" && /^\d{4}-\d{2}-\d{2}$/.test(raw.trim());
}

export function chicagoYmd(ms: number): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: MARKET_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(ms));
}

/** Date-only start lives the whole market day. Missing end is not "over in 3 hours." */
export function dateOnlyTiming(
  raw: string,
  nowMs: number,
): "upcoming" | "on-now" | "ended" {
  const day = raw.trim();
  const today = chicagoYmd(nowMs);
  if (day < today) return "ended";
  if (day > today) return "upcoming";
  return "on-now";
}

export function dateOnlyOnChicagoDay(raw: string, dayStartMs: number, dayEndMs: number): boolean {
  const day = raw.trim();
  const tabDay = chicagoYmd(dayStartMs);
  // endMs is next midnight; still the same printed day if we use start.
  void dayEndMs;
  return day === tabDay;
}
