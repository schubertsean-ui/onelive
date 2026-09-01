import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * The DEFAULT VIEW is where "San Antonio cannot reach a user" now lives.
 *
 * Coverage Law (2026-09-01) made the catalog greedy and the view picky: the
 * read path forwards every legally-seen row and /tonight scopes to CAPCOG as a
 * VIEW filter. That is only safe if the view actually scopes — and if it SAYS
 * what it is scoping, because a silent scope is indistinguishable from a
 * coverage gap. Both are asserted here against real rendered markup, not
 * against the helper the component happens to call.
 *
 * Scope of this file: the CAPCOG default, which is what a reader lands on.
 * The cleared-region arithmetic ("M is not CAPCOG-only") is proven over the
 * same computation the component renders from, lib/feed.viewCounts — the repo
 * has no DOM test environment, so a click cannot be simulated without adding
 * a dependency, and the numbers are the part that can be wrong.
 */
vi.mock("./flow.css", () => ({}));

import FeedApp from "./FeedApp";
import type { LicensedEvent } from "../../../lib/licensed";

const NOW = new Date("2026-08-04T18:00:00-05:00").getTime();
const TONIGHT = new Date("2026-08-04T21:00:00-05:00").toISOString();

function ev(over: Partial<LicensedEvent>): LicensedEvent {
  return {
    licensed_event_id: "e", title: "Show", performer: "Act",
    category: "live-music", subsegment: null, start_time: TONIGHT,
    end_time: null, price_min: null, price_max: null, is_free: false,
    ticket_url: null, image_url: null, venue_name: "The Cellar", venue_area: "East",
    venue_city: "Austin", venue_address: null, venue_lat: null, venue_lng: null,
    venue_url: null, venue_phone: null, confidence: "confirmed", status: "scheduled",
    external_id: "x", on_sale_status: null, currency: null,
    source_provider: "ticketmaster", ...over,
  } as LicensedEvent;
}

const rows = [
  ev({ licensed_event_id: "in1", performer: "Austin Act", venue_city: "Austin" }),
  ev({ licensed_event_id: "in2", performer: "Bastrop Act", venue_city: "Bastrop" }),
  ev({ licensed_event_id: "unk", performer: "Unrecognised Act", venue_city: "Flavortown" }),
  ev({ licensed_event_id: "out1", performer: "Majestic Act", venue_city: "San Antonio" }),
  ev({ licensed_event_id: "out2", performer: "Seguin Act", venue_city: "Seguin" }),
];

const html = renderToStaticMarkup(<FeedApp events={rows} serverNowMs={NOW} />);

describe("the default /tonight view scopes to CAPCOG, and says so", () => {
  it("does not render a known-outside listing", () => {
    expect(html).not.toContain("Majestic Act");
    expect(html).not.toContain("Seguin Act");
  });

  it("renders in-market listings AND unrecognised places (keep-and-count)", () => {
    // An unrecognised city is a coverage gap, not a border. Dropping it would
    // make the feed look cleaner while hiding the very rows this product is
    // trying to win.
    expect(html).toContain("Austin Act");
    expect(html).toContain("Bastrop Act");
    expect(html).toContain("Unrecognised Act");
  });

  it("states N of M with M excluding only the known-outside rows", () => {
    expect(html).toContain("Showing 3 of 3 known listings for Today");
  });

  it("names the scope and counts what it is holding back — never silently", () => {
    expect(html).toContain("Scoped to the CAPCOG test region");
    expect(html).toContain("2 more listings in this window sit outside it, still in the catalog");
    expect(html).toContain("Show everywhere");
  });

  it("holds the scope without hiding a DISPUTED in-market row", () => {
    // The region is a place filter; it must never become a second trust filter.
    const h = renderToStaticMarkup(
      <FeedApp serverNowMs={NOW} events={[
        ev({ licensed_event_id: "d1", performer: "Disputed Act", confidence: "disputed" }),
        ev({ licensed_event_id: "o1", performer: "Outside Act", venue_city: "San Antonio" }),
      ]} />,
    );
    expect(h).toContain("Disputed Act");
    expect(h).toContain("sources disagree");
    expect(h).not.toContain("Outside Act");
    expect(h).toContain("Showing 1 of 1 known listing for Today");
  });

  it("agrees with itself on singular/plural — one row 'sits', many 'sit'", () => {
    const h = renderToStaticMarkup(
      <FeedApp serverNowMs={NOW} events={[
        ev({ licensed_event_id: "a1" }),
        ev({ licensed_event_id: "o1", performer: "Outside Act", venue_city: "San Antonio" }),
      ]} />,
    );
    expect(h).toContain("1 more listing in this window sits outside it, still in the catalog");
  });

  it("says nothing about held-back rows when the scope is holding none back", () => {
    const h = renderToStaticMarkup(
      <FeedApp serverNowMs={NOW} events={[ev({ licensed_event_id: "a1" })]} />,
    );
    expect(h).toContain("Scoped to the CAPCOG test region.");
    expect(h).not.toContain("sit outside it");
  });
});

describe("the source credit rides the card (founder 2026-09-01)", () => {
  it("names a promoted row's real source on the card itself", () => {
    const h = renderToStaticMarkup(
      <FeedApp serverNowMs={NOW} events={[ev({
        licensed_event_id: "p1", performer: "Promoted Act",
        source_provider: "promoted",
        origin_name: "Bastrop Opera House",
        origin_url: "https://bastropoperahouse.example",
      })]} />,
    );
    expect(h).toContain("via Bastrop Opera House");
  });

  it("stays silent on the card when the row carries no source name", () => {
    // The generic phrase belongs in the lens/detail "How we know" block, where
    // a reader asked for provenance — not as a line of chrome on every card.
    const h = renderToStaticMarkup(
      <FeedApp serverNowMs={NOW} events={[ev({
        licensed_event_id: "p2", performer: "Bare Act",
        source_provider: "promoted", origin_name: null, origin_url: null,
      })]} />,
    );
    expect(h).toContain("Bare Act");
    expect(h).not.toContain("a local listing");
    expect(h).not.toContain("via ");
  });
});
