// Share card (group-plans P0 / design brief §6.D5) — the compact, forwardable
// summary a person texts to a friend ("hey, check out this show").
//
// This is the PURE half: it builds the share TITLE, TEXT and absolute URL from
// an event, with no DOM and no browser APIs, so it is unit-tested in full. The
// browser half (Web Share sheet / clipboard fallback) lives in the client
// component ShareButton.tsx and calls these.
//
// TRUST-CRITICAL (CLAUDE.md prime directive 1 — the invariants ride along into
// the shared artifact, group-plans trust screen #5):
//   * No badges, no "confirmed", no ranking/"best" language — we state facts the
//     row already carries (title, when, venue, price) and nothing more.
//   * `disputed` is NEVER hidden: a disputed event carries an honest one-line
//     caveat into the share text itself, not just on the page it links to.
//   * A price we do not know is never dressed as free — we reuse detailPrice,
//     which already fails toward "See tickets".

import type { LicensedEvent } from "./licensed";
import {
  detailWhen,
  detailPrice,
  detailProviderLabel,
  detailTrustKind,
  statusNote,
} from "./detail";
import { trustDisplay } from "./trust";

// Compact per-state caveat for a SHARED artifact — shorter than the detail
// page's full "How we know" sheet, but carrying the same fact. Keyed on the
// confidence state trustDisplay resolves (which already degrades unknown ->
// unverified), so a shared row can never claim more certainty than the card.
const CONFIDENCE_CAVEAT: Record<string, string> = {
  disputed: "Sources disagree on the details — check the venue before you go.",
  likely: "Listed by a single source, not yet confirmed — check the venue.",
  unverified: "Not yet verified — check the venue before you go.",
};

// The one caveat line the share text and the link-preview both carry, highest
// stakes first:
//   1. a cancelled / postponed / moved STATUS — a recipient must never be texted
//      a dead event as if it were on (reused from statusNote, the same sentence
//      the detail page shows);
//   2. otherwise, an uncertainty note for any non-confirmed confidence
//      (likely / unverified / disputed) — unverified data never rides into a
//      forwardable artifact wearing confirmed-fact authority.
// Returns null only for a scheduled, confirmed row (which shows clean, no badge,
// per the trust rules).
export function shareCaveat(e: LicensedEvent): string | null {
  const status = statusNote(e);
  if (status) return status;
  const t = trustDisplay(e.confidence, detailProviderLabel(e), detailTrustKind(e));
  if (!t.surface) return null;
  return CONFIDENCE_CAVEAT[t.key] ?? CONFIDENCE_CAVEAT.unverified;
}

// Short, human title for the OS share sheet. The details go in the TEXT so the
// sheet's title stays a glanceable headline (many share targets show them
// separately).
export function shareTitle(e: LicensedEvent): string {
  return e.title || "A show on 1LIVE";
}

// The multi-line factual body. No URL here — Web Share takes the url as its own
// field, and the clipboard fallback appends it once (buildClipboardText), so a
// link never gets duplicated in the message.
export function shareText(e: LicensedEvent): string {
  const lines: string[] = [];

  // Headline: title, plus the performer only when it adds information the title
  // does not already carry (avoid "Sister Neon — Sister Neon").
  const title = e.title || "";
  const perf = (e.performer || "").trim();
  lines.push(title || perf || "A live show");
  if (perf && perf.toLowerCase() !== title.trim().toLowerCase()) {
    lines.push(perf);
  }

  lines.push(detailWhen(e));

  const where = [e.venue_name, e.venue_area].filter(Boolean).join(" · ");
  if (where) lines.push(where);

  const price = detailPrice(e);
  // Only state a price we actually know; "See tickets" is not information worth
  // texting, and stating it as if it were a price would overclaim.
  if (price.known) lines.push(price.text);

  // The trust caveat travels WITH the artifact: a cancelled/postponed/moved
  // status, or an uncertainty note for any non-confirmed row. A recipient must
  // never be sent a dead or unverified event dressed as an ordinary show.
  const caveat = shareCaveat(e);
  if (caveat) lines.push(`⚠ ${caveat}`);

  lines.push("via 1LIVE");
  return lines.join("\n");
}

// Absolute link to the event's detail page. `origin` is the site origin
// (window.location.origin at call time); the path is the same one eventHref
// builds, so a shared link and an in-app link resolve identically.
export function shareUrl(e: LicensedEvent, origin: string): string {
  const base = (origin || "").replace(/\/+$/, "");
  return `${base}/tonight/${encodeURIComponent(e.licensed_event_id)}`;
}

export type ShareData = { title: string; text: string; url: string };

// The payload for navigator.share(...).
export function shareData(e: LicensedEvent, origin: string): ShareData {
  return { title: shareTitle(e), text: shareText(e), url: shareUrl(e, origin) };
}

// The single string copied to the clipboard when Web Share is unavailable
// (desktop). Text plus the link, once.
export function buildClipboardText(e: LicensedEvent, origin: string): string {
  return `${shareText(e)}\n${shareUrl(e, origin)}`;
}
