// Card slots for the two-room card (founder paste 2026-09-08).
// Print a slot only when a desk printed it. Never invent photo, spark, glyph,
// character, specials, doors, or distance.

import type { LicensedEvent } from "./licensed";
import { domainLabel } from "./domains";
import { venueWebsite } from "./detail";

export const LOOKING_FOR_MORE =
  "We\u2019re looking for more information. Check or call the site, artist, or organizer to confirm details.";

const FAKE_PLACE = new Set(["unknown venue", "venue", "unknown", "tbd", "n/a", "na"]);

/** Place name a desk printed. Never "Unknown Venue". */
export function printablePlace(e: LicensedEvent): string | null {
  const raw = (e.venue_name ?? "").trim();
  if (!raw) return null;
  if (FAKE_PLACE.has(raw.toLowerCase())) return null;
  return raw;
}

/** Kind chip text: category label + subgenre when a desk printed one. */
export function kindChip(e: LicensedEvent): string | null {
  const raw = (e.category ?? "").trim();
  // Missing category is a hole, not "Other". Other is only when a desk printed unmapped.
  const label = raw ? domainLabel(raw) : null;
  const sub = (e.subsegment ?? "").trim() || null;
  const parts = [label, sub].filter(Boolean) as string[];
  const uniq = parts.filter((v, i) => parts.indexOf(v) === i);
  return uniq.length ? uniq.join(" \u00b7 ") : null;
}

/** Title / place / topic still empty after other desks + the activity page. */
export function lookingForMore(e: LicensedEvent): boolean {
  const title = (e.title ?? "").trim() || (e.performer ?? "").trim();
  const place = printablePlace(e);
  const topic = (e.category ?? "").trim() || (e.title ?? "").trim();
  return !title || !place || !topic;
}

/** Quiet "?" only when details are thin. Not a verified badge. */
export function detailsThin(e: LicensedEvent): boolean {
  if (lookingForMore(e)) return true;
  if (!(e.start_time ?? "").trim()) return true;
  const conf = (e.confidence ?? "").toLowerCase();
  return conf === "unverified" || conf === "disputed";
}

/** Mini-map chip label: printed area or city. No fake miles. */
export function venueAreaLabel(e: LicensedEvent): string | null {
  const area = (e.venue_area ?? "").trim();
  if (area) return area;
  const city = (e.venue_city ?? "").trim();
  return city || null;
}

/** Venue site as a host string for the card (text only; link lives in the lens). */
export function venueSiteHost(url: string | null): string | null {
  const site = venueWebsite(url);
  if (!site) return null;
  try {
    return new URL(site).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}
