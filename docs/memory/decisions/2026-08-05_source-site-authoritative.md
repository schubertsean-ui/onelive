# 2026-08-05 — Source-site data is authoritative; the callback over-gating rolls back

## Founder directive (verbatim, 2026-08-05)

> For god's sake how many times do I need to state that if something comes
> from the source site it's authoritative - no additional gating or checking
> needed. You have overengineered this and are strangling my display of
> valid events.

Issued after eight evaluator rounds on PR #189 progressively tightened the
date-recovery callback's identity guards (nameless-Event refusal,
word-overlap thresholds, cross-format contradiction refusal).

## The ruling, applied

Once the callback link is PROVEN to be the source's own (the verbatim
URL-token check — which is what makes the page "from the source site"),
what that page declares is authoritative. REMOVED as over-gating:

- the identity-alignment guard (`_identity_aligned`) in all its forms —
  name matching, nameless refusal, word-overlap thresholds;
- the cross-format contradiction refusal (JSON-LD precedence simply wins,
  as it always did);
- the parser's Event-name capture machinery, which existed only to feed
  the removed guard.

RETAINED, with the distinction stated so this rollback is never read as
wider than it is:

- the verbatim link-token check — provenance proof, not gating: it is the
  mechanism that establishes the page IS the source's own (an
  AI-hallucinated link is not from the source);
- the SSRF bounds (private/loopback IP refusal, redirect re-validation,
  byte cap with refusal-not-truncation) — infrastructure security, not
  data gating;
- single-Event-per-format attribution: a multi-event page offers no way to
  know WHICH event's date is the candidate's — skipping it is inability to
  attribute, not distrust of the source;
- strict datetime normalization — format parsing (garbage in, nothing
  out), not second-guessing;
- the year rule's weekday consistency check — refusing to resolve
  "Friday, August 8" into a year where that date is not a Friday is
  refusing to MISQUOTE the source, never doubting it.

## Open question flagged to the founder (not acted on)

Whether this ruling also extends to gate3's corroboration hold
("Insufficient corroboration (have 1; need 2)") for discovered events from
a single source site — the pattern holding 4 of 5 sources in every
verification run. That is a promotion-gate change (founder-crucial), asked
as one consolidated question in the session report; the 2026-08-04
single-trusted-source ruling and the earned-confidence machinery already
govern what publishes today.
