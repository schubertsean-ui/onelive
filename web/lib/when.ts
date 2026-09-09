/** 1Live when: start date and start time are two facts.
 *
 * Date-only strings and UTC-midnight stamps keep the printed calendar day.
 * A real clock uses America/Chicago. Never invent 17:00.
 */

const MARKET_TZ = "America/Chicago";

export function marketDayString(ms: number): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: MARKET_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(ms));
}

export function isDateOnlyStart(iso: string): boolean {
  const raw = iso.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return true;
  return /T00:00(?::00)?(?:\.0+)?(?:Z|[+-]00:00)?$/.test(raw);
}

export function startDate(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const m = iso.trim().match(/^(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2}))?/);
  if (!m) return null;
  const day = m[1];
  if (isDateOnlyStart(iso.trim()) || !m[2]) return day;
  const instant = Date.parse(iso);
  if (Number.isNaN(instant)) return day;
  return marketDayString(instant);
}

export function startTime(iso: string | null | undefined): string | null {
  if (!iso || isDateOnlyStart(iso.trim())) return null;
  const m = iso.trim().match(/T(\d{2}):(\d{2})/);
  if (!m) return null;
  if (m[1] === "00" && m[2] === "00") return null;
  const instant = Date.parse(iso);
  if (Number.isNaN(instant)) return `${m[1]}:${m[2]}`;
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: MARKET_TZ,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(instant));
}
