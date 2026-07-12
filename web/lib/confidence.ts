// Honest confidence display — the trust contract rendered in the UI.
//
// RULES (mirror the product's trust invariants):
//  * Every event shows its confidence state explicitly. There is no "silent"
//    or hidden state.
//  * `disputed` is always shown AS disputed (never dropped, never softened).
//  * `unverified` is shown with its caveat — never dressed up as trusted.
//  * An UNKNOWN or MISSING confidence value degrades to the most cautious
//    presentation ("unverified"-style), never to a confident one. Failing safe
//    means failing toward LESS trust, not more.
import { Confidence, isConfidence } from "./public-types";

export type ConfidenceDisplay = {
  key: Confidence;
  label: string; // human-facing badge text
  blurb: string; // one-line honest explanation (for tooltip / aria)
  tone: "confirmed" | "likely" | "unverified" | "disputed"; // drives styling
  // Whether the UI should visually foreground a caution treatment.
  cautious: boolean;
};

const TABLE: Record<Confidence, ConfidenceDisplay> = {
  confirmed: {
    key: "confirmed",
    label: "Confirmed",
    blurb: "Corroborated by an anchor source or multiple independent sources.",
    tone: "confirmed",
    cautious: false,
  },
  likely: {
    key: "likely",
    label: "Likely",
    blurb: "Supported by a credible source but not yet fully corroborated.",
    tone: "likely",
    cautious: false,
  },
  unverified: {
    key: "unverified",
    label: "Unverified",
    blurb: "Reported by a single non-anchor source. Treat with caution.",
    tone: "unverified",
    cautious: true,
  },
  disputed: {
    key: "disputed",
    label: "Disputed",
    blurb: "Sources conflict on this event. Shown deliberately — verify before you go.",
    tone: "disputed",
    cautious: true,
  },
};

// Resolve any raw API value to a display. Unknown/missing -> cautious fallback.
export function confidenceDisplay(raw: string | null | undefined): ConfidenceDisplay {
  if (isConfidence(raw)) {
    return TABLE[raw];
  }
  // Fail safe: an unrecognized or absent state is treated as the LEAST trusted
  // presentation, and labels the value as unverified.
  return {
    key: "unverified",
    label: "Unverified",
    blurb:
      raw == null
        ? "No confidence state reported. Treated as unverified until corroborated."
        : `Unrecognized confidence state (\u201c${raw}\u201d). Treated as unverified.`,
    tone: "unverified",
    cautious: true,
  };
}
