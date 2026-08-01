# Adversarial Review v2 — the panel reviewer (founder-directed 2026-07-25)

Greppable summary: the Independent Evaluator upgraded from a single-lens
single-seat reviewer to a measured LENS PANEL, to convert multi-round
serial discovery into a one-pass exhaustive review. Canon here; code in
`tools/adversarial_review.py` (`--panel --po-seed <sha>`); scorecard in
`tools/reviewer_scorecard.py`. Founder ratifications (verbatim: the
Contract #26 decision record): the structured escape hatch, the M9
scorecard, the Gemini second seat (key founder-minted), and the per-seat
forced lenses + rotating po.

## The panel
Per SEAT, two forced lenses (a method lens + a po-seeded lens):
- **OpenAI seat:** attacker-smuggle (find the intentional backdoor) +
  absence-only (report only what is MISSING — where the clock/identity
  holes lived).
- **Gemini seat** (when `GEMINI_API_KEY` exists; else an EXPLICIT empty
  seat, printed): dataflow-taint (caller value → sink without validation)
  + spec-vs-contract (claim vs mechanism).
Decorrelation within a family comes from METHOD-forcing (dictating the
search procedure), not personality — the N-version lesson (Knight &
Leveson) that different methods decorrelate better than different
personnel. The po lens adds a de Bono provocation battery seeded from the
PR head SHA (rotating per run, printed for audit): stimuli, never facts —
hypothesize → verify at file:line → discard unverified movement
explicitly. A po lens can only ADD candidate findings, never argue APPROVE.

## Verdict physics (a strict tightening)
ANY lens REQUEST-CHANGES = panel red. Any unparseable lens output = hard
failure (never a quiet skip). Convergent gate stays convergent: divergence
enters through the lenses, convergence comes out through the verdict.

## The escape hatch, structured (founder-ratified)
A trust-invariant violation, gate-custody weakening, or auth/custody
fail-open MUST block in ANY round — obligation, not discretion. Any OTHER
class first raised after round 1 must also state, in one sentence, why it
was not findable in round 1 (new code / new evidence / the reviewer's own
miss — the scorecard counts the last). A real quality gap outside the
contract's scope and not invariant-class goes to RECOMMEND-RECORD (a
RECORD row with an objective trigger), not to blockers.

## Measuring the reviewer (M9)
`tools/reviewer_scorecard.py` derives per reviewed-PR arc, from the ledger:
round-1 recall (rising = improving), sibling-misses (a class recurring in a
later round — falling to 0), novelty decay (churn signal). Escapes stay
kaizen_trends' hard gate (zero, absolute). Lens overlap (lenses returning
near-identical findings) drives pruning — the lens portfolio is managed
empirically, like the carousel bandit manages creative factors.

## Custody unchanged
CI runs the BASE-owned trusted copy (a PR never runs its own reviewer);
model/env fail-closed rules and write/grade separation (non-Claude only)
hold on BOTH seats. Adding a non-gating experimental seat (e.g. Bittensor)
is a founder decision — held, per the data-egress posture for a required
gate.
