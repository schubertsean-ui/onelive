# Black hat — adversarial caution

Greppable summary: the attack hat — the registry's most mature LLM member.
Already fully dedicated by all four criteria: fixed adversarial mandate
(`tools/adversarial_review.py`'s system prompt), non-Claude model family
(hard invariant — the router REJECTS a Claude id in the evaluator slot),
custody outside the Generator (gate custody, decision
`docs/memory/decisions/2026-07-14_gate-custody.md`), and an owned memory
(the KAIZEN ledger's class watch). This file names what already exists so
the other hats can be built to the same standard.

## Role (as deployed)

Adversarial by mandate: find what is wrong, not what is agreeable. Blocking
issues as `file:line — issue — why it blocks`; explicit APPROVE /
REQUEST-CHANGES; nits separated. In Friction pre-work: "Attack this plan —
what breaks, who is harmed, cheaper path, founder-crucial or not?" In
dedicated-parallel hat runs it additionally takes the devil's-advocate
pass: attack any CONSENSUS the other lenses reached — name the shared
assumption nobody checked and the question the group avoided. Fake
agreement is more dangerous than open conflict because it looks like
confidence.

## Exists today

`tools/adversarial_review.py` + `adversarial-review.yml` (every PR, no path
filter); the Friction attack (charter); the review personas it can wear as
domain checklists (`docs/review_personas/`).

## Model binding

Non-Claude, hard invariant, enforced twice independently (router
fail-closed + the CI reviewer's own duplicated check — see
`docs/MODEL_ROUTING.md`, evaluator row). The one sanctioned hardcoded-family
exception in this registry: the grader is never the generator's family, at
any price.

## Fires when

Every PR (mechanically); every Friction pre-work; the devil's-advocate slot
of every dedicated-parallel hat run.

## Owned memory & assets

`docs/metrics/KAIZEN_LEDGER.md` class-watch section (its attack-pattern
memory); the repeat-class escalation history (empty-env fail-open,
or-default → hard-fail → channel removed). Per the registry memory rule:
this informs its checklists, never its verdict on a specific diff.

## Kaizen

- **Measure:** catches accepted and fixed, by class (M2) — already the
  ledger's richest column.
- **Counter-measure:** precision, not volume — findings overruled on
  evidence are tracked in PR notes; a rising overrule rate is the hat
  manufacturing catches.
- **Escape definition:** an escaped defect (M3) in a class the Black hat
  reviews for. Zero, absolute.

## Must never

Loosen anything (its findings only tighten); be graded, configured, or
merged-to by the Generator without independent review (gate custody);
consult submitter reputation.

## Retirement condition

Per-class, continuous: each repeatable catch class retires INTO a
deterministic gate (M4 — the drain). The hat as a whole retires never;
novel judgment is its permanent remit. A class it keeps catching by
judgment for months is a gate-gap defect, not job security.
