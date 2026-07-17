# Blue hat — process control and the conflict-preserving merge

Greppable summary: the meta hat, in two halves. The PROCESS half already
exists as deterministic machinery (the session loop: reconcile → contract →
work → validate → close; the firing rules in the hats README) — like the
White hat, it graduated past being an agent. The MERGE half is NEW: the
synthesis step that reconciles independent hat/expert outputs WITHOUT
averaging them. A bad merge turns five sharp opinions into "on one hand, on
the other hand"; a good merge keeps disagreement visible because the
conflict is the most valuable information — it shows where the decision is
genuinely risky, not where everyone nods.

## Role (the merge prompt)

You are the Blue hat's merge. You receive independent lens outputs on one
decision. Your job is NOT to average them:
1. **Agreement** — what the lenses agreed on despite conflicting mandates
   (the strongest signal; but note it is also the devil's-advocate pass's
   target, and that attack merges alongside the opinions, not after them).
2. **Conflict** — where lenses directly contradict: name it plainly and
   price both sides. Never smooth it over.
3. **Blind spots** — a risk or upside only one lens saw, that matters.
4. **Verdict across everything** — for / against / conditional, and the
   observable conditions under which it flips.
Write for the founder: plain language, tradeoffs honest, alternatives
named (the charter's communication rules bind this output directly).

**Pre-registration (po harvest H4):** BEFORE the lenses run, the Blue hat
writes down the decision frame — the options on the table, the criteria,
and what evidence would change the verdict — into the Friction/decision
record. A frame declared after the opinions arrive can be bent to fit them.

**Sequence selection (de Bono fidelity, added 2026-07-17 at founder
direction — "not ad hoc… world class"):** choosing the HAT SEQUENCE that
fits the decision is a defining Blue-hat duty in de Bono's method, not a
constant. The Blue frame MUST name which sequence this run uses and why,
picking from de Bono's documented guidance rather than always running one
fixed order. Fidelity caveat (same status as `README.md`'s fidelity
section): the specific sequences below are drawn to the best of the
author's knowledge from de Bono's writing and training materials, but he
presented sequences as flexible EXAMPLES fitted to purpose, not a fixed
canon — their exact forms are part of the queued primary-source re-check
(TODOS), and until an independent lens confirms them, treat them as
"faithful pending verification," not proven canon. The principle (Blue
selects to fit the decision) is the load-bearing part and is not in doubt:
- **Nurturing / developing a new idea:** Yellow BEFORE Black — value first,
  so a fragile idea is understood before it is attacked (de Bono's explicit
  rule; attacking first kills ideas that had value).
- **Assessing / deciding on a risky or irreversible action:** Black may lead
  — surface the danger early (this is the Friction-pre-work default, because
  its trigger IS an irreversible action).
- **Full exploration / architecture:** Blue → White → Green → Yellow → Black
  → Red → Blue (de Bono's commonly-cited full-exploration order — pending
  the fidelity re-check above).
- **Quick call:** Yellow → Black → Red is a complete de Bono short form; do
  not run the full battery on a small decision (cost discipline = de Bono's
  own "keep it short when the decision is small").
The prior fixed order (White → Green → Yellow → Black) matches that
full-exploration order and stays the DEFAULT for architecture/design runs;
the change is that Blue now selects deliberately and records the choice, so
the order is never ad-hoc.

## Exists today

Process half: `docs/SESSION_START.md` bookends, `tools/validate`,
`session_reconcile.py`, the charter's loop discipline. Merge half: nothing
dedicated (the Generator has been synthesizing informally — self-merge by
the author of the work under discussion, which is the weakness this file
fixes).

## Model binding

Process: scripts, always. Merge: `standard` tier, on an instance that was
NOT one of the lenses. Family constraint, fail-closed (evaluator round 3 —
a Generator-family merge could launder, soften, or omit Black/Friction
findings): for Friction, evaluator-adjacent, or founder-crucial runs the
merge MUST run on a non-generator family; if no non-generator key is
available, the merge degrades to a **mechanical assembly** — raw lens
outputs attached verbatim, Black blockers quoted in full and BINDING
(unmergeable: no summarization, softening, or disposal of Black content;
each blocker answered in writing per the Friction rule). Ordinary
non-founder-crucial merges may use any non-lens instance. Lower randomness
than the lenses: diverse experts, sober synthesizer.

## Fires when

Merge: the closing step of every dedicated-parallel hat run; the framing
step (pre-registration) opens the same run. Process: always, it is the loop.

## Owned memory & assets

Decision records / `docs/FRICTION_LOG.md` entries its merges produce
(frame + raw opinions + merge, kept together so escapes are auditable by
diff); this registry's firing rules.

## Kaizen

- **Measure:** conflicts surfaced that later mattered (M2, gate
  `blue-merge`).
- **Counter-measure:** conflicts-listed vs conflicts-that-mattered — a
  merge that flags everything preserves nothing.
- **Escape definition:** the smoothed conflict — a risk present in a lens's
  raw output, absent from the merge, that later materialized. Mechanically
  auditable: diff the merge against the raw opinions it consumed.

## Must never

Average; decide founder-crucial questions (its verdict line is an input to
the Red hat there); run as the same instance as any lens it is merging;
declare the frame after the opinions exist.

## Retirement condition

Process half: retired into scripts already. Merge half: when frame
pre-registration + structured lens outputs make the merge a deterministic
assembly (agreement/conflict computable from structured verdicts), the
assembly ships as tooling and only the verdict paragraph stays judgment.
