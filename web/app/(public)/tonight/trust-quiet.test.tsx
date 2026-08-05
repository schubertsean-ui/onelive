import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * Trust display is QUIET (founder ruling 2026-08-05, verbatim record
 * docs/memory/decisions/2026-08-05_trust-display-quiet.md, restoring the
 * design-canon rule the #188 every-state disclosure drifted from):
 *
 *   - A solid listing (confirmed / likely) is simply CLEAN — no "How we
 *     know" block, no trust prose, no real estate spent. Provenance stays
 *     tracked internally; nothing renders.
 *   - ONLY cautious states (unverified / disputed) carry the small note:
 *     the quiet marker plus the honest sentence.
 *   - The SOURCE LINK is not part of that note. Quieting the trust display
 *     must not remove the way to check: a venue/library/university-calendar
 *     row often has no ticket URL and no venue website, and the source chip
 *     was its only path back. It is an ordinary action now, present on every
 *     row (adversarial pre-review blocker, 2026-08-05).
 *   - The unknown-price "See tickets" text never renders beside the real
 *     Get-tickets control — price shows only when actually known.
 *   - Ticket handoffs open a NEW TAB (superseding nav canon §8 same-tab):
 *     1live stays where the user left it.
 */
vi.mock("./flow.css", () => ({}));

import { Lens } from "./FeedApp";
import type { LicensedEvent } from "../../../lib/licensed";

function ev(over: Partial<LicensedEvent>): LicensedEvent {
  return {
    id: "e1",
    title: "Quiet Hollow",
    performer: "Quiet Hollow",
    category: "live-music",
    subsegment: null,
    start_time: new Date("2026-08-03T21:00:00-05:00").toISOString(),
    end_time: null,
    price_min: null,
    price_max: null,
    is_free: false,
    ticket_url: "https://tickets.example/e/1",
    image_url: null,
    venue_name: "The Cellar",
    venue_area: null,
    venue_city: "Austin",
    venue_address: null,
    venue_lat: null,
    venue_lng: null,
    venue_url: null,
    venue_phone: null,
    confidence: "confirmed",
    status: "scheduled",
    source_provider: "ticketmaster",
    ...over,
  } as LicensedEvent;
}

const noop = () => undefined;

function lensHtml(e: LicensedEvent, side: "artist" | "venue" = "artist") {
  return renderToStaticMarkup(
    <Lens e={e} side={side} onNow={false} onSide={noop} onClose={noop} />,
  );
}

describe("solid listings are clean — no trust block anywhere in the lens", () => {
  it("confirmed: neither tab renders 'How we know' or trust prose", () => {
    for (const side of ["artist", "venue"] as const) {
      const h = lensHtml(ev({}), side);
      expect(h).not.toContain("How we know");
      expect(h).not.toContain("lknow");
      expect(h).not.toContain("authoritative ticketing source");
    }
  });

  it("likely (single credible source) is equally clean", () => {
    const h = lensHtml(ev({ confidence: "likely" }));
    expect(h).not.toContain("How we know");
    expect(h).not.toContain("lknow");
  });
});

describe("only cautious states carry the small note", () => {
  it("unverified: quiet marker + honest sentence render", () => {
    const h = lensHtml(ev({ confidence: "unverified" }));
    expect(h).toContain("lknow");
    expect(h).toContain("unverified");
    expect(h).toContain("Not yet verified");
  });

  it("disputed: never hidden, marker present", () => {
    const h = lensHtml(ev({ confidence: "disputed" }));
    expect(h).toContain("lknow");
    expect(h).toContain("sources disagree");
  });

  it("unknown confidence degrades to the cautious note, never to clean", () => {
    const h = lensHtml(ev({ confidence: "???" as never }));
    expect(h).toContain("lknow");
  });
});

describe("dead controls and handoffs (founder ruling 2026-08-05)", () => {
  it("unknown price renders NO price text beside the real Get-tickets button", () => {
    const h = lensHtml(ev({ price_min: null, price_max: null, is_free: false }));
    expect(h).toContain("Get tickets");
    expect(h).not.toContain("See tickets");
  });

  it("a known price still renders", () => {
    const h = lensHtml(ev({ price_min: 25, price_max: 25 }));
    expect(h).toContain("$25");
  });

  it("the ticket handoff opens a new tab so 1live keeps its place", () => {
    const h = lensHtml(ev({}));
    const tix = h.match(/<a[^>]*class="lbtn"[^>]*>Get tickets[\s\S]*?<\/a>/);
    expect(tix).not.toBeNull();
    expect(tix![0]).toContain('target="_blank"');
    expect(tix![0]).toContain("noopener");
  });
});


describe("the source link survives the quieting (pre-review blocker)", () => {
  it("a SOLID row with no tickets and no venue site still links to the source", () => {
    // source_provider "promoted" IS the affected population: originLink only
    // resolves for promoted rows, i.e. exactly the venue/library/university
    // calendars that carry no ticket URL.
    const h = lensHtml(
      ev({ source_provider: "promoted", origin_url: "https://thevenue.example/",
           ticket_url: null, venue_url: null, venue_phone: null }), "venue");
    // Still clean — the ruling holds.
    expect(h).not.toContain("lknow");
    expect(h).not.toContain("How we know");
    // But reachable — the whole point.
    expect(h).toContain("See the source");
  });

  it("the source link is an action, not a trust element", () => {
    const h = lensHtml(
      ev({ source_provider: "promoted", origin_url: "https://thevenue.example/" }),
      "venue");
    const i = h.indexOf("See the source");
    expect(i).toBeGreaterThan(-1);
    // It sits in the actions row (.lact), never inside a trust note.
    expect(h.slice(0, i)).toContain("lact");
  });
});
