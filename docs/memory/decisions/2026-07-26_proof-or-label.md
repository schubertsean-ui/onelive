# Decision — proof or label, never an unverified claim as fact (founder-ratified 2026-07-26)

**Founder directive, verbatim:** "Never make a claim or statement that has
not been independently verified and delivered with actual proof. This means
you can never make assumptions."

Follow-up in the same exchange, verbatim: "codify this."

## What it changes

`CLAUDE.md` → "Communicating with the founder" gains rule 6. Every factual
statement to the founder is now exactly one of two visible things:

- **VERIFIED** — ships with proof the founder can re-run without me: the
  command and its output, a job/run id and URL, a commit SHA, a file:line.
  A NUMBER never appears without the command that produced it.
- **UNVERIFIED** — labelled in the same sentence, with what verification
  would take.

Estimates, projections and plans remain allowed. What is forbidden is
stating one in the grammar of a fact. Where the answer is unknown and the
check is unavailable, the answer is "unknown" — an assumption is never
load-bearing.

## Why now — the four instances that produced it

All from the PR #73 arc, all mine, all cheap to have checked:

1. **"8 minutes → 90 seconds per round."** A plausible decomposition
   delivered as a measurement. Never measured; retracted.
2. **"The second seat's FIRST working run."** An ordinal asserted from
   evidence about one run. Going to prove it DISPROVED it — job
   89754035048 completed a Gemini review ~7 minutes earlier.
3. **"§2 (approval key, already covered)."** I verified that a boundary
   EXISTED and recorded that as verifying its CONTENT. It was missing three
   of its parts.
4. **Five review rounds cited (#73 r2–r5) with no ledger rows behind them.**
   The citations named rounds the repo had no record of.

The common shape is not haste. In each case the check was one command or
one API call away, and I substituted a plausible answer for a measurable
one. Hence the rule's sharpest clause: **the cheapness of the check is the
reason to run it, never the reason to skip it.**

## Mechanism, because a rule alone is `rule-stronger-than-mechanism`

The class `unverified-claim-as-fact` is indexed in
`docs/memory/RED_CLASSES.md` with claim-grammar trigger tokens. Since
`tools/construction_gate.py` matches red classes against diff CONTENT (not
only paths), any change carrying that language is BLOCKED until an
`[S3:unverified-claim-as-fact]` citation exists.

STRENGTH, STATED EXACTLY (r9 — the first draft of this record overstated it,
which was itself an instance of the class): the gate enforces that the
citation is PRESENT. It cannot evaluate whether the proof behind each claim
is real; that judgement stays with the adversarial review. This is a forcing
function that makes the claim-audit unskippable, not an automated
proof-checker.

## The alternative that was measured and rejected

A blocking scanner over agent-authored prose (STATE.md, the changelog, the
ledger, RED_CLASSES, RECORD) requiring a proof token near every
claim-shaped line. Measured on this PR's own added record lines before
building it:

```
$ python docs/session_arcs/evidence/scripts/probe_claim_scan.py
added record lines : 112
  claim-shaped     : 85
  WITHOUT any proof token (would fire): 44
  fire rate over claim lines: 51%
```

r13 (evaluator, class `unverified-claim-as-fact`): the previous version of
this block printed `57 percent`. The script emits `%`, so what was labelled
VERBATIM OUTPUT had been hand-edited — I changed the character to dodge a
shell-quoting problem while writing the file. Editing text under a
"verbatim" label is fabricating evidence, however small the edit, and it is
the exact failure this artifact exists to prevent.

SELF-REFERENTIAL, stated so the number is not read as stable: this probe
counts claim-shaped lines in THIS BRANCH'S diff, and the evidence file is
part of that diff — so writing the count changes the count. The output above
is from commit 19d014f. Re-running it later gives a different number BY
CONSTRUCTION, not because either run was wrong. The finding is what is
stable: a majority of claim-shaped lines fire, so the scanner stays
rejected. Run the script for the current figure rather than trusting this
paste to still match.

r10 correction: the first version of this block used
`<count added lines matching…>` as a stand-in for the command — a placeholder
where the record demanded proof, inside the record codifying that demand. The
script is now committed and runnable, and the block above is its real output.
r12: an earlier `79 / 55 / 36` run was also cited, but its output was never
preserved — an unpreserved run is not evidence under this record's own rule,
so that pair is withdrawn. Counts move as the branch grows; the finding is
that a majority of claim-shaped lines fire. Every other number in this arc is
reproduced with its command and output in the timing/measurement evidence
file under `docs/session_arcs/evidence/`.

Rejected on that evidence. Judging whether prose is verified is a judgment
task wearing a regex costume, and a gate that fires on a MAJORITY of
claim-shaped lines (see the probe output above — the exact rate moves because
the probe measures the diff that contains it) is one that gets weakened — which is worse than no gate, because a weakened gate still reads
as protection. This is the second mechanism this session rejected by
measuring first (the other: extending `deferral_scan` over prose, 6 of 7
hits false).

The compensating control is the mandatory non-Claude adversarial review, whose
v2 lens panel treats a false claim as a blocker in its own right
(`CLASS:false-confidence-gate`, discipline rule 2 — "VERIFY that claimed
fixes and citations are real").

CORRECTED #73 r29. This sentence originally read "the one that has actually
caught every instance of this class". That universal is FALSE, and this
document's own opening disproves it: the instance that produced this rule was
caught by the FOUNDER, not by the review. Several later instances were
self-caught before review reached them, and at least one — the r21
satisfiability overclaim — was caught by running a command rather than by any
reviewer. The review catches many instances and is the strongest net available;
it does not catch all of them, and no measurement here supports "every".

A decision record codifying "proof or label" cannot itself ship an unproven
universal about the control that enforces it. That it did, for three days,
is the sharpest available illustration of why the rule exists — the claim was
cheap to check and I did not check it.

## Scope note

This is a TIGHTENING of a reporting standard, not a gate threshold change,
so it is not a gate-threshold relaxation and needs no separate ratification
beyond the directive above. It does not weaken or bypass any existing
check. Nothing about the trust invariants moves.
