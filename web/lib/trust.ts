// The product's trust vocabulary, rendered honestly in the consumer feed.
//
// This is CANON, not decoration (CLAUDE.md prime directive 1 — trust invariants
// are physics). The four confidence states, and the non-negotiable display rule:
//
//   * Every event's confidence is HONORED by the UI — the renderer branches on
//     it; it is never fetched-and-ignored.
//   * `disputed` is ALWAYS surfaced as disputed. Never hidden, never softened,
//     never dressed in the same authority language as a confirmed listing.
//   * `unverified` / `likely` are shown with a quiet, visible caveat.
//   * An UNKNOWN or MISSING value degrades to the MOST cautious presentation
//     (unverified-style), never to a confident one — failing toward LESS trust.
//   * Trust display rule for the licensed feed: NO badges and no "confirmed"
//     text. A confirmed listing is simply clean; caution is a quiet marker plus
//     an honest "How we know" line. (docs/design brief; charter trust rules.)
//
// The licensed feed imports rows as `confirmed` by construction, but the UI must
// hold the invariant STRUCTURALLY — so a non-confirmed row can never slip
// through wearing authority language. Proven in lib/trust.test.ts.

export type Confidence = "confirmed" | "likely" | "unverified" | "disputed";

export const CONFIDENCE_VALUES: Confidence[] = [
  "confirmed",
  "likely",
  "unverified",
  "disputed",
];

export function isConfidence(v: unknown): v is Confidence {
  return typeof v === "string" && (CONFIDENCE_VALUES as string[]).includes(v);
}

export type TrustDisplay = {
  key: Confidence;
  // Must this state be shown to the user? confirmed = false (clean, no badge);
  // every cautious state (incl. unknown) = true and is NEVER hidden.
  surface: boolean;
  // disputed = the strongest, never-softened treatment.
  disputed: boolean;
  // Quiet visible marker (null for confirmed — no "confirmed" badge, per rule).
  marker: string | null;
  // Honest one-liner for the "How we know" disclosure.
  sheet: string;
};

// Resolve a raw confidence value (+ the human source label) to how the feed
// should present it. Unknown/missing -> cautious fallback.
//
// `kind` distinguishes the two confirmed provenances honestly: a LICENSED row is
// stated by an authoritative ticketing API; a PROMOTED (pipeline-gated) row was
// reviewed through our trust gate and published from a venue/organizer listing.
// It defaults to "ticketing" so the licensed feed's copy (and its tests) are
// unchanged; only promoted rows opt into the listing wording. Nothing about this
// weakens a cautious state — likely/unverified/disputed copy is already generic.
export function trustDisplay(
  raw: string | null | undefined,
  sourceLabel: string,
  kind: "ticketing" | "listing" = "ticketing",
): TrustDisplay {
  const src = sourceLabel || "the listing source";
  switch (raw) {
    case "confirmed":
      return {
        key: "confirmed",
        surface: false,
        disputed: false,
        marker: null,
        sheet:
          kind === "listing"
            ? `Reviewed and published from ${src}. Times and prices can change; ` +
              `the venue's own page and the ticket link are the last word.`
            : `Listed by ${src} — an authoritative ticketing source. Times and ` +
              `prices can change; the venue's own page and the ticket link are the ` +
              `last word.`,
      };
    case "likely":
      return {
        key: "likely",
        surface: true,
        disputed: false,
        marker: "single source",
        sheet:
          `Reported by ${src} but not yet corroborated — shown as likely, not ` +
          `confirmed. Check the venue or ticket link before you rely on it.`,
      };
    case "disputed":
      return {
        key: "disputed",
        surface: true,
        disputed: true,
        marker: "sources disagree",
        sheet:
          `Sources disagree on this event. It is shown deliberately — not ` +
          `hidden — so you can verify before you go. Check the venue or ticket ` +
          `link as the last word.`,
      };
    // `unverified`, and ANY unknown/missing value, share the cautious fallback:
    // fail toward less trust, never more.
    default:
      return {
        key: "unverified",
        surface: true,
        disputed: false,
        marker: "unverified",
        sheet:
          raw == null || raw === "unverified"
            ? `Not yet verified against an authoritative source. Treat with ` +
              `caution and confirm via the venue or ticket link.`
            : `Unrecognized confidence state ("${raw}") — treated as unverified. ` +
              `Confirm via the venue or ticket link.`,
      };
  }
}
