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

  it("unverified is surfaced with a quiet caveat", () => {
    const t = trustDisplay("unverified", SRC);
    expect(t.surface).toBe(true);
    expect(t.marker).toBeTruthy();
    expect(t.disputed).toBe(false);
  });

  // Founder ruling 2026-08-04 ("Trustworthy is trustworthy … publish without
  // the uncertainty marker"): 'likely' — one CREDIBLE source — displays clean
  // like confirmed; its sheet keeps honest provenance without doubt language.
  it("likely displays CLEAN — no marker, no caveat surface (founder ruling 2026-08-04)", () => {
    const t = trustDisplay("likely", SRC);
    expect(t.surface).toBe(false);
    expect(t.marker).toBeNull();
    expect(t.disputed).toBe(false);
    expect(t.sheet.toLowerCase()).not.toContain("not yet");
    expect(t.sheet).toContain("last word");
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
