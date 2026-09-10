import { describe, it, expect, vi, beforeEach } from "vitest";

const licensed = vi.fn();
const promoted = vi.fn();
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
vi.mock("./rooms.css", () => ({}));

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
      row({ venue_name: "Seguin Coliseum", venue_city: "Seguin" }),
      row({ venue_name: "Cheatham", venue_city: "San Marcos" }),
    ]);
    const props = await render();
    const names = (props.events ?? []).map((e) => e.venue_name);
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
