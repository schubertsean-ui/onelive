// Contract #28 — the event DETAIL surface. Every trust rule the contract states
// is an assertion here rather than a sentence in a comment, because a rule with
// no failing case is a claim, not a guarantee.

import { describe, expect, it } from "vitest";
import {
  detailMapUrl,
  detailPrice,
  detailProviderLabel,
  detailTrustKind,
  detailWhen,
  eventHref,
  httpOrNull,
  statusNote,
} from "./detail";
import { buildLicensedQuery, type LicensedEvent } from "./licensed";
import { buildPromotedQuery, routeForEventId, PROMOTED_ID_PREFIX } from "./promoted";

function ev(over: Partial<LicensedEvent> = {}): LicensedEvent {
  return {
    licensed_event_id: "abc-123",
    source_provider: "ticketmaster",
    external_id: "tm-1",
    title: "A Show",
    category: "music",
    subsegment: null,
    performer: null,
    start_time: "2026-08-01T02:00:00.000Z",
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: null,
    price_max: null,
    currency: "USD",
    is_free: null,
    ticket_url: null,
    image_url: null,
    venue_name: "The Venue",
    venue_city: "Austin",
    venue_area: null,
    venue_address: null,
    venue_lat: null,
    venue_lng: null,
    confidence: "likely",
    ...over,
  };
}

// ── id dispatch: BOTH branches plus the reject path (untested-gate-branch) ────

describe("routeForEventId", () => {
  it("routes a bare uuid to the licensed read", () => {
    expect(routeForEventId("abc-123")).toEqual({ kind: "licensed", id: "abc-123" });
  });

  it("routes the promoted prefix to the promoted read, prefix stripped", () => {
    expect(routeForEventId(`${PROMOTED_ID_PREFIX}xyz-789`)).toEqual({
      kind: "promoted",
      id: "xyz-789",
    });
  });

  it("rejects an empty id and a bare prefix rather than querying for nothing", () => {
    expect(routeForEventId("")).toBeNull();
    expect(routeForEventId("   ")).toBeNull();
    expect(routeForEventId(PROMOTED_ID_PREFIX)).toBeNull();
  });

  it("round-trips the id a card links to", () => {
    const promoted = ev({ licensed_event_id: `${PROMOTED_ID_PREFIX}u-1` });
    const href = eventHref(promoted);
    const id = decodeURIComponent(href.replace("/tonight/", ""));
    expect(routeForEventId(id)).toEqual({ kind: "promoted", id: "u-1" });
  });
});

// ── the detail read must never filter on confidence, and must not hide a
//    cancelled event behind the feed's relevance filter ─────────────────────

describe("detail queries", () => {
  it("never filters on confidence, licensed or promoted", () => {
    // `confidence` IS in the select list — the surface reads and displays it.
    // The rule is that it is never a PREDICATE, which in PostgREST is a
    // `&confidence=` parameter. Asserting the bare word would pass only by
    // accident of the column list, so the check names the filter form.
    for (const q of [
      buildLicensedQuery({ eventId: "abc-123", anyStatus: true }),
      buildPromotedQuery({ eventId: "abc-123", anyStatus: true }),
    ]) {
      expect(q).not.toContain("&confidence=");
      expect(q).toContain("confidence"); // ...and it is still SELECTED
    }
    // The check is not vacuous: this is what a violation would look like.
    expect("select=a,confidence&confidence=eq.likely").toContain("&confidence=");
  });

  it("selects the one row by id on both paths", () => {
    expect(buildLicensedQuery({ eventId: "abc-123" }))
      .toContain("licensed_event_id=eq.abc-123");
    expect(buildPromotedQuery({ eventId: "xyz-789" })).toContain("event_id=eq.xyz-789");
  });

  it("drops the feed's status filter for a single event, and keeps it for the feed", () => {
    expect(buildLicensedQuery({ eventId: "abc-123", anyStatus: true }))
      .not.toContain("status=in.");
    expect(buildPromotedQuery({ eventId: "abc-123", anyStatus: true }))
      .not.toContain("status=in.");
    // The feed is unchanged: no opts, same relevance filter as before.
    expect(buildLicensedQuery()).toContain("status=in.");
    expect(buildPromotedQuery()).toContain("status=in.");
  });

  it("still bakes in no row limit", () => {
    expect(buildLicensedQuery({ eventId: "abc-123" })).not.toContain("limit");
    expect(buildPromotedQuery({ eventId: "abc-123" })).not.toContain("limit");
  });
});

// ── an event whose status changed SAYS so ────────────────────────────────────

describe("statusNote", () => {
  it("names a cancelled, postponed, rescheduled or moved event", () => {
    expect(statusNote(ev({ status: "cancelled" }))).toMatch(/cancelled/i);
    expect(statusNote(ev({ status: "canceled" }))).toMatch(/cancelled/i);
    expect(statusNote(ev({ status: "postponed" }))).toMatch(/postponed/i);
    expect(statusNote(ev({ status: "rescheduled" }))).toMatch(/rescheduled/i);
    expect(statusNote(ev({ status: "moved" }))).toMatch(/moved/i);
  });

  it("says nothing for a normal event, and invents nothing for an unknown status", () => {
    expect(statusNote(ev({ status: "scheduled" }))).toBeNull();
    expect(statusNote(ev({ status: "some-new-state" }))).toBeNull();
  });
});

// ── price: an unknown price is never rendered as free ────────────────────────

describe("detailPrice", () => {
  it("says Free only when the row says so", () => {
    expect(detailPrice(ev({ is_free: true })).free).toBe(true);
    expect(detailPrice(ev({ price_min: 0 })).free).toBe(true);
  });

  it("never infers free from a missing price", () => {
    const p = detailPrice(ev({ price_min: null, price_max: null, is_free: null }));
    expect(p.free).toBe(false);
    expect(p.known).toBe(false);
    expect(p.text).toBe("See tickets");
  });

  it("renders a range and a floor", () => {
    expect(detailPrice(ev({ price_min: 20, price_max: 45 })).text).toBe("$20–$45");
    expect(detailPrice(ev({ price_min: 20, price_max: 20 })).text).toBe("$20+");
    expect(detailPrice(ev({ price_min: 20 })).text).toBe("$20+");
  });
});

// ── links: no non-http scheme reaches an href ────────────────────────────────

describe("httpOrNull", () => {
  it("passes http and https", () => {
    expect(httpOrNull("https://e.org/t")).toBe("https://e.org/t");
    expect(httpOrNull("http://e.org/t")).toBe("http://e.org/t");
  });

  it("drops javascript:, data:, and unparseable values", () => {
    expect(httpOrNull("javascript:alert(1)")).toBeNull();
    expect(httpOrNull("data:text/html,<script>")).toBeNull();
    expect(httpOrNull("not a url")).toBeNull();
    expect(httpOrNull(null)).toBeNull();
  });
});

// ── the two surfaces cannot drift into different claims about one row ────────

describe("provenance wording is shared, not re-derived", () => {
  it("calls a promoted row a listing, never a ticketing source", () => {
    const p = ev({ source_provider: "promoted" });
    expect(detailTrustKind(p)).toBe("listing");
    expect(detailProviderLabel(p)).toMatch(/venue or organizer listing/);
  });

  it("names the real ticketing provider for licensed rows", () => {
    expect(detailTrustKind(ev({ source_provider: "ticketmaster" }))).toBe("ticketing");
    expect(detailProviderLabel(ev({ source_provider: "seatgeek" }))).toBe("SeatGeek");
    expect(detailProviderLabel(ev({ source_provider: "eventbrite" }))).toBe("Eventbrite");
  });

  it("falls back to the raw provider rather than inventing a name", () => {
    expect(detailProviderLabel(ev({ source_provider: "somethingnew" })))
      .toBe("somethingnew");
  });
});

// ── missing facts are absent, never filled in ────────────────────────────────

describe("detailWhen and detailMapUrl", () => {
  it("says the date is unannounced rather than guessing one", () => {
    expect(detailWhen(ev({ start_time: null }))).toMatch(/announced/i);
    expect(detailWhen(ev({ start_time: "not-a-date" }))).toMatch(/announced/i);
  });

  it("prefers coordinates and falls back to a text query", () => {
    expect(detailMapUrl(ev({ venue_lat: 30.26, venue_lng: -97.74 })))
      .toBe("https://maps.apple.com/?q=30.26,-97.74");
    expect(detailMapUrl(ev({ venue_name: "The Venue", venue_city: "Austin" })))
      .toContain("The%20Venue");
  });

  it("returns no map link at all when there is nothing to point at", () => {
    expect(detailMapUrl(ev({ venue_name: null, venue_city: null, venue_address: null })))
      .toBeNull();
  });
});

// ── the detail route is gated EXACTLY like the feed ──────────────────────────
// PR #80 found a middleware matcher that made `/sign-inevil` public through a
// prefix rule, so "the new route inherits the feed's treatment" is checked
// rather than assumed. Read statically: the public list is a literal in
// middleware.ts, and neither `/tonight` nor any prefix of it may appear there.

describe("the detail route is not accidentally public", () => {
  it("has no /tonight entry in the middleware public-route list", async () => {
    const { readFileSync } = await import("node:fs");
    const src = readFileSync(
      new URL("../middleware.ts", import.meta.url),
      "utf8",
    );
    const list = src.slice(
      src.indexOf("const isPublicRoute = createRouteMatcher(["),
    );
    const body = list.slice(0, list.indexOf("]);"));
    expect(body).not.toContain("/tonight");
    // Non-vacuous: the block really is the public list we think it is.
    expect(body).toContain("/access");
  });
});
