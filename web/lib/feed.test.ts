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
  splitByTiming,
  namedWindows,
  tonightWindow,
  weekendWindow,
  resolveTab,
  emptyWindowNote,
  inDayTab,
  EVENING_HOUR,
  NIGHT_END_HOUR,
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
    const days = tabs.filter((t) => t.kind === "day");
    expect(tabs[0].key).toBe("today"); // Today still leads and is the default
    expect(tabs[0].label).toBe("Today");
    expect(days[1].label).toBe("Tomorrow");
    expect(tabs[tabs.length - 1].key).toBe("all");
    expect(days).toHaveLength(8); // today + 7 more market days
    // The named windows sit BETWEEN Today and the catch-all; the three tabs
    // the founder named as keepers are all still here, in their own places
    // (2026-09-07: "Keep Today, Tomorrow, All upcoming").
    expect(tabs.map((t) => t.key).slice(0, 3)).toEqual(["today", "tonight", "d1"]);
    expect(tabs.filter((t) => t.kind === "all")).toHaveLength(1);
  });

  it("adds the six named windows and keeps Today / Tomorrow / All upcoming", () => {
    const keys = dayTabs(NOW, 7).map((t) => t.key);
    for (const k of ["tonight", "this-week", "this-weekend", "this-month", "next-week", "next-month"]) {
      expect(keys).toContain(k);
    }
    for (const k of ["today", "d1", "all"]) expect(keys).toContain(k);
    // Every key is unique — a duplicate would make resolveTab ambiguous and
    // let two chips claim the same window.
    expect(new Set(keys).size).toBe(keys.length);
  });

  // ── Market-day boundary physics (adversarial-review r3, 2026-08-04) ────────
  // Chicago's fall-back day (Sun 2026-11-01) is 25 hours; spring-forward
  // (Sun 2027-03-14) is 23. Day windows must be derived per-day from the
  // market calendar, never advanced by a fixed 24h — a fixed width drifts
  // every boundary after the transition by an hour and mis-buckets late shows.
  it("day windows stay on market midnights across the fall-back DST transition", () => {
    // Fri 2026-10-30 18:00 CDT = 23:00Z. Sunday Nov 1 is the 25-hour day.
    const tabs = dayTabs(Date.UTC(2026, 9, 30, 23), 7).filter((t) => t.kind === "day");
    for (let i = 0; i + 1 < tabs.length; i++) {
      // Contiguous: each day ends exactly where the next begins (nothing can
      // fall between two tabs), and every boundary is a true market midnight.
      expect(tabs[i].endMs).toBe(tabs[i + 1].startMs);
      const h = new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", hour: "2-digit", hour12: false }).format(new Date(tabs[i].startMs));
      expect(["00", "24"]).toContain(h);
    }
    // The transition day itself is 25 hours; its neighbors are 24.
    const widths = tabs.map((t) => t.endMs - t.startMs);
    expect(widths).toContain(25 * 3_600_000);
    expect(widths.filter((w) => w === 24 * 3_600_000).length).toBeGreaterThan(0);
  });

  it("day windows stay on market midnights across the spring-forward transition (23h day)", () => {
    // Fri 2027-03-12 18:00 CST = 2027-03-13T00:00Z; Sun Mar 14 is 23 hours.
    const tabs = dayTabs(Date.UTC(2027, 2, 13, 0), 7).filter((t) => t.kind === "day");
    const widths = tabs.map((t) => t.endMs - t.startMs);
    expect(widths).toContain(23 * 3_600_000);
    for (let i = 0; i + 1 < tabs.length; i++) expect(tabs[i].endMs).toBe(tabs[i + 1].startMs);
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


// ── Named windows (founder 2026-09-07) ───────────────────────────────────────
// Tonight · This week · This weekend · This month · Next week · Next month.
// Every bound below is asserted as a MARKET WALL-CLOCK reading, not as an
// epoch number: the number is the thing under test, so an expectation written
// as another number proves only that two computations agree. `wall` reads the
// instant back through America/Chicago the way a person in Austin would.
function wall(ms: number): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Chicago", weekday: "short", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(new Date(ms));
}
function win(nowMs: number, key: string) {
  const t = dayTabs(nowMs, 7).find((x) => x.key === key);
  if (!t) throw new Error(`no tab ${key}`);
  return t;
}
// Thu 2026-09-10, 10:00 in Austin — a plain weekday morning, well clear of
// every boundary the windows are built from.
const THU_10AM = Date.UTC(2026, 8, 10, 15);

describe("named windows — bounds are the MARKET's calendar (America/Chicago)", () => {
  it("Tonight runs 5pm → 3am on the market clock", () => {
    const t = win(THU_10AM, "tonight");
    expect(t.kind).toBe("night");
    expect(wall(t.startMs)).toBe("Thu, 09/10/2026, 17:00");
    expect(wall(t.endMs)).toBe("Fri, 09/11/2026, 03:00");
    expect(EVENING_HOUR).toBe(17);
    expect(NIGHT_END_HOUR).toBe(3);
  });

  it("in the small hours Tonight is still the night IN PROGRESS, not the next one", () => {
    // Fri 2026-09-11, 01:00 Austin. The night that began Thursday 5pm has not
    // ended, so Tonight must still be pointing at it — otherwise a show that
    // is ON NOW at 1am belongs to no named window at all.
    const friday1am = Date.UTC(2026, 8, 11, 6);
    const t = win(friday1am, "tonight");
    expect(wall(t.startMs)).toBe("Thu, 09/10/2026, 17:00");
    expect(wall(t.endMs)).toBe("Fri, 09/11/2026, 03:00");
    // …and Today/Tomorrow still carry the day, exactly as the founder said.
    expect(win(friday1am, "today").startMs).toBe(
      dayTabs(friday1am, 7).filter((x) => x.kind === "day")[0].startMs,
    );
    expect(wall(win(friday1am, "today").startMs)).toBe("Fri, 09/11/2026, 00:00");
  });

  it("after 3am Tonight rolls to the coming night (a window, never a mood)", () => {
    const friday4am = Date.UTC(2026, 8, 11, 9);
    const t = win(friday4am, "tonight");
    expect(wall(t.startMs)).toBe("Fri, 09/11/2026, 17:00");
    expect(wall(t.endMs)).toBe("Sat, 09/12/2026, 03:00");
  });

  it("Tonight survives both DST transitions — an 11-hour night and a 9-hour one", () => {
    // Fall back: Sun 2026-11-01 02:00 CDT → 01:00 CST, so Sat night is 11h.
    const fall = win(Date.UTC(2026, 9, 31, 23), "tonight"); // Sat 6pm CDT
    expect(wall(fall.startMs)).toBe("Sat, 10/31/2026, 17:00");
    expect(wall(fall.endMs)).toBe("Sun, 11/01/2026, 03:00");
    expect(fall.endMs - fall.startMs).toBe(11 * 3_600_000);
    // Spring forward: Sun 2027-03-14 02:00 CST → 03:00 CDT, so Sat night is 9h.
    const spring = win(Date.UTC(2027, 2, 14, 0), "tonight"); // Sat 6pm CST
    expect(wall(spring.startMs)).toBe("Sat, 03/13/2027, 17:00");
    expect(wall(spring.endMs)).toBe("Sun, 03/14/2027, 03:00");
    expect(spring.endMs - spring.startMs).toBe(9 * 3_600_000);
  });

  it("This week is the calendar week (Sunday → Sunday), Next week the one after", () => {
    const thisWeek = win(THU_10AM, "this-week");
    const nextWeek = win(THU_10AM, "next-week");
    expect(wall(thisWeek.startMs)).toBe("Sun, 09/06/2026, 00:00");
    expect(wall(thisWeek.endMs)).toBe("Sun, 09/13/2026, 00:00");
    expect(wall(nextWeek.startMs)).toBe("Sun, 09/13/2026, 00:00");
    expect(wall(nextWeek.endMs)).toBe("Sun, 09/20/2026, 00:00");
    // Contiguous: nothing can fall between this week and next.
    expect(thisWeek.endMs).toBe(nextWeek.startMs);
  });

  it("This month / Next month are calendar months, and roll the year", () => {
    const m = win(THU_10AM, "this-month");
    const n = win(THU_10AM, "next-month");
    expect(wall(m.startMs)).toBe("Tue, 09/01/2026, 00:00");
    expect(wall(m.endMs)).toBe("Thu, 10/01/2026, 00:00");
    expect(wall(n.startMs)).toBe("Thu, 10/01/2026, 00:00");
    expect(wall(n.endMs)).toBe("Sun, 11/01/2026, 00:00");
    expect(m.endMs).toBe(n.startMs);
    // December: next month is January of the NEXT year, not month 13.
    const dec = Date.UTC(2026, 11, 15, 18); // Tue 2026-12-15 12:00 CST
    expect(wall(win(dec, "next-month").startMs)).toBe("Fri, 01/01/2027, 00:00");
    expect(wall(win(dec, "next-month").endMs)).toBe("Mon, 02/01/2027, 00:00");
  });

  it("This weekend is Friday 5pm → Monday 3am, forward on a weekday", () => {
    const w = win(THU_10AM, "this-weekend"); // Thursday morning
    expect(w.kind).toBe("span");
    expect(wall(w.startMs)).toBe("Fri, 09/11/2026, 17:00");
    expect(wall(w.endMs)).toBe("Mon, 09/14/2026, 03:00");
  });

  it("This weekend stays on the weekend IN PROGRESS from Friday night to Monday 3am", () => {
    for (const [nowMs, when] of [
      [Date.UTC(2026, 8, 11, 23), "Fri 6pm"],
      [Date.UTC(2026, 8, 12, 6), "Sat 1am"],
      [Date.UTC(2026, 8, 13, 20), "Sun 3pm"],
      [Date.UTC(2026, 8, 14, 6), "Mon 1am"], // Sunday night, still running
    ] as Array<[number, string]>) {
      const w = win(nowMs, "this-weekend");
      expect(`${when}: ${wall(w.startMs)}`).toBe(`${when}: Fri, 09/11/2026, 17:00`);
      expect(`${when}: ${wall(w.endMs)}`).toBe(`${when}: Mon, 09/14/2026, 03:00`);
    }
    // …and once Monday is properly under way it points at the NEXT weekend.
    const w = win(Date.UTC(2026, 8, 14, 15), "this-weekend"); // Mon 10am
    expect(wall(w.startMs)).toBe("Fri, 09/18/2026, 17:00");
  });

  it("namedWindows and the exported window builders agree with the chips", () => {
    const named = namedWindows(THU_10AM);
    expect(named.map((t) => t.key)).toEqual([
      "tonight", "this-weekend", "this-week", "next-week", "this-month", "next-month",
    ]);
    expect(tonightWindow(THU_10AM)).toEqual({
      startMs: win(THU_10AM, "tonight").startMs, endMs: win(THU_10AM, "tonight").endMs,
    });
    expect(weekendWindow(THU_10AM)).toEqual({
      startMs: win(THU_10AM, "this-weekend").startMs, endMs: win(THU_10AM, "this-weekend").endMs,
    });
    // Every named window states its span in plain language — a reader never
    // has to guess where "This weekend" starts.
    for (const t of named) expect(t.note && t.note.length).toBeTruthy();
  });
});

describe("named windows — a view narrows, it never deletes", () => {
  const now = THU_10AM;

  it("Tonight includes a show that is ON NOW but started before 5pm", () => {
    const evening = Date.UTC(2026, 8, 10, 23); // Thu 6pm Austin
    const t = win(evening, "tonight");
    const startedAt4 = ev({
      start_time: "2026-09-10T21:00:00Z", // Thu 4pm CDT — before the window
      end_time: "2026-09-11T00:00:00Z", //   Thu 7pm CDT — still running at 6
      confidence: "disputed", // and hiding a disputed row is a trust break
    });
    expect(liveEvents([startedAt4], evening)).toContain(startedAt4);
    expect(inDayTab(startedAt4, t)).toBe(true);
    // An ended matinee does NOT ride along on that rule.
    const ended = ev({ start_time: "2026-09-10T16:00:00Z", end_time: "2026-09-10T18:00:00Z" });
    expect(inDayTab(ended, t)).toBe(false);
  });

  it("a morning row is never dropped from a window that contains its day", () => {
    const morning = ev({ start_time: "2026-09-10T14:00:00Z" }); // Thu 9am CDT
    for (const key of ["today", "this-week", "this-month"]) {
      expect(inDayTab(morning, win(now, key))).toBe(true);
    }
    // It is simply not part of TONIGHT — a window, not a deletion: Today and
    // This week still carry it, which is the whole point.
    expect(inDayTab(morning, win(now, "tonight"))).toBe(false);
  });

  it("countInWindow and applyFilters agree for every named window", () => {
    const rows = [
      ev({ start_time: "2026-09-10T14:00:00Z" }), // Thu morning
      ev({ start_time: "2026-09-11T02:00:00Z" }), // Thu 9pm
      ev({ start_time: "2026-09-12T03:00:00Z" }), // Fri 10pm
      ev({ start_time: "2026-09-24T01:00:00Z" }), // later in September
      ev({ start_time: "2026-10-20T01:00:00Z" }), // October
      ev({ start_time: null }), // date TBA — "All upcoming" only
    ];
    for (const t of dayTabs(now, 7)) {
      expect(countInWindow(rows, t)).toBe(applyFilters(rows, { tab: t }).length);
      expect(countInWindow(rows, t)).toBeLessThanOrEqual(rows.length);
    }
    // A date-TBA row is never put on a named window — it has no date to put
    // it on — and never disappears either: All upcoming holds it.
    const tba = rows[rows.length - 1];
    for (const t of dayTabs(now, 7)) {
      if (t.key !== "all") expect(inDayTab(tba, t)).toBe(false);
    }
    expect(inDayTab(tba, win(now, "all"))).toBe(true);
  });
});

describe("splitByTiming — on now leads, and the split is sum-preserving", () => {
  const now = Date.parse("2026-09-10T23:00:00Z"); // Thu 6pm Austin

  it("puts running shows first and everything else in coming-up", () => {
    const onAir = ev({ start_time: "2026-09-10T22:00:00Z", title: "ON" }); // 5pm, running
    const later = ev({ start_time: "2026-09-11T01:00:00Z", title: "LATER" }); // 8pm
    const { onNow, upcoming } = splitByTiming([later, onAir], now);
    expect(onNow.map((e) => e.title)).toEqual(["ON"]);
    expect(upcoming.map((e) => e.title)).toEqual(["LATER"]);
  });

  it("both halves always sum to the input — a clock can never drop a row", () => {
    const rows = [
      ev({ start_time: "2026-09-10T22:00:00Z" }), // on now
      ev({ start_time: "2026-09-10T14:00:00Z", end_time: "2026-09-10T16:00:00Z" }), // ended
      ev({ start_time: "2026-09-11T01:00:00Z" }), // upcoming
      ev({ start_time: null }), // date TBA
      ev({ start_time: "not-a-date" }), // unparseable
    ];
    const { onNow, upcoming } = splitByTiming(rows, now);
    expect(onNow.length + upcoming.length).toBe(rows.length);
    expect([...onNow, ...upcoming].map((e) => e.licensed_event_id).sort())
      .toEqual(rows.map((e) => e.licensed_event_id).sort());
    expect(splitByTiming([], now)).toEqual({ onNow: [], upcoming: [] });
  });

  it("keeps a DISPUTED running show in the on-now half (a clock, never a trust filter)", () => {
    const d = ev({ start_time: "2026-09-10T22:00:00Z", confidence: "disputed", title: "D" });
    expect(splitByTiming([d], now).onNow.map((e) => e.title)).toEqual(["D"]);
  });

  it("sorts each half soonest-first", () => {
    const a = ev({ start_time: "2026-09-11T04:00:00Z", title: "late" });
    const b = ev({ start_time: "2026-09-11T01:00:00Z", title: "early" });
    expect(splitByTiming([a, b], now).upcoming.map((e) => e.title)).toEqual(["early", "late"]);
  });
});

describe("resolveTab — a token we do not serve renders Today, never nothing", () => {
  const tabs = dayTabs(THU_10AM, 7);

  it("resolves every key the chips publish", () => {
    for (const t of tabs) expect(resolveTab(tabs, t.key).key).toBe(t.key);
  });

  it("falls back to the DEFAULT window on any unknown or missing token", () => {
    for (const bad of ["", "tonite", "this_week", "weekend", "../../etc", "0", "ALL", null, undefined]) {
      expect(resolveTab(tabs, bad).key).toBe("today");
    }
  });
});

describe("emptyWindowNote — an empty window is a state, never '0 events in Austin'", () => {
  const tonight = win(THU_10AM, "tonight");

  it("says nothing at all while the view has rows", () => {
    expect(emptyWindowNote(tonight, { shown: 3, windowTotal: 5, heldBackByRegion: 0 })).toBeNull();
  });

  it("an empty WINDOW says we are gathering, and that walls are unknown", () => {
    const note = emptyWindowNote(tonight, { shown: 0, windowTotal: 0, heldBackByRegion: 0 });
    expect(note?.kind).toBe("gathering");
    expect(note?.headline).toContain("Tonight");
    expect(note?.headline).toMatch(/still gathering/i);
    expect(note?.detail).toMatch(/what we have read/i);
    expect(note?.detail).toMatch(/unknown, not empty/i);
    // The failure this exists to prevent: a finished-sounding zero.
    const all = `${note?.headline} ${note?.detail}`;
    expect(all).not.toMatch(/\bno events\b/i);
    expect(all).not.toMatch(/0 events/i);
    expect(all).not.toMatch(/\bnone\b/i);
  });

  it("an empty view over a NON-empty window points at the reader's own filters", () => {
    const note = emptyWindowNote(tonight, { shown: 0, windowTotal: 12, heldBackByRegion: 4 });
    expect(note?.kind).toBe("filtered");
    expect(note?.detail).toContain("12");
    expect(note?.detail).toMatch(/clear a filter/i);
    // …and it must NOT claim we are still gathering: we are not, for this
    // window — we are holding rows back on the reader's instruction.
    expect(note?.detail).not.toMatch(/gathering/i);
  });

  it("singular reads as singular", () => {
    const note = emptyWindowNote(tonight, { shown: 0, windowTotal: 1, heldBackByRegion: 0 });
    expect(note?.detail).toContain("1 listing in this window");
    expect(note?.detail).toContain("to see it.");
    expect(note?.detail).not.toContain("listings");
  });
});
