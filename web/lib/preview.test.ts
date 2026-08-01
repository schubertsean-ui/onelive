import { describe, it, expect } from "vitest";
import { contextualPreview } from "./preview";
import type { LicensedEvent } from "./licensed";

// A complete LicensedEvent with sane defaults; each test overrides only what it
// exercises (category / performer / title). Kept fully typed — no casts — so the
// test breaks if the row shape drifts.
function ev(over: Partial<LicensedEvent>): LicensedEvent {
  const base: LicensedEvent = {
    licensed_event_id: "x1",
    source_provider: "ticketmaster",
    external_id: "e1",
    title: "The Show",
    performer: "The Band",
    category: "live-music",
    subsegment: null,
    status: "scheduled",
    confidence: "confirmed",
    start_time: "2026-08-01T02:00:00Z",
    end_time: null,
    price_min: null,
    price_max: null,
    currency: "USD",
    is_free: null,
    on_sale_status: null,
    ticket_url: null,
    image_url: null,
    venue_name: "The Room",
    venue_city: "Austin",
    venue_area: "Downtown",
    venue_address: null,
    venue_lat: null,
    venue_lng: null,
    venue_url: null,
    venue_phone: null,
  };
  return { ...base, ...over };
}

describe("contextualPreview — polymorphic by event type", () => {
  it("music keeps the three-service listen row", () => {
    const p = contextualPreview(ev({ category: "live-music", performer: "Khruangbin" }));
    expect(p?.label).toBe("Hear them");
    expect(p?.links.map((l) => l.service)).toEqual(["Spotify", "Apple Music", "YouTube"]);
    expect(p?.links[0].url).toContain("Khruangbin");
  });

  it("nightlife is treated as music", () => {
    expect(contextualPreview(ev({ category: "nightlife", performer: "DJ X" }))?.label).toBe("Hear them");
  });

  it("a talk searches for the speaker's lectures", () => {
    const p = contextualPreview(ev({ category: "ideas", performer: "Jane Goodall", title: "An Evening With" }));
    expect(p?.label).toBe("Watch a talk");
    expect(p?.links).toHaveLength(1);
    expect(p?.links[0].service).toBe("YouTube");
    expect(decodeURIComponent(p!.links[0].url)).toContain("Jane Goodall talk lecture");
  });

  it("comedy searches for a set", () => {
    expect(contextualPreview(ev({ category: "comedy", performer: "Comic Y" }))?.label).toBe("See a set");
  });

  it("film searches the TITLE for a trailer, not the performer", () => {
    const p = contextualPreview(ev({ category: "film", title: "Dune", performer: "n/a" }));
    expect(p?.label).toBe("Watch the trailer");
    expect(decodeURIComponent(p!.links[0].url)).toContain("Dune trailer");
  });

  it("film with a blank title falls back to the performer, never a bare 'trailer' search", () => {
    const p = contextualPreview(ev({ category: "film", title: "  ", performer: "Austin Film Society" }));
    const url = decodeURIComponent(p!.links[0].url);
    expect(url).toContain("Austin Film Society trailer");
    expect(url).not.toMatch(/search_query=\s*trailer\s*$/); // never just "trailer"
  });

  it("visual arts links to a web search for the artist's work", () => {
    const p = contextualPreview(ev({ category: "visual-arts", performer: "Painter Z" }));
    expect(p?.label).toBe("See their work");
    expect(p?.links[0].url).toContain("google.com/search");
  });

  it("an un-previewable type is an honest gap (null), never filler", () => {
    expect(contextualPreview(ev({ category: "food-drink" }))).toBeNull();
    expect(contextualPreview(ev({ category: "sports" }))).toBeNull();
  });

  it("no name to search on → null", () => {
    expect(contextualPreview(ev({ category: "live-music", performer: "", title: "  " }))).toBeNull();
  });

  it("a very long performer name falls back to the title", () => {
    const long = "x".repeat(90);
    const p = contextualPreview(ev({ category: "live-music", performer: long, title: "Real Title" }));
    expect(p?.links[0].url).toContain("Real%20Title");
  });
});
