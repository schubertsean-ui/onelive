import { describe, it, expect } from "vitest";
import type { LicensedEvent } from "./licensed";
import {
  LOOKING_FOR_MORE,
  kindChip,
  lookingForMore,
  detailsThin,
  venueAreaLabel,
  venueSiteHost,
  printablePlace,
} from "./cardSlots";

function ev(over: Partial<LicensedEvent> = {}): LicensedEvent {
  return {
    licensed_event_id: "e1",
    source_provider: "ticketmaster",
    external_id: "x",
    title: "Jutes",
    category: "live-music",
    subsegment: "Rock",
    performer: "Jutes",
    start_time: "2026-09-08T23:00:00Z",
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: 20,
    price_max: 20,
    currency: "USD",
    is_free: false,
    ticket_url: "https://ticketmaster.com/e/1",
    image_url: null,
    venue_name: "Emo's Austin",
    venue_city: "Austin",
    venue_area: "East",
    venue_address: "2015 E Riverside Dr",
    venue_lat: 30.24,
    venue_lng: -97.72,
    venue_url: "https://emosaustin.com",
    venue_phone: null,
    confidence: "confirmed",
    ...over,
  };
}

describe("card slots — print only what a desk printed", () => {
  it("kind chip joins category + printed subgenre", () => {
    expect(kindChip(ev())).toBe("Live Music \u00b7 Rock");
    expect(kindChip(ev({ subsegment: null }))).toBe("Live Music");
    expect(kindChip(ev({ category: null, subsegment: null }))).toBeNull();
  });

  it("looking-for-more only when title or place or topic is empty", () => {
    expect(lookingForMore(ev())).toBe(false);
    expect(lookingForMore(ev({ title: "", performer: "", venue_name: "Emo's Austin" }))).toBe(true);
    expect(lookingForMore(ev({ venue_name: "" }))).toBe(true);
    expect(lookingForMore(ev({ category: null, title: "", performer: "Act", venue_name: "Emo's" }))).toBe(true);
    expect(LOOKING_FOR_MORE).toContain("looking for more information");
  });

  it("Unknown Venue is a hole, not a place", () => {
    expect(printablePlace(ev({ venue_name: "Unknown Venue" }))).toBeNull();
    expect(printablePlace(ev({ venue_name: "unknown venue" }))).toBeNull();
    expect(printablePlace(ev({ venue_name: "Emo's Austin" }))).toBe("Emo's Austin");
    expect(lookingForMore(ev({ venue_name: "Unknown Venue" }))).toBe(true);
  });

  it("quiet ? when unverified, disputed, undated, or looking-for-more", () => {
    expect(detailsThin(ev())).toBe(false);
    expect(detailsThin(ev({ confidence: "unverified" }))).toBe(true);
    expect(detailsThin(ev({ confidence: "disputed" }))).toBe(true);
    expect(detailsThin(ev({ start_time: null }))).toBe(true);
    expect(detailsThin(ev({ venue_name: "" }))).toBe(true);
  });

  it("mini-map uses printed area, else city, never invented miles", () => {
    expect(venueAreaLabel(ev())).toBe("East");
    expect(venueAreaLabel(ev({ venue_area: null }))).toBe("Austin");
    expect(venueAreaLabel(ev({ venue_area: null, venue_city: null }))).toBeNull();
  });

  it("venue site host drops ticketing hosts and javascript urls", () => {
    expect(venueSiteHost("https://emosaustin.com/calendar")).toBe("emosaustin.com");
    expect(venueSiteHost("https://www.ticketmaster.com/venue/emos")).toBeNull();
    expect(venueSiteHost("javascript:alert(1)")).toBeNull();
    expect(venueSiteHost(null)).toBeNull();
  });
});
