// Cross-source duplicate collapse for the consumer feed (founder-caught live
// 2026-08-05, decision record docs/memory/decisions/
// 2026-08-05_today-density-and-duplicates.md): the same real-world show can
// arrive through MULTIPLE providers — a ticketing API and the venue's own
// structured feed — and the per-provider external-id dedupe cannot see across
// lanes, so the feed rendered the same event twice.
//
// TRUST RULES this module must hold (and their tests pin):
//   * Only collapse rows that agree on ALL THREE of venue, start time, and
//     title (normalized). A same-title show at a DIFFERENT venue or time is
//     never collapsed — when sources disagree we show both honestly rather
//     than guess which is right.
//   * A `disputed` row NEVER participates in a collapse, on either side —
//     disputed is shown, never hidden, and never absorbed into a clean row.
//   * The kept card is the RICHEST record (most non-null user-facing fields),
//     tie-broken by provider authority (ticketing first) then stable id order
//     — deterministic, money-blind, content-blind.
//   * Nothing is silently dropped: the return carries the collapsed rows and
//     the caller logs the count (no-silent-truncation discipline).
import type { LicensedEvent } from "./licensed";

// Lowercased, punctuation/whitespace-squashed comparison form. "The Moody
// Theater" == "Moody Theater"; "O.A.R., Gavin DeGraw" == "OAR Gavin DeGraw".
export function normalizeForDedupe(s: string | null | undefined): string {
  if (!s) return "";
  return s
    .toLowerCase()
    // Dots/apostrophes vanish entirely FIRST so an initialism keeps its
    // letters together: "O.A.R." → "oar", not "o a r" (whose lone "a" the
    // article-stripper below would then eat — caught by this module's test).
    .replace(/[.'’]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\b(the|at|a|an)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// User-facing event STATE is part of identity (evaluator #191 r1, absence-only
// blocker): a cancelled/postponed row must never be absorbed behind a
// scheduled-looking card. Spelling variants of the same state normalize
// together ("canceled"/"cancelled") so a trivial variant can't split a true
// duplicate; different STATES always keep both rows visible.
function normalizeStatus(s: string | null | undefined): string {
  const v = (s ?? "scheduled").trim().toLowerCase();
  return v === "canceled" ? "cancelled" : v;
}

/** Identity key for "the same real-world listing", or null when the row lacks
 *  enough identity to dedupe safely (no venue or no start time → never
 *  collapse; absence of identity must not become accidental identity). */
export function dedupeKey(e: LicensedEvent): string | null {
  const venue = normalizeForDedupe(e.venue_name);
  const title = normalizeForDedupe(e.performer || e.title);
  if (!venue || !title || !e.start_time) return null;
  const t = Date.parse(e.start_time);
  if (Number.isNaN(t)) return null;
  return `${venue}|${t}|${title}|${normalizeStatus(e.status)}`;
}

// Provider authority for tie-breaks only (never for ranking): authoritative
// ticketing sources first, the gated pipeline last. Unknown providers sit
// between — richer data still beats any authority rank.
const PROVIDER_ORDER: Record<string, number> = {
  ticketmaster: 0,
  seatgeek: 1,
  eventbrite: 2,
  promoted: 9,
};

function richness(e: LicensedEvent): number {
  const fields: Array<unknown> = [
    e.price_min, e.price_max, e.is_free, e.image_url, e.performer,
    e.subsegment, e.venue_address, e.venue_lat, e.ticket_url, e.venue_url,
    e.origin_url,
  ];
  return fields.filter((v) => v !== null && v !== undefined).length;
}

function keeperOf(a: LicensedEvent, b: LicensedEvent): LicensedEvent {
  const ra = richness(a);
  const rb = richness(b);
  if (ra !== rb) return ra > rb ? a : b;
  const pa = PROVIDER_ORDER[a.source_provider] ?? 5;
  const pb = PROVIDER_ORDER[b.source_provider] ?? 5;
  if (pa !== pb) return pa < pb ? a : b;
  // Fully stable last resort so the same input always renders the same card.
  return a.licensed_event_id <= b.licensed_event_id ? a : b;
}

export type DedupeResult = {
  kept: LicensedEvent[];
  // The rows a keeper absorbed — returned so the caller can COUNT and log
  // them; they are duplicates of a shown card, not hidden events.
  collapsed: LicensedEvent[];
};

/** Collapse cross-source duplicates. Order-preserving: each keeper stays at
 *  the position its group first appeared. */
export function dedupeEvents(events: LicensedEvent[]): DedupeResult {
  const byKey = new Map<string, LicensedEvent>();
  const order: Array<{ kind: "keyed"; key: string } | { kind: "solo"; e: LicensedEvent }> = [];
  const collapsed: LicensedEvent[] = [];

  for (const e of events) {
    // Disputed rows never collapse (either direction): pass through verbatim.
    const key = e.confidence === "disputed" ? null : dedupeKey(e);
    if (!key) {
      order.push({ kind: "solo", e });
      continue;
    }
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, e);
      order.push({ kind: "keyed", key });
      continue;
    }
    const keeper = keeperOf(existing, e);
    const loser = keeper === existing ? e : existing;
    byKey.set(key, keeper);
    collapsed.push(loser);
  }

  const kept = order.map((o) => (o.kind === "solo" ? o.e : byKey.get(o.key)!));
  return { kept, collapsed };
}
