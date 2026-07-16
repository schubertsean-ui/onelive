# docs/hats — the dedicated-hat registry (founder-approved 2026-07-16)

Greppable summary: de Bono's six thinking hats as STANDING dedicated agents,
one file per hat. A dedicated hat is NOT a system prompt — per call, "an
agent that is only ever the Black hat" and "a model handed a Black-hat
prompt" are identical, because a model has no identity between calls.
Dedication is real only through four durable assets: **its own prompt**
(this file's Role section), **its own memory** (owned artifacts that make it
better at its hat over time), **its own model binding** (family constraints
via `docs/MODEL_ROUTING.md`, never a hardcoded vendor), and **its own
custody** (what it may and may not touch). Prompt alone = a costume.
Origin: the swarm-of-agents / Six Hats analysis conversation, founder
"Yes to all — build the hat registry with per-hat Kaizen measures"
(2026-07-16). Po battery run on the design: seed 20260716, word "scaffold",
harvest H1–H5 (ledgered under M6).

## The six

| Hat | Function | Today's organ | Model binding | Status |
|---|---|---|---|---|
| [White](white.md) | Facts before opinions | `session_reconcile.py`, eval harness, trust_gate | Deterministic scripts first; LLM only narrates | EXISTS (as scripts) |
| [Red](red.md) | Gut, values, go/no-go | The founder | Human, permanently | EXISTS (constitutional) |
| [Black](black.md) | Adversarial caution | Independent Evaluator + Friction attack | Non-Claude, hard invariant | EXISTS (most mature) |
| [Yellow](yellow.md) | Deliberate best case | — none (the gap this registry closes) | Non-generator family preferred | NEW |
| [Green](green.md) | Provocation, alternatives | Po battery (`tools/po_battery.py`) | Cheap tier (mechanical) | EXISTS (as tool) |
| [Blue](blue.md) | Process + conflict-preserving merge | Session loop + validate (process half); merge is NEW | Scripts for process; merge on a non-expert instance | HALF-EXISTS |

## Firing rules (inherited from po, extended)

Hats fire at **divergent and founder-crucial moments only** — Friction
pre-work before irreversible actions, sprint/architecture planning,
design-direction selection — and **never inside convergent gates**
(validate / trust_gate / evaluator verdicts stay purely convergent).
Never for trivial mechanical work: ritual is not insight, and cost
discipline applies to thinking tools too.

Two tiers (po harvest H3, cost discipline):

1. **Sequential mode (cheap, default):** one agent wears the hats in
   de Bono's original sequence — Blue frames, White facts, Green diverges,
   Yellow then Black argue, Blue merges — for ordinary decisions worth
   structuring but not worth a fleet.
2. **Dedicated-parallel mode (irreversible / founder-crucial):** each hat is
   a separate call on its bound family, run independently (see Independence
   below), devil's-advocate pass against any consensus, Blue merge last.
   This is the mandatory shape of the Friction pre-work (charter, Friction
   Agent bullet).

## The one-way valve (trust integration — non-negotiable)

No hat's output is ever **evidence**. Confidence states derive from source
corroboration only; a hat may flag doubt (routing a thing to human review —
fail-closed) but expertise, enthusiasm, or consensus never raises
confidence, never enters candidate data, memory, or user-facing copy except
by surviving the normal gates as an ordinary, evidenced change. Black-hat
findings may only tighten. Making any hat's output count as evidence, or
using a hat to relax any gate, is a trust-invariant change — founder
escalation, never an agent decision.

## Independence (from the swarm-analysis review)

Hats — and review personas generally — run as **independent calls that do
not see each other's output**; their findings meet only at the Blue merge.
A lens that has read another lens's findings is conformed, not independent.
(Parallel execution gives this for free; sequential mode trades it away
knowingly, which is part of why it is the cheap tier.)

## Kaizen (per-hat, in the existing ledger — no new ledgers)

Each hat file declares three things: its **measure**, its **counter-measure**
(every measure ships with its Goodhart inverse — a hat rewarded per catch
will manufacture catches), and its **escape definition** (what it means for
this hat to have failed). Rows land in `docs/metrics/KAIZEN_LEDGER.md`
using the existing M-series — a hat is simply another catcher named in M2,
another gate-gap source in M4 — because cross-hat trends (a class escaping
Black but caught by White) are only visible in one table. Yellow's
validated-upside measure is M8 (`docs/KAIZEN.md`).

**Drain to mechanization (the telos):** a hat's Kaizen curve should bend
toward its own replacement. Repeatable catches become deterministic checks
(the White hat already completed this journey — it IS scripts); a class
caught by LLM judgment month after month is a gate-gap fix nobody wrote.
Accordingly every hat file carries a **retirement condition** (po harvest
H5): the observable state in which the hat's judgment work is fully
mechanized and the file is archived, not the vague hope of one.

## Memory rules (po harvest H1)

A hat's owned memory follows `docs/memory/` conventions (distill, update
don't duplicate, delete what's proven wrong, never secrets) — and it informs
the hat's **checklists, never its verdict on a specific target**. The Black
hat consults its attack-pattern list; it never consults "this author is
usually right." Every judgment is made fresh on the evidence in front of it.

## Custody of these files

Hat files define prompts for the friction/evaluation workflow, so changes
ride the independent evaluator like every PR (`adversarial-review.yml`,
path-filterless by design). Model bindings go through
`tools/model_router.py` stages, never hardcoded vendors (po harvest H2) —
with one exception stated in black.md: the Black hat's non-Claude constraint
is a hard invariant enforced by the router itself.
