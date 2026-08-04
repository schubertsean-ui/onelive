# Decision: ratification flag normalized out of the certification hash — founder-approved "Option A" (2026-08-04)

**Founder, verbatim:** "Option A approved"

**The deadlock (discovered 2026-08-04, first post-re-lock re-opening attempt).**
`tools/routing_data.py` is a harness-manifest file, so flipping
`EXTRACTION_THRESHOLD_RATIFIED` changes the certification hash. trust_gate's
re-lock requires record hash == current tree hash while the flag is True; the
base-owned authenticator only admits records carrying the BASE (pre-flip)
tree's hash. Net: every possible flag-flip PR failed the re-lock by
construction. Latent since the re-lock armed (PR #36–#40): the only prior flip
(PR #31, 2026-07-17) predated the re-lock, and the 2026-07-18 record was minted
on an already-flipped master — so the contradiction was never exercised until
today's three-step (exam run 30923197163 → record PR #161 → flip).

**The decision.** Normalize the single `EXTRACTION_THRESHOLD_RATIFIED = True|False`
line to a canonical form before hashing `tools/routing_data.py` — in BOTH
independent hasher implementations (`ai/golden_exam.py` compute_harness_sha and
`tools/trust_gate.py` _compute_harness_sha_independent; the circular-trust
firewall between them is unchanged). Exactly one flag line is required; zero or
multiple raises and the certification check fails closed.

**Why this is sound.** The flag gates PRODUCTION publishing
(`check_ai_never_promotes` / the provider gate's `is True`), never the exam:
the attended exam does not execute it, so trees differing only in the flag have
byte-identical exam behavior. Every other byte of routing_data.py (STAGE_MODELS
above all) and every other manifest file keeps drifting the hash exactly as
before. Alternatives rejected: a one-time red-merge exception (opens a
gate-red window on master — the exact state the re-lock exists to prevent);
leaving extraction closed (contradicts the founder's standing "fully running
ingestion engine asap").

**Authority.** Gate-mechanics changes are founder-crucial (CLAUDE.md: the
classified certification surface / any named exception). Escalated with
options and tradeoffs 2026-08-04; founder approved Option A in writing (quoted
above). The change itself merges only at the mandatory non-Claude adversarial
review's APPROVE; the golden-exam verifier is red BY DESIGN on this PR
(manifest-bound refusal, flag already literal False — the enumerated,
compensated exception class (a)).

**Follow-through (the re-opening choreography under the new fingerprint).**
Post-merge master hashes to `6d023c0dbcb748d3af9d3818a9bfaa585c1e736c17c8ca6076324f952783655b`
(both hashers agree; verified invariant under a flag flip). Then: founder
attended exam #1 (subject = post-merge master tip) → record PR (authenticated,
carries the new hash) → flag-flip PR (founder attended exam #2 bound to the
flip head; trust_gate now green because the flip no longer moves the hash).
Future re-openings keep this shape permanently — the flip itself can never
deadlock the re-lock again.
