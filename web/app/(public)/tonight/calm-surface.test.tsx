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

import FeedApp from "./FeedApp";
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

const NOW = new Date("2026-08-04T20:00:00-05:00").getTime();
// One event per density tier: rich (2 days out), compact (12 days), line (45 days).
const events = [
  ev({ licensed_event_id: "r1", start_time: new Date("2026-08-06T21:00:00-05:00").toISOString() }),
  ev({ licensed_event_id: "c1", start_time: new Date("2026-08-16T21:00:00-05:00").toISOString(), title: "MidShow", performer: "Mid Act" }),
  ev({ licensed_event_id: "l1", start_time: new Date("2026-09-18T21:00:00-05:00").toISOString(), title: "FarShow", performer: "Far Act" }),
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
    expect(html).toContain("no pay-to-rank");
  });
});

describe("no page-load taps (canon §6.1)", () => {
  it("the resting feed markup contains NO anchor to /tonight/<id> — rows are lens-opening buttons", () => {
    expect(html).not.toMatch(/<a[^>]+href="\/tonight\//);
    expect(html).toMatch(/<button[^>]*class="tilink"[^>]*aria-label="Mid Act — open details"/);
    expect(html).toMatch(/<button[^>]*class="tilink"[^>]*aria-label="Far Act — open details"/);
  });
});
