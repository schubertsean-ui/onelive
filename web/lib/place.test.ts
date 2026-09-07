import { describe, it, expect } from "vitest";
import {
  parsePlaceToken,
  resolvePlace,
  filterToPlace,
  placeQueryStartsCrawl,
  type PlaceRow,
} from "./place";

function row(city: string, extra: Partial<PlaceRow> = {}): PlaceRow {
  return { venue_city: city, confidence: "confirmed", ...extra };
}

const catalog: PlaceRow[] = [
  row("Austin"),
  row("Round Rock"),
  row("Round Rock, TX", { confidence: "disputed" }),
  row("San Antonio"),
];

describe("parsePlaceToken — garbage fails closed", () => {
  it("accepts Round Rock TX", () => {
    expect(parsePlaceToken("Round Rock TX")).toBe("round rock");
    expect(parsePlaceToken("Round Rock, TX")).toBe("round rock");
  });

  it("fails closed on empty, punctuation, urls, markup", () => {
    for (const bad of [
      "",
      "   ",
      "???",
      "123",
      "<script>",
      "https://evil.example",
      "javascript:alert(1)",
      "a@b.c",
      "x".repeat(81),
    ]) {
      expect(parsePlaceToken(bad)).toBeNull();
    }
  });
});

describe("resolvePlace — Show / gathering / fail-closed", () => {
  it("(a) typed Round Rock TX shows Round Rock rows if present", () => {
    const r = resolvePlace("Round Rock TX", catalog);
    expect(r.kind).toBe("show");
    if (r.kind !== "show") return;
    expect(r.key).toBe("round rock");
    const shown = filterToPlace(catalog, r.key);
    expect(shown.every((row) => /round rock/i.test(String(row.venue_city)))).toBe(true);
    expect(shown.length).toBe(2);
  });

  it("(d) disputed Round Rock rows are still shown", () => {
    const shown = filterToPlace(catalog, "round rock");
    expect(shown.some((r) => r.confidence === "disputed")).toBe(true);
  });

  it("(b) unknown well-formed place is gathering, not zero", () => {
    const r = resolvePlace("Miami FL", catalog);
    expect(r.kind).toBe("gathering");
    if (r.kind !== "gathering") return;
    expect(r.label.toLowerCase()).toContain("miami");
    expect(filterToPlace(catalog, r.key)).toHaveLength(0);
  });

  it("(c) ?place= garbage fails closed to the default view", () => {
    expect(resolvePlace("???", catalog).kind).toBe("default");
    expect(resolvePlace("", catalog).kind).toBe("default");
    expect(resolvePlace(null, catalog).kind).toBe("default");
    expect(resolvePlace("<script>", catalog).kind).toBe("default");
  });

  it("(e) resolving a place does not start a crawl", () => {
    expect(placeQueryStartsCrawl()).toBe(false);
    resolvePlace("Round Rock TX", catalog);
    expect(placeQueryStartsCrawl()).toBe(false);
  });
});
