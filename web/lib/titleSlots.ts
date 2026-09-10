// Print-only parse of leftover title text. Never invent an hour or a length.
// Yearless month+day = upcoming night (founder 2026-09-08). No dateparser.

import type { LicensedEvent } from "./licensed";
import { printablePlace } from "./cardSlots";
import { marketDayString } from "./when";

const TZ = "America/Chicago";

const MONTH: Record<string, number> = {
  jan: 1, january: 1, feb: 2, february: 2, mar: 3, march: 3,
  apr: 4, april: 4, may: 5, jun: 6, june: 6, jul: 7, july: 7,
  aug: 8, august: 8, sep: 9, sept: 9, september: 9,
  oct: 10, october: 10, nov: 11, november: 11, dec: 12, december: 12,
};

const FAKE_PLACE = new Set(["unknown venue", "venue", "unknown", "tbd", "n/a", "na"]);

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** Yearless month+day → YYYY-MM-DD. Upcoming night. Last 14 days stay this year. */
export function upcomingYmd(month: number, day: number, nowMs: number): string | null {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  const today = marketDayString(nowMs, TZ);
  const y = Number(today.slice(0, 4));
  const thisYear = `${y}-${pad(month)}-${pad(day)}`;
  if (thisYear >= today) return thisYear;
  const thisNoon = Date.parse(`${thisYear}T12:00:00-05:00`);
  if (Number.isFinite(thisNoon) && (nowMs - thisNoon) / 86_400_000 <= 14) return thisYear;
  return `${y + 1}-${pad(month)}-${pad(day)}`;
}

const MD_SLASH = /(?:^[\s@])(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?(?=\s*$|[\s,)])/;
const MD_SLASH_ANY = /(?:^|[\s@])(\d{1,2})\/(\d{1,2})(?:\/(\d{2,4}))?(?=\s*$|[\s,)])/;
const MD_NAME = /\b(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)?[a-z.]*\s*(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b/i;

/** Printed calendar day in the title. Date-only. No invented hour. */
export function titleWhen(title: string | null | undefined, nowMs: number): string | null {
  const raw = (title ?? "").trim();
  if (!raw) return null;
  const named = raw.match(MD_NAME);
  if (named) {
    const month = MONTH[named[1].toLowerCase().replace(/\.$/, "")];
    const day = Number(named[2]);
    if (named[3]) {
      const y = Number(named[3]);
      return `${y}-${pad(month)}-${pad(day)}`;
    }
    return month ? upcomingYmd(month, day, nowMs) : null;
  }
  const slash = raw.match(MD_SLASH_ANY);
  if (slash) {
    const month = Number(slash[1]);
    const day = Number(slash[2]);
    if (slash[3]) {
      const y = slash[3].length === 2 ? 2000 + Number(slash[3]) : Number(slash[3]);
      return `${y}-${pad(month)}-${pad(day)}`;
    }
    return upcomingYmd(month, day, nowMs);
  }
  return null;
}

const DATE_TAIL = /\s+(?:on\s+)?(?:\d{1,2}\/\d{1,2}(?:\/\d{2,4})?|(?:mon|tue|wed|thu|fri|sat|sun)[a-z.]*\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s*\d{4})?\s*$/i;
const SLASH_TAIL = /\s+(?:on\s+)?\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\s*$/;

function cleanPlace(raw: string): string | null {
  let s = raw.replace(DATE_TAIL, "").replace(SLASH_TAIL, "").trim();
  s = s.replace(/[,.;:]+$/, "").replace(/^["\u201c]+|["\u201d]+$/g, "").trim();
  if (!s || FAKE_PLACE.has(s.toLowerCase())) return null;
  if (s.length > 80) return null;
  return s;
}

/** Place named in the title: @ Name, at Name, Live at Name, X House Band. */
export function titlePlace(title: string | null | undefined): string | null {
  const raw = (title ?? "").trim();
  if (!raw) return null;
  const at = raw.match(/(?:^|\s)(?:@|at|live\s+at)\s+(.+)$/i);
  if (at) {
    const place = cleanPlace(at[1]);
    if (place) return place;
  }
  const house = raw.match(/^(.+?)\s+House Band\b/i);
  if (house) {
    const place = cleanPlace(house[1]);
    if (place && !/[+,]/.test(place)) return place;
  }
  return null;
}

function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Room only when the SAME title names both the printed venue and a different @/at spot. */
export function titleRoom(title: string | null | undefined, venueName: string | null | undefined): string | null {
  const raw = (title ?? "").trim();
  const venue = (venueName ?? "").trim();
  if (!raw || !venue || FAKE_PLACE.has(venue.toLowerCase())) return null;
  const place = titlePlace(title);
  if (!place) return null;
  if (place.toLowerCase() === venue.toLowerCase()) return null;
  if (!new RegExp(escapeRe(venue), "i").test(raw)) return null;
  if (!/@/.test(raw) && !/\bat\b/i.test(raw)) return null;
  return place;
}

/** Fill empty when/place from title text already on the row. Does not invent. */
export function applyTitleSlots(e: LicensedEvent, nowMs: number): LicensedEvent {
  const storedPlace = printablePlace(e);
  const fromTitle = titlePlace(e.title);
  const place = storedPlace ?? fromTitle;
  const when = (e.start_time ?? "").trim() || titleWhen(e.title, nowMs);
  if (place === printablePlace(e) && when === ((e.start_time ?? "").trim() || null)) return e;
  return {
    ...e,
    venue_name: place ?? e.venue_name,
    start_time: when || e.start_time,
  };
}
