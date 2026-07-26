// Shared presentation helpers for the event surfaces (Contract #28).
//
// These lived inside FeedApp.tsx. The detail route needs the same price
// formatting, the same map link, the same provider wording and the same trust
// KIND — and a second copy is the release-path-weaker-than-generation class:
// two surfaces drifting into different claims about one row. So there is one
// implementation, imported by both. Pure ⇒ unit-tested with no DOM and no
// network.

import type { LicensedEvent } from "./licensed";

export const TZ = "America/Chicago";

// Provenance-accurate provider wording. A licensed row is stated by an
// authoritative TICKETING source; a "promoted" row was gated and published
// from a venue/organizer LISTING, so it must never borrow ticketing wording.
const PROVIDER_LABEL: Record<string, string> = {
  ticketmaster: "Ticketmaster",
  seatgeek: "SeatGeek",
  eventbrite: "Eventbrite",
  promoted: "a local venue or organizer listing",
};

export function detailProviderLabel(e: LicensedEvent): string {
  return PROVIDER_LABEL[e.source_provider] ?? e.source_provider;
}

export function detailTrustKind(e: LicensedEvent): "ticketing" | "listing" {
  return e.source_provider === "promoted" ? "listing" : "ticketing";
}

export function detailWhen(iso: string | null): string;
export function detailWhen(e: LicensedEvent): string;
export function detailWhen(x: LicensedEvent | string | null): string {
  const iso = typeof x === "string" || x === null ? x : x.start_time;
  if (!iso) return "Date to be announced";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "Date to be announced";
  return d.toLocaleString("en-US", {
    timeZone: TZ,
    weekday: "long",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// An unknown price is "See tickets", never "Free". `free` is true only when the
// row literally says so — inferring free from a missing price is the
// false-price-claim class.
export function detailPrice(
  e: LicensedEvent,
): { text: string; free: boolean; known: boolean } {
  if (e.is_free || e.price_min === 0) return { text: "Free", free: true, known: true };
  if (e.price_min != null && e.price_max != null && e.price_max !== e.price_min) {
    return {
      text: `$${Math.round(e.price_min)}–$${Math.round(e.price_max)}`,
      free: false,
      known: true,
    };
  }
  if (e.price_min != null) {
    return { text: `$${Math.round(e.price_min)}+`, free: false, known: true };
  }
  return { text: "See tickets", free: false, known: false };
}

// Only http(s) survives — a stored `javascript:` or `data:` URL must never
// reach an href.
export function httpOrNull(u: string | null): string | null {
  if (!u) return null;
  try {
    const p = new URL(u).protocol;
    return p === "http:" || p === "https:" ? u : null;
  } catch {
    return null;
  }
}

export function detailMapUrl(e: LicensedEvent): string | null {
  if (e.venue_lat != null && e.venue_lng != null) {
    return `https://maps.apple.com/?q=${e.venue_lat},${e.venue_lng}`;
  }
  const q = [e.venue_name, e.venue_address, e.venue_city].filter(Boolean).join(", ");
  return q ? `https://maps.apple.com/?q=${encodeURIComponent(q)}` : null;
}

// The detail surface reads rows the feed filters out (Contract #28: a visitor
// who followed a LINK to one event asked for that event, so a cancelled event
// says it was cancelled instead of 404-ing). This is the sentence that says so.
// It reports the STORED status and nothing else — no guess about whether the
// event might still happen.
export function statusNote(e: LicensedEvent): string | null {
  switch ((e.status ?? "").toLowerCase()) {
    case "cancelled":
    case "canceled":
      return "This event has been cancelled.";
    case "postponed":
      return "This event has been postponed — no new date has been published.";
    case "rescheduled":
      return "This event was rescheduled; the time shown is the current one.";
    case "moved":
      return "This event moved — the venue shown is the current one.";
    default:
      return null; // scheduled, or a status we do not have wording for
  }
}

// Stable link target for one event. The id already carries its own routing
// (`promoted:` prefix), so the path needs nothing else; it is encoded because
// that prefix contains a colon.
export function eventHref(e: LicensedEvent): string {
  return `/tonight/${encodeURIComponent(e.licensed_event_id)}`;
}
