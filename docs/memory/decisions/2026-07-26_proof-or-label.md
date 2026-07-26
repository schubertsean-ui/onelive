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
added record lines : 93
  claim-shaped     : 69
  WITHOUT any proof token (would fire): 40
  fire rate over claim lines: 57 percent
```

r10 correction: the first version of this block used
`<count added lines matching…>` as a stand-in for the command — a placeholder
where the record demanded proof, inside the record codifying that demand. The
script is now committed and runnable. Counts move as the branch grows (79 /
55 / 36 at r8, 93 / 69 / 40 here); both runs show a majority of claim-shaped
lines firing, which is the finding. Every other number in this arc is
reproduced with its command and output in the timing/measurement evidence
file under `docs/session_arcs/evidence/`.

Rejected on that evidence. Judging whether prose is verified is a judgment
task wearing a regex costume, and a 65%-noise gate is one that gets
weakened — which is worse than no gate, because a weakened gate still reads
as protection. This is the second mechanism this session rejected by
measuring first (the other: extending `deferral_scan` over prose, 6 of 7
hits false).

The compensating control is the one that has actually caught every instance
of this class: the mandatory non-Claude adversarial review, whose v2 lens
panel treats a false claim as a blocker in its own right
(`CLASS:false-confidence-gate`, discipline rule 2 — "VERIFY that claimed
fixes and citations are real").

## Scope note

This is a TIGHTENING of a reporting standard, not a gate threshold change,
so it is not a gate-threshold relaxation and needs no separate ratification
beyond the directive above. It does not weaken or bypass any existing
check. Nothing about the trust invariants moves.
