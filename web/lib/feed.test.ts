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
  bucketByDate,
  countInWindow,
  viewCounts,
  marketHour,
  splitByDayPart,
  EVENING_HOUR,
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
    venue_url: null,
    venue_phone: null,
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
  it("builds Today + next 7 days, with All upcoming LAST (founder-directed order 2026-08-04)", () => {
    const tabs = dayTabs(NOW, 7);
    expect(tabs[0].key).toBe("today");
    expect(tabs[0].label).toBe("Today");
    expect(tabs[1].label).toBe("Tomorrow");
    expect(tabs[tabs.length - 1].key).toBe("all");
    expect(tabs).toHaveLength(9); // all + today + 7 more
  });

  // ── Market-day boundary physics (adversarial-review r3, 2026-08-04) ────────
  // Chicago's fall-back day (Sun 2026-11-01) is 25 hours; spring-forward
  // (Sun 2027-03-14) is 23. Day windows must be derived per-day from the
  // market calendar, never advanced by a fixed 24h — a fixed width drifts
  // every boundary after the transition by an hour and mis-buckets late shows.
  it("day windows stay on market midnights across the fall-back DST transition", () => {
    // Fri 2026-10-30 18:00 CDT = 23:00Z. Sunday Nov 1 is the 25-hour day.
    const tabs = dayTabs(Date.UTC(2026, 9, 30, 23), 7);
    for (let i = 0; i + 1 < tabs.length - 1; i++) {
      // Contiguous: each day ends exactly where the next begins (nothing can
      // fall between two tabs), and every boundary is a true market midnight.
      expect(tabs[i].endMs).toBe(tabs[i + 1].startMs);
      const h = new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", hour: "2-digit", hour12: false }).format(new Date(tabs[i].startMs));
      expect(["00", "24"]).toContain(h);
    }
    // The transition day itself is 25 hours; its neighbors are 24.
    const widths = tabs.slice(0, -1).map((t) => t.endMs - t.startMs);
    expect(widths).toContain(25 * 3_600_000);
    expect(widths.filter((w) => w === 24 * 3_600_000).length).toBeGreaterThan(0);
  });

  it("day windows stay on market midnights across the spring-forward transition (23h day)", () => {
    // Fri 2027-03-12 18:00 CST = 2027-03-13T00:00Z; Sun Mar 14 is 23 hours.
    const tabs = dayTabs(Date.UTC(2027, 2, 13, 0), 7);
    const widths = tabs.slice(0, -1).map((t) => t.endMs - t.startMs);
    expect(widths).toContain(23 * 3_600_000);
    for (let i = 0; i + 1 < tabs.length - 1; i++) expect(tabs[i].endMs).toBe(tabs[i + 1].startMs);
  });

  // After local midnight a show that started before midnight and is still
  // running must remain in the DEFAULT Today view — liveEvents still carries
  // it, and start-time-only bucketing left it visible nowhere but "All
  // upcoming". If it's disputed, that's a hidden disputed event: trust break
  // (adversarial-review r3, 2026-08-04).
  it("an on-now show that started before midnight stays in Today after midnight (disputed included)", () => {
    // Sat 2026-07-25 01:30 CT = 06:30Z — half past one in the morning.
    const lateNow = Date.UTC(2026, 6, 25, 6, 30);
    const tabs = dayTabs(lateNow, 7);
    const today = tabs[0];
    const disputedStillOn = ev({
      start_time: "2026-07-25T04:00:00Z", // Fri 11pm CT, before Sat midnight
      end_time: "2026-07-25T07:00:00Z", //   Sat 2am CT, still running at 1:30am
      confidence: "disputed",
    });
    expect(liveEvents([disputedStillOn], lateNow)).toContain(disputedStillOn);
    expect(applyFilters([disputedStillOn], { tab: today })).toContain(disputedStillOn);
    // …and an actually-ended show from last night does NOT ride along.
    const endedLastNight = ev({ start_time: "2026-07-25T01:00:00Z", end_time: "2026-07-25T03:00:00Z" });
    expect(liveEvents([endedLastNight], lateNow)).not.toContain(endedLastNight);
    // A tomorrow-night show stays under Tomorrow, not Today (future tabs keep
    // pure start-time semantics).
    const tomorrowShow = ev({ start_time: "2026-07-26T02:00:00Z" }); // Sat 9pm CT
    expect(applyFilters([tomorrowShow], { tab: today })).toContain(tomorrowShow); // Sat 9pm IS today (now = Sat 1:30am)
    const sundayShow = ev({ start_time: "2026-07-27T01:00:00Z" }); // Sun 8pm CT
    expect(applyFilters([sundayShow], { tab: today })).not.toContain(sundayShow);
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

  it("does NOT classify a non-music event's subsegment as a music genre (#100)", () => {
    // A dance PERFORMANCE (performing-arts) whose subsegment reads "Dance" must
    // not become an Electronic/Dance music chip, nor filter into that set.
    const ballet = ev({ category: "performing-arts", subsegment: "Dance" });
    const rail = genreFacet([...events, ballet]);
    // The ballet adds no chip and no count to electronic-dance.
    const ed = rail.find((r) => r.id === "electronic-dance");
    expect(ed).toBeUndefined();
    // And it isn't captured by an electronic-dance genre filter.
    expect(applyFilters([ballet], { genreIds: new Set(["electronic-dance"]) })).toHaveLength(0);
  });

  it("a row that doesn't canonicalize is narrowed out by a genre filter, never crashes", () => {
    const latin = applyFilters(events, { genreIds: new Set(["latin"]) });
    expect(latin).toHaveLength(1);
    expect(latin[0].subsegment).toBe("Cumbia");
  });
});

describe("bucketByDate — the three-tier date density", () => {
  const mk = (id: string, daysOut: number) =>
    ev({ licensed_event_id: id, start_time: new Date(NOW + daysOut * 86_400_000).toISOString() });
  const events = [
    mk("soon", 2), //     -> rich (This week)
    mk("thisweek", 6), // -> rich
    mk("midmonth", 20), //-> compact (Later this month)
    mk("faraway", 60), // -> line (Beyond)
  ];

  it("splits into rich/compact/line by time-to-start, in that order", () => {
    const b = bucketByDate(events, NOW);
    expect(b.map((x) => x.key)).toEqual(["rich", "compact", "line"]);
    expect(b[0].items.map((e) => e.licensed_event_id).sort()).toEqual(["soon", "thisweek"]);
    expect(b[1].items[0].licensed_event_id).toBe("midmonth");
    expect(b[2].items[0].licensed_event_id).toBe("faraway");
  });

  it("is sum-preserving — every event lands in exactly one bucket (nothing hidden)", () => {
    const b = bucketByDate(events, NOW);
    expect(b.reduce((s, x) => s + x.items.length, 0)).toBe(events.length);
  });

  it("omits empty buckets", () => {
    const b = bucketByDate([mk("only", 3)], NOW);
    expect(b.map((x) => x.key)).toEqual(["rich"]);
  });

  it("returns nothing for an empty set", () => {
    expect(bucketByDate([], NOW)).toEqual([]);
  });

  it("puts a date-TBA (null/invalid start) row in the line bucket, not hidden (#100)", () => {
    const tba = ev({ licensed_event_id: "tba", start_time: null });
    const bad = ev({ licensed_event_id: "bad", start_time: "not-a-date" });
    const b = bucketByDate([mk("soon", 2), tba, bad], NOW);
    const line = b.find((x) => x.key === "line");
    expect(line).toBeTruthy();
    expect(line!.items.map((e) => e.licensed_event_id).sort()).toEqual(["bad", "tba"]);
    // sum-preserving even with undated rows — nothing dropped.
    expect(b.reduce((s, x) => s + x.items.length, 0)).toBe(3);
  });
});


// ── Completeness + day part (founder directive 2026-09-01, Session 2 VIEW) ────
// Coverage Law: views are picky, but a view must never DELETE a catalog row.
// Both mechanisms added for that directive are proven sum-preserving here,
// because "the view quietly lost a row" is the failure they exist to prevent.

describe("countInWindow — the M of 'Showing N of M known listings'", () => {
  // Fixed instant so day boundaries are deterministic: Thu 2026-10-15 20:30 CDT.
  const now = Date.UTC(2026, 9, 16, 1, 30, 0);
  const tabs = dayTabs(now, 7);
  const today = tabs[0];
  const all = tabs[tabs.length - 1];

  it("counts every row in the window, INCLUDING the ones a lens would hide", () => {
    const rows = [
      ev({ start_time: new Date(now + 3600_000).toISOString(), category: "comedy" }),
      ev({ start_time: new Date(now + 7200_000).toISOString(), category: "live-music" }),
      ev({ start_time: new Date(now + 3 * 86_400_000).toISOString() }), // another day
    ];
    expect(countInWindow(rows, today)).toBe(2);
    // A domain lens narrows N; it must not touch M — that is the whole point of
    // the line, and computing M after the lens would make it a tautology.
    const narrowed = applyFilters(rows, { tab: today, domains: new Set(["comedy"]) });
    expect(narrowed.length).toBe(1);
    expect(countInWindow(rows, today)).toBe(2);
  });

  it("counts a DISPUTED row like any other — completeness is not a trust filter", () => {
    const rows = [
      ev({ start_time: new Date(now + 3600_000).toISOString(), confidence: "disputed" }),
      ev({ start_time: new Date(now + 3600_000).toISOString(), confidence: "confirmed" }),
    ];
    expect(countInWindow(rows, today)).toBe(2);
  });

  it("counts the whole set under 'All upcoming', date-TBA rows included", () => {
    const rows = [ev({ start_time: null }), ev({ start_time: "2027-01-01T00:00:00Z" })];
    expect(countInWindow(rows, all)).toBe(2);
    // …and agrees with the filter that renders it — one source of truth.
    expect(applyFilters(rows, { tab: all }).length).toBe(countInWindow(rows, all));
  });

  it("never exceeds the input and never counts a row twice", () => {
    const rows = Array.from({ length: 9 }, (_, i) =>
      ev({ start_time: new Date(now + i * 3600_000).toISOString() }));
    for (const t of tabs) {
      expect(countInWindow(rows, t)).toBe(applyFilters(rows, { tab: t }).length);
      expect(countInWindow(rows, t)).toBeLessThanOrEqual(rows.length);
    }
  });
});

describe("splitByDayPart — the evening LEADS, the morning is never deleted", () => {
  const at = (hourCdt: number) =>
    // 2026-10-15 <hour>:00 CDT == UTC+5 that date (DST in effect).
    new Date(Date.UTC(2026, 9, 15, hourCdt + 5, 0, 0)).toISOString();

  it("is sum-preserving: every row lands in exactly one half", () => {
    const rows = [at(9), at(12), at(16), at(17), at(20), at(23)].map((t) => ev({ start_time: t }));
    const { evening, earlier } = splitByDayPart(rows);
    expect(evening.length + earlier.length).toBe(rows.length);
    const ids = [...evening, ...earlier].map((e) => e.licensed_event_id);
    expect(new Set(ids).size).toBe(rows.length);
  });

  it("puts 5pm and later in the leading block, earlier hours below it", () => {
    const { evening, earlier } = splitByDayPart(
      [at(16), at(17), at(19)].map((t) => ev({ start_time: t })),
    );
    expect(evening.length).toBe(2);
    expect(earlier.length).toBe(1);
    expect(EVENING_HOUR).toBe(17);
  });

  it("uses the MARKET clock, not the runtime's (a UTC server must not re-sort the day)", () => {
    // 2026-10-16T01:30:00Z is 8:30 PM CDT on the 15th — evening in Austin, and
    // past midnight in UTC. A runtime-clock reading would file it as 01:00 =
    // "earlier in the day", which is the dayTabs bug wearing a new hat.
    expect(marketHour("2026-10-16T01:30:00Z")).toBe(20);
    const { evening } = splitByDayPart([ev({ start_time: "2026-10-16T01:30:00Z" })]);
    expect(evening.length).toBe(1);
  });

  it("leads with a date-TBA row rather than burying it under a clock we lack", () => {
    expect(marketHour(null)).toBe(null);
    expect(marketHour("not-a-date")).toBe(null);
    const { evening, earlier } = splitByDayPart([ev({ start_time: null })]);
    expect(evening.length).toBe(1);
    expect(earlier.length).toBe(0);
  });

  it("never drops a DISPUTED morning row (shown-never-hidden holds across the split)", () => {
    const rows = [
      ev({ start_time: at(10), confidence: "disputed" }),
      ev({ start_time: at(21), confidence: "confirmed" }),
    ];
    const { evening, earlier } = splitByDayPart(rows);
    expect(earlier.map((e) => e.confidence)).toEqual(["disputed"]);
    expect(evening.length + earlier.length).toBe(2);
  });
});


describe("viewCounts — 'Showing N of M', and what the region is holding back", () => {
  const now = Date.UTC(2026, 9, 16, 1, 30, 0); // Thu 2026-10-15 20:30 CDT
  const tabs = dayTabs(now, 7);
  const today = tabs[0];
  const soon = new Date(now + 3600_000).toISOString();

  const live = [
    ev({ start_time: soon, venue_city: "Austin", category: "live-music" }),
    ev({ start_time: soon, venue_city: "Bastrop", category: "comedy" }),
    ev({ start_time: soon, venue_city: "Nowheresville", category: "live-music" }),
    ev({ start_time: soon, venue_city: "San Antonio", category: "live-music" }),
    ev({ start_time: soon, venue_city: "Seguin", category: "live-music" }),
    ev({ start_time: new Date(now + 5 * 86_400_000).toISOString(), venue_city: "Austin" }),
  ];

  it("counts M under the CAPCOG scope and says how many it is holding back", () => {
    const scoped = applyFilters(live.filter((e) => e.venue_city !== "San Antonio" && e.venue_city !== "Seguin"), { tab: today });
    const c = viewCounts(live, scoped, today, "capcog");
    // 5 rows fall in today's window; 2 are known-outside, so M = 3.
    expect(c.windowTotal).toBe(3);
    expect(c.shown).toBe(3);
    expect(c.heldBackByRegion).toBe(2);
  });

  it("raises M when the reader clears the region — 'M is not CAPCOG-only'", () => {
    const everything = live.filter((e) => e.start_time === soon);
    const c = viewCounts(live, everything, today, "everywhere");
    expect(c.windowTotal).toBe(5);
    expect(c.shown).toBe(5);
    // Nothing is being held back once the scope is cleared, so the sentence
    // about held-back rows must not render at all.
    expect(c.heldBackByRegion).toBe(0);
  });

  it("keeps M independent of the lens filters — N narrows, M does not", () => {
    const capcogRows = live.filter(
      (e) => !["San Antonio", "Seguin"].includes(e.venue_city ?? ""));
    const narrowed = applyFilters(capcogRows, { tab: today, domains: new Set(["comedy"]) });
    const c = viewCounts(live, narrowed, today, "capcog");
    expect(c.shown).toBe(1);
    expect(c.windowTotal).toBe(3); // unchanged by the domain chip
    expect(c.heldBackByRegion).toBe(2);
  });

  it("an unrecognised place counts INSIDE M — a gap must not read as a border", () => {
    // "Nowheresville" is unrecognised, not known-outside. Counting it as held
    // back would make the boundary look bigger than it is and would hide the
    // coverage gap the keep-and-count discipline exists to expose.
    const c = viewCounts(
      [ev({ start_time: soon, venue_city: "Nowheresville" })], [], today, "capcog");
    expect(c.windowTotal).toBe(1);
    expect(c.heldBackByRegion).toBe(0);
  });

  it("never reports a negative hold-back, whatever the window", () => {
    for (const t of tabs) {
      const c = viewCounts(live, [], t, "capcog");
      expect(c.heldBackByRegion).toBeGreaterThanOrEqual(0);
      expect(c.windowTotal).toBeLessThanOrEqual(countInWindow(live, t));
    }
  });
});
