# 2026-07-25 — Adversarial Review v2 (founder-directed): panel, metrics, forced lenses, po

## Directives (founder, verbatim, 2026-07-25, session `onelife-meta-carousel`)

- "I want you to deeply evaluate the adversarial review process and specific
  instructions and operating model. Would we benefit by applying the 7 steps
  method - or version of - to the instructions for the adversarial reviewer?
  … I want this aspect of the model - adversarial review - to be true world
  class."
- On the escape hatch: "approved with the escape hatch" — then "is 'may' [too]
  loose and not flexible yet structured within a structure or some such?"
  (→ MUST-block on invariants any round; post-round-1 discoveries carry a
  named class + why-not-findable-in-round-1).
- "We also need to put a metric measure on the reviewer to ensure it is also
  getting better." (→ the M9 scorecard.)
- "should we also invite one more external reviewer - perhaps a World Model or
  one from the Bittensor network - so that we get as divergent a model analysis
  as possible?" (→ Gemini second family now; Bittensor/world-model HELD, stated
  reasons: data-egress posture for a required gate; no world model clears the
  bar yet.)
- "is there a way to try and 'get around' the fact that all the models are
  similarly constructed? … a 'forcing function' … operate as a different kind
  of frontier model within the constraints of their current model build?"
  (→ forced METHOD lenses per seat — decorrelate the search, not the prior.)
- "What if you added the deBono po to each reviewers methods on a recurring
  basis to see if that might generate even more deccorelation?" (→ a po-seeded
  lens per seat, rotating seed = the PR head SHA; stimuli-never-facts.)
- "1. Go" (build authorization for v2).

## Decisions taken (agent, within charter; gate-custody = evaluator-mandatory)

1. The reviewer is a LENS PANEL: per seat, one forced method lens + one
   po-seeded lens. OpenAI: attacker-smuggle + absence-only. Gemini (when
   the founder-minted key exists): dataflow-taint + spec-vs-contract.
2. Verdict is a strict tightening: ANY lens red = red; unparseable = hard
   fail. Convergent gate stays convergent (divergence in the lenses,
   convergence in the verdict).
3. The escape hatch is structured, not "may": invariants MUST block any
   round; other post-r1 classes carry class + why-not-earlier.
4. M9 scorecard measures the reviewer mechanically from the ledger
   (round-1 recall, sibling-misses, novelty); advisory, feeds pruning +
   digest; escapes stay kaizen_trends' hard zero.
5. Second family = Gemini, key founder-minted (never agent-minted);
   absent key = explicit empty seat, never a silent narrowing. Bittensor
   / world-model seats HELD (reasons above).
6. po provocations are stimuli, never facts (charter po rule preserved):
   hypothesize → verify at file:line → discard unverified; can only add
   candidate findings, never argue APPROVE.

## Custody / non-changes
CI runs the BASE-owned trusted copy (a PR never runs its own reviewer);
write/grade separation (non-Claude only) and the fail-closed env rules
hold on both seats; the founder-ratified 800 KB diff cap and --require
are unchanged. No downstream gate relaxed — v2 ADDS lenses and a metric.

## This PR's custody note
This PR is judged by v1 (the base copy), correct by design; v2 activates
on PRs that land AFTER it merges.

---

**Codified by:** `tools/adversarial_review.py` (panel, forced lenses, two seats, any-lens-red blocks) + `.github/workflows/adversarial-review.yml` + `docs/skills/adversarial_review_v2.md`.
