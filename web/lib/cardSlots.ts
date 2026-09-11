// Card slots for the two-room card (founder paste 2026-09-08).
// Place, photo, and venue site are always on the activity. Missing = finder miss.
// Never invent photo, spark, glyph, character, specials, doors, or distance.
// City is not Place. A clock mashed into the name is not Place.

import type { LicensedEvent } from "./licensed";
import { domainLabel } from "./domains";
import { venueWebsite } from "./detail";

export const LOOKING_FOR_MORE =
  "We\u2019re looking for more information. Check or call the site, artist, or organizer to confirm details.";

export const PLACE_HOLE = "Looking for the venue";

const FAKE_PLACE = new Set([
  "unknown venue",
  "venue",
  "unknown",
  "tbd",
  "n/a",
  "na",
  "place to be confirmed",
  "to be confirmed",
]);

const CITY_ONLY = new Set(["austin", "atx"]);

const AREA_ONLY = new Set([
  "downtown",
  "midtown",
  "uptown",
  "campus",
  "north",
  "south",
  "east",
  "west",
  "central",
  "nearby",
  "local",
  "north austin",
  "south austin",
  "east austin",
  "west austin",
  "central austin",
  "downtown austin",
  "midtown austin",
  "uptown austin",
  "campus austin",
  "beyond austin",
  "greater austin",
]);

function placeNameOnly(raw: string): string {
  if (!/,/.test(raw)) return raw;
  if (!/\d/.test(raw)) return raw;
  if (!/\b(austin|tx|street|st\.?|ave|avenue|blvd|rd\.?|drive|dr\.?|lane|ln\.?)\b/i.test(raw)) return raw;
  const name = raw.split(",")[0].trim();
  return name || raw;
}

function stripClockPrefix(raw: string): string {
  let s = raw.trim();
  s = s.replace(/^(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?\s*,?\s+/i, "");
  s = s.replace(/^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+/i, "");
  s = s.replace(/^(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\.?\s+/i, "");
  return s.trim();
}

function normalizedPlaceKey(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/[.’']/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function isCityOrAreaOnly(name: string): boolean {
  const key = normalizedPlaceKey(name);
  if (!key) return true;
  if (CITY_ONLY.has(key) || AREA_ONLY.has(key)) return true;
  const withoutCity = key.replace(/,\s*(austin|atx|tx)$/i, "").replace(/\s+(austin|atx)$/i, "").trim();
  if (!withoutCity) return true;
  if (CITY_ONLY.has(withoutCity) || AREA_ONLY.has(withoutCity)) return true;
  return false;
}

/** Place a desk printed. Never city-only. Never a clock. Never invented copy. */
export function printablePlace(e: LicensedEvent): string | null {
  const raw = (e.venue_name ?? "").trim();
  if (!raw) return null;
  if (FAKE_PLACE.has(raw.toLowerCase())) return null;
  const stripped = stripClockPrefix(placeNameOnly(raw));
  if (!stripped) return null;
  if (FAKE_PLACE.has(stripped.toLowerCase())) return null;
  if (isCityOrAreaOnly(stripped)) return null;
  return stripped;
}

export function kindChip(e: LicensedEvent): string | null {
  const raw = (e.category ?? "").trim();
  const label = raw ? domainLabel(raw) : null;
  const sub = (e.subsegment ?? "").trim() || null;
  const parts = [label, sub].filter(Boolean) as string[];
  const uniq = parts.filter((v, i) => parts.indexOf(v) === i);
  return uniq.length ? uniq.join(" \u00b7 ") : null;
}

export function venueSiteHost(url: string | null): string | null {
  const site = venueWebsite(url);
  if (!site) return null;
  try {
    return new URL(site).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

export function lookingForMore(e: LicensedEvent): boolean {
  const title = (e.title ?? "").trim() || (e.performer ?? "").trim();
  const place = printablePlace(e);
  const topic = (e.category ?? "").trim() || (e.title ?? "").trim();
  const site = venueSiteHost(e.venue_url);
  const photo = (e.image_url ?? "").trim();
  return !title || !place || !topic || !site || !photo;
}

export function detailsThin(e: LicensedEvent): boolean {
  if (lookingForMore(e)) return true;
  if (!(e.start_time ?? "").trim()) return true;
  const conf = (e.confidence ?? "").toLowerCase();
  return conf === "unverified" || conf === "disputed";
}

export function venueAreaLabel(e: LicensedEvent): string | null {
  const area = (e.venue_area ?? "").trim();
  if (area) return area;
  const city = (e.venue_city ?? "").trim();
  return city || null;
}
