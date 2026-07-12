import { describe, it, expect } from "vitest";
import { confidenceDisplay } from "./confidence";
import { CONFIDENCE_VALUES, isConfidence } from "./public-types";

describe("confidenceDisplay", () => {
  it("maps every known confidence state to a matching display", () => {
    for (const c of CONFIDENCE_VALUES) {
      const d = confidenceDisplay(c);
      expect(d.key).toBe(c);
      expect(d.tone).toBe(c);
      expect(d.label.length).toBeGreaterThan(0);
      expect(d.blurb.length).toBeGreaterThan(0);
    }
  });

  it("marks unverified and disputed as cautious; confirmed and likely as not", () => {
    expect(confidenceDisplay("confirmed").cautious).toBe(false);
    expect(confidenceDisplay("likely").cautious).toBe(false);
    expect(confidenceDisplay("unverified").cautious).toBe(true);
    expect(confidenceDisplay("disputed").cautious).toBe(true);
  });

  it("disputed is never softened — label stays 'Disputed' and tone stays disputed", () => {
    const d = confidenceDisplay("disputed");
    expect(d.label).toBe("Disputed");
    expect(d.tone).toBe("disputed");
    expect(d.cautious).toBe(true);
  });

  it("null confidence fails SAFE: degrades to cautious unverified, not to trusted", () => {
    const d = confidenceDisplay(null);
    expect(d.tone).toBe("unverified");
    expect(d.cautious).toBe(true);
    // must never silently present as confirmed/likely
    expect(["confirmed", "likely"]).not.toContain(d.tone);
  });

  it("undefined confidence fails SAFE the same way as null", () => {
    const d = confidenceDisplay(undefined);
    expect(d.tone).toBe("unverified");
    expect(d.cautious).toBe(true);
  });

  it("unrecognized confidence string fails SAFE and names the bad value honestly", () => {
    const d = confidenceDisplay("super-legit-trust-me");
    expect(d.tone).toBe("unverified");
    expect(d.cautious).toBe(true);
    expect(d.blurb).toContain("super-legit-trust-me");
  });
});

describe("isConfidence type guard", () => {
  it("accepts exactly the four known states", () => {
    for (const c of CONFIDENCE_VALUES) expect(isConfidence(c)).toBe(true);
  });
  it("rejects unknown / non-string values", () => {
    expect(isConfidence("nope")).toBe(false);
    expect(isConfidence(null)).toBe(false);
    expect(isConfidence(undefined)).toBe(false);
    expect(isConfidence(42)).toBe(false);
    expect(isConfidence("")).toBe(false);
  });
});
