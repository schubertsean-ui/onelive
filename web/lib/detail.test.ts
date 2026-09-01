// Contract #28 — the event DETAIL surface. Every trust rule the contract states
// is an assertion here rather than a sentence in a comment, because a rule with
// no failing case is a claim, not a guarantee.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  detailMapUrl,
  detailPrice,
  detailProviderLabel,
  detailTrustKind,
  detailWhen,
  eventHref,
  httpOrNull,
  originLink,
  sourceCredit,
  GENERIC_SOURCE_NAME,
  telHref,
  venueWebsite,
  resolveDetailView,
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
    venue_url: null,
    venue_phone: null,
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

  it("names a promoted row by its REAL source when provenance is present (0020)", () => {
    const p = ev({ source_provider: "promoted", origin_name: "Mohawk Austin" });
    expect(detailProviderLabel(p)).toBe("Mohawk Austin");
    // The trust KIND stays 'listing' — honest wording, never ticketing.
    expect(detailTrustKind(p)).toBe("listing");
  });

  it("never lets origin_name rename a LICENSED provider (their provenance IS the provider)", () => {
    const l = ev({ source_provider: "seatgeek", origin_name: "Should Not Show" });
    expect(detailProviderLabel(l)).toBe("SeatGeek");
    expect(originLink(ev({ source_provider: "seatgeek", origin_url: "https://x.example" }))).toBeNull();
  });

  it("originLink is http(s)-only and honest about absence", () => {
    expect(originLink(ev({ source_provider: "promoted", origin_url: "https://mohawkaustin.com" })))
      .toBe("https://mohawkaustin.com");
    // A stored javascript: URL must never reach an href.
    expect(originLink(ev({ source_provider: "promoted", origin_url: "javascript:alert(1)" })))
      .toBeNull();
    expect(originLink(ev({ source_provider: "promoted" }))).toBeNull();
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

// ── PR #87 r2. The S3 evidence claimed "injected fetch doubles" and
// "not-found path covered" and neither existed — the exact false-confidence
// class this repo treats as a trust defect, in my own contract. Both seats
// were right. These are the tests those sentences described.

describe("single-event reads, with the fetch injected", () => {
  const ENV = {
    NEXT_PUBLIC_SUPABASE_URL: "https://sb.test",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon-key",
  };
  let saved: Record<string, string | undefined>;
  let calls: string[];

  beforeEach(() => {
    saved = {};
    for (const [k, v] of Object.entries(ENV)) {
      saved[k] = process.env[k];
      process.env[k] = v;
    }
    calls = [];
  });
  afterEach(() => {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
    vi.unstubAllGlobals();
  });

  /** Serves `pages` in order; every page after the data is empty, which is how
   *  the real pagination loop terminates. */
  function stubFetch(pages: unknown[][], ok = true, status = 200) {
    let i = 0;
    vi.stubGlobal("fetch", async (url: string) => {
      calls.push(String(url));
      const body = i < pages.length ? pages[i++] : [];
      return {
        ok,
        status,
        json: async () => body,
        text: async () => JSON.stringify(body),
      } as unknown as Response;
    });
  }

  it("returns null when the row genuinely does not exist", async () => {
    stubFetch([[]]);
    const { fetchLicensedEventById } = await import("./licensed");
    await expect(fetchLicensedEventById("no-such-id")).resolves.toBeNull();
  });

  it("returns the one row when it exists", async () => {
    stubFetch([[ev({ licensed_event_id: "abc-123", title: "Real Show" })]]);
    const { fetchLicensedEventById } = await import("./licensed");
    const got = await fetchLicensedEventById("abc-123");
    expect(got?.title).toBe("Real Show");
  });

  it("THROWS on a duplicate id instead of rendering an arbitrary row", async () => {
    stubFetch([[ev({ title: "One" }), ev({ title: "Two" })]]);
    const { fetchLicensedEventById } = await import("./licensed");
    await expect(fetchLicensedEventById("abc-123")).rejects.toThrow(/corrupt data/i);
  });

  it("THROWS on a failed read — an error is never a missing row", async () => {
    stubFetch([[]], false, 500);
    const { fetchLicensedEventById } = await import("./licensed");
    await expect(fetchLicensedEventById("abc-123")).rejects.toThrow(/read failed/i);
  });

  it("does NOT window a by-id read by date", async () => {
    // gemini dataflow-taint reported a default 36-hour window that would make
    // any event outside tonight read as absent. Refuted at the query: no
    // start_time predicate is emitted unless a caller asks for one. Kept as a
    // regression case so the refutation stays true.
    stubFetch([[ev()]]);
    const { fetchLicensedEventById } = await import("./licensed");
    await fetchLicensedEventById("abc-123");
    expect(calls[0]).not.toContain("start_time=");
    expect(calls[0]).toContain("licensed_event_id=eq.abc-123");
  });
});

// ── PR #87 r3. Two failures of the SAME shape as r2's, caught by the same
// seats: the r2 citation said "both readers are exercised" and only the
// licensed one was, and the page's own branches had no test at all.

describe("the promoted single-event read, with the fetch injected", () => {
  const ENV = {
    NEXT_PUBLIC_SUPABASE_URL: "https://sb.test",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon-key",
  };
  let saved: Record<string, string | undefined>;
  let calls: string[];

  function promotedRow(over: Record<string, unknown> = {}) {
    return {
      event_id: "u-1",
      title: "Promoted Show",
      category: "music",
      subsegment: null,
      artist_ids: [],
      start_time: "2026-08-01T02:00:00.000Z",
      end_time: null,
      status: "scheduled",
      ticket_url: null,
      confidence: "likely",
      venue: null,
      ...over,
    };
  }

  beforeEach(() => {
    saved = {};
    for (const [k, v] of Object.entries(ENV)) {
      saved[k] = process.env[k];
      process.env[k] = v;
    }
    calls = [];
  });
  afterEach(() => {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
    vi.unstubAllGlobals();
  });

  function stubFetch(pages: unknown[][], ok = true, status = 200) {
    let i = 0;
    vi.stubGlobal("fetch", async (url: string) => {
      calls.push(String(url));
      const body = i < pages.length ? pages[i++] : [];
      return {
        ok, status,
        json: async () => body,
        text: async () => JSON.stringify(body),
      } as unknown as Response;
    });
  }

  it("returns null when the promoted row does not exist", async () => {
    stubFetch([[]]);
    const { fetchPromotedEventById } = await import("./promoted");
    await expect(fetchPromotedEventById("u-nope")).resolves.toBeNull();
  });

  it("returns the one promoted row, shaped like a card", async () => {
    stubFetch([[promotedRow()]]);
    const { fetchPromotedEventById } = await import("./promoted");
    const got = await fetchPromotedEventById("u-1");
    expect(got?.title).toBe("Promoted Show");
    // Provenance survives the reshape — this is what makes it a LISTING.
    expect(got?.source_provider).toBe("promoted");
    expect(got?.licensed_event_id).toBe("promoted:u-1");
  });

  it("THROWS on a duplicate promoted id", async () => {
    stubFetch([[promotedRow({ title: "One" }), promotedRow({ title: "Two" })]]);
    const { fetchPromotedEventById } = await import("./promoted");
    await expect(fetchPromotedEventById("u-1")).rejects.toThrow(/corrupt data/i);
  });

  it("THROWS on a failed promoted read", async () => {
    stubFetch([[]], false, 500);
    const { fetchPromotedEventById } = await import("./promoted");
    await expect(fetchPromotedEventById("u-1")).rejects.toThrow();
  });

  it("does NOT window a promoted by-id read by date", async () => {
    stubFetch([[promotedRow()]]);
    const { fetchPromotedEventById } = await import("./promoted");
    await fetchPromotedEventById("u-1");
    expect(calls[0]).not.toContain("start_time=");
    expect(calls[0]).toContain("event_id=eq.u-1");
  });
});

// ── the page's own branches, as data ─────────────────────────────────────────

describe("resolveDetailView", () => {
  const base = { configured: true, routed: true, error: null, event: null };

  it("reports a misconfigured deploy before anything else", () => {
    expect(resolveDetailView({ ...base, configured: false }).kind)
      .toBe("unconfigured");
  });

  it("reports a bad link when the id does not route", () => {
    expect(resolveDetailView({ ...base, routed: false }).kind).toBe("bad-link");
  });

  it("keeps a read ERROR distinct from an absent row", () => {
    const err = resolveDetailView({ ...base, error: "Supabase read failed (500)" });
    expect(err.kind).toBe("read-error");
    expect(resolveDetailView({ ...base, error: null, event: null }).kind)
      .toBe("not-found");
    // The distinction that matters: "the database is down" must never render
    // as "there is no such event".
    expect(err.kind).not.toBe("not-found");
  });

  it("returns the event when there is one — including a disputed one", () => {
    const disputed = ev({ confidence: "disputed" });
    const view = resolveDetailView({ ...base, event: disputed });
    expect(view).toEqual({ kind: "event", event: disputed, outsideRegion: false });
  });

  it("shows a CANCELLED event rather than treating it as absent", () => {
    const cancelled = ev({ status: "cancelled" });
    const view = resolveDetailView({ ...base, event: cancelled });
    expect(view.kind).toBe("event");
    expect(statusNote(cancelled)).toMatch(/cancelled/i);
  });

  // Coverage Law 2026-09-01 replaced the PR #107 REFUSAL with a LABEL: the row
  // is in the catalog and renders; the region is a view scope, not a delete.
  // The classification itself is unchanged and still proven here.
  it("LABELS a known-outside event instead of refusing it (Coverage Law)", () => {
    const outside = ev({ venue_city: "San Antonio", venue_name: "Majestic" });
    const v = resolveDetailView({ ...base, event: outside });
    expect(v.kind).toBe("event");
    expect(v.kind === "event" && v.outsideRegion).toBe(true);
    // A city string that embeds a contradictory in-market county cannot smuggle
    // its way to an UNLABELLED render (the reachable vector for a licensed row,
    // which has no county field): the drop-direction rule still wins.
    const smuggled = ev({ venue_city: "San Antonio, Travis County, TX" });
    const vs = resolveDetailView({ ...base, event: smuggled });
    expect(vs.kind === "event" && vs.outsideRegion).toBe(true);
    // An in-market event renders unlabelled; so does an unrecognised city —
    // keep-and-count discipline: unrecognised is NOT "outside".
    for (const city of ["Austin", "Nowheresville"]) {
      const inv = resolveDetailView({ ...base, event: ev({ venue_city: city }) });
      expect(inv.kind).toBe("event");
      expect(inv.kind === "event" && inv.outsideRegion).toBe(false);
    }
  });
});

// ── a denial of free entry outranks a zero floor ─────────────────────────────

describe("detailPrice and contradictory free data", () => {
  it("does not claim Free when the row explicitly denies it", () => {
    const p = detailPrice(ev({ is_free: false, price_min: 0 }));
    expect(p.free).toBe(false);
    expect(p.known).toBe(false);
  });

  it("still treats a zero floor as free when nothing denies it", () => {
    expect(detailPrice(ev({ is_free: null, price_min: 0 })).free).toBe(true);
    expect(detailPrice(ev({ is_free: true, price_min: null })).free).toBe(true);
  });
});

// ── PR #87 r4: the artist-lookup branch, which no promoted test entered
// because every stub row had `artist_ids: []` (gemini). Testing it also
// SETTLES the encoding question raised in two rounds: if percent-encoding the
// `in.(...)` expression broke PostgREST, the name would not resolve here.

describe("promoted artist resolution", () => {
  const ENV = {
    NEXT_PUBLIC_SUPABASE_URL: "https://sb.test",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: "anon-key",
  };
  let saved: Record<string, string | undefined>;
  let calls: string[];

  beforeEach(() => {
    saved = {};
    for (const [k, v] of Object.entries(ENV)) {
      saved[k] = process.env[k];
      process.env[k] = v;
    }
    calls = [];
  });
  afterEach(() => {
    for (const [k, v] of Object.entries(saved)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
    vi.unstubAllGlobals();
  });

  /** Routes by endpoint rather than by call order, so the artist request is
   *  identified by what it asks for, not by when it happens. */
  function stubByEndpoint(byPath: Record<string, unknown[]>) {
    const served: Record<string, boolean> = {};
    vi.stubGlobal("fetch", async (url: string) => {
      const u = String(url);
      calls.push(u);
      const hit = Object.keys(byPath).find((k) => u.includes(k));
      const body = hit && !served[hit] ? byPath[hit] : [];
      if (hit) served[hit] = true;
      return {
        ok: true, status: 200,
        json: async () => body,
        text: async () => JSON.stringify(body),
      } as unknown as Response;
    });
  }

  it("resolves performer names through the encoded in.(...) filter", async () => {
    stubByEndpoint({
      "/rest/v1/event": [{
        event_id: "u-2",
        title: "Two Acts",
        category: "music",
        subsegment: null,
        artist_ids: ["a-1", "a-2"],
        start_time: "2026-08-01T02:00:00.000Z",
        end_time: null,
        status: "scheduled",
        ticket_url: null,
        confidence: "likely",
        venue: null,
      }],
      "/rest/v1/artist": [
        { artist_id: "a-1", name: "First Act" },
        { artist_id: "a-2", name: "Second Act" },
      ],
    });
    const { fetchPromotedEventById } = await import("./promoted");
    const got = await fetchPromotedEventById("u-2");

    // The branch ran at all...
    const artistCall = calls.find((c) => c.includes("/rest/v1/artist"));
    expect(artistCall).toBeDefined();
    // ...asking for both ids, as ONE percent-encoded filter value...
    expect(artistCall).toContain("artist_id=in.");
    expect(decodeURIComponent(artistCall!)).toContain('in.("a-1","a-2")');
    // ...and the names actually came back onto the event.
    expect(got?.performer).toContain("First Act");
    expect(got?.performer).toContain("Second Act");
  });

  it("omits an unresolved artist rather than inventing a name", async () => {
    stubByEndpoint({
      "/rest/v1/event": [{
        event_id: "u-3",
        title: "One Known",
        category: "music",
        subsegment: null,
        artist_ids: ["a-1", "a-missing"],
        start_time: "2026-08-01T02:00:00.000Z",
        end_time: null,
        status: "scheduled",
        ticket_url: null,
        confidence: "likely",
        venue: null,
      }],
      "/rest/v1/artist": [{ artist_id: "a-1", name: "First Act" }],
    });
    const { fetchPromotedEventById } = await import("./promoted");
    const got = await fetchPromotedEventById("u-3");
    expect(got?.performer).toBe("First Act");
    expect(got?.performer).not.toContain("a-missing");
  });
});

describe("telHref — a dialable tel: only when the number is real", () => {
  it("extracts digits from prose/punctuation and builds tel:", () => {
    expect(telHref("(512) 474-5664")).toBe("tel:5124745664");
    expect(telHref("Box office: 512.474.5664")).toBe("tel:5124745664");
  });
  it("preserves a leading + country code", () => {
    expect(telHref("+1 512-474-5664")).toBe("tel:+15124745664");
  });
  it("returns null for a non-number, empty, or too-short string", () => {
    expect(telHref(null)).toBeNull();
    expect(telHref("call the box office")).toBeNull();
    expect(telHref("867-5309")).toBeNull(); // 7 digits, not dialable as-is
    expect(telHref("")).toBeNull();
  });
});

describe("venueWebsite — only the venue's OWN site, never a ticketing page", () => {
  it("passes a genuine external venue domain", () => {
    expect(venueWebsite("https://elephantroomjazz.com")).toBe("https://elephantroomjazz.com");
    expect(venueWebsite("https://www.thecontinentalclub.com/austin")).toBe(
      "https://www.thecontinentalclub.com/austin",
    );
  });
  it("drops a ticketing-provider page (not the venue's authority, #101)", () => {
    expect(venueWebsite("https://www.ticketmaster.com/venue/12345")).toBeNull();
    expect(venueWebsite("https://seatgeek.com/venues/acl-live")).toBeNull();
    expect(venueWebsite("https://www.eventbrite.com/o/some-venue")).toBeNull();
  });
  it("drops non-http and unparseable values", () => {
    expect(venueWebsite(null)).toBeNull();
    expect(venueWebsite("javascript:alert(1)")).toBeNull();
    expect(venueWebsite("not a url")).toBeNull();
  });
});


// ── Naming the source (founder directive 2026-09-01, Session 2 VIEW) ─────────
// "Card or detail shows source name + source URL when the event row has them …
// Use generic 'a local listing' only when the fields are empty."
describe("sourceCredit — who listed this, said out loud", () => {
  it("names a promoted row's real source and links its site", () => {
    const e = ev({
      source_provider: "promoted",
      origin_name: "Mohawk Austin",
      origin_url: "https://mohawkaustin.com",
    });
    expect(sourceCredit(e)).toEqual({
      name: "Mohawk Austin", url: "https://mohawkaustin.com", generic: false,
    });
  });

  it("says the generic phrase ONLY when the row carries no source name", () => {
    const bare = ev({ source_provider: "promoted", origin_name: null, origin_url: null });
    expect(sourceCredit(bare)).toEqual({
      name: GENERIC_SOURCE_NAME, url: null, generic: true,
    });
    expect(GENERIC_SOURCE_NAME).toBe("a local listing");
    // Whitespace is not a name — a blank-but-present value must not render as
    // an empty credit line pretending to be provenance.
    const blank = ev({ source_provider: "promoted", origin_name: "   ", origin_url: null });
    expect(sourceCredit(blank).generic).toBe(true);
  });

  it("keeps the NAME even when the URL is unusable, never the reverse", () => {
    // A stored javascript:/data: URL must never reach an href, but losing the
    // link is no reason to also lose the honest name of who listed the event.
    const e = ev({
      source_provider: "promoted",
      origin_name: "Bastrop Opera House",
      origin_url: "javascript:alert(1)",
    });
    expect(sourceCredit(e)).toEqual({
      name: "Bastrop Opera House", url: null, generic: false,
    });
  });

  it("names the ticketing provider for a licensed row, with no invented URL", () => {
    // A licensed row's source IS its provider. We hold no per-source site for
    // it — the ticket link is its link — so url stays null rather than the
    // provider's homepage dressed up as provenance.
    expect(sourceCredit(ev({ source_provider: "ticketmaster" })))
      .toEqual({ name: "Ticketmaster", url: null, generic: false });
    expect(sourceCredit(ev({ source_provider: "seatgeek" })).name).toBe("SeatGeek");
    // An unmapped provider is reported AS ITSELF, never silently genericised —
    // an unknown provider is a catalog fact, not an absent one.
    expect(sourceCredit(ev({ source_provider: "somefeed" })))
      .toEqual({ name: "somefeed", url: null, generic: false });
  });

  it("is independent of confidence — a DISPUTED row still names its source", () => {
    // The whole reason this exists: the confirmed/likely trust sheets name the
    // source in prose, but the unverified and disputed wordings are generic, so
    // the rows a reader most needs to check were the ones that never said who
    // listed them.
    for (const confidence of ["confirmed", "likely", "unverified", "disputed"]) {
      const e = ev({
        confidence,
        source_provider: "promoted",
        origin_name: "Bastrop Opera House",
        origin_url: "https://bastropoperahouse.com",
      });
      expect(sourceCredit(e).name).toBe("Bastrop Opera House");
      expect(sourceCredit(e).url).toBe("https://bastropoperahouse.com");
    }
  });
});
