import { describe, it, expect } from "vitest";
import {
  inCapcog,
  normalizePlace,
  filterToCapcog,
  normalizeCounty,
  countyInPlace,
  inCapcogCounty,
  rowVerdict,
} from "./region";
import boundary from "./capcog-boundary.json";

describe("CAPCOG boundary on the read path", () => {
  it("drops the San Antonio venues that reached the live feed", () => {
    const rows = [
      { venue_city: "San Antonio", venue_name: "Majestic Theatre" },
      { venue_city: "San Antonio", venue_name: "Freeman Expo Hall" },
      { venue_city: "New Braunfels", venue_name: "Gruene Hall" },
      { venue_city: "Austin", venue_name: "Mohawk" },
    ];
    const out = filterToCapcog(rows);
    expect(out.kept.map((r) => r.venue_name)).toEqual(["Mohawk"]);
    expect(out.droppedOutside).toHaveLength(3);
  });

  it("KEEPS unrecognised cities and counts them, never silently drops", () => {
    // A small Bastrop or Llano venue we have not catalogued yet is exactly the
    // long-tail coverage we are trying to win. Dropping it would hide a data
    // gap while making the feed look cleaner.
    const out = filterToCapcog([{ venue_city: "Nowheresville", venue_name: "X" }]);
    expect(out.kept).toHaveLength(1);
    expect(out.unknown).toHaveLength(1);
    expect(out.droppedOutside).toHaveLength(0);
  });

  it("keeps venues across all ten counties", () => {
    for (const city of ["Austin", "Round Rock", "San Marcos", "Bastrop",
                        "Lockhart", "Marble Falls", "Johnson City", "Llano",
                        "Giddings", "La Grange"]) {
      expect(inCapcog(city)).toBe(true);
    }
  });

  it("rejects the near-misses that a 75-mile radius swept in", () => {
    for (const city of ["San Antonio", "New Braunfels", "Seguin", "Killeen",
                        "Temple", "Belton", "Lampasas"]) {
      expect(inCapcog(city)).toBe(false);
    }
  });

  it("survives the address shapes venues actually publish", () => {
    expect(normalizePlace("Austin, TX 78701")).toBe("austin");
    expect(inCapcog("Austin, TX 78701")).toBe(true);
    expect(inCapcog("San Antonio, TX 78205")).toBe(false);
    expect(inCapcog("")).toBeNull();
    expect(inCapcog(null)).toBeNull();
  });

  it("a country suffix does not smuggle a known-outside city onto the page", () => {
    // The founder's invariant failing open through formatting alone: one strip
    // per pass left "San Antonio, TX, USA" matching neither table, so it came
    // back null — and filterToCapcog KEEPS nulls.
    for (const shape of [
      "San Antonio, TX, USA",
      "San Antonio, Texas, United States",
      "SAN ANTONIO, TX 78205, USA",
      "san antonio, tx, us",
    ]) {
      expect(normalizePlace(shape)).toBe("san antonio");
      expect(inCapcog(shape)).toBe(false);
    }
    expect(inCapcog("Austin, TX, USA")).toBe(true);
  });

  it("normalizes exactly what the Python source of truth normalizes", () => {
    // The tables were generated while this logic was hand-copied, which is
    // precisely where the two sides drifted. These vectors carry Python's own
    // answers, so a future one-sided edit fails here instead of on the page.
    for (const { input, expected } of boundary.normalization_vectors) {
      expect(normalizePlace(input)).toBe(expected);
    }
  });

  it("an event with no city is shown, not assumed outside", () => {
    const out = filterToCapcog([{ venue_city: null, venue_name: "X" }]);
    expect(out.kept).toHaveLength(1);
  });

  // ---- r12 evaluator findings ------------------------------------------------

  it("a county qualifier does not smuggle an outside city onto the page", () => {
    for (const shape of [
      "San Antonio, Bexar County, TX",
      "san antonio, bexar county",
      "SAN ANTONIO, BEXAR COUNTY, TEXAS, USA",
    ]) {
      expect(normalizePlace(shape)).toBe("san antonio");
      expect(inCapcog(shape)).toBe(false);
    }
    expect(inCapcog("Austin, Travis County, TX")).toBe(true);
  });

  it("a prototype property name is not a CAPCOG place", () => {
    // `"constructor" in {}` is TRUE. Feed-supplied city strings reached that
    // check, so these were classified as real member places.
    for (const key of ["constructor", "toString", "valueOf", "hasOwnProperty"]) {
      expect(inCapcog(key)).toBe(null);
    }
    const out = filterToCapcog([{ venue_city: "constructor", venue_name: "X" }]);
    expect(out.unknown).toHaveLength(1);
    expect(out.kept).toHaveLength(1);
  });

  it("an EMPTY venue_city does not hide a real city", () => {
    // `??` only falls through on null/undefined, so "" won outright and the
    // row went out as unknown — which filterToCapcog keeps and renders.
    const out = filterToCapcog([
      { venue_city: "", city: "San Antonio", venue_name: "Majestic" },
      { venue_city: "   ", city: "San Antonio", venue_name: "Freeman" },
      { venue_city: "", city: "Austin", venue_name: "Mohawk" },
    ]);
    expect(out.kept.map((r) => r.venue_name)).toEqual(["Mohawk"]);
    expect(out.droppedOutside).toHaveLength(2);
  });

  it("county evidence decides a row the city cannot", () => {
    const out = filterToCapcog([
      { county: "Bexar", venue_city: null, venue_name: "Majestic" },
      { venue_county: "Bexar County, TX", city: "Nowhere", venue_name: "X" },
      { venue_county: "Travis", venue_name: "Mohawk" },
      { county: "Llano", city: "Somewhere Unlisted", venue_name: "Y" },
    ]);
    expect(out.kept.map((r) => r.venue_name)).toEqual(["Mohawk", "Y"]);
    expect(out.droppedOutside).toHaveLength(2);
  });

  it("county beats city when the two disagree", () => {
    expect(rowVerdict({ county: "Bexar", city: "Austin" })).toBe(false);
    expect(rowVerdict({ venue_county: "Travis", city: "San Antonio" })).toBe(true);
    expect(rowVerdict({ county: "Nowhere County" })).toBe(null);
  });

  it("agrees with Python on every county vector", () => {
    for (const { input, expected, verdict } of boundary.county_vectors) {
      expect(normalizeCounty(input)).toBe(expected);
      expect(inCapcogCounty(input)).toBe(verdict);
    }
  });

  it("county evidence INSIDE a city string survives a state suffix", () => {
    // r13: COUNTY_RE is anchored at the end, so running it on the raw string
    // meant ", TX" defeated the anchor and the decisive fact was dropped.
    const out = filterToCapcog([
      { venue_city: "Unlisted Spot, Bexar County, TX", venue_name: "X" },
      { venue_city: "Unlisted Spot, Bexar County, TX, USA", venue_name: "Y" },
      { venue_city: "Nowhere Bar, Travis County, TX", venue_name: "Keep" },
    ]);
    expect(out.kept.map((r) => r.venue_name)).toEqual(["Keep"]);
    expect(out.droppedOutside).toHaveLength(2);
  });

  it("agrees with Python on every embedded-county vector", () => {
    for (const { input, expected } of boundary.embedded_county_vectors) {
      expect(countyInPlace(input)).toBe(expected);
    }
  });
});
