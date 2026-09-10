import type { LicensedEvent } from "./licensed";
import { marketHour } from "./feed";
import { isDateOnlyStart } from "./when";

export type ClockList = {
  timed: LicensedEvent[];
  undated: LicensedEvent[];
};

function byStart(a: LicensedEvent, b: LicensedEvent): number {
  const ta = a.start_time ? Date.parse(a.start_time) : Infinity;
  const tb = b.start_time ? Date.parse(b.start_time) : Infinity;
  const na = Number.isNaN(ta) ? Infinity : ta;
  const nb = Number.isNaN(tb) ? Infinity : tb;
  return na - nb;
}

function hasPrintedHour(e: LicensedEvent): boolean {
  if (!e.start_time) return false;
  if (isDateOnlyStart(e.start_time)) return false;
  return marketHour(e.start_time) != null;
}

/** One list: earliest printed clock first, latest last, no hour at the bottom. Never drops a row. */
export function byClock(events: LicensedEvent[]): ClockList {
  const timed: LicensedEvent[] = [];
  const undated: LicensedEvent[] = [];
  for (const e of events) {
    if (hasPrintedHour(e)) timed.push(e);
    else undated.push(e);
  }
  return { timed: timed.sort(byStart), undated };
}
