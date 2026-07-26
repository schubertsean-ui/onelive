# docs/hats — the dedicated-hat registry

> **KERNEL DOC — project-agnostic, inherited verbatim.** The firing rules, the
> one-way valve, the independence convention, and the per-hat Kaizen contract are
> kernel and must not be weakened. Which concrete tool or model plays each hat is
> project data — it belongs in `OVERLAY.md`. Text in `[square brackets]` is a
> placeholder the overlay must bind.

Greppable summary: de Bono's six thinking hats as STANDING dedicated agents,
one file per hat. A dedicated hat is NOT a system prompt — per call, "an
agent that is only ever the Black hat" and "a model handed a Black-hat
prompt" are identical, because a model has no identity between calls.
Dedication is real only through four durable assets: **its own prompt**
(each file's Role section), **its own memory** (owned artifacts that make it
better at its hat over time), **its own model binding** (family constraints
via `docs/MODEL_ROUTING.md`, never a hardcoded vendor), and **its own
custody** (what it may and may not touch). Prompt alone = a costume.

## The six

| Hat | Function | Typical organ | Model binding | Status |
|---|---|---|---|---|
| [White](white.md) | Facts before opinions | `tools/session_reconcile.py`, [eval harness], [project trust gate] | Deterministic scripts first; LLM only narrates | usually EXISTS (as scripts) |
| [Red](red.md) | Gut, values, go/no-go | The founder | Human, permanently | EXISTS (constitutional) |
| [Black](black.md) | Adversarial caution | the Independent Evaluator + the Friction attack | Non-generator family, hard invariant | the most mature LLM hat |
| [Yellow](yellow.md) | Deliberate best case | — often the gap this registry closes | Non-generator family preferred | usually NEW |
| [Green](green.md) | Provocation, alternatives | The po battery (`tools/po_battery.py`) | Cheap tier (mechanical) | EXISTS (as tool) |
| [Blue](blue.md) | Process + conflict-preserving merge | Session loop + `tools/validate` (process half); merge is NEW | Scripts for process; merge on a non-lens instance | HALF-EXISTS |

## Firing rules (inherited from po, extended)

Hats fire at **divergent and founder-crucial moments only** — Friction
pre-work before irreversible actions, sprint/architecture planning,
design-direction selection. The full hat swarm **never runs inside
convergent gates** — `tools/validate` / [project trust gate] / Independent Evaluator verdicts stay purely
convergent; the Black hat's evaluator duty is not a swarm run, it IS the
existing convergent gate and keeps firing on every PR exactly as before.
Never for trivial mechanical work: ritual is not insight, and cost
discipline applies to thinking tools too.

Two tiers:

1. **Sequential mode (cheap, default):** one agent wears the hats in
   de Bono's original sequence — Blue frames, White facts, Green diverges,
   Yellow then Black argue, Blue merges — for ordinary decisions worth
   structuring but not worth a fleet.
   **Custody boundary (fail-closed):** sequential mode never discharges the
   Black hat's custody. A Generator "wearing Black" on its own work is
   self-critique — useful, but it carries no adversarial authority and
   satisfies nothing: wherever the charter requires the Independent
   Evaluator or the Friction attack (every PR; every irreversible action),
   only the real non-generator-family Black hat counts, whatever mode the other
   hats ran in.
2. **Dedicated-parallel mode (irreversible / founder-crucial):** each hat is
   a separate call on its bound family, run independently (see Independence
   below), devil's-advocate pass against any consensus, Blue merge last.
   This is the mandatory shape of the Friction pre-work. Until a decision-swarm
   tool exists, these runs are manual — so the decision record MUST preserve each
   lens's raw output, captured before any lens saw another's, alongside the
   merge; a merge without its raw inputs attached is invalid evidence of a run.

## The one-way valve (trust integration — non-negotiable)

No hat's output is ever **evidence**. Trust states derive from source
corroboration only; a hat may flag doubt (routing a thing to human review —
fail-closed) but expertise, enthusiasm, or consensus never raises
confidence, never enters candidate data, `docs/memory/`, or user-facing copy except
by surviving the normal gates as an ordinary, evidenced change. Black-hat
findings may only tighten. Making any hat's output count as evidence, or
using a hat to relax any gate, is a trust-invariant change — the founder
escalation, never an agent decision.

## Independence

Hats — and review personas generally — run as **independent calls that
never see another lens's FINDINGS**; their findings meet only at the Blue
merge. Shared INPUTS are fine and expected: every lens may receive the same
pre-registered Blue frame, the same White facts pass, and the same Green
option set — independence is about conclusions, not about starting
material. A lens that has read another lens's findings is conformed, not
independent.
(Parallel execution gives this for free; sequential mode trades it away
knowingly, which is part of why it is the cheap tier.)

## Kaizen (per-hat, in the existing ledger — no new ledgers)

Each hat file declares three things: its **measure**, its **counter-measure**
(every measure ships with its Goodhart inverse — a hat rewarded per catch
will manufacture catches), and its **escape definition** (what it means for
this hat to have failed). One constitutional exception, stated here so it
never reads as a skipped requirement: the **Red hat is the founder and
declares no measure** — the harness does not grade the owner; Red's
Kaizen surface is the AGENTS' interrupt hygiene (see red.md). Rows land in
`docs/metrics/KAIZEN_LEDGER.md` using the existing M-series — a hat is simply
another catcher named in M2, another gate-gap source in M4 — because cross-hat
trends (a class escaping Black but caught by White) are only visible in one
table. Yellow's validated-upside measure is M8 (`docs/KAIZEN.md`).

**Drain to mechanization (the telos):** a hat's Kaizen curve should bend
toward its own replacement. Repeatable catches become deterministic checks
(the White hat already completed this journey — it IS scripts); a class
caught by LLM judgment month after month is a gate-gap fix nobody wrote.
Accordingly every hat file carries a **retirement condition**: the observable
state in which the hat's judgment work is fully mechanized and the file is
archived, not the vague hope of one.

## Memory rules

A hat's owned memory follows `docs/memory/` conventions (distill, update
don't duplicate, delete what's proven wrong, never secrets) — and it informs
the hat's **checklists, never its verdict on a specific target**. The Black
hat consults its attack-pattern list; it never consults "this author is
usually right." Every judgment is made fresh on the evidence in front of it.

## Custody of these files

Hat files define prompts for the friction/evaluation workflow, so changes
ride the independent evaluator like every PR (the adversarial-review workflow,
path-filterless by design). Model bindings go through `docs/MODEL_ROUTING.md`
stages, never hardcoded vendors — with one exception stated in black.md: the
Black hat's non-generator-family constraint is a hard invariant enforced by the
router itself.
