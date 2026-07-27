import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * THE READ PATH ITSELF, not the helper it happens to call.
 *
 * r15 blocker: `lib/region.test.ts` proves filterToCapcog is correct, and
 * would keep passing if /tonight stopped calling it altogether. The done
 * criterion is not "the helper works" — it is "San Antonio cannot reach a
 * user". This test binds the assertion to the page that renders to one.
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
  // would let a crashing page satisfy every "these rows are dropped"
  // assertion below — failure reading as a pass. Fail loud instead.
  expect(el.type).toBe(FeedAppMock);
  return el.props;
}

describe("/tonight never renders an out-of-market event", () => {
  it("drops San Antonio and every shape it arrives in", async () => {
    licensed.mockResolvedValue([
      row({ venue_name: "Majestic Theatre", venue_city: "San Antonio" }),
      row({ venue_name: "Freeman", venue_city: "San Antonio, TX, USA" }),
      row({ venue_name: "County only", venue_city: "Bexar County" }),
      row({ venue_name: "Blank city", venue_city: "", city: "San Antonio" }),
      row({ venue_name: "By county field", county: "Bexar" }),
      row({ venue_name: "Mohawk", venue_city: "Austin" }),
    ]);
    promoted.mockResolvedValue([
      row({ venue_name: "Gruene Hall", venue_city: "New Braunfels" }),
      row({ venue_name: "Cheatham", venue_city: "San Marcos" }),
    ]);
    const props = await render();
    const names = (props.events ?? []).map((e) => e.venue_name);
    expect(names).toEqual(["Mohawk", "Cheatham"]);
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
