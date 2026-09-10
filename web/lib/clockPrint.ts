// Printed when. Date-only stays a date. Never invent 7:00 PM from midnight.

import { isDateOnlyStart, startDate, startTime } from "./when";

function dayLabel(ymd: string): string {
  const [y, m, d] = ymd.split("-").map(Number);
  if (!y || !m || !d) return ymd;
  return new Date(Date.UTC(y, m - 1, d, 12)).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function hourLabel(hhmm: string): string {
  const [h, min] = hhmm.split(":").map(Number);
  if (!Number.isFinite(h) || !Number.isFinite(min)) return hhmm;
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return min === 0 ? `${h12} ${ampm}` : `${h12}:${String(min).padStart(2, "0")} ${ampm}`;
}

/** Card clock. Date TBA when nothing printed. No invented hour. */
export function printWhen(iso: string | null | undefined): string {
  if (!iso || !iso.trim()) return "Date TBA";
  const day = startDate(iso);
  if (!day) return "Date TBA";
  const label = dayLabel(day);
  if (isDateOnlyStart(iso)) return label;
  const t = startTime(iso);
  if (!t) return label;
  return `${label}, ${hourLabel(t)}`;
}
