# ONE LIVE — Held-Out Brain Eval v1 (the un-game-able test split)

**What this is (plain language):** a SECOND brain benchmark that a
self-optimizing agent cannot cheat. The first benchmark
(`docs/strategy/ONE_LIVE_BRAIN_BENCHMARK_v1.md`, run by `tools/brain_eval.py`)
is committed and readable, so an agent trying to make the brain "score higher"
could simply tune it to those exact questions — a fake improvement that teaches
the brain nothing. This adds the standard machine-learning fix: a **held-out
test set** the optimizing change cannot see, alter, or grade, scored from a
**base-owned** copy exactly like the extraction golden exam.

- Run it (dev mirror): `python tools/brain_held_out_eval.py`
- The hidden set + loader: `brain/eval/held_out.py` + `brain/eval/held_out_pages.json`
- The authority: `.github/workflows/brain-held-out-eval.yml` (base-owned, on every PR)
- The proofs: `tests/test_brain_held_out_eval.py`

## Why this, not the alternatives

- **Why a held-out set, not "just trust `brain_eval.py`"?** A single visible
  benchmark measures memory, but it also *teaches to the test*: once the
  questions are in the repo, "improving the score" and "overfitting the score"
  look identical. The dev/test split is the oldest, cheapest, best-understood
  defense against that specific failure.
- **Why base-ownership (pull_request_target), not a secret file?** Nothing in a
  git repo is truly secret to a PR author — they can read every committed byte.
  Hiding the file would be security theater. Instead we borrow the mechanism the
  repo already trusts for the extraction exam: GitHub runs the **base branch's**
  copy of the workflow, the scorer, and the hidden questions against the PR's
  brain. A PR that rewrites the questions, lowers the floor, or softens the
  scorer is judged by the copy it does **not** control. Tradeoff: the questions
  are visible in git history, so this stops *tampering and self-grading*, not
  *inference* (see "What this does NOT protect against").
- **Why reuse the existing scorer, not a new one?** The held-out set runs
  through the SAME deterministic `harness.run_benchmark` (no LLM, no network, no
  spend). Reusing it means the hidden set can only be *harder or easier*, never
  *scored more leniently* — there is one scorer, and base owns it.

## How the blindness works (step by step)

1. A PR changes the brain (`brain/graph.py`, `brain/schema.py`, ...) — possibly
   also touching `brain/eval/held_out*` to try to cheat.
2. `.github/workflows/brain-held-out-eval.yml` fires on `pull_request_target`,
   so GitHub runs the **base** branch's copy of the workflow.
3. It checks out base (the trusted judge) and the PR head (the brain under test),
   then **overlays base's** `brain/eval/{__init__,benchmark,harness,held_out}.py`,
   `brain/eval/held_out_pages.json`, and `tools/brain_held_out_eval.py` over the
   subject tree.
4. It runs the scorer from the subject root, so the questions + scorer + floor
   are **base's**, but the brain **engine** answering them is the PR head's.
5. Below-floor (exit 1) or could-not-run (exit 2) fails the check, closed.

The in-repo copy is the **DEV MIRROR** — it lets us run and test the machinery
locally; the BASE-run copy is the **AUTHORITY**. A local green is not proof,
because the same PR that changes the brain can change its local copy of this
tool; only the base-owned run cannot be edited by the PR it judges.

## Security posture (honest)

To measure the PR's brain we **must execute the PR head's brain engine** — that
is subject code, and `pull_request_target` normally carries a write token and
secrets. We shrink the blast radius to nothing worth stealing and state the
residual instead of hiding it:

- `permissions: contents: read` — the token is read-only; executed subject code
  cannot push, comment, or mutate.
- **No secrets** reach any step — the eval is deterministic and offline, so
  there is nothing to exfiltrate (this is exactly why running subject code is
  acceptable here but not in the golden exam, which needs the Anthropic key and
  therefore never runs subject code).
- `persist-credentials: false` on both checkouts — no git credential on disk.
- Only the **base-owned** scorer/CLI runs; we do **not** run the subject's
  tests, build, or setup scripts.
- **Residual, stated plainly:** the subject brain engine runs on the runner.
  That is inherent to evaluating a code artifact; the read-only, secretless job
  makes it a safe residual rather than a live risk.

## What this does and does NOT protect against

**Protects against:**
- Overfitting the visible questions and posting a fake improvement — proven by
  the test where an answerer that **memorizes the visible gold answers** scores
  a perfect 1.0 on the visible set but collapses below the floor on the held-out
  set (`test_memorizing_visible_set_passes_visible_but_fails_held_out`).
- Tampering with the hidden set, floor, or scorer in the same PR — base owns the
  copy that runs.
- A brain that quietly regresses — planted regressions (dropped hop, time-blind
  read, fabrication, broken resolution) each turn the held-out gate red.

**Does NOT protect against (named honestly):**
- **Distribution inference.** The held-out corpus is committed, so a
  sufficiently capable agent can *read it in git history* and infer the shape,
  categories, entities, and phrasing of the hidden questions, then optimize for
  that distribution. This is base-ownership's inherent limit: it defeats
  *self-grading and tampering*, not *knowing the test exists*. A truly blind set
  would require an off-repo secret store (a future step, gated as a trust
  change). Until then, treat a held-out pass as *necessary, not sufficient*.
- **Shared-distribution overfitting.** Because the held-out set mirrors the
  visible set's *structure* (same six categories, same claim-encoding
  convention), an agent could overfit the *family* of questions rather than the
  exact strings. The disjointness guarantee is on question text and gold
  answers, not on the underlying skill distribution.
- **A wrong or too-low floor.** The floor is a one-way ratchet, but its starting
  value is a human judgment. A floor set too low certifies a weak brain; raising
  it is gate-custody (evaluator-reviewed).

## The one-way ratchet

`brain/eval/held_out_pages.json` → `baselines.categories` are per-category
floors. When the brain genuinely improves, RE-MEASURE and RAISE the affected
floor in the same PR — it only ever goes up (mirrors `brain_eval.py` and
`surface_regression_exam.py`). Lowering a floor is a gate-threshold relaxation:
founder-crucial.

## This is a fitness function

This held-out score is precisely the objective a future self-improvement loop (a
po-driven search, or a multi-brain population competing on memory quality) must
optimize **without being able to see the answer key**. That is the whole reason
it is base-owned: an optimizer that could edit its own test set would climb a
fake hill. Here, the hill is fixed by base, so climbing it means the brain
actually got better at held-out memory — subject to the inference caveat above.
