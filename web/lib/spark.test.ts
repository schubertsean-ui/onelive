import { describe, it, expect, vi } from "vitest";
import type { LicensedEvent, SparkLine } from "./licensed";
import { eventRef, buildSparkInList, attachSparkLines, withSparkLines } from "./spark";

function ev(over: Partial<LicensedEvent>): LicensedEvent {
  const base: LicensedEvent = {
    licensed_event_id: "x1", source_provider: "ticketmaster", external_id: "e1",
    title: "The Show", performer: "The Meridian", category: "live-music",
    subsegment: null, status: "scheduled", confidence: "confirmed",
    start_time: "2026-08-01T02:00:00Z", end_time: null, price_min: null,
    price_max: null, currency: "USD", is_free: null, on_sale_status: null,
    ticket_url: null, image_url: null, venue_name: "The Room", venue_city: "Austin",
    venue_area: "Downtown", venue_address: null, venue_lat: null, venue_lng: null,
    venue_url: null, venue_phone: null,
  };
  return { ...base, ...over };
}

const SPARK: SparkLine = { text: "brass. menace. amen.", tier: "C", attribution: null };

describe("eventRef", () => {
  it("returns the trimmed identity ref", () => {
    expect(eventRef(ev({ artist_ref: "  mbid-1 " }))).toBe("mbid-1");
  });
  it("is empty when no identity is resolved (name is never an identity)", () => {
    expect(eventRef(ev({ artist_ref: null }))).toBe("");
    expect(eventRef(ev({ artist_ref: undefined }))).toBe("");
    expect(eventRef(ev({ performer: "The Meridian" }))).toBe(""); // name ignored
  });
});

describe("buildSparkInList", () => {
  it("double-quotes each ref and comma-joins", () => {
    expect(buildSparkInList(["mbid-1", "wd:Q42"])).toBe('in.("mbid-1","wd:Q42")');
  });
  it("doubles an embedded quote so the value cannot break out", () => {
    expect(buildSparkInList(['a"b'])).toBe('in.("a""b")');
  });
});

describe("attachSparkLines — by IDENTITY, never by name", () => {
  it("attaches when the event's identity ref matches", () => {
    const events = [ev({ artist_ref: "mbid-1" })];
    const out = attachSparkLines(events, new Map([["mbid-1", SPARK]]));
    expect(out[0].spark).toEqual(SPARK);
  });

  it("does NOT attach on a same-name act with a different identity ref", () => {
    // The exact hazard: two acts named "The Meridian", one line approved for
    // mbid-1. The mbid-2 act must NEVER inherit it.
    const events = [
      ev({ licensed_event_id: "a", performer: "The Meridian", artist_ref: "mbid-1" }),
      ev({ licensed_event_id: "b", performer: "The Meridian", artist_ref: "mbid-2" }),
    ];
    const out = attachSparkLines(events, new Map([["mbid-1", SPARK]]));
    expect(out[0].spark).toEqual(SPARK);
    expect(out[1].spark).toBeUndefined();
  });

  it("does NOT attach to a ref-less event even if the name would have matched", () => {
    // Fail closed by construction: no identity resolved => no line, regardless of
    // any name-based coincidence.
    const events = [ev({ performer: "The Meridian", artist_ref: null })];
    const out = attachSparkLines(events, new Map([["the meridian", SPARK], ["mbid-1", SPARK]]));
    expect(out[0].spark).toBeUndefined();
  });

  it("leaves an event whose ref has no row untouched", () => {
    const events = [ev({ artist_ref: "mbid-9" })];
    const out = attachSparkLines(events, new Map([["mbid-1", SPARK]]));
    expect(out[0].spark).toBeUndefined();
  });

  it("preserves order and length (display only, never reorders)", () => {
    const events = [
      ev({ licensed_event_id: "a", artist_ref: "r-a" }),
      ev({ licensed_event_id: "b", artist_ref: "mbid-1" }),
      ev({ licensed_event_id: "c", artist_ref: "r-c" }),
    ];
    const out = attachSparkLines(events, new Map([["mbid-1", SPARK]]));
    expect(out.map((e) => e.licensed_event_id)).toEqual(["a", "b", "c"]);
    expect(out[1].spark).toEqual(SPARK);
    expect(out[0].spark).toBeUndefined();
    expect(out[2].spark).toBeUndefined();
  });

  it("does not mutate the input events", () => {
    const events = [ev({ artist_ref: "mbid-1" })];
    attachSparkLines(events, new Map([["mbid-1", SPARK]]));
    expect(events[0].spark).toBeUndefined();
  });
});

describe("withSparkLines — additive, never blanks the feed", () => {
  it("returns the feed unchanged when the Spark Line read fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const events = [ev({ artist_ref: "mbid-1" }), ev({ licensed_event_id: "y", artist_ref: "mbid-2" })];
    const out = await withSparkLines(events);
    expect(out.map((e) => e.licensed_event_id)).toEqual(["x1", "y"]);
    expect(out.every((e) => e.spark == null)).toBe(true);
    vi.unstubAllGlobals();
  });

  it("attaches nothing (and makes no request) when no event has a resolved identity", async () => {
    const spy = vi.fn();
    vi.stubGlobal("fetch", spy);
    const events = [ev({ performer: "The Meridian", artist_ref: null })];
    const out = await withSparkLines(events);
    expect(out[0].spark).toBeUndefined();
    expect(spy).not.toHaveBeenCalled(); // fail closed with no query
    vi.unstubAllGlobals();
  });
});
