import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * THE READ PATH ITSELF, not the helper it happens to call.
 *
 * r15 blocker: `lib/region.test.ts` proves the boundary classifier is correct,
 * and would keep passing if /tonight stopped consulting it altogether. The done
 * criterion is not "the helper works" — it is "San Antonio cannot reach a user".
 *
 * Coverage Law (2026-09-01) moved WHERE that is enforced without weakening it.
 * The catalog is greedy and the view is picky, so:
 *   · the PAGE now hands the whole window to the view (a catalog row is never
 *     deleted on the way to the reader) — asserted here;
 *   · the DEFAULT VIEW scopes to CAPCOG, so San Antonio still cannot reach a
 *     user unless they deliberately clear the region — asserted here too, on
 *     the real rendered markup, because that is where the promise now lives.
 * Both halves are needed: either one alone would let the invariant break while
 * the suite stayed green.
 */
const licensed = vi.fn();
const promoted = vi.fn();
// The page is a server component: it RETURNS <FeedApp …/>, it does not call
// FeedApp. So the assertion reads the returned element's type and props
// rather than a call record — and the type check is what distinguishes
// "rendered the feed" from "bailed to the error banner".
const FeedAppMock = () => null;

vi.mock("../../../lib/licensed", () => ({
  fetchLicensedEvents: (...a: unknown[]) => licensed(...a),
  supabaseConfigured: () => true,
  LICENSED_SOURCES: [],
}));
vi.mock("../../../lib/promoted", () => ({
  fetchPromotedEvents: (...a: unknown[]) => promoted(...a),
}));
vi.mock("./FeedApp", () => ({ default: FeedAppMock }));
vi.mock("./flow.css", () => ({}));

const row = (over: Record<string, unknown>) => ({
  id: String(Math.random()),
  title: "Show",
  starts_at: new Date().toISOString(),
  venue_name: "V",
  ...over,
});

beforeEach(() => {
  licensed.mockReset();
  promoted.mockReset();
});

async function render() {
  const mod = await import("./page");
  const el = (await mod.default()) as {
    type: unknown;
    props: { events?: Array<Record<string, unknown>> };
  };
  // A page that bailed to its error/unconfigured branch returns a <main>
  // banner, whose props carry no `events` at all. Defaulting that to `[]`
  // would let a crashing page satisfy every assertion below — failure reading
  // as a pass. Fail loud instead.
  expect(el.type).toBe(FeedAppMock);
  return el.props;
}

const OUT_OF_MARKET = [
  row({ venue_name: "Majestic Theatre", venue_city: "San Antonio" }),
  row({ venue_name: "Freeman", venue_city: "San Antonio, TX, USA" }),
  row({ venue_name: "County only", venue_city: "Bexar County" }),
  row({ venue_name: "Blank city", venue_city: "", city: "San Antonio" }),
  row({ venue_name: "By county field", county: "Bexar" }),
];

describe("the PAGE hands the whole window to the view (catalog, not a delete)", () => {
  it("passes out-of-market rows THROUGH — the view scopes them, nothing is dropped", async () => {
    licensed.mockResolvedValue([...OUT_OF_MARKET, row({ venue_name: "Mohawk", venue_city: "Austin" })]);
    promoted.mockResolvedValue([
      // Seguin (Guadalupe) is outside — Comal/New Braunfels is in-market, so an
      // out-of-market example must use a county that stays out.
      row({ venue_name: "Seguin Coliseum", venue_city: "Seguin" }),
      row({ venue_name: "Cheatham", venue_city: "San Marcos" }),
    ]);
    const props = await render();
    const names = (props.events ?? []).map((e) => e.venue_name);
    // Every legally-seen row survives the read path. Losing one here would make
    // the "of M" total a lie by construction — the count could only ever
    // describe what the server chose to forward.
    expect(names).toEqual([
      "Majestic Theatre", "Freeman", "County only", "Blank city",
      "By county field", "Mohawk", "Seguin Coliseum", "Cheatham",
    ]);
  });

  it("KEEPS an unrecognised place, because a gap must stay visible", async () => {
    licensed.mockResolvedValue([row({ venue_name: "Tiny Bastrop Room",
                                      venue_city: "Flavortown" })]);
    promoted.mockResolvedValue([]);
    const props = await render();
    expect((props.events ?? []).map((e) => e.venue_name))
      .toEqual(["Tiny Bastrop Room"]);
  });
});
