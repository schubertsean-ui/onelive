import { describe, it, expect } from "vitest";
import {
  buildPromotedQuery,
  reshapePromoted,
  type PromotedRow,
} from "./promoted";

function params(qs: string): URLSearchParams {
  return new URLSearchParams(qs);
}

describe("buildPromotedQuery", () => {
  it("NEVER filters on confidence — a disputed promoted event is not dropped", () => {
    const p = params(buildPromotedQuery({ fromISO: "2026-07-25T00:00:00Z" }));
    expect(p.get("confidence")).toBeNull();
    expect((p.get("select") ?? "")).toContain("confidence");
  });

  it("bakes in NO row limit — position can never cap the result", () => {
    const p = params(buildPromotedQuery());
    expect(p.get("limit")).toBeNull();
    expect(p.get("offset")).toBeNull();
  });

  it("filters only on status (a time/status lens), never a trust field", () => {
    // getAll because status is appended as a PostgREST predicate.
    const p = params(buildPromotedQuery());
    expect(p.getAll("status")).toContain("in.(scheduled,moved)");
  });

  it("orders with a stable unique tiebreaker so paging cannot skip/dupe", () => {
    expect(params(buildPromotedQuery()).get("order")).toBe(
      "start_time.asc,event_id.asc",
    );
  });

  it("does NOT select privacy/internal columns (private_access, is_private_rsvp, notes)", () => {
    const select = params(buildPromotedQuery()).get("select") ?? "";
    expect(select).not.toContain("private_access");
    expect(select).not.toContain("is_private_rsvp");
    expect(select).not.toContain("notes");
  });

  it("selects the source provenance columns (0020) so 'How we know' can name the listing", () => {
    const select = params(buildPromotedQuery()).get("select") ?? "";
    expect(select).toContain("source_name");
    expect(select).toContain("source_url");
  });

  it("applies category + date-window filters when given", () => {
    const p = params(
      buildPromotedQuery({ category: "comedy", fromISO: "A", toISO: "B" }),
    );
    expect(p.getAll("category")).toContain("eq.comedy");
    expect(p.get("or")).toBe("(and(start_time.gte.A,start_time.lte.B),start_time.is.null)");
  });

  // PR #216 r1, openai/absence-only (blocking): a bare `gte` drops NULLs, so a
  // promoted row whose clock the evidence never settled was never FETCHED —
  // while feed.ts is written to place exactly those rows under "All". A view
  // may narrow; it may not delete a catalog row (Coverage Law).
  it("a date-TBA row is inside the window, not outside it", () => {
    const p = params(buildPromotedQuery({ fromISO: "A" }));
    expect(p.get("or")).toBe("(start_time.gte.A,start_time.is.null)");
    expect(p.getAll("start_time")).toEqual([]);
  });

  it("adds no window predicate at all when no window is asked for", () => {
    const p = params(buildPromotedQuery());
    expect(p.get("or")).toBeNull();
  });
});

function row(over: Partial<PromotedRow> = {}): PromotedRow {
  return {
    event_id: "e1",
    title: "Standup Night",
    category: "comedy",
    subsegment: null,
    start_time: "2026-07-25T02:00:00Z",
    end_time: null,
    status: "scheduled",
    confidence: "confirmed",
    price_min: null,
    price_max: null,
    currency: null,
    is_free: null,
    ticket_url: "https://tix.example/e1",
    image_url: null,
    artist_ids: [],
    source_name: null,
    source_url: null,
    venue: { name: "The Hideout", city: "Austin", area: "Downtown", address: "617 Congress", lat: 30.27, lng: -97.74 },
    ...over,
  };
}

describe("reshapePromoted", () => {
  it("keys the feed with a promoted: prefix that cannot collide with a licensed id", () => {
    const [e] = reshapePromoted([row()], new Map());
    expect(e.licensed_event_id).toBe("promoted:e1");
    expect(e.external_id).toBe("e1");
    expect(e.source_provider).toBe("promoted");
  });

  it("preserves a disputed promoted event (shown-never-hidden at the data layer)", () => {
    const [e] = reshapePromoted([row({ confidence: "disputed" })], new Map());
    expect(e.confidence).toBe("disputed");
  });

  it("resolves performer from the artist map and OMITS unknown ids (no fabricated names)", () => {
    const names = new Map([["a1", "Spoon"]]);
    const [e] = reshapePromoted(
      [row({ artist_ids: ["a1", "a-missing"] })],
      names,
    );
    expect(e.performer).toBe("Spoon"); // "a-missing" produces no name, not a guess
  });

  it("leaves performer null when there are no artists (never invents one)", () => {
    const [e] = reshapePromoted([row({ artist_ids: [] })], new Map());
    expect(e.performer).toBeNull();
  });

  it("carries source provenance through as data (origin_name/origin_url)", () => {
    const [e] = reshapePromoted(
      [row({ source_name: "Mohawk Austin", source_url: "https://mohawkaustin.com" })],
      new Map(),
    );
    expect(e.origin_name).toBe("Mohawk Austin");
    expect(e.origin_url).toBe("https://mohawkaustin.com");
  });

  it("leaves absent provenance null — the UI's generic wording, never a guess", () => {
    const [e] = reshapePromoted([row()], new Map());
    expect(e.origin_name).toBeNull();
    expect(e.origin_url).toBeNull();
  });

  it("maps venue + card fields through faithfully", () => {
    const [e] = reshapePromoted([row({ price_min: 0, is_free: true })], new Map());
    expect(e.venue_name).toBe("The Hideout");
    expect(e.venue_area).toBe("Downtown");
    expect(e.venue_lat).toBe(30.27);
    expect(e.ticket_url).toBe("https://tix.example/e1");
    expect(e.category).toBe("comedy");
    expect(e.is_free).toBe(true);
  });

  it("is null-safe when the venue embed is absent", () => {
    const [e] = reshapePromoted([row({ venue: null })], new Map());
    expect(e.venue_name).toBeNull();
    expect(e.venue_lat).toBeNull();
  });

  it("falls back to performer then a neutral title when title is null (never blank/undefined)", () => {
    const withPerf = reshapePromoted(
      [row({ title: null, artist_ids: ["a1"] })],
      new Map([["a1", "Spoon"]]),
    )[0];
    expect(withPerf.title).toBe("Spoon");
    const bare = reshapePromoted([row({ title: null, artist_ids: [] })], new Map())[0];
    expect(bare.title).toBe("Live event");
  });
});
