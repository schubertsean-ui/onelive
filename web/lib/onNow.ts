// Founder 2026-09-10: hedge when no end is printed.
// Not a stored length. Not 2h/3h.

import type { LicensedEvent } from "./licensed";
import { isDateOnlyStart } from "./when";

export const JUST_STARTED_MS = 60 * 60 * 1000;

/** Badge only. Does not hide the row. */
export function showOnNow(e: LicensedEvent, nowMs: number): boolean {
  if (!e.start_time) return false;
  if (isDateOnlyStart(e.start_time)) return false;
  const start = Date.parse(e.start_time);
  if (!Number.isFinite(start) || start > nowMs) return false;
  if (e.end_time) {
    const end = Date.parse(e.end_time);
    return Number.isFinite(end) && end > nowMs;
  }
  return nowMs - start <= JUST_STARTED_MS;
}
