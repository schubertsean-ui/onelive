# The golden-exam red-by-design exception (the one enumerated exception to "every required check green")

**Status: CANON.** Extracted verbatim from `CLAUDE.md` prime directive 1 on
2026-07-26 so the charter can be read in one sitting. **Nothing here is weakened
or reworded** — the governing text is quoted below exactly as it was ratified.
The mechanisms it describes are unchanged and remain live.

## Plain-language summary (read this first)

The agent may merge its own pull request only when the independent non-Claude
reviewer has **APPROVED** and **every required check on the final head is
green**. Red or pending is a hard stop.

There is exactly **one** enumerated exception, and it exists because one check is
*designed* to go red. The golden-exam verifier refuses to certify any change to
the extraction exam's own harness — it will not vouch for code the attended exam
did not execute. That refusal is correct behaviour, not a failure.

The exception is safe only because a **machine**, never the agent's judgement,
decides whether it applies:

- `tools/classify_extraction_surface.py` reads the harness manifest **as data**
  from the single source the exam runner stamps, and partitions the refused files
  into two classes.
- **Manifest-bound files** (the exact set the harness hash covers) are eligible
  only if the same PR turns extraction **off** (`EXTRACTION_THRESHOLD_RATIFIED`
  set to literal `False`). Extraction then stays off, fail-closed, until the
  standing three-step re-opens it: the founder's attended exam on the new harness
  → an authenticated record PR → a head-bound flag-flip PR. There is no
  double-red merge path.
- **Non-manifest files** are covered structurally: they affect no trust decision
  except through base-owned copies (a PR's own copy never judges it), and the
  change merges only at the mandatory non-Claude review's APPROVE.
- An **unreadable manifest** makes a refusal INELIGIBLE. Any change to
  `ai/golden/CERTIFIED_HARNESS.json` accompanying a refusal makes it INELIGIBLE.
  Both print a canonical `EXCEPTION-INELIGIBLE` marker and the review's evidence
  step fails closed on it mechanically.

**Adding any further named exception is a gate-threshold relaxation:
founder-crucial.** Never an agent decision.

## The ratified text, verbatim

> **Trust invariants are physics, not policy.** AI never publishes; orchestrator
> cannot import the promote path; no pay-to-rank surface, ever; disputed
> shown-never-hidden; RLS stays fail-closed. Any change touching these = STOP and
> escalate to founder. Scope note (founder-ratified 2026-07-18, verbatim directive
> "You do the merge and notify me" —
> docs/memory/decisions/2026-07-18_agent-merges-on-green.md): "AI never publishes"
> governs the PRODUCT data path (extraction → candidate → gate → promote → users)
> and every outward-facing product surface — it is NOT narrowed by repo
> operations. Distinctly and explicitly: the agent MAY merge its own PR only when
> the independent non-Claude evaluator has APPROVED and every required check on
> the final head is green (red or pending = hard stop, no exceptions), notifying
> the founder at merge. Product publishing remains gate-custodied and
> founder-controlled exactly as before. Exception, enumerated, closed, and
> MECHANICALLY compensated per class (founder-ratified 2026-07-18 "Ratified";
> mechanics added at the evaluator's demand on PR #36, the per-class scope split at
> its r3 — the classified surface is broader than the certification hash, so one
> blanket "red moves" claim was fail-open): the golden-exam verifier is red BY
> DESIGN on any PR that modifies the exam harness surface — the CLASSIFIER is the
> verifier's own harness-refusal output ("changes extraction HARNESS code that the
> attended exam does not execute"), never agent judgment, and the classifier
> itself partitions the refused files into the two classes below
> (tools/classify_extraction_surface.py, reading HARNESS_MANIFEST as data from the
> single source the exam runner stamps — mechanical identity, never
> hand-mirrored). That red does not count against "every required check green"
> ONLY for refusals PROVEN to contain no manifest-bound file — eligibility is read
> off the classifier's own printed partition (or, for refusals emitted by the
> pre-partition classifier, checked directly: no listed file appears in
> HARNESS_MANIFEST), and an unreadable manifest makes a refusal INELIGIBLE (the
> classifier prints exactly that — fail closed, never fail-open). Both classes are
> covered, each by a LIVE compensating control (the bootstrap completed 2026-07-18
> — gate #36, evidence plumbing #37/#38, verifier hygiene #39, authenticated
> record #40, re-lock in the same commit as this sentence; no unmerged code ever
> judged anything): (a) MANIFEST-BOUND files (the exact set compute_harness_sha()
> covers): trust_gate's extraction-certification re-lock fails the whole tree
> whenever EXTRACTION_THRESHOLD_RATIFIED is True while the current harness hash
> differs from the committed attended-exam certification record
> (ai/golden/CERTIFIED_HARNESS.json, outside the manifest so recording cannot
> alter what it certifies, and enterable or changeable ONLY through the base-owned
> online authenticator in extraction-eval.yml). Because that re-lock fires on the
> PR itself, a manifest-bound refusal is eligible ONLY when the SAME PR sets
> EXTRACTION_THRESHOLD_RATIFIED to literal False (the classifier verifies this
> from the subject's routing data and prints it; anything else carries the
> EXCEPTION-INELIGIBLE marker — there is no double-red merge path, ever): the
> closure moves, not the red — extraction is OFF, fail-closed, from merge until
> the standing three-step re-opens it (founder's attended exam on the new harness
> → authenticated record PR → head-bound flag-flip PR), and trust_gate stays green
> throughout because a closed extraction needs no certification while the re-lock
> still hard-stops any certified-but-drifted state (e.g. a direct push). The
> re-lock computes the harness hash with trust_gate's OWN manifest copy and
> hasher, never the manifest-bound runner's (r3: circular trust — the compensated
> PR class must not be able to alter the computation that judges it); single-sided
> copy drift fails the test suite in the same PR, and a coordinated change of both
> copies necessarily touches trust-path files, whose compensation is the mandatory
> review. The re-lock compensates the UNCHANGED, previously-authenticated record
> only — a refusal accompanied by ANY change to ai/golden/CERTIFIED_HARNESS.json
> is INELIGIBLE (the refusal precludes the authenticator from running, so the
> changed record would enter unverified; the classifier prints a canonical
> EXCEPTION-INELIGIBLE marker and the review's evidence step fails closed on it
> mechanically — land records separately, after their harness merges and an
> attended exam certifies them). An unclassifiable refusal (unreadable manifest)
> is likewise INELIGIBLE, same marker, same mechanical fail. (b) NON-manifest
> surface files (verifier/trust-path code and exam data outside the manifest) ARE
> covered now: their compensation is structural and already live — they affect no
> trust decision except through base-owned copies (pull_request_target: a PR's
> copy never judges itself) and per-run data bindings re-derived from base at every
> evidence verification (golden/prompt/model/dependency-lock hashes), and the
> change itself merges only at the mandatory non-Claude adversarial review's
> APPROVE on that very PR (adversarial-review.yml, every PR, no path filter).
> Adding any further named exception is a gate-threshold relaxation:
> founder-crucial.

## One correction the 2026-07-26 audit requires

The opening clause "AI never publishes" is **narrower than it reads**, and the
charter now states the narrower form directly. On 2026-07-25 the founder ratified
auto-publish at earned confidence
(`docs/memory/decisions/2026-07-25_auto-publish-earned-confidence-ratification.md`).
What is physics is: **the AI that extracts never decides what publishes** —
extraction cannot promote, the gate decides, and fabrication is never published.
Applying a *gate-passing* decision without a human click is an operational rule
the founder may set, and did. Nothing about that changes the text above, which
governs repo merges and the exam exception only.
