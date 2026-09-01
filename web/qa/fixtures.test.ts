import { describe, it, expect, afterEach } from "vitest";
import {
  QA_FROZEN_NOW_MS,
  qaFixtureEventById,
  qaFixtureEvents,
  qaFixturesEnabled,
} from "./fixtures";
import { bucketByDate, eventTiming, liveEvents } from "../lib/feed";

const ORIGINAL = process.env.ONELIVE_QA_FIXTURES;
afterEach(() => {
  if (ORIGINAL === undefined) delete process.env.ONELIVE_QA_FIXTURES;
  else process.env.ONELIVE_QA_FIXTURES = ORIGINAL;
});

describe("qaFixturesEnabled — fail-closed gate", () => {
  it("is OFF when the env var is unset (the default everywhere)", () => {
    delete process.env.ONELIVE_QA_FIXTURES;
    expect(qaFixturesEnabled()).toBe(false);
  });
  it("is OFF for every value except the exact string '1'", () => {
    for (const v of ["0", "true", "yes", "on", " 1", "1 ", ""]) {
      process.env.ONELIVE_QA_FIXTURES = v;
      expect(qaFixturesEnabled()).toBe(false);
    }
  });
  it("is ON only for exactly '1'", () => {
    process.env.ONELIVE_QA_FIXTURES = "1";
    expect(qaFixturesEnabled()).toBe(true);
  });
});

describe("the fixture set exercises every display rule the canon pins", () => {
  const all = qaFixtureEvents();
  const scheduled = all.filter((e) => e.status === "scheduled" || e.status === "moved");

  it("covers all four confidence states — disputed included, shown never hidden", () => {
    const states = new Set(scheduled.map((e) => e.confidence));
    for (const s of ["confirmed", "likely", "unverified", "disputed"]) {
      expect(states, `missing confidence state ${s}`).toContain(s);
    }
  });

  it("fills all three density tiers relative to the frozen clock", () => {
    const buckets = bucketByDate(liveEvents(scheduled, QA_FROZEN_NOW_MS), QA_FROZEN_NOW_MS);
    expect(buckets.map((b) => b.key).sort()).toEqual(["compact", "line", "rich"]);
    for (const b of buckets) {
      expect(b.items.length, `empty bucket: ${b.label}`).toBeGreaterThan(0);
    }
  });

  it("has exactly the states a live screenshot needs: two on-now, none ended", () => {
    const live = liveEvents(scheduled, QA_FROZEN_NOW_MS);
    expect(live.length).toBe(scheduled.length); // nothing silently dropped
    // qa-1 (an evening show already under way) and qa-11 (a noon-to-11:30pm
    // daytime run). The second one is deliberate: it is the row that proves
    // the day-part ordering keeps a DAYTIME listing instead of deleting it.
    expect(scheduled.filter((e) => eventTiming(e, QA_FROZEN_NOW_MS) === "on-now").length).toBe(2);
  });

  it("carries both Spark Line registers (tier B attribution, tier C ✳)", () => {
    const tiers = new Set(scheduled.map((e) => e.spark?.tier).filter(Boolean));
    expect(tiers).toContain("B");
    expect(tiers).toContain("C");
  });

  it("includes a free event (mint pill) and an unknown price (honest 'See tickets')", () => {
    expect(scheduled.some((e) => e.is_free === true)).toBe(true);
    expect(scheduled.some((e) => e.price_min === null && e.is_free === null)).toBe(true);
  });

  it("includes a cancelled event for the detail status-note baseline (feed-filtered out)", () => {
    expect(all.some((e) => e.status === "cancelled")).toBe(true);
  });

  it("is deterministic offline: NO event carries an image URL", () => {
    for (const e of all) expect(e.image_url, e.licensed_event_id).toBeNull();
  });

  it("asserts nothing about real entities: example.com venues, reserved 555 numbers", () => {
    for (const e of all) {
      expect(e.venue_url, e.licensed_event_id).toMatch(/\.example\.com$/);
      expect(e.venue_phone, e.licensed_event_id).toMatch(/^\+1512555/);
      if (e.ticket_url) expect(e.ticket_url).toMatch(/^https:\/\/tickets\.example\.com\//);
    }
  });

  it("keeps every fixture in Austin EXCEPT the one that pins the region scope", () => {
    // Coverage Law 2026-09-01: CAPCOG is a view filter, not a catalog delete.
    // One deliberate out-of-region fixture is what lets a baseline prove the
    // default view scopes it out AND says how many rows it is holding back —
    // without it, a scope that silently dropped everything would look
    // identical to a correct one.
    const outside = all.filter((e) => e.venue_city !== "Austin");
    expect(outside.map((e) => e.venue_city)).toEqual(["San Antonio"]);
    expect(outside).toHaveLength(1);
  });

  it("carries one PROMOTED row with fictional source provenance (0020 columns)", () => {
    const promoted = all.filter((e) => e.source_provider === "promoted");
    expect(promoted).toHaveLength(1);
    expect(promoted[0].origin_name).toBe("QA Fictional Venue Calendar");
    // Same no-real-entity discipline as venue_url: a source link in a fixture
    // must never point at a real organization.
    expect(promoted[0].origin_url).toMatch(/^https:\/\/[a-z0-9-]+\.example\.com$/);
  });

  it("has unique ids and qaFixtureEventById round-trips them", () => {
    const ids = all.map((e) => e.licensed_event_id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of ids) {
      expect(qaFixtureEventById(id)?.licensed_event_id).toBe(id);
    }
    expect(qaFixtureEventById("no-such-fixture")).toBeNull();
  });
});
