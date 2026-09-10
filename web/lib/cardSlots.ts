// Card slots for the two-room card (founder paste 2026-09-08).
// Print a slot only when a desk printed it. Never invent photo, spark, glyph,
// character, specials, doors, or distance.

import type { LicensedEvent } from "./licensed";
import { domainLabel } from "./domains";
import { venueWebsite } from "./detail";

export const LOOKING_FOR_MORE =
  "We\u2019re looking for more information. Check or call the site, artist, or organizer to confirm details.";

const FAKE_PLACE = new Set(["unknown venue", "venue", "unknown", "tbd", "n/a", "na"]);

/** Classroom / building-room codes are not a Place. */
function isRoomCode(raw: string): boolean {
  return /^[A-Z]{2,5}\s*\d+[A-Z.]?\d+[A-Z]?$/i.test(raw.trim());
}

/** Desk stuffed street into venue_name. Print the name only. */
function placeNameOnly(raw: string): string {
  if (!/,/.test(raw)) return raw;
  if (!/\d/.test(raw)) return raw;
  if (!/\b(austin|tx|street|st\.?|ave|avenue|blvd|rd\.?|drive|dr\.?|lane|ln\.?)\b/i.test(raw)) return raw;
  const name = raw.split(",")[0].trim();
  return name || raw;
}

/** Place name a desk printed. Never "Unknown Venue". */
export function printablePlace(e: LicensedEvent): string | null {
  const raw = (e.venue_name ?? "").trim();
  if (!raw) return null;
  if (FAKE_PLACE.has(raw.toLowerCase())) return null;
  if (isRoomCode(raw)) return null;
  const name = placeNameOnly(raw);
  if (FAKE_PLACE.has(name.toLowerCase())) return null;
  return name;
}

export function kindChip(e: LicensedEvent): string | null {
  const raw = (e.category ?? "").trim();
  const label = raw ? domainLabel(raw) : null;
  const sub = (e.subsegment ?? "").trim() || null;
  const parts = [label, sub].filter(Boolean) as string[];
  const uniq = parts.filter((v, i) => parts.indexOf(v) === i);
  return uniq.length ? uniq.join(" \u00b7 ") : null;
}

export function lookingForMore(e: LicensedEvent): boolean {
  const title = (e.title ?? "").trim() || (e.performer ?? "").trim();
  const place = printablePlace(e);
  const topic = (e.category ?? "").trim() || (e.title ?? "").trim();
  return !title || !place || !topic;
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

export function venueSiteHost(url: string | null): string | null {
  const site = venueWebsite(url);
  if (!site) return null;
  try {
    return new URL(site).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
