# Health check #1 — the 2026-07-26 revamp, before and after

**This is the permanent record of what the 2026-07-26 evaluation-and-revamp
actually changed.** The founder asked to see it proven rather than described:
*"I want an accounting of the number of lines of code, types, etc — whatever would
be world class evaluation of a code and functionality and structure and

## PRUNED to its numbers and its regeneration command (2026-07-27)

**The prose sections of this snapshot were removed.** They are a *generated report's*
commentary, and the r5 reviewer's own nit said it plainly: this file is "visibly stale
relative to the current diff and validate output… future readers need to be steered
harder toward regenerating rather than trusting the snapshot prose."

**Steering, then.** Do not read a snapshot for current state — regenerate it:

```
PATH="$HOME/.venvs/onelive/bin:$PATH" python tools/health_check.py --baseline f907a51
```

The numbers below are kept because they are the before/after accounting the founder
asked for, and a table of measurements does not go stale silently — it is dated, and its
`--baseline` is named. The removed narrative is in git history
(`git show 94895a9:docs/health/2026-07-26_health-check-01-revamp-baseline.md`) and its
uncomfortable findings are tracked where they can be acted on: R-066 (unwired modules),
J8 (prose growth), and `docs/BAR.md`'s own status column.

**Why now:** the mandatory independent review HARD-FAILED because PR #76 exceeded the
founder-ratified reviewer cap. A generated report's prose is the cheapest thing in the
diff to lose and the reviewer had already asked for exactly this change. R-088.

| Metric | Before | After | BAR row |
|---|---|---|---|
| Code lines — product | 13295 | 13273 | F5 / J8 |
| Code lines — tests | 22896 | 23316 | F5 / J8 |
| Code lines — harness_tools | 9836 | 10353 | F5 / J8 |
| Code lines — brain | 5393 | 5393 | F5 / J8 |
| Code lines — off_mission | 3974 | 3974 | F5 / J8 |
| Prose words (all tracked Markdown) | 270317 | 302921 | J8 |
| Read-before-code words | 12116 | 11256 | J8 |
| Read-before-code documents | 7 | 4 | J8 |
|   ...which binding set was measured | legacy set (pre-2026-07-26) | CANON (post-2026-07-26) | J8 |
| BAR rows — rows | 0 | 80 | — |
| BAR rows — purpose_rows | 0 | 14 | P1–P14 |
| BAR rows — MET | 0 | 51 | — |
| BAR rows — NOT MET | 0 | 13 | — |
| BAR rows — UNMEASURED | 0 | 12 | — |
| BAR rows — NOT BUILT | 0 | 2 | — |
| RECORD rows OPEN | 40 | 51 | F7 |
| RECORD rows RESOLVED | 14 | 15 | F7 |
| Red classes indexed | 35 | 37 | J6 |
| Escaped defects (M3) | 0 | 1 | G4 |
| validate checks | 14 | 14 | — |
| Unwired modules (prod-unreachable) | 16 | 14 | F5 |
| Gate/threshold files changed vs baseline | — | tools/validate | J5 |

## Unwired modules — 14 production-unreachable (BAR F5)

Imported by nothing except tests. Each is built, green, and reachable
from no production path. `wire it or delete it` — a module nothing can
reach is not done.

- `brain/paths.py`
- `social/carousel/agent_loop.py`
- `social/carousel/example_fixtures.py`
- `social/carousel/launch.py`
- `social/carousel/publish_gate.py`
- `ventures/promise_ledger/eval/golden.py`
- `ventures/promise_ledger/extract/due_dates.py`
- `ventures/promise_ledger/ingest/edgar.py`
- `ventures/promise_ledger/store/ledger.py`
- `worker/convergence/decisions.py`
- `worker/fetch/render_fetch.py`
- `worker/publish_policy.py`
- `worker/source_rank.py`
- `worker/source_reliability.py`

All metrics computed; nothing unverified.
---

## Interpretation of specific rows

**Read-before-code, 12,116 → 11,147 words across 7 → 4 documents (−8.0%).** The
comparison is like-for-like: at the baseline the tool measures the set that was
*then* binding (`CLAUDE.md`, `OPERATING_RULES`, `WORLD_CLASS`, `KAIZEN`,
`construction_loop`, `hats/README`, `adversarial_review_v2`), because measuring
today's four-document CANON list against a past that contained one of them would
report growth where the truth is consolidation. The word cull is modest; the
structural gain — a bar with numbers instead of a citation essay, a v1 definition
that did not exist, an index saying which of 152 documents bind you — is the part
worth having.

**Escaped defects 0 → 1.** This is not a regression introduced by the work; it is
a pre-existing escape becoming *visible*. The defect shipped before this session.
What changed is that the ledger now records it in the form the gate can count,
which is why the gate is currently red and why founder ask 5 exists.

**Unwired modules — the list below is the real backlog.** Sixteen modules,
including `worker/publish_policy.py` (the founder-ratified auto-publish policy) and
`worker/source_reliability.py` (safeguard 1 of that same ratification). The
detector found both independently, having been written without reference to those
findings — which is the check on the check.

## What a real revamp would be, if that is what comes next

Untouched by this work: the architecture, the promote path, the deployment, and the
16 unwired modules. An honest scope for an actual code-and-structure revamp:

1. **Decide the 16.** Each is wire-it-or-delete-it. `brain/` (5,393 lines),
   `ventures/promise_ledger`, and the carousel posting path are whole subsystems
   inside that list. This is a decision first and a day of work second.
2. **Wire `worker/autopromote.py`** so a gate-passing event reaches users without a
   human click — `docs/V1.md` Step 2, the largest real engineering left, and the
   thing the founder said does not scale.
3. **Measure the experience** — `docs/V1.md` Steps 5–7, including the ten-second
   answer that has never been measured once.

Two of those three are already the top of `docs/V1.md`. None of them is
documentation.

---

## Reproduce this

```bash
python tools/health_check.py --baseline f907a51
git diff --shortstat f907a51 HEAD
git diff --stat f907a51 HEAD -- tools/   # empty: no gate code touched
```
