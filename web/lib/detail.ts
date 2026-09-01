// Shared presentation helpers for the event surfaces (Contract #28).
//
// These lived inside FeedApp.tsx. The detail route needs the same price
// formatting, the same map link, the same provider wording and the same trust
// KIND — and a second copy is the release-path-weaker-than-generation class:
// two surfaces drifting into different claims about one row. So there is one
// implementation, imported by both. Pure ⇒ unit-tested with no DOM and no
// network.

import type { LicensedEvent } from "./licensed";
import { rowVerdict } from "./region";

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
  // A promoted row that carries its real source (0020) is named honestly by
  // it — "Reviewed and published from Mohawk Austin" beats the generic
  // "a local venue or organizer listing". Absent provenance (older rows, an
  // unregistered source) keeps the generic wording: never a guessed name.
  // Licensed rows NEVER take this branch — their provenance is the provider.
  if (e.source_provider === "promoted" && e.origin_name) return e.origin_name;
  return PROVIDER_LABEL[e.source_provider] ?? e.source_provider;
}

// The source's own page for a promoted row — the tappable "last word" link the
// trust sheet's wording promises (canon trust display: dismissible sheet +
// source link). http(s) only via httpOrNull (a stored javascript:/data: URL
// never reaches an href); null for licensed rows, whose provenance link is the
// ticket/provider link the surfaces already carry.
export function originLink(e: LicensedEvent): string | null {
  if (e.source_provider !== "promoted") return null;
  return httpOrNull(e.origin_url ?? null);
}

// ── The named source, as a first-class visible fact ──────────────────────────
// Founder directive (2026-09-01, Session 2 VIEW): "Card or detail shows source
// name + source URL when the event row has them … Use generic 'a local listing'
// only when the fields are empty."
//
// Before this, a promoted row's real source name reached the reader only INSIDE
// the trust sheet's prose, and only for the confirmed/likely wordings — an
// `unverified` or `disputed` row's sheet copy is generic by design, so the one
// row a reader most needs to check was also the one that never named who said
// it. This returns the credit as DATA so every surface renders the same fact.
//
// No fabrication and no guessing: the name is whatever the row carries
// (registry-bound at promote — worker/promote.py writes the source registry's
// canonical name/base_url or NULLs, never the candidate's raw label), the URL
// survives only if it is http(s), and an empty pair degrades to the generic
// phrase rather than to a plausible-sounding one. A licensed row's source IS
// its ticketing provider, which is a name we hold but not a per-source URL —
// its link is the ticket link the surfaces already carry, so `url` is null
// rather than the provider's homepage dressed up as provenance.
export type SourceCredit = {
  /** Display name — the row's own source when it has one, else the generic. */
  name: string;
  /** The source's own site, http(s) only; null when the row carries none. */
  url: string | null;
  /** True when `name` is the generic fallback, not a name the row carries. */
  generic: boolean;
};

export const GENERIC_SOURCE_NAME = "a local listing";

export function sourceCredit(e: LicensedEvent): SourceCredit {
  if (e.source_provider === "promoted") {
    const name = (e.origin_name ?? "").trim();
    return {
      name: name || GENERIC_SOURCE_NAME,
      url: originLink(e),
      generic: !name,
    };
  }
  const provider = PROVIDER_LABEL[e.source_provider] ?? e.source_provider;
  const name = (provider ?? "").trim();
  return { name: name || GENERIC_SOURCE_NAME, url: null, generic: !name };
}

export function detailTrustKind(e: LicensedEvent): "ticketing" | "listing" {
  return e.source_provider === "promoted" ? "listing" : "ticketing";
}

export function detailWhen(iso: string | null): string;
export function detailWhen(e: LicensedEvent): string;
export function detailWhen(x: LicensedEvent | string | null | undefined): string {
  const iso = typeof x === "object" && x !== null ? x.start_time : x ?? null;
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

// An unknown price is "See tickets", never "Free". A MISSING price never
// implies free (the false-price-claim class); a zero floor does, unless the row
// explicitly denies it. The comment used to say "only when the row literally
// says so", which overstated the code — a null is_free with price_min 0 is
// still read as free, deliberately (openai r4 nit).
export function detailPrice(
  e: LicensedEvent,
): { text: string; free: boolean; known: boolean } {
  // `is_free === false` is the row DENYING free entry, and a denial outranks a
  // zero floor (PR #87 r3, openai attacker-smuggle). A row saying
  // `is_free: false, price_min: 0` is contradictory, and the honest reading of
  // contradictory price data is "we do not know", never the claim that
  // benefits us. `price_min === 0` still means free when nothing denies it.
  if (e.is_free === true) return { text: "Free", free: true, known: true };
  if (e.price_min === 0 && e.is_free !== false) {
    return { text: "Free", free: true, known: true };
  }
  if (e.is_free === false && e.price_min === 0) {
    return { text: "See tickets", free: false, known: false };
  }
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

// A dialable `tel:` href from a stored phone string (which may carry prose,
// punctuation, or a leading country code). Digits only, preserving a leading
// `+`; null when there aren't enough digits to be a real number — so a
// tap-to-call control is only ever offered when it will actually dial.
export function telHref(phone: string | null): string | null {
  if (!phone) return null;
  const plus = phone.trim().startsWith("+");
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 10 || digits.length > 15) return null;
  return `tel:${plus ? "+" : ""}${digits}`;
}

// Ticketing-provider hosts — a venue "url" pointing at one of these is a
// THIRD-PARTY page, not the venue's own site.
const PROVIDER_HOSTS = [
  "ticketmaster.com", "livenation.com", "seatgeek.com", "eventbrite.com",
];

// The venue's OWN website, or null. A provider's stored venue url (often
// `ticketmaster.com/venue/...`) must NOT be presented as "the venue's website"
// in a confirm-with-the-venue affordance — a user could treat a ticketing page
// as venue-confirmation authority (adversarial-review #101). So a provider-hosted
// URL returns null here; only a genuine external venue domain passes. Real venue
// sites for the rest arrive with the Places enrichment.
export function venueWebsite(url: string | null): string | null {
  const safe = httpOrNull(url);
  if (!safe) return null;
  try {
    const host = new URL(safe).hostname.toLowerCase().replace(/^www\./, "");
    if (PROVIDER_HOSTS.some((h) => host === h || host.endsWith("." + h))) return null;
    return safe;
  } catch {
    return null;
  }
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


// ── The detail page's BRANCH SELECTION, as data (PR #87 r3, openai
// absence-only, class missing-contract-test). The route previously chose
// between "not configured", "bad link", "read failed", "no such event" and
// "here is the event" inline in JSX, so no test could reach those branches and
// the page could stop displaying trust with every test still green. The choice
// is made here and the component only renders it.

export type DetailView =
  | { kind: "unconfigured" }
  | { kind: "bad-link" }
  | { kind: "read-error"; message: string }
  | { kind: "not-found" }
  // A real event that is in the CATALOG but outside the CAPCOG test region.
  //
  // This used to be its own REFUSAL branch (PR #107): a direct/shared link to a
  // San Antonio row rendered "isn't one of our listings". The Coverage Law
  // (2026-09-01) repealed exactly that reading — "CAPCOG is the TEST LOCALE and
  // a view filter, not the map", and "dropping a legally seen row is a defect".
  // So the fact survives as a LABEL on the event rather than as a refusal to
  // show it: the row renders, honestly marked as outside the region the default
  // /tonight view scopes to. Nothing about the marking is optional — a reader
  // who followed a link must be told which market they are looking at, and the
  // feed's default scope is unchanged (FeedApp still scopes to CAPCOG until the
  // reader clears it).
  | { kind: "event"; event: LicensedEvent; outsideRegion: boolean };

export function resolveDetailView(input: {
  configured: boolean;
  routed: boolean;
  error: string | null;
  event: LicensedEvent | null;
}): DetailView {
  if (!input.configured) return { kind: "unconfigured" };
  if (!input.routed) return { kind: "bad-link" };
  // A read ERROR and an ABSENT row are different facts and must never collapse
  // into one message: "the database is down" is not "there is no such event".
  if (input.error !== null) return { kind: "read-error", message: input.error };
  if (input.event === null) return { kind: "not-found" };
  // The boundary still CLASSIFIES on every surface — it just labels instead of
  // refusing. An unrecognised city is not "outside" (keep-and-count discipline,
  // same as the feed); only a KNOWN-OUTSIDE reading is marked.
  return {
    kind: "event",
    event: input.event,
    outsideRegion: rowVerdict(input.event) === false,
  };
}
