import { describe, it, expect } from "vitest";
import { inCapcog, normalizePlace, filterToCapcog } from "./region";
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
});
