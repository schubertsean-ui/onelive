# 2026-07-24 — Primary-source gate on strategic/deep research (founder directive)

**Directive (verbatim):** "Don't ever assume or summarize or proceed to perform
any strategic or deep research that you are unable to access the primary
documents or files or information."

**Context:** issued immediately after PR #60 merged. That PR's
`docs/strategy/UNIVERSAL_DEV_OPERATING_MODEL_v1.md` Part 1 reconstructed Boris
Cherny's "Steps of AI Adoption" from search-result excerpts because the primary
article and every mirror returned HTTP 403 through the sandbox proxy. The
reconstruction was heavily caveated (provenance block, verbatim-excerpt
appendix, founder spot-check ask) — and that is exactly the pattern the
directive forbids: caveats do not license proceeding. The correct move was to
STOP the article-dependent thread, report the access blocker with the smallest
founder unblock (paste the text / open the link), and continue only the
repo-derived work (the Part 3 kernel, which needed no external source).

**Rule as encoded** (`docs/OPERATING_RULES.md` §1, "No research without the
primary source"): inaccessible primary ⇒ that research thread stops; blocker
report + smallest founder unblock; no excerpt/mirror/memory reconstruction as a
substitute. Work not depending on the inaccessible source may continue.

**Retroactive application (as first written):** PR #60's Part 1 was marked
BLOCKED-ON-PRIMARY-VERIFICATION (SUPERSEDED — see the Update below)
in the doc itself (same commit as this
record's first version); Parts 2–5 stood where they derive from the repo, and
any Part 2 sentence leaning on the article inherited the block. Kaizen:
founder(Red) catch, class `research-without-primary-source`, in the ledger
with this record as the counter-measure.

**Update — same day, same PR (2026-07-24):** the founder supplied the primary
artifact directly into the session ("Review this"). It is committed for audit
as `docs/research/sources/Boris_Cherny_Jul_16_2026.md` with a SHA-256
manifest alongside. Verification against it found FIVE substantive deviations
in the excerpt reconstruction (itemized in the doc's Part 1 corrections
note) — the concrete evidence for this rule. Part 1 is now VERIFIED and the
block is lifted; the gate itself stands unchanged for all future research.

**Not narrowed by:** provenance honesty, excerpt agreement across sources,
appendices, or founder-spot-check asks. None of those convert secondary
material into a primary source.

---

**Codified by:** `docs/OPERATING_RULES.md` §1 + `docs/RECORD.md` R-065, which records the gate actually firing and stopping research rather than caveating it.
