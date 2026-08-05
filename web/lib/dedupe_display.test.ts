import { describe, expect, it } from "vitest";
import { dedupeEvents, dedupeKey, normalizeForDedupe } from "./dedupe_display";
import type { LicensedEvent } from "./licensed";

function ev(over: Partial<LicensedEvent> = {}): LicensedEvent {
  return {
    licensed_event_id: over.licensed_event_id ?? `id-${Math.abs(JSON.stringify(over).split("").reduce((a, c) => a + c.charCodeAt(0), 0))}`,
    source_provider: "ticketmaster",
    external_id: "x",
    title: "O.A.R., Gavin DeGraw, Lisa Loeb",
    category: "live-music",
    subsegment: "Rock",
    performer: "O.A.R., Gavin DeGraw, Lisa Loeb",
    start_time: "2026-08-05T23:30:00Z",
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: 45,
    price_max: 120,
    currency: "USD",
    is_free: false,
    ticket_url: "https://tm.example/t",
    image_url: "https://img.example/i.jpg",
    venue_name: "Austin City Limits Live at The Moody Theater",
    venue_city: "Austin",
    venue_area: "Downtown",
    venue_address: "310 Willie Nelson Blvd",
    venue_lat: 30.26,
    venue_lng: -97.75,
    venue_url: null,
    venue_phone: null,
    confidence: "confirmed",
    ...over,
  };
}

describe("normalizeForDedupe", () => {
  it("squashes punctuation, case, and articles", () => {
    expect(normalizeForDedupe("O.A.R., Gavin DeGraw")).toBe(
      normalizeForDedupe("OAR Gavin DeGraw"));
    expect(normalizeForDedupe("The Moody Theater")).toBe(
      normalizeForDedupe("Moody   Theater!"));
  });
});

describe("dedupeKey", () => {
  it("is null without venue, title, or a parseable start time — absence of identity never becomes identity", () => {
    expect(dedupeKey(ev({ venue_name: null }))).toBeNull();
    expect(dedupeKey(ev({ performer: null, title: "" }))).toBeNull();
    expect(dedupeKey(ev({ start_time: null }))).toBeNull();
    expect(dedupeKey(ev({ start_time: "not-a-date" }))).toBeNull();
  });
});

describe("dedupeEvents", () => {
  it("collapses the founder's O.A.R. case: same show via two providers", () => {
    const tm = ev({ licensed_event_id: "a", source_provider: "ticketmaster", subsegment: "Rock" });
    const feed = ev({ licensed_event_id: "b", source_provider: "jsonld", subsegment: "Alternative", price_min: null, price_max: null, image_url: null });
    const { kept, collapsed } = dedupeEvents([tm, feed]);
    expect(kept).toHaveLength(1);
    expect(kept[0].licensed_event_id).toBe("a"); // richer ticketing record wins
    expect(collapsed).toHaveLength(1);
    expect(collapsed[0].licensed_event_id).toBe("b");
  });

  it("does NOT collapse same title at DIFFERENT venues (Summer Stock case)", () => {
    const a = ev({ licensed_event_id: "a", title: "Summer Stock Austin", performer: null, venue_name: "McCullough Theater" });
    const b = ev({ licensed_event_id: "b", title: "Summer Stock Austin", performer: null, venue_name: "Bass Concert Hall" });
    expect(dedupeEvents([a, b]).kept).toHaveLength(2);
  });

  it("does NOT collapse same title/venue at different times (matinee vs evening)", () => {
    const a = ev({ licensed_event_id: "a", start_time: "2026-08-05T18:00:00Z" });
    const b = ev({ licensed_event_id: "b", start_time: "2026-08-06T00:30:00Z" });
    expect(dedupeEvents([a, b]).kept).toHaveLength(2);
  });

  it("rows disagreeing on STATUS never collapse — a cancellation must not hide behind a live card (evaluator #191)", () => {
    const live = ev({ licensed_event_id: "a", status: "scheduled" });
    const cancelled = ev({ licensed_event_id: "b", status: "cancelled", source_provider: "jsonld" });
    expect(dedupeEvents([live, cancelled]).kept).toHaveLength(2);
    const postponed = ev({ licensed_event_id: "c", status: "postponed", source_provider: "jsonld" });
    expect(dedupeEvents([live, postponed]).kept).toHaveLength(2);
  });

  it("spelling variants of the SAME status still collapse (canceled == cancelled)", () => {
    const us = ev({ licensed_event_id: "a", status: "canceled" });
    const uk = ev({ licensed_event_id: "b", status: "cancelled", source_provider: "jsonld", image_url: null });
    const { kept } = dedupeEvents([us, uk]);
    expect(kept).toHaveLength(1);
  });

  it("a disputed row NEVER collapses, in either direction (shown-never-hidden)", () => {
    const clean = ev({ licensed_event_id: "a" });
    const disputed = ev({ licensed_event_id: "b", confidence: "disputed" });
    const r1 = dedupeEvents([clean, disputed]);
    expect(r1.kept).toHaveLength(2);
    const r2 = dedupeEvents([disputed, clean]);
    expect(r2.kept).toHaveLength(2);
  });

  it("richness beats provider authority; authority breaks ties; id breaks everything", () => {
    const richPromoted = ev({ licensed_event_id: "p", source_provider: "promoted" });
    const poorTm = ev({ licensed_event_id: "t", source_provider: "ticketmaster", price_min: null, price_max: null, is_free: null, image_url: null, venue_address: null, venue_lat: null, ticket_url: null });
    expect(dedupeEvents([poorTm, richPromoted]).kept[0].licensed_event_id).toBe("p");

    const tmSameRich = ev({ licensed_event_id: "t2", source_provider: "ticketmaster" });
    const ebSameRich = ev({ licensed_event_id: "e2", source_provider: "eventbrite" });
    expect(dedupeEvents([ebSameRich, tmSameRich]).kept[0].licensed_event_id).toBe("t2");
  });

  it("same venue NAME at conflicting LOCATIONS never collapses (evaluator #191 r2)", () => {
    const east = ev({ licensed_event_id: "a", venue_area: "East Austin" });
    const south = ev({ licensed_event_id: "b", venue_area: "South Congress", source_provider: "jsonld" });
    expect(dedupeEvents([east, south]).kept).toHaveLength(2);

    const addr1 = ev({ licensed_event_id: "c", venue_area: null, venue_address: "100 Main St" });
    const addr2 = ev({ licensed_event_id: "d", venue_area: null, venue_address: "900 Far Rd", source_provider: "jsonld" });
    expect(dedupeEvents([addr1, addr2]).kept).toHaveLength(2);

    const near = ev({ licensed_event_id: "e", venue_area: null, venue_address: null, venue_lat: 30.26, venue_lng: -97.75 });
    const far = ev({ licensed_event_id: "f", venue_area: null, venue_address: null, venue_lat: 30.40, venue_lng: -97.75, source_provider: "jsonld" });
    expect(dedupeEvents([near, far]).kept).toHaveLength(2);
  });

  it("an ABSENT location signal stays compatible — one provider omitting the address must not split a true duplicate", () => {
    const withAddr = ev({ licensed_event_id: "a" });
    const noAddr = ev({ licensed_event_id: "b", source_provider: "jsonld", venue_address: null, venue_area: null, venue_lat: null, venue_lng: null, image_url: null });
    const { kept } = dedupeEvents([withAddr, noAddr]);
    expect(kept).toHaveLength(1);
    expect(kept[0].licensed_event_id).toBe("a");
  });

  it("preserves feed order and keeps every non-duplicate", () => {
    const a = ev({ licensed_event_id: "a", title: "Show One", performer: "Show One", venue_name: "Mohawk" });
    const b = ev({ licensed_event_id: "b", title: "Show Two", performer: "Show Two", venue_name: "Continental Club" });
    const dupOfA = ev({ licensed_event_id: "c", title: "Show One", performer: "Show One", venue_name: "Mohawk", source_provider: "jsonld", image_url: null });
    const { kept, collapsed } = dedupeEvents([a, b, dupOfA]);
    expect(kept.map((e) => e.licensed_event_id)).toEqual(["a", "b"]);
    expect(collapsed.map((e) => e.licensed_event_id)).toEqual(["c"]);
  });
});
