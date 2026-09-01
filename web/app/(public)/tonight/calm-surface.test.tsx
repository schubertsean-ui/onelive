import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * The calm opening surface + no-page-load taps (canon §1/§6.1/§6.5/§9,
 * founder re-flag 2026-08-04: "still super cluttered upon opening … the card
 * doesn't slide it's a new window").
 *
 * Pins three conformance facts about the DEFAULT (just-opened) feed:
 *  1. Filter chips are NOT on the surface — they live behind the one quiet
 *     "Filters" entry (canon: "Filters slide in"; "a quiet entry point").
 *  2. The non-canonical KPI trio is gone (the masthead count line is the
 *     canon carrier of counts).
 *  3. NO event row/card is an <a> to the detail route — every tap opens the
 *     in-place lens ("not a page load"); the detail page remains reachable
 *     from inside the lens ("Open full page"), which is the ONLY sanctioned
 *     /tonight/<id> link and renders only while a lens is open.
 */
vi.mock("./flow.css", () => ({}));

import FeedApp, { CondensedRow, LineRow } from "./FeedApp";
import type { LicensedEvent } from "../../../lib/licensed";

function ev(over: Partial<LicensedEvent>): LicensedEvent {
  return {
    id: over.licensed_event_id ?? "e", title: "Show", performer: "Act",
    category: "live-music", subsegment: null,
    start_time: over.start_time ?? new Date("2026-08-05T21:00:00-05:00").toISOString(),
    end_time: null, price_min: null, price_max: null, is_free: false,
    ticket_url: null, image_url: null, venue_name: "The Cellar", venue_area: "East",
    venue_city: "Austin", venue_address: null, venue_lat: null, venue_lng: null,
    venue_url: null, venue_phone: null, confidence: "confirmed", status: "scheduled",
    source_provider: "ticketmaster", ...over,
  } as LicensedEvent;
}

const NOW = new Date("2026-08-04T18:00:00-05:00").getTime();
// The default view is TODAY (founder-directed 2026-08-04) — a tonight event
// renders as a rich card; later events exist but sit behind other tabs.
const events = [
  ev({ licensed_event_id: "t1", start_time: new Date("2026-08-04T21:00:00-05:00").toISOString(), performer: "Tonight Act" }),
  ev({ licensed_event_id: "c1", start_time: new Date("2026-08-16T21:00:00-05:00").toISOString(), title: "MidShow", performer: "Mid Act" }),
];

const html = renderToStaticMarkup(<FeedApp events={events} serverNowMs={NOW} />);

describe("the calm opening surface (canon §6.5/§9)", () => {
  it("shows ONE quiet Filters entry and no chip rows at rest", () => {
    expect(html).toContain(">Filters<");
    expect(html).not.toContain("Free only");        // lives inside the panel
    expect(html).not.toContain('id="filterpanel"'); // panel unmounted when closed
  });
  it("carries counts in the canon masthead line, not a KPI trio", () => {
    expect(html).not.toContain("happening &amp; upcoming");
    expect(html).not.toContain("cultural domains");
    // Founder edit 2026-08-04: the "no pay-to-rank" TEXT is removed from the
    // count line (the INVARIANT is behavior — ranking stays money-blind, and
    // trust.test.ts still guards the ranking code; only the copy is gone).
    expect(html).not.toContain("no pay-to-rank");
    // The count line now states COMPLETENESS, not just a total (founder
    // 2026-09-01 / Coverage Law: "Views should say 'Showing N of M'"). One
    // event is in the default Today window, and it is the one rendered.
    expect(html).toContain("Showing 1 of 1 known");
  });
  it("the ordering disclosure describes the rendered structure, never a false chronology (evaluator r4)", () => {
    // Default Today river is domain-grouped with each group start-time sorted —
    // claiming a flat "by start time" order was a misleading trust display.
    // The day-part split is subject to the SAME rule: this fixture's only
    // today-event is at 9pm, so there is no daytime block and the plain river
    // renders — the line must not promise "evening first, then earlier".
    expect(html).toContain("by category, soonest first");
    expect(html).not.toContain("by start time");
    expect(html).not.toContain("evening first, then earlier in the day");
    expect(html).not.toContain("Earlier in the day");
  });

  it("says which region the default view is scoped to, and offers to clear it", () => {
    // Coverage Law 2026-09-01: CAPCOG is a view filter, not the map. The
    // default view may scope to it — but it must SAY so and be clearable,
    // because a silent scope is indistinguishable from a coverage gap.
    expect(html).toContain("Scoped to the CAPCOG test region");
    expect(html).toContain("Show everywhere");
  });

  it("splits the day when there IS a daytime block, and never drops it", () => {
    const morning = ev({
      licensed_event_id: "m1", performer: "Morning Market",
      start_time: new Date("2026-08-04T10:00:00-05:00").toISOString(),
    });
    const night = ev({
      licensed_event_id: "n2", performer: "Night Set",
      start_time: new Date("2026-08-04T21:00:00-05:00").toISOString(),
    });
    const h = renderToStaticMarkup(<FeedApp events={[morning, night]} serverNowMs={NOW} />);
    expect(h).toContain("Evening &amp; night");
    expect(h).toContain("Earlier in the day");
    // The evening block LEADS…
    expect(h.indexOf("Evening &amp; night")).toBeLessThan(h.indexOf("Earlier in the day"));
    // …and the morning row is still rendered, and still counted in both N and M.
    expect(h).toContain("Morning Market");
    expect(h).toContain("Showing 2 of 2 known");
    expect(h).toContain("evening first, then earlier in the day");
  });
});

describe("on-now stays in the default view (trust: disputed-on-now must never hide)", () => {
  it("a show that already started but has not ended renders under the default Today tab", () => {
    const onNow = ev({
      licensed_event_id: "n1", performer: "On Stage Now", confidence: "disputed",
      start_time: new Date("2026-08-04T17:00:00-05:00").toISOString(), // started 1h before NOW
    });
    const h = renderToStaticMarkup(<FeedApp events={[onNow]} serverNowMs={NOW} />);
    expect(h).toContain("On Stage Now");
  });
});

describe("no page-load taps (canon §6.1)", () => {
  it("the resting feed markup contains NO anchor to /tonight/<id>", () => {
    expect(html).not.toMatch(/<a[^>]+href="\/tonight\//);
    expect(html).toContain("Tonight Act"); // today's card rendered (default tab = Today)
  });
  it("Today is the default and leads the tab row; All upcoming closes it", () => {
    const tabs = [...html.matchAll(/<nav class="datetabs">([\s\S]*?)<\/nav>/g)][0][1];
    expect(tabs.indexOf(">Today<")).toBeGreaterThan(-1);
    expect(tabs).toMatch(/class="on"[^>]*>Today</);
    expect(tabs.lastIndexOf("All upcoming")).toBeGreaterThan(tabs.indexOf("Sat"));
  });
  it("compact and line rows are lens-opening BUTTONS, never links", () => {
    const e = events[1];
    for (const row of [
      renderToStaticMarkup(<CondensedRow e={e} onNow={false} onOpen={() => {}} />),
      renderToStaticMarkup(<LineRow e={e} onOpen={() => {}} />),
    ]) {
      expect(row).not.toContain("<a ");
      expect(row).toMatch(/<button[^>]*class="tilink"[^>]*aria-label="Mid Act — open details"/);
    }
  });
});
