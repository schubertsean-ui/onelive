import { describe, it, expect, vi } from "vitest";
import type { LicensedEvent, SparkLine } from "./licensed";
import { sparkKey, buildSparkInList, attachSparkLines, withSparkLines } from "./spark";

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

describe("sparkKey", () => {
  it("lower-cases and trims", () => {
    expect(sparkKey("  The Meridian ")).toBe("the meridian");
    expect(sparkKey("MARA QUINN")).toBe("mara quinn");
  });
  it("maps null/undefined to empty", () => {
    expect(sparkKey(null)).toBe("");
    expect(sparkKey(undefined)).toBe("");
  });
});

describe("buildSparkInList", () => {
  it("double-quotes each key and comma-joins", () => {
    expect(buildSparkInList(["the meridian", "mara quinn"])).toBe(
      'in.("the meridian","mara quinn")',
    );
  });
  it("doubles an embedded quote so the value cannot break out", () => {
    expect(buildSparkInList(['a"b'])).toBe('in.("a""b")');
  });
});

describe("attachSparkLines", () => {
  it("attaches by case-insensitive performer key", () => {
    const events = [ev({ performer: "the meridian" })];
    const out = attachSparkLines(events, new Map([["the meridian", SPARK]]));
    expect(out[0].spark).toEqual(SPARK);
  });

  it("leaves an event without a matching key untouched", () => {
    const events = [ev({ performer: "Someone Else" })];
    const out = attachSparkLines(events, new Map([["the meridian", SPARK]]));
    expect(out[0].spark).toBeUndefined();
  });

  it("preserves order and length (display only, never reorders)", () => {
    const events = [ev({ licensed_event_id: "a", performer: "A" }), ev({ licensed_event_id: "b", performer: "the meridian" }), ev({ licensed_event_id: "c", performer: "C" })];
    const out = attachSparkLines(events, new Map([["the meridian", SPARK]]));
    expect(out.map((e) => e.licensed_event_id)).toEqual(["a", "b", "c"]);
    expect(out[1].spark).toEqual(SPARK);
    expect(out[0].spark).toBeUndefined();
    expect(out[2].spark).toBeUndefined();
  });

  it("does not mutate the input events", () => {
    const events = [ev({ performer: "the meridian" })];
    attachSparkLines(events, new Map([["the meridian", SPARK]]));
    expect(events[0].spark).toBeUndefined();
  });
});

describe("withSparkLines — additive, never blanks the feed", () => {
  it("returns the feed unchanged when the Spark Line read fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const events = [ev({ performer: "the meridian" }), ev({ licensed_event_id: "y", performer: "Other" })];
    const out = await withSparkLines(events);
    expect(out.map((e) => e.licensed_event_id)).toEqual(["x1", "y"]);
    expect(out.every((e) => e.spark == null)).toBe(true);
    vi.unstubAllGlobals();
  });
});
