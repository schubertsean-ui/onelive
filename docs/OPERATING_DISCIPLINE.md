# OPERATING DISCIPLINE — near-zero error at maximum efficiency (PROPOSAL, 2026-07-23)

Greppable summary: founder directive (2026-07-23) after a real cost overrun —
"limit and eliminate errors as close to zero AND operate maximally efficient
without sacrificing top-1% performance; prove it; cite peer-reviewed / real-world-
validated sources; build it into operating process and apply to agents." This doc
is the answer, encoded. It EXTENDS the existing discipline (docs/KAIZEN.md already
practices Deming's zero-ESCAPED-defects + `validate` = stop-the-line + AGENT_FEEDBACK
= hansei); it fills the two gaps the overrun exposed: **prevention** (build quality
in BEFORE the expensive review rounds) and **efficiency governance** (an explicit
error budget / cost dial). Status: PROPOSAL; the numeric knobs are FOUNDER-SET
(gate-threshold + spend = founder-crucial, CLAUDE.md escalations).

## The one validated answer (why "near-zero AND efficient" is not a contradiction)

Six independent, validated bodies of practice converge on the SAME answer, and one
of them proves the trade-off the question fears does not exist at the frontier:

1. **Stop depending on inspection — build quality in at the source.** Deming's
   Point 3: "Cease dependence on inspection to achieve quality … build quality into
   the product in the first place" (Deming, *Out of the Crisis*, MIT CAES, 1986).
   Crosby's *Quality Is Free* (McGraw-Hill, 1979): a quality system must focus on
   PREVENTION, not appraisal/detection; the cost of nonconformance dwarfs the cost
   of doing it right first. The **1-10-100 rule** of quality cost: a defect prevented
   at the source ≈ $1, caught internally ≈ $10, escaped to the customer ≈ $100.
   > *Our overrun in one line:* PR #54 took 18 review rounds — that is paying the
   > $10 (internal appraisal) eighteen times because we skipped the $1 (prevention).

2. **Source inspection + poka-yoke (mistake-proofing).** Shingo, *Zero Quality
   Control: Source Inspection and the Poka-Yoke System* (Productivity Press, 1986):
   source inspection catches ERRORS before they become DEFECTS; poka-yoke devices
   make the defect impossible or stop the line the instant one forms. Shingo's 112
   shop-floor examples mostly cost < $100 — mistake-proofing is cheap. This is
   exactly OneLive's "physics not policy / mechanical not remembered" rule.

3. **Design-time correctness for hard problems.** Newcombe, Rath, Zhang, Munteanu,
   Brooker, Deardeuff, "How Amazon Web Services Uses Formal Methods," *Communications
   of the ACM* 58(4):66–73, 2015 (DOI 10.1145/2699417): AWS engineers use TLA+
   specification + model checking to find subtle DESIGN defects before code reaches
   production. The lesson isn't "use TLA+ for everything" — it's **converge the
   design against an adversary BEFORE building**, which is the cheapest possible
   place to be wrong.

4. **Jidoka — stop the line (already live here).** Ohno, *Toyota Production System:
   Beyond Large-Scale Production* (Productivity Press, 1988): a defect halts the
   line immediately (andon) so it can never propagate. OneLive's `tools/validate` /
   trust_gate ARE this — keep them absolute.

5. **Govern the reliability↔velocity trade with an error budget.** Beyer, Jones,
   Petoff, Murphy (eds.), *Site Reliability Engineering* (O'Reilly/Google, 2016):
   error budget = 1 − SLO; a control loop spends it — while within budget, ship
   fast; when the budget is exhausted, feature work HALTS and effort shifts to
   reliability/prevention. This is the validated mechanism for "maximum efficiency
   WITHOUT sacrificing reliability": it prevents both under- and over-investing in
   quality, and it is the founder's spend-ceiling as a first-class control.

6. **Mindful organizing (how orgs sustain near-zero catastrophic error).** Weick &
   Sutcliffe, *Managing the Unexpected* (Jossey-Bass/Wiley; 2nd ed. 2007, 3rd ed.
   2015): five HRO principles — preoccupation with failure, reluctance to simplify,
   sensitivity to operations, commitment to resilience, deference to expertise (the
   first three anticipate, the last two contain). Validated in nuclear carriers, air
   traffic control, aviation. "Reluctance to simplify" is the direct antidote to the
   r16→r17 lesson (I shipped the simple-but-wrong audit-record design).

7. **The proof it is not a trade-off.** Forsgren, Humble, Kim, *Accelerate: The
   Science of Lean Software and DevOps* (IT Revolution, 2018) — four years of DORA
   survey research, rigorous statistics: **speed and stability are POSITIVELY
   correlated, not traded.** Elite performers deploy more often AND fail less; they
   are fast BECAUSE they are reliable (small batches, automation, fast feedback).
   The four measures: lead time, deployment frequency, change-fail rate, MTTR.

**Through-line:** near-zero error at max efficiency = prevent at the source (1,2,3)
+ stop the line on the rare defect that forms (4) + govern the trade with an
explicit budget (5) + a mindful stance at the sharp moments (6) — and (7) done this
way, quality and speed rise TOGETHER. The overrun happened because we were strong
on (4) and weak on (1)/(5). This doc closes that.

## The operating rules (tiered by risk — over-applying rigor is its own waste)

DORA/Lean warn against ceremony that doesn't earn its keep, so rigor is TIERED:

- **Trust-critical change** (auth, pipeline, SQL/RLS, data-trust, prompt/model,
  gate custody, audit-record invariants): **prevention-first is mandatory.** Before
  the PR opens, attach a **design-time correctness note**: (a) state the INVARIANT
  the change must hold, in one sentence, up front; (b) a self-red-team of the design
  against the world-class bar (the failure modes an adversary would find) — the
  thing PR #54 discovered over 18 rounds instead of stating in round 0. Sources 1,3.
- **Standard change:** the existing gates (lint, trust_gate, tests-in-PR, evaluator)
  suffice — no extra ceremony.
- **Trivial/mechanical change:** light. Do not spec a typo fix (source 7: ceremony
  without payoff lowers, not raises, performance).

- **Poka-yoke every repeat class.** Reaffirms the existing Kaizen M2/M4 rule: a
  defect class caught twice becomes a MECHANICAL gate, never a reminder (source 2).
  A poka-yoke that MIS-fires — e.g. the arming binding forcing a paid smoke-run for a
  file the pipeline never executes — is itself a defect to fix (source 2: the device
  must detect the real error, nothing else), and its fix is the first efficiency win.

- **Error budget = the efficiency dial (FOUNDER-SET numbers).** SLIs, measured on
  the Kaizen ledger, that define "top-1% operating performance":
  - *Escaped defects* = **0, absolute** (already M3 / Deming zero-escaped). Not a
    budget — a hard floor.
  - *Convergence* = evaluator rounds-to-green per trust-critical PR (M1). Budget:
    **[FOUNDER-SET, e.g. ≤ N rounds]**; exceeding it triggers a prevention review of
    WHY it didn't converge in design.
  - *Verification cost per PR* = evaluator calls + CI minutes + **real API spend on
    smoke/verification** (extends M5 to count dollars). Budget: **[FOUNDER-SET spend
    ceiling]**; the control loop (source 5): within budget → proceed; budget spent →
    STOP feature work, invest in prevention/mistake-proofing until back in budget.
  - Each SLI budget is itself pre-registered as an M9 prediction (we predict the
    cost, measure the actual) so the dial is honest, not asserted.

- **Mindful stance at divergent / high-consequence moments** (source 6): map the
  five HRO principles onto the existing hats (docs/hats/) — preoccupation with
  failure = the evaluator/friction attack; reluctance to simplify = do NOT ship the
  simple-but-wrong design (r16→r17); deference to expertise = FRONT-LOAD the
  independent evaluator into DESIGN for trust-critical work, not only into review.

- **Measure that we're not trading quality for speed** (source 7): the ledger
  already carries M1 (a lead-time/convergence proxy) and M3 (a change-fail proxy);
  read them together — if convergence cost falls while escapes stay 0, we are moving
  toward the elite quadrant, not away from it.

## Application to agents (docs/hats/, the agent org in CLAUDE.md)

- **Generator (this Claude session):** for trust-critical work, produce the
  design-time correctness note (invariant + self-red-team) BEFORE opening the PR;
  batch changes to avoid per-round re-verification; never dispatch a paid
  verification for a change that provably does not touch the runtime.
- **Independent Evaluator (non-Claude):** unchanged as the review gate, and ALSO
  invited into design for trust-critical changes (deference to expertise, source 6)
  — the cheapest round is the one before code exists.
- **Friction / hats:** the Black-hat attack becomes a DESIGN-time step, not only a
  pre-irreversible-action step, for trust-critical changes.
- **Librarian / session close:** records the M1/M5(+spend)/M9 numbers so the error
  budget is visible in the founder digest.

## What this does NOT change (and the honest trade-offs)

- Quality gates never relax (charter). Prevention is ADDED before the gates, never
  substituted for them. Source 7's point is that this raises speed too — but only
  if rigor is tiered; mis-applied to trivial work it is pure overhead (the reason
  the tiering above is explicit).
- The error-budget NUMBERS (rounds ceiling, spend ceiling, SLO targets) are
  gate-threshold + spend decisions = **founder-crucial**; this doc proposes the
  STRUCTURE and leaves the knobs to the founder (CLAUDE.md escalations).
- Prevention has an up-front cost on any single change; the payoff is on the
  aggregate (fewer $10/$100 rounds). It is a bet that the 1-10-100 economics hold —
  which the sources and our own 18-round overrun both attest.

## Sources (peer-reviewed OR real-world-validated; no encyclopedic/unvetted refs)

- Deming, W.E. *Out of the Crisis.* MIT Center for Advanced Educational Services,
  1986. (Real-world validated: post-war Japanese industrial quality.)
- Crosby, P.B. *Quality Is Free.* McGraw-Hill, 1979. (Cost-of-quality / prevention;
  industry-validated. 1-10-100 cost-of-quality rule.)
- Shingo, S. *Zero Quality Control: Source Inspection and the Poka-Yoke System.*
  Productivity Press, 1986. (Toyota-validated mistake-proofing.)
- Newcombe, C., Rath, T., Zhang, F., Munteanu, B., Brooker, M., Deardeuff, M. "How
  Amazon Web Services Uses Formal Methods." *Communications of the ACM* 58(4):66–73,
  2015. DOI 10.1145/2699417. (Peer-reviewed; AWS-validated.)
- Ohno, T. *Toyota Production System: Beyond Large-Scale Production.* Productivity
  Press, 1988. (Jidoka/JIT; Toyota-validated.)
- Beyer, B., Jones, C., Petoff, J., Murphy, N.R. (eds.) *Site Reliability
  Engineering: How Google Runs Production Systems.* O'Reilly, 2016. (Google-validated;
  error budgets.)
- Weick, K.E., Sutcliffe, K.M. *Managing the Unexpected.* Jossey-Bass/Wiley, 2nd ed.
  2007 / 3rd ed. 2015. (Peer-reviewed organizational science; HRO principles.)
- Forsgren, N., Humble, J., Kim, G. *Accelerate: The Science of Lean Software and
  DevOps.* IT Revolution, 2018. (Rigorous multi-year DORA survey research; the
  speed-and-stability-correlate finding.)
