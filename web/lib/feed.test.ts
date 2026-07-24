import { describe, it, expect } from "vitest";
import { groupByDomain, normalizeDomain } from "./feed";
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
    confidence: "confirmed",
    ...part,
  };
}

describe("normalizeDomain", () => {
  it("keeps known ids, folds null/unknown into unmapped", () => {
    expect(normalizeDomain("live-music")).toBe("live-music");
    expect(normalizeDomain(null)).toBe("unmapped");
    expect(normalizeDomain("some-new-genre-not-in-taxonomy")).toBe("unmapped");
  });
});

describe("groupByDomain — nothing is silently dropped", () => {
  it("preserves total count across all groups", () => {
    const events = [
      ev({ category: "live-music" }),
      ev({ category: "comedy" }),
      ev({ category: null }),
      ev({ category: "totally-unknown-category" }),
    ];
    const groups = groupByDomain(events);
    const rendered = groups.reduce((n, g) => n + g.items.length, 0);
    expect(rendered).toBe(events.length); // no row lost
  });

  it("routes unknown/null categories into the Other (unmapped) bucket", () => {
    const groups = groupByDomain([
      ev({ category: "totally-unknown-category" }),
      ev({ category: null }),
    ]);
    const other = groups.find((g) => g.domain.id === "unmapped");
    expect(other).toBeTruthy();
    expect(other!.items).toHaveLength(2);
  });

  it("renders a disputed event even when its category is unknown", () => {
    const disputed = ev({ category: "mystery", confidence: "disputed", title: "DISPUTED" });
    const groups = groupByDomain([disputed]);
    const all = groups.flatMap((g) => g.items);
    expect(all.map((e) => e.title)).toContain("DISPUTED");
  });

  it("keeps a large domain fully — no per-domain cap", () => {
    const events = Array.from({ length: 50 }, () => ev({ category: "live-music" }));
    const groups = groupByDomain(events);
    const music = groups.find((g) => g.domain.id === "live-music");
    expect(music!.items).toHaveLength(50);
  });
});
