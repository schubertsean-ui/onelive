# Security red team — six-hats po, cross-family (founder-directed 2026-07-17)

Greppable summary: a standing security red team that attacks
`docs/security/THREAT_MODEL.md` using de Bono's six-hats + po provocation
structure, run on a DIFFERENT AI family than both the Generator (Claude) and
the standing evaluator (GPT-5.5). Founder direction (2026-07-17): after asking
whether an external reviewer should check for AI-inherent/architectural bias
(threat model §6), founder chose items 1/2/4 and: "Create a red team for 3 that
uses the deBono po - 6 hats model via a different AI." This is that red team —
the structured, cross-family AI complement to the deferred human security review.

## What it is, and the honest limit (stated first)

This red team is a THINKING TOOL producing FINDINGS, never evidence — the
one-way valve (`docs/hats/README.md`) is absolute here: no red-team output
raises confidence, enters candidate data, or relaxes a gate; findings may only
tighten, and each becomes an ordinary evidenced change through the normal gates
or a `docs/RECORD.md` entry with a trigger. It reuses the existing hat registry;
it does not invent a parallel governance track.

The honest ceiling (founder decided to build this ANYWAY, with eyes open): a
cross-family AI red team narrows AI-shared bias (threat model §6) but does not
escape the paradigm — it is still an LLM reasoning about an AI-built system. It
is a strong COMPLEMENT to, not a full SUBSTITUTE for, the one-time human
security review, which stays OPEN in the Record (R-020) with a go-live trigger.
Value bought: structured adversarial coverage, a third model family's blind
spots differing from Claude's and GPT-5.5's, and a repeatable cadence — for
roughly the price of a few model calls instead of a security-engineer
engagement.

## Composition (the six hats, mapped — reusing docs/hats/)

Same hats as the registry, pointed at the threat model. Dedicated-parallel mode
(the irreversible/founder-crucial tier): each hat is a separate call on its
bound family, run independently (never sees another hat's findings until the
Blue merge — the Independence rule), devil's-advocate pass on any consensus,
Blue merge last preserving conflict.

| Hat | In THIS red team | Model family constraint |
|---|---|---|
| **Blue** | Frames the run: names the target scope (a threat-model section, a specific boundary, a PR's design) BEFORE lenses run; merges last, preserving conflict, never averaging | cross-family; process steps may be a script |
| **White** | Facts only: what the code/config/tests ACTUALLY enforce today (not what docs claim). Reads the closed-attack log and the real workflow files | deterministic extraction preferred; cross-family LLM narrates |
| **Green (po)** | Provocation: `tools/po_battery.py` operators against each boundary — "po: the exam key is public", "po: the maintainer is the attacker", "po: two AIs share the exact wrong assumption". Provocations are stimuli, never claims | cheap tier, any non-Claude family |
| **Yellow** | Best-case steelman: where is the design genuinely STRONGER than it looks, so the team doesn't waste rounds on non-issues and doesn't cry wolf | non-generator family (M8 validated-upside) |
| **Black** | The attacker: tries to REOPEN each closed attack (threat model §5), find a new boundary crossing, or exploit the §6 residual. Hard invariant: non-Claude, AND for this red team specifically, a THIRD family — neither Claude nor the GPT-5.5 that already reviews every PR — so its blind spots are maximally different | **third family** — REQUIRED by this charter; router enforcement not yet built (see Custody: design-only today) |
| **Red** | The founder: go/no-go on whether findings warrant the human review, and on any finding touching money/legal/trust invariants | human, permanently |

**Why a THIRD family for Black (the point of the whole exercise):** the standing
evaluator is GPT-5.5. If the red team's attacker were also GPT-5.5, it would
share that reviewer's blind spots — defeating the purpose. Black here binds to a
family distinct from BOTH Claude and GPT (Gemini via `GEMINI_API_KEY` is the
chartered option; any non-Claude-non-GPT frontier family qualifies). This is the
cross-family diversity that makes the red team worth more than another GPT round.

## Cadence (when it fires — divergent/founder-crucial only, never convergent)

Never inside a convergent gate (validate/trust_gate/evaluator stay purely
convergent). The red team fires at:

1. **Pre-go-live (mandatory, once):** full six-hat pass over the whole threat
   model before the Clerk allowlist opens to non-founder traffic. Output feeds
   the R-020 human-review go/no-go.
2. **On any trust-invariant or gate-custody design change** (not every PR — the
   evaluator already covers those; the red team fires when the DESIGN of a
   boundary changes, e.g. a new secret surface, a new external service, an RLS
   policy change).
3. **On founder request**, any time.
4. **Quarterly drift check** once live: reality moves, the threat model must be
   re-attacked against what the system actually became.

## Custody & mechanics

- **Target:** `docs/security/THREAT_MODEL.md` (kept current — a stale model
  wastes the run). Every finding updates that file in the same change.
- **Model binding — NOT YET IMPLEMENTED, stated plainly (evaluator PR #33 r1):**
  Black's third-family constraint is a REQUIREMENT this charter sets, not a
  control that exists in code today. This doc is design; nothing here enforces
  it. Making it real is its own gate-custody change (evaluator-mandatory,
  TODOS): a `tools/model_router.py` family binding for the `red-team-black`
  stage (mirroring black.md's router-enforced non-Claude invariant, extended
  to exclude the GPT family too) PLUS the runner (`tools/decision_swarm.py`)
  that fails loud when no third-family key is configured. Until both ship, the
  red team cannot run in its intended form at all — there is no "degraded"
  auto-run substituting GPT-5.5 for the third family, because no runner exists
  to do so; the FIRST red-team run is blocked on that tooling landing, and any
  interim manual run MUST record in its own report that third-family diversity
  was not achieved (a manual run without it is not the chartered control).
- **Independence & raw-output preservation:** manual until
  `tools/decision_swarm.py` (TODOS) — so each hat's raw output is captured
  before any hat sees another's, and the decision record preserves all raw
  lenses alongside the Blue merge. A merge without its raw inputs is invalid
  evidence of a run (inherited from `docs/hats/README.md`).
- **Kaizen:** red-team catches are M2 rows (gate `red-team`, class = the attack
  family); a class the red team catches repeatedly is a gate-gap fix nobody
  wrote (M4). Counter-measure (Goodhart inverse): a red team rewarded per
  finding manufactures findings — so Yellow's steelman is mandatory in every
  run, and a finding that does not survive to a THREAT-MODEL update or a Record
  entry is not counted. Escape definition: a real security defect reaches
  go-live that a competent six-hat pass over the then-current threat model
  would have surfaced.

## Retirement condition (the telos — every hat drains to mechanization)

When a class of red-team finding recurs, it becomes a deterministic check
(`trust_gate.py` invariant, a workflow guard, a test) and leaves the red team's
judgment scope. The red team is fully retired when the threat model's every
boundary is mechanically enforced AND the pre-go-live human review has run once
with no findings the red team missed — at which point standing security rests on
the mechanical gates plus the quarterly drift check, and this file is archived.
