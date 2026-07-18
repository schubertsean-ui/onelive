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
design-direction selection. The full hat swarm **never runs inside
convergent gates** — validate / trust_gate / evaluator verdicts stay purely
convergent; the Black hat's evaluator duty is not a swarm run, it IS the
existing convergent gate and keeps firing on every PR exactly as before.
Never for trivial mechanical work: ritual is not insight, and cost
discipline applies to thinking tools too.

Two tiers (po harvest H3, cost discipline):

1. **Sequential mode (cheap, default):** one agent wears the hats in
   de Bono's original sequence — Blue frames, White facts, Green diverges,
   Yellow then Black argue, Blue merges — for ordinary decisions worth
   structuring but not worth a fleet.
   **Custody boundary (fail-closed):** sequential mode never discharges the
   Black hat's custody. A Generator "wearing Black" on its own work is
   self-critique — useful, but it carries no adversarial authority and
   satisfies nothing: wherever the charter requires the Independent
   Evaluator or the Friction attack (every PR; every irreversible action),
   only the real non-Claude Black hat counts, whatever mode the other hats
   ran in.
2. **Dedicated-parallel mode (irreversible / founder-crucial):** each hat is
   a separate call on its bound family, run independently (see Independence
   below), devil's-advocate pass against any consensus, Blue merge last.
   This is the mandatory shape of the Friction pre-work (charter, Friction
   Agent bullet). Until `tools/decision_swarm.py` exists (TODOS), these runs
   are manual — so the decision record MUST preserve each lens's raw output,
   captured before any lens saw another's, alongside the merge; a merge
   without its raw inputs attached is invalid evidence of a run.

## Fidelity to de Bono — canonical vs. our adaptations (added 2026-07-17 at founder direction)

Founder demand (2026-07-17): the hats and po must run at world-class
fidelity, "not ad hoc or interpreted… or 'some of'." This section states,
without hedging, exactly what is faithful to de Bono's published method and
exactly where we deliberately DEPART — so no adaptation hides as canon.

**Believed faithful to the canon (checked to the best of the author's
knowledge against de Bono's *Six Thinking Hats* and *Lateral Thinking /
Serious Creativity*, NOT yet independently verified — the primary-source
re-check and cross-family red-team pass below are still pending; do not read
"faithful" here as "verified"):**
- All six hat mandates, each per de Bono: White = facts + named unknowns;
  Red = feeling with NO justification required; Black = logical-negative
  caution; Yellow = logical-positive benefit, as disciplined as Black;
  Green = creativity/provocation; Blue = process control + focus + summary.
- One hat at a time / separation of thinking types (sequential mode).
- Po: the full canonical operator set — escape, reversal, exaggeration,
  distortion, wishful, random entry — with NO sampling (`tools/po_battery.py`
  refuses to trim), and all five canonical MOVEMENT techniques (extract
  principle, focus on difference, moment-to-moment, positive aspects, special
  circumstances). Provocation is never judged, only moved from.

**Deliberate ADAPTATIONS (NOT pure de Bono — named here so they are never
mistaken for the canon):**
1. **"Dedicated-parallel mode" adapts, but is closer to de Bono's later
   work than first stated (corrected 2026-07-17 after researching his
   expanded corpus, per founder direction).** In *Six Thinking Hats*
   (1985) parallel thinking = every person wears the SAME hat at the SAME
   time (parallel across people, sequential across hats), to stop
   ego-driven human debate — and our SEQUENTIAL mode runs exactly that.
   But *Parallel Thinking* (1994) expanded the idea to "several parallel
   tracks (preferably more than two), all contributing in parallel" — so
   de Bono's own later framing is more flexible about simultaneous tracks
   than the strict 1985 rule. Our dedicated-parallel mode (each hat an
   INDEPENDENT agent, blind to the others until the Blue merge) is an
   AI-specific extension of that direction, motivated by the cited
   LLM-conformity research (AI's failure mode is conformity, not ego).
   It is NOT identical to either de Bono form and remains an adaptation —
   but a smaller one than "not de Bono at all," which overstated it.
2. **The "absurd" operator** (po P6) extends past de Bono's five into
   category error — a founder addition, labelled as such in
   `po_provocation.md`, not claimed as canonical.
3. **Red = the founder ONLY.** De Bono lets anyone wear Red; we forbid an
   agent from ever holding the Red slot, because a model can simulate a
   preference but cannot be accountable for one. A constraint, not a
   liberty — stricter than de Bono, deliberately.
4. **Movement uses "≥2 techniques per provocation," not all five.** This is
   faithful — de Bono's movement techniques are a TOOLKIT you draw value
   from, not a mandatory five-step checklist; ≥2 is a floor against lazy
   single-lens harvesting, not a "some of" shortcut.

**The corpus this is checked against is de Bono's FULL body of work, not
only the early books (founder direction 2026-07-17 — he expanded the ideas
across decades of later books, talks, seminars, and interviews).** Sources
that must inform the fidelity re-check, beyond *The Use of Lateral Thinking*
(1967) and *Six Thinking Hats* (1985): *Lateral Thinking* (1970),
*Po: Beyond Yes and No* (1972), *Serious Creativity* (1992), *Water Logic*
(1993, the rock-logic-vs-water-logic perception model that underpins po's
"movement, not judgement"), *Parallel Thinking* (1994), *Teach Yourself to
Think* (1995), *Six Value Medals* (2005), plus the de Bono Group's current
program materials and recorded talks/interviews.

**Concrete enrichment candidate surfaced by that wider corpus:** the Yellow
hat currently hunts generic "benefits." De Bono's *Six Value Medals* (2005)
is his OWN later, more rigorous tool for exactly this — value assessment
across six named lenses (the author's reading of the taxonomy: gold =
human/core values, silver = organisational, steel = quality, glass =
innovation, wood = ecological/relational, brass = perceptual/appearance —
this lens list is a CANDIDATE INTERPRETATION pending the same primary-source
review, not established de Bono structure for this project). Adopting that
taxonomy would make Yellow's output structured rather than ad-hoc. Queued as
a candidate upgrade (TODOS), to be adopted only through the normal gates —
not asserted here.

**This fidelity claim is not self-certified.** These docs are authored by the
Generator; the Generator asserting its own de Bono fidelity is the exact
self-review bias the trust harness exists to prevent. The claim rides the
adversarial-review gate like every change, and a primary-source fidelity
re-check (against the full corpus above) is queued for the cross-family red
team's first run (it is a `THREAT_MODEL`-adjacent design claim;
`RED_TEAM_CHARTER.md`). Until an independent lens has checked it against
de Bono's primary and expanded texts, treat this section as "faithful to the
best of the author's knowledge, pending adversarial verification," not as
proven.

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
declares no measure** — the harness does not grade the founder; Red's
Kaizen surface is the AGENTS' interrupt hygiene (see red.md). Rows land in `docs/metrics/KAIZEN_LEDGER.md`
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
