# Decision — one red-check merge for PR #72 (founder-ratified 2026-07-26)

**Founder directive, verbatim:** "Approve one red-check merge."

Asked as a consolidated choice between (a) temporarily removing
`GEMINI_API_KEY` so the panel runs single-family and nothing merges on
red, (b) authorizing one merge with `adversarial-review` red, and (c)
parking until morning. The founder chose (b).

## What was deadlocked, and why no code could break it

CI runs the reviewer from the BASE branch, so a PR never runs the judge
that judges it. `master`'s copy calls `gemini-2.5-pro`, which the
project's Gemini tier no longer serves:

```
adversarial_review: HARD FAIL — Gemini API HTTP 404:
  "This model models/gemini-2.5-pro is no longer available to new users."
```

The fix — a callable model, plus the preflight that would have caught
this in one second instead of three minutes — lives inside PR #72. Every
route to green passes through a value only a merge can change. This is
the same bootstrap shape `.github/workflows/adversarial-review.yml`
already documents for the reviewer script itself ("merged with this
check red, once; afterwards the gate is self-consistent"), now recurring
for the second seat's model.

The condition was created by PR #71, which set `gemini-2.5-pro` as the
default while the panel was still inactive, so nothing exercised it
until the seat first ran.

## Scope of this exception — narrow, and stated so it cannot be cited loosely

RATIFIED: exactly one merge of PR #72 with `adversarial-review` red,
where the red is the Gemini seat's inability to call a retired model.

NOT ratified, and unchanged by this record:
- Merging on red for any other reason, on any other PR. The standing
  rule stays evaluator APPROVE + every required check green.
- Any relaxation of verdict physics. ANY-lens-red is still red; an
  unreachable seat still fails the gate rather than narrowing the panel.
- Any weakening of custody. The self-weakenable-review-model fix (r9)
  ships IN this merge: the PR-owned workflow supplies neither seat's
  model, and an absence invariant asserts it.

## What the OpenAI seat actually said

The first seat is unaffected by the Gemini outage and reviewed the full
diff across nine rounds. Its final objection — that bounding the
subject-controlled model input was not enough and it had to be REMOVED —
was adopted in r9 before this merge. So the diff carries a completed
independent review; what is red is a credential/tier fact about the
second seat, not an unresolved finding.

## Why the alternative was declined

Option (a) would have avoided merging on red entirely, at the cost of
one PR reviewed by one model family. The founder preferred keeping the
key in place. Recorded because the road not taken is part of the
precedent: a future reader should know a no-red-merge path existed.

## What must be true immediately after

1. `master` carries a callable second-seat model and the preflight, so
   this class cannot recur silently — the preflight now fails in about a
   second with the callable list printed, instead of three minutes into
   a review.
2. The NEXT PR is the proof: its Gemini seat must complete a review. If
   it does not, that is a new finding, not a continuation of this
   exception.
3. R-052 stays OPEN — `gemini-flash-latest` is a floating alias, and the
   first preflight run that prints the advertised list yields a concrete
   id to replace it.
