import { describe, it, expect } from "vitest";
import {
  groupByDomain,
  normalizeDomain,
  eventTiming,
  liveEvents,
  dayTabs,
  applyFilters,
  applyDesire,
  buildPlan,
  genreFacet,
} from "./feed";
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

const NOW = Date.parse("2026-07-24T20:00:00Z");

describe("eventTiming / liveEvents — only still-relevant events show", () => {
  it("classifies upcoming, on-now (started, not ended), and ended", () => {
    const upcoming = ev({ start_time: "2026-07-24T23:00:00Z" });
    const onNowKnownEnd = ev({ start_time: "2026-07-24T19:00:00Z", end_time: "2026-07-24T22:00:00Z" });
    const onNowAssumed = ev({ start_time: "2026-07-24T18:30:00Z", end_time: null }); // +3h assumed
    const ended = ev({ start_time: "2026-07-24T15:00:00Z", end_time: "2026-07-24T17:00:00Z" });
    expect(eventTiming(upcoming, NOW)).toBe("upcoming");
    expect(eventTiming(onNowKnownEnd, NOW)).toBe("on-now");
    expect(eventTiming(onNowAssumed, NOW)).toBe("on-now");
    expect(eventTiming(ended, NOW)).toBe("ended");
  });

  it("never hides a date-TBA event (treated as upcoming)", () => {
    expect(eventTiming(ev({ start_time: null }), NOW)).toBe("upcoming");
  });

  it("liveEvents drops only ended, keeps a disputed on-now event", () => {
    const disputedOnNow = ev({ start_time: "2026-07-24T19:30:00Z", confidence: "disputed" });
    const ended = ev({ start_time: "2026-07-24T10:00:00Z", end_time: "2026-07-24T12:00:00Z" });
    const live = liveEvents([disputedOnNow, ended], NOW);
    expect(live).toContain(disputedOnNow); // time filter, never a confidence filter
    expect(live).not.toContain(ended);
  });
});

describe("dayTabs + applyFilters — lenses that narrow the view, not the trust", () => {
  it("builds All + Today + next 7 days", () => {
    const tabs = dayTabs(NOW, 7);
    expect(tabs[0].key).toBe("all");
    expect(tabs[1].label).toBe("Today");
    expect(tabs[2].label).toBe("Tomorrow");
    expect(tabs).toHaveLength(9); // all + today + 7 more
  });

  it("a disputed event still passes a domain lens it matches", () => {
    const d = ev({ category: "comedy", confidence: "disputed" });
    const out = applyFilters([d, ev({ category: "live-music" })], { domains: new Set(["comedy"]) });
    expect(out).toEqual([d]); // lens narrows by domain; disputed is not special-dropped
  });

  it("freeOnly keeps free events (is_free or price 0)", () => {
    const free = ev({ is_free: true });
    const paid = ev({ is_free: false, price_min: 20 });
    expect(applyFilters([free, paid], { freeOnly: true })).toEqual([free]);
  });
});

describe("applyDesire — Ask layer lenses are backed and non-gating", () => {
  it("'free' matches free events with a why", () => {
    const free = ev({ is_free: true, start_time: "2026-07-24T23:00:00Z" });
    const paid = ev({ is_free: false, price_min: 30 });
    expect(applyDesire([free, paid], "free", NOW)).toEqual([free]);
  });
  it("'laugh' matches the comedy domain", () => {
    const c = ev({ category: "comedy" });
    expect(applyDesire([c, ev({ category: "live-music" })], "laugh", NOW)).toEqual([c]);
  });
  it("an unknown desire key returns nothing (never throws)", () => {
    expect(applyDesire([ev({})], "nonsense", NOW)).toEqual([]);
  });
});

describe("buildPlan — a suggestion assembled from the honest set", () => {
  it("fills night blocks with non-repeating events, soonest first", () => {
    const events = [
      ev({ licensed_event_id: "early", start_time: "2026-07-24T23:30:00Z" }), // ~6:30pm CT
      ev({ licensed_event_id: "main", start_time: "2026-07-25T01:30:00Z" }), // ~8:30pm CT
      ev({ licensed_event_id: "late", start_time: "2026-07-25T04:00:00Z" }), // ~11pm CT
    ];
    const plan = buildPlan(events, "night", NOW);
    const ids = plan.map((s) => s.event.licensed_event_id);
    expect(new Set(ids).size).toBe(ids.length); // no event used twice
    expect(plan.every((s) => s.why.length > 0)).toBe(true); // provenance on every slot
  });
  it("returns an empty plan when nothing fits (never throws/fabricates)", () => {
    expect(buildPlan([], "night", NOW)).toEqual([]);
  });
});

describe("genre rail (canonical Layer-1) — facet + filter", () => {
  const events = [
    ev({ subsegment: "Alternative Rock" }), // -> indie-alternative
    ev({ subsegment: "Indie" }), //            -> indie-alternative
    ev({ subsegment: "Cumbia" }), //           -> latin
    ev({ subsegment: "R&B" }), //              -> rnb-soul
    ev({ subsegment: "Polka" }), //            -> null (Other, no chip)
    ev({ subsegment: null }), //               -> null (Other, no chip)
  ];

  it("derives the present canonical genres with counts, most-common first", () => {
    const rail = genreFacet(events);
    expect(rail[0]).toEqual({ id: "indie-alternative", label: "Indie/Alternative", n: 2 });
    const ids = rail.map((r) => r.id);
    expect(ids).toContain("latin");
    expect(ids).toContain("rnb-soul");
    // "Polka" and the null subsegment contribute to NO chip (Other, not faked).
    expect(rail.reduce((s, r) => s + r.n, 0)).toBe(4);
  });

  it("filters by canonical id — raw variants of one genre collapse together", () => {
    const only = applyFilters(events, { genreIds: new Set(["indie-alternative"]) });
    expect(only).toHaveLength(2); // both "Alternative Rock" and "Indie"
  });

  it("an empty genre set is no filter (the honest full set passes)", () => {
    expect(applyFilters(events, { genreIds: new Set() })).toHaveLength(events.length);
  });

  it("a row that doesn't canonicalize is narrowed out by a genre filter, never crashes", () => {
    const latin = applyFilters(events, { genreIds: new Set(["latin"]) });
    expect(latin).toHaveLength(1);
    expect(latin[0].subsegment).toBe("Cumbia");
  });
});
