import { describe, expect, it } from "vitest";
import { dedupeEvents } from "./dedupe_display";
import type { LicensedEvent } from "./licensed";

function ev(over: Partial<LicensedEvent> = {}): LicensedEvent {
  return {
    licensed_event_id: "x", source_provider: "ticketmaster", external_id: "x",
    title: "Same Show", category: "live-music", subsegment: "Rock",
    performer: "Same Show", start_time: "2026-08-05T23:30:00Z", end_time: null,
    status: "scheduled", on_sale_status: null, price_min: 45, price_max: 120,
    currency: "USD", is_free: false, ticket_url: "https://tm/t",
    image_url: "https://img/i.jpg", venue_name: "The Parish", venue_city: "Austin",
    venue_area: "Downtown", venue_address: "310 Willie Nelson Blvd",
    venue_lat: 30.26, venue_lng: -97.75, venue_url: null, venue_phone: null,
    confidence: "confirmed", ...over,
  };
}

describe("claim", () => {
  it("three rows, location-less keeper", () => {
    const a = ev({ licensed_event_id: "a", source_provider: "ticketmaster",
      venue_area: null, venue_address: null, venue_lat: null, venue_lng: null,
      venue_url: "https://venue/x", origin_url: "https://origin/x" });
    const b = ev({ licensed_event_id: "b", source_provider: "jsonld",
      venue_area: null, venue_address: "100 Main St", venue_lat: 30.26, venue_lng: -97.75 });
    const c = ev({ licensed_event_id: "c", source_provider: "jsonld",
      venue_area: null, venue_address: "900 Far Rd", venue_lat: 30.45, venue_lng: -97.60 });
    const r = dedupeEvents([a, b, c]);
    throw new Error("ABC kept="+JSON.stringify(r.kept.map(x=>x.licensed_event_id))+" collapsed="+JSON.stringify(r.collapsed.map(x=>x.licensed_event_id))+" BC="+JSON.stringify(dedupeEvents([b,c]).kept.map(x=>x.licensed_event_id))+" BAC="+JSON.stringify(dedupeEvents([b,a,c]).kept.map(x=>x.licensed_event_id)));
    const r2 = dedupeEvents([b, c]);
    console.log("BC kept:", r2.kept.map(x => x.licensed_event_id));
    // ordering variant: conflicting row first
    const r3 = dedupeEvents([b, a, c]);
    console.log("BAC kept:", r3.kept.map(x => x.licensed_event_id), "collapsed:", r3.collapsed.map(x => x.licensed_event_id));
  });
});
