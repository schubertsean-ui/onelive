import { describe, it, expect } from "vitest";
import { buildLicensedQuery } from "./licensed";

function params(qs: string): URLSearchParams {
  return new URLSearchParams(qs);
}

describe("buildLicensedQuery", () => {
  it("NEVER filters on confidence — no confidence state is dropped", () => {
    const p = params(buildLicensedQuery({ fromISO: "2026-07-24T00:00:00Z" }));
    // confidence is SELECTED (so the UI can honor it) but is never a filter
    // parameter — no confidence state, disputed included, is ever excluded.
    expect(p.get("confidence")).toBeNull();
    expect((p.get("select") ?? "").split(",")).toContain("confidence");
  });

  it("selects only granted columns and excludes raw", () => {
    const p = params(buildLicensedQuery());
    const select = p.get("select") ?? "";
    expect(select).toContain("licensed_event_id");
    expect(select).toContain("confidence");
    expect(select.split(",")).not.toContain("raw");
  });

  it("applies status, ordering, and a default limit", () => {
    const p = params(buildLicensedQuery());
    expect(p.getAll("status")).toContain("in.(scheduled,moved)");
    expect(p.get("order")).toBe("start_time.asc");
    expect(p.get("limit")).toBe("1000");
  });

  it("threads optional filters through as PostgREST operators", () => {
    const p = params(
      buildLicensedQuery({
        category: "live-music",
        fromISO: "2026-07-24T00:00:00Z",
        toISO: "2026-07-31T00:00:00Z",
        limit: 50,
      }),
    );
    expect(p.get("category")).toBe("eq.live-music");
    expect(p.getAll("start_time")).toContain("gte.2026-07-24T00:00:00Z");
    expect(p.getAll("start_time")).toContain("lte.2026-07-31T00:00:00Z");
    expect(p.get("limit")).toBe("50");
  });
});
