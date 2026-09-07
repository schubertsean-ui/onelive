import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * Named windows on the rendered surface (founder 2026-09-07).
 *
 * lib/feed.test.ts proves the WINDOW MATHS — bounds in America/Chicago, the
 * sum-preserving on-now/coming-up split, the fail-closed token. This file
 * proves the two things that can only be wrong in the markup:
 *
 *  1. the chips a person can actually tap, in the order the founder set, with
 *     Today still the default and Today / Tomorrow / All upcoming all kept;
 *  2. an EMPTY window says we are gathering — never "0 events in Austin" as a
 *     finished fact (Locale Launch Law §2), and always carries the way out,
 *     because an empty Tonight is not an empty site.
 *
 * The repo has no DOM test environment, so a chip cannot be clicked here. The
 * empty-window state is reached the honest way instead: a catalog whose rows
 * all sit outside the DEFAULT window, which is exactly the 1am case.
 */
vi.mock("./flow.css", () => ({}));

import FeedApp from "./FeedApp";
import type { LicensedEvent } from "../../../lib/licensed";

function ev(over: Partial<LicensedEvent>): LicensedEvent {
  return {
    licensed_event_id: "e", title: "Show", performer: "Act",
    category: "live-music", subsegment: null,
    start_time: new Date("2026-09-10T21:00:00-05:00").toISOString(),
    end_time: null, price_min: null, price_max: null, is_free: false,
    ticket_url: null, image_url: null, venue_name: "The Cellar", venue_area: "East",
    venue_city: "Austin", venue_address: null, venue_lat: null, venue_lng: null,
    venue_url: null, venue_phone: null, confidence: "confirmed", status: "scheduled",
    external_id: "x", on_sale_status: null, currency: null,
    source_provider: "ticketmaster", ...over,
  } as LicensedEvent;
}

// Thu 2026-09-10, 10:00 in Austin.
const NOW = new Date("2026-09-10T10:00:00-05:00").getTime();

const tonightRow = ev({ licensed_event_id: "t1", performer: "Tonight Act" });
const html = renderToStaticMarkup(<FeedApp events={[tonightRow]} serverNowMs={NOW} />);
const tabRow = [...html.matchAll(/<nav class="datetabs">([\s\S]*?)<\/nav>/g)][0][1];

describe("the chip row carries the named windows", () => {
  it("offers every window the founder named", () => {
    for (const label of [
      "Today", "Tonight", "Tomorrow", "This weekend", "This week",
      "Next week", "This month", "Next month", "All upcoming",
    ]) {
      expect(tabRow).toContain(`>${label}<`);
    }
  });

  it("keeps Today as the default and first, and All upcoming last", () => {
    expect(tabRow).toMatch(/class="on"[^>]*>Today</);
    expect(tabRow.indexOf(">Today<")).toBeLessThan(tabRow.indexOf(">Tonight<"));
    expect(tabRow.indexOf(">Tonight<")).toBeLessThan(tabRow.indexOf(">Tomorrow<"));
    expect(tabRow.lastIndexOf(">All upcoming<")).toBe(
      Math.max(...["Today", "Tonight", "Tomorrow", "This weekend", "This week",
        "Next week", "This month", "Next month", "All upcoming"]
        .map((l) => tabRow.lastIndexOf(`>${l}<`))),
    );
  });

  it("renders the default day, so adding windows did not move what a reader lands on", () => {
    expect(html).toContain("Tonight Act");
    expect(html).toContain("Showing 1 of 1 known listing for Today");
  });
});

describe("an empty window is a gathering state, not a verdict", () => {
  // Every row this catalog holds is a month out: the DEFAULT window is empty
  // while the site plainly is not — the 1am-Tonight shape, reachable in SSR.
  const later = ev({ licensed_event_id: "later", performer: "October Act",
    start_time: new Date("2026-10-14T21:00:00-05:00").toISOString() });
  const empty = renderToStaticMarkup(<FeedApp events={[later]} serverNowMs={NOW} />);

  it("says we are gathering, and that unread doors are unknown rather than empty", () => {
    expect(empty).toContain("we are still gathering");
    expect(empty).toContain("not a finished count of what is on");
    expect(empty).toContain("unknown, not empty");
  });

  it("never states the zero as a finished fact", () => {
    expect(empty).not.toMatch(/no events/i);
    expect(empty).not.toMatch(/0 events/i);
    expect(empty).not.toMatch(/nothing (is )?(on|happening)/i);
    // N of M still renders — the honest number, next to the honest caveat.
    expect(empty).toContain("Showing 0 of 0 known listings for Today");
  });

  it("carries the way out: an empty window is not an empty site", () => {
    const note = empty.slice(empty.indexOf('class="gnote"'));
    expect(note).toContain(">Tomorrow<");
    expect(note).toContain(">All upcoming<");
    // …and does not offer the window the reader is already looking at.
    expect(note.slice(0, note.indexOf("</div>"))).not.toContain(">Today<");
  });

  it("does not silently drop the row it does hold — All upcoming still counts it", () => {
    // The October row is out of the Today WINDOW, never out of the catalog:
    // the region line and the catch-all tab are both still on the surface.
    expect(empty).toContain(">All upcoming<");
    expect(empty).toContain("Scoped to the CAPCOG test region");
  });
});
