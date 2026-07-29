// Share card (group-plans P0 / brief §6.D5). The trust rules that ride into the
// shared artifact are assertions here, not sentences in a comment: disputed is
// never hidden, an unknown price is never texted as a claim, and a shared link
// resolves to the same detail page an in-app tap does.

import { describe, expect, it } from "vitest";
import { shareTitle, shareText, shareUrl, shareData, buildClipboardText } from "./share";
import { eventHref } from "./detail";
import type { LicensedEvent } from "./licensed";

function ev(over: Partial<LicensedEvent> = {}): LicensedEvent {
  return {
    licensed_event_id: "abc-123",
    source_provider: "ticketmaster",
    external_id: "tm-1",
    title: "Sister Neon",
    category: "music",
    subsegment: null,
    performer: null,
    start_time: "2026-08-01T02:00:00.000Z",
    end_time: null,
    status: "scheduled",
    on_sale_status: null,
    price_min: null,
    price_max: null,
    currency: "USD",
    is_free: null,
    ticket_url: null,
    image_url: null,
    venue_name: "Sahara Lounge",
    venue_city: "Austin",
    venue_area: "East Austin",
    venue_address: null,
    venue_lat: null,
    venue_lng: null,
    confidence: "confirmed",
    ...over,
  };
}

describe("shareTitle", () => {
  it("is the event title", () => {
    expect(shareTitle(ev())).toBe("Sister Neon");
  });
  it("falls back when a row somehow has no title", () => {
    expect(shareTitle(ev({ title: "" }))).toBe("A show on ONE LIVE");
  });
});

describe("shareText", () => {
  it("carries title, when, venue+area and a known price — the factual core", () => {
    const t = shareText(ev({ is_free: true }));
    expect(t).toContain("Sister Neon");
    expect(t).toContain("Sahara Lounge · East Austin");
    expect(t).toContain("Free");
    expect(t).toContain("via ONE LIVE");
  });

  it("adds the performer only when it differs from the title", () => {
    const same = shareText(ev({ performer: "Sister Neon" }));
    // "Sister Neon" should appear once as the headline, not twice.
    expect(same.split("\n").filter((l) => l === "Sister Neon")).toHaveLength(1);

    const diff = shareText(ev({ title: "Live at Sahara", performer: "Sister Neon" }));
    expect(diff).toContain("Live at Sahara");
    expect(diff).toContain("Sister Neon");
  });

  it("never texts a price it does not know (no 'See tickets' as if it were a price)", () => {
    // Default row has null price + null is_free -> price unknown.
    const t = shareText(ev());
    expect(t).not.toContain("See tickets");
    expect(t).not.toMatch(/\$/);
  });

  it("never dresses an unknown price as free", () => {
    // is_free:false with price_min:0 is contradictory -> unknown, not free.
    const t = shareText(ev({ is_free: false, price_min: 0 }));
    expect(t).not.toContain("Free");
  });

  it("carries the disputed caveat INTO the artifact — never hidden", () => {
    const t = shareText(ev({ confidence: "disputed" }));
    expect(t.toLowerCase()).toContain("sources disagree");
  });

  it("does not add a disputed caveat to a non-disputed row", () => {
    for (const c of ["confirmed", "likely", "unverified"]) {
      expect(shareText(ev({ confidence: c })).toLowerCase()).not.toContain("sources disagree");
    }
  });
});

describe("shareUrl", () => {
  it("is an absolute link to the SAME path eventHref builds in-app", () => {
    const e = ev();
    const url = shareUrl(e, "https://onelive.app");
    expect(url).toBe(`https://onelive.app${eventHref(e)}`);
  });

  it("tolerates a trailing slash on the origin without doubling it", () => {
    expect(shareUrl(ev(), "https://onelive.app/")).toBe(
      "https://onelive.app/tonight/abc-123",
    );
  });

  it("percent-encodes a promoted id's colon so the link stays valid", () => {
    const url = shareUrl(ev({ licensed_event_id: "promoted:xyz" }), "https://onelive.app");
    expect(url).toBe("https://onelive.app/tonight/promoted%3Axyz");
  });
});

describe("shareData / buildClipboardText", () => {
  it("shareData bundles title, text and url for navigator.share", () => {
    const d = shareData(ev(), "https://onelive.app");
    expect(d.title).toBe("Sister Neon");
    expect(d.text).toContain("Sahara Lounge");
    expect(d.url).toBe("https://onelive.app/tonight/abc-123");
  });

  it("clipboard fallback appends the link exactly once", () => {
    const s = buildClipboardText(ev(), "https://onelive.app");
    expect(s.match(/https:\/\/onelive\.app/g)).toHaveLength(1);
    expect(s.endsWith("https://onelive.app/tonight/abc-123")).toBe(true);
  });
});
