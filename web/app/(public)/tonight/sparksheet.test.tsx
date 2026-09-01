import { describe, it, expect, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

/**
 * The ✳ tap-to-dismiss disclosure sheet (UI Canon §4).
 *
 * What must hold, verbatim from canon: an AI-drafted (tier C) Spark Line
 * "renders in a slightly distinct register … with a small ✳"; "Tapping opens a
 * one-tap-dismiss sheet: 'Drafted from [artist]'s own materials.'" (the second
 * sentence founder-removed 2026-08-04) — and trust display is physics, so this suite pins
 * the sheet's existence, its copy, and the structural constraint that makes it
 * legal on the card: the disclosure is interactive, therefore it must never
 * nest inside the artist-door <button> (axe: nested-interactive).
 */
vi.mock("./flow.css", () => ({}));

import FeedApp, { SparkLineView } from "./FeedApp";
import type { LicensedEvent } from "../../../lib/licensed";

const tierC = { text: "porch hymns, slow and holy", tier: "C" as const, attribution: "first notes" };
const tierB = { text: "brass. menace. amen.", tier: "B" as const, attribution: "QA Weekly" };

function ev(over: Partial<LicensedEvent>): LicensedEvent {
  return {
    // The feed keys its card lists on licensed_event_id. This fixture carried a
    // stale `id` instead (bypassing the type through the `as` cast below), so
    // every render through FeedApp handed React key={undefined} and emitted
    // "Each child in a list should have a unique key prop" — a warning that
    // says nothing about the app and would mask a real one (evaluator nit,
    // PR #202). The app code was always right; the test data was not.
    licensed_event_id: "e1",
    title: "Quiet Hollow",
    performer: "Quiet Hollow",
    category: "live-music",
    subsegment: null,
    start_time: new Date("2026-08-03T21:00:00-05:00").toISOString(),
    end_time: null,
    price_min: null,
    price_max: null,
    is_free: true,
    ticket_url: null,
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

describe("SparkLineView — the §4 disclosure", () => {
  it("tier C renders a native <details> disclosure whose sheet carries the canon copy with the artist's name", () => {
    const html = renderToStaticMarkup(<SparkLineView spark={tierC} artist="Quiet Hollow" />);
    expect(html).toContain("<details");
    expect(html).toContain("<summary");
    expect(html).toContain("✳");
    // The canon sentence, personalized — the sheet is real content, not a title tooltip.
    expect(html).toContain("Drafted from Quiet Hollow’s own materials.");
    // Founder-removed 2026-08-04 ("Remove this: [Artist] can make it theirs anytime.").
    expect(html).not.toContain("can make it theirs");
    // One tap in, one tap gone: a <details> needs no JS, no modal, no history entry.
    expect(html).not.toContain("dialog");
  });

  it("tier B renders plain text with attribution — no disclosure, no ✳", () => {
    const html = renderToStaticMarkup(<SparkLineView spark={tierB} artist="Quiet Hollow" />);
    expect(html).not.toContain("<details");
    expect(html).not.toContain("✳");
    expect(html).toContain("brass. menace. amen.");
    expect(html).toContain("QA Weekly");
  });

  it("no spark → renders nothing (honest gap, never filler)", () => {
    expect(renderToStaticMarkup(<SparkLineView spark={null} artist="X" />)).toBe("");
  });
});

describe("the card — disclosure never nests inside the artist door", () => {
  function feedHtml(spark: typeof tierC | typeof tierB) {
    return renderToStaticMarkup(
      <FeedApp events={[ev({ spark })]} serverNowMs={new Date("2026-08-03T20:00:00-05:00").getTime()} />,
    );
  }

  it("tier C: every <button> is childless of <details>/<summary> (axe nested-interactive)", () => {
    const html = feedHtml(tierC);
    expect(html).toContain("<details");
    for (const m of html.matchAll(/<button[^>]*>([\s\S]*?)<\/button>/g)) {
      expect(m[1]).not.toContain("<details");
      expect(m[1]).not.toContain("<summary");
    }
  });

  it("the artist door still announces the spark text and still exists as a button", () => {
    const html = feedHtml(tierC);
    expect(html).toMatch(/<button[^>]*aria-label="[^"]*porch hymns, slow and holy[^"]*open artist details/);
  });

  it("tier B: no disclosure appears anywhere on the card", () => {
    expect(feedHtml(tierB)).not.toContain("<details");
  });
});
