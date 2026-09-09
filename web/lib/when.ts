/** 1Live when: start date + optional start time.
 *
 * Timezone is the locale pack IANA zone (test default: CAPCOG America/Chicago).
 * Date-only and UTC-midnight keep the printed calendar day.
 * Do not invent a minute.
 */

export const TEST_LOCALE_TZ = "America/Chicago";

export function marketDayString(ms: number, timeZone = TEST_LOCALE_TZ): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
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

export function startDate(
  iso: string | null | undefined,
  timeZone = TEST_LOCALE_TZ,
): string | null {
  if (!iso) return null;
  const m = iso.trim().match(/^(\d{4}-\d{2}-\d{2})(?:T(\d{2}):(\d{2}))?/);
  if (!m) return null;
  const day = m[1];
  if (isDateOnlyStart(iso.trim()) || !m[2]) return day;
  const instant = Date.parse(iso);
  if (Number.isNaN(instant)) return day;
  return marketDayString(instant, timeZone);
}

export function startTime(
  iso: string | null | undefined,
  timeZone = TEST_LOCALE_TZ,
): string | null {
  if (!iso || isDateOnlyStart(iso.trim())) return null;
  const m = iso.trim().match(/T(\d{2}):(\d{2})/);
  if (!m) return null;
  if (m[1] === "00" && m[2] === "00") return null;
  const instant = Date.parse(iso);
  if (Number.isNaN(instant)) return `${m[1]}:${m[2]}`;
  return new Intl.DateTimeFormat("en-GB", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(instant));
}
