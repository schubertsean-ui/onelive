import { describe, it, expect } from "vitest";
import { trustDisplay, isConfidence, CONFIDENCE_VALUES } from "./trust";

const SRC = "Ticketmaster";

describe("trustDisplay — the trust invariant, rendered", () => {
  it("confirmed is clean: no marker, not surfaced (no badge)", () => {
    const t = trustDisplay("confirmed", SRC);
    expect(t.surface).toBe(false);
    expect(t.marker).toBeNull();
    expect(t.disputed).toBe(false);
  });

  it("disputed is ALWAYS surfaced as disputed — never hidden, never softened", () => {
    const t = trustDisplay("disputed", SRC);
    expect(t.surface).toBe(true);
    expect(t.disputed).toBe(true);
    expect(t.marker).toBeTruthy();
    // and it must NOT be dressed in confirmed authority language
    expect(t.sheet).not.toBe(trustDisplay("confirmed", SRC).sheet);
    expect(t.sheet.toLowerCase()).toContain("verify");
  });

  it("unverified and likely are surfaced with a quiet caveat", () => {
    for (const k of ["unverified", "likely"] as const) {
      const t = trustDisplay(k, SRC);
      expect(t.surface).toBe(true);
      expect(t.marker).toBeTruthy();
      expect(t.disputed).toBe(false);
    }
  });

  it("unknown / missing degrades to the MOST cautious state, never confident", () => {
    for (const raw of [null, undefined, "", "banana", "CONFIRMED!!"]) {
      const t = trustDisplay(raw as string | null | undefined, SRC);
      expect(t.surface).toBe(true); // shown, not silently trusted
      expect(t.key).toBe("unverified");
      expect(t.disputed).toBe(false);
    }
  });

  it("isConfidence only accepts the four canon states", () => {
    for (const v of CONFIDENCE_VALUES) expect(isConfidence(v)).toBe(true);
    for (const v of ["", "banana", null, undefined, 3]) {
      expect(isConfidence(v)).toBe(false);
    }
  });
});
