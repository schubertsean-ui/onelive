// Card slot helpers for the two-room card (UI Canon §2, founder paste 2026-09-08).
// Print a slot only when a desk printed it. Never invent photo / spark / glyph /
// character / specials / miles / doors. Incomplete fill is not a disqualifier.

import { domainLabel } from "./domains";
import type { LicensedEvent } from "./licensed";

export const LOOKING_FOR_MORE =
  "We're looking for more information. Check or call the site, artist, or organizer to confirm details.";

function blank(value: string | null | undefined): boolean {
  return !value || !value.trim();
}

/** Topic = kind or title. Empty topic is a hole, not a reason to invent one. */
export function topicOf(e: Pick<LicensedEvent, "title" | "category">): string | null {
  const title = (e.title ?? "").trim();
  const kind = e.category ? domainLabel(e.category) : "";
  return title || kind || null;
}

/** Founder 2026-09-08: after other desks + the activity page, if title, place,
 *  or topic is still empty, print the looking-for-more sentence. Never use it
 *  as filler on a complete card. */
export function needsMoreInfo(
  e: Pick<LicensedEvent, "title" | "venue_name" | "category">,
): boolean {
  return blank(e.title) || blank(e.venue_name) || !topicOf(e);
}

/** Quiet "?" only when details are thin: missing title, place, when, or kind.
 *  TrustMark already covers unverified/disputed — do not double the mark. */
export function detailsThin(
  e: Pick<LicensedEvent, "title" | "venue_name" | "start_time" | "category">,
): boolean {
  return blank(e.title) || blank(e.venue_name) || blank(e.start_time) || blank(e.category);
}

/** Kind chip: Live Music + subgenre when a desk printed one. */
export function kindChip(
  e: Pick<LicensedEvent, "category" | "subsegment">,
): { kind: string; sub: string | null } | null {
  if (blank(e.category)) return null;
  const kind = domainLabel(e.category);
  const sub = (e.subsegment ?? "").trim() || null;
  return { kind, sub };
}

/** Mini-map chip label: neighborhood or city the desk printed. No fake miles. */
export function areaChip(
  e: Pick<LicensedEvent, "venue_area" | "venue_city">,
): string | null {
  const area = (e.venue_area ?? "").trim();
  const city = (e.venue_city ?? "").trim();
  return area || city || null;
}

/** Venue site as host text for the card (the real link lives in the lens). */
export function siteHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    return host || null;
  } catch {
    return null;
  }
}
