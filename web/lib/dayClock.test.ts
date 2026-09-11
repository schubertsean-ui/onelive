import { describe, it, expect } from "vitest";
import { byClock } from "./dayClock";
import type { LicensedEvent } from "./licensed";

function ev(part: Partial<LicensedEvent>): LicensedEvent {
  return {
    licensed_event_id: Math.random().toString(36).slice(2),
    source_provider: "ticketmaster",
    external_id: "x",
    title: "t",
    category: "live-music",
    subsegment: null,
    performer: null,
    start_time: "2026-07-25T00:00:00Z",
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: null,
    price_max: null,
    currency: null,
    is_free: null,
    ticket_url: null,
    image_url: null,
    venue_name: "v",
    venue_city: "Austin",
    venue_area: null,
    venue_address: null,
    venue_lat: null,
    venue_lng: null,
    venue_url: null,
    venue_phone: null,
    confidence: "confirmed",
    ...part,
  };
}

describe("byClock — soonest first, TBA last, nothing dropped", () => {
  it("keeps Date TBA and sorts printed clocks earliest to latest", () => {
    const seven = ev({
      licensed_event_id: "7pm",
      start_time: "2026-10-16T00:00:00Z",
    });
    const noon = ev({
      licensed_event_id: "noon",
      start_time: "2026-10-15T17:00:00Z",
    });
    const tba = ev({ licensed_event_id: "tba", start_time: null });
    const out = byClock([tba, seven, noon]);
    expect(out.timed.map((row: LicensedEvent) => row.licensed_event_id)).toEqual([
      "noon",
      "7pm",
    ]);
    expect(out.undated.map((row: LicensedEvent) => row.licensed_event_id)).toEqual([
      "tba",
    ]);
    expect(out.timed.length + out.undated.length).toBe(3);
  });
});
