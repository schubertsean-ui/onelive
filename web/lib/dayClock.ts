import type { LicensedEvent } from "./licensed";
import { marketHour, type DayPartSplit } from "./feed";

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

/** Timed evening first, timed earlier second, Date TBA last. Never drops a row. */
export function clockBuckets(split: DayPartSplit): ClockBuckets {
  const timedEve: LicensedEvent[] = [];
  const timedEarly: LicensedEvent[] = [];
  const undated: LicensedEvent[] = [];
  for (const e of split.evening) {
    if (marketHour(e.start_time) == null) undated.push(e);
    else timedEve.push(e);
  }
  for (const e of split.earlier) {
    if (marketHour(e.start_time) == null) undated.push(e);
    else timedEarly.push(e);
  }
  return {
    evening: timedEve.sort(byStart),
    earlier: timedEarly.sort(byStart),
    undated,
  };
}
