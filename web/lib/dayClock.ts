import type { LicensedEvent } from "./licensed";
import { marketHour, type DayPartSplit } from "./feed";
import { isDateOnlyStart } from "./when";

export type ClockBuckets = {
  evening: LicensedEvent[];
  earlier: LicensedEvent[];
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

/** Timed evening first, timed earlier second, date-only in evening after timed, Date TBA last. Never drops a row. */
export function clockBuckets(split: DayPartSplit): ClockBuckets {
  const timedEve: LicensedEvent[] = [];
  const datedEve: LicensedEvent[] = [];
  const timedEarly: LicensedEvent[] = [];
  const undated: LicensedEvent[] = [];
  for (const e of split.evening) {
    if (!e.start_time) undated.push(e);
    else if (hasPrintedHour(e)) timedEve.push(e);
    else datedEve.push(e);
  }
  for (const e of split.earlier) {
    if (!e.start_time) undated.push(e);
    else if (hasPrintedHour(e)) timedEarly.push(e);
    else datedEve.push(e);
  }
  return {
    evening: [...timedEve.sort(byStart), ...datedEve.sort(byStart)],
    earlier: timedEarly.sort(byStart),
    undated,
  };
}
