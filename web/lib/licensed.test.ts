import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { buildLicensedQuery, fetchLicensedEvents } from "./licensed";

function params(qs: string): URLSearchParams {
  return new URLSearchParams(qs);
}

describe("buildLicensedQuery", () => {
  it("NEVER filters on confidence — no confidence state is dropped", () => {
    const p = params(buildLicensedQuery({ fromISO: "2026-07-24T00:00:00Z" }));
    expect(p.get("confidence")).toBeNull();
    expect((p.get("select") ?? "").split(",")).toContain("confidence");
  });

  it("bakes in NO row limit — position can never cap the result", () => {
    const p = params(buildLicensedQuery());
    expect(p.get("limit")).toBeNull();
    expect(p.get("offset")).toBeNull();
  });

  it("selects only granted columns and excludes raw", () => {
    const select = params(buildLicensedQuery()).get("select") ?? "";
    expect(select).toContain("confidence");
    expect(select.split(",")).not.toContain("raw");
  });

  it("orders with a stable unique tiebreaker so paging cannot skip/dupe", () => {
    expect(params(buildLicensedQuery()).get("order")).toBe(
      "start_time.asc,licensed_event_id.asc",
    );
  });

  it("threads optional filters through as PostgREST operators", () => {
    const p = params(
      buildLicensedQuery({
        category: "live-music",
        fromISO: "2026-07-24T00:00:00Z",
        toISO: "2026-07-31T00:00:00Z",
      }),
    );
    expect(p.get("category")).toBe("eq.live-music");
    expect(p.getAll("start_time")).toContain("gte.2026-07-24T00:00:00Z");
    expect(p.getAll("start_time")).toContain("lte.2026-07-31T00:00:00Z");
  });
});

describe("fetchLicensedEvents — pagination never drops rows by position", () => {
  const OLD = { ...process.env };
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://example.supabase.co";
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = "sb_publishable_test";
  });
  afterEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = OLD.NEXT_PUBLIC_SUPABASE_URL;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = OLD.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    vi.restoreAllMocks();
  });

  function row(i: number) {
    return { licensed_event_id: `id-${i}`, confidence: i === 1500 ? "disputed" : "confirmed" };
  }

  it("fetches BEYOND a single server-capped page (1000) and keeps the disputed row at 1500", async () => {
    // Server caps each response at 1000 rows regardless of requested Range.
    const total = 1600;
    const fetchMock = vi.fn(async (_url: string, init: RequestInit) => {
      const range = (init.headers as Record<string, string>).Range;
      const [from] = range.split("-").map(Number);
      const slice: Array<ReturnType<typeof row>> = [];
      for (let i = from; i < Math.min(from + 1000, total); i++) slice.push(row(i));
      return {
        ok: true,
        json: async () => slice,
        text: async () => "",
      } as unknown as Response;
    });
    vi.stubGlobal("fetch", fetchMock);

    const all = await fetchLicensedEvents();
    expect(all).toHaveLength(total); // nothing dropped past the 1000 cap
    expect(all.some((e) => e.confidence === "disputed")).toBe(true);
    expect(fetchMock.mock.calls.length).toBeGreaterThan(1); // it actually paged
  });

  it("throws (never silently truncates) on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 403, text: async () => "denied" }) as unknown as Response),
    );
    await expect(fetchLicensedEvents()).rejects.toThrow(/403/);
  });
});
