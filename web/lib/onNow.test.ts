import { describe, it, expect } from "vitest";
import { showOnNow } from "./onNow";
import type { LicensedEvent } from "./licensed";

function ev(part: Partial<LicensedEvent>): LicensedEvent {
  return {
    licensed_event_id: "x",
    source_provider: "promoted",
    external_id: "x",
    title: "t",
    category: "live-music",
    subsegment: null,
    performer: null,
    start_time: null,
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

describe("showOnNow — 60-min hedge, no invented end", () => {
  const now = Date.parse("2026-09-10T20:00:00-05:00");

  it("printed end still ahead → on now", () => {
    expect(showOnNow(ev({
      start_time: "2026-09-10T18:00:00-05:00",
      end_time: "2026-09-10T21:00:00-05:00",
    }), now)).toBe(true);
  });

  it("printed end already passed → not on now", () => {
    expect(showOnNow(ev({
      start_time: "2026-09-10T15:00:00-05:00",
      end_time: "2026-09-10T16:00:00-05:00",
    }), now)).toBe(false);
  });

  it("no end, started 20 min ago → on now", () => {
    expect(showOnNow(ev({
      start_time: "2026-09-10T19:40:00-05:00",
    }), now)).toBe(true);
  });

  it("no end, started 3 hours ago → not on now", () => {
    expect(showOnNow(ev({
      start_time: "2026-09-10T03:00:00-05:00",
    }), now)).toBe(false);
  });

  it("date-only start → not on now", () => {
    expect(showOnNow(ev({ start_time: "2026-09-10" }), now)).toBe(false);
  });
});
