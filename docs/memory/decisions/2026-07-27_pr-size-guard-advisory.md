# Decision — the PR-size guard reports over-cap as ADVISORY, and PR #76 may be split (founder, 2026-07-27)

**Status:** RATIFIED by the founder. Two things were asked as a pair and answered
"yes to both". Both touch gate enforcement, which is why they were escalated rather
than decided by the agent.

## The directives (verbatim)

The agent asked, at the end of six review rounds on PR #76:

> 1. **A second branch** — "This splits, the security fixes land, the deferrals in
>    R-087/R-088/R-096 ship."
> 2. **Whether `pr_size_check`'s over-cap path should exit 3 (advisory) rather than 1
>    (tool-failure)** — "Exit 3 is what its own semantics call for … but it changes a
>    red row to an advisory one, so it's a gate call."

Founder: **"yes to both"**.

## What each authorises

### (1) The size-guard exit code — a correctness fix to a mis-signal

`tools/pr_size_check.py` is an early-warning instrument, not the size gate. The
**reviewer** is the real gate: it makes the actual size call on the diff CI
constructs, against its own `--max-diff-bytes`. The guard's job is only to warn
before that happens.

Its over-cap path returned **1**. `tools/validate`'s `run_advisory` classifies exit
1 as *"the tool itself broke (rc=1)"* and turns the whole run **RED**; it reserves
exit **3** for *"findings, advisory"*. So an accurate, deliberately-conservative size
finding was being reported as a crashed tool — and that red stopped the
`adversarial-review` workflow's own `validate` step before the reviewer could run to
make the real call. The guard built to prevent false confidence was producing a
false *failure*.

Changing which exit code that path returns changes whether `validate` goes red, so
it is a gate-enforcement change and founder-crucial. Ratified: the over-cap path now
exits **3** — surfaced loudly, ADVISORY in a normal run, still **FAIL under
`--strict`** so a final gate blocks. A genuine internal error still exits non-3 and
is still reported as a tool failure; that distinction is the point. **Nothing is
loosened:** the founder-ratified 781 KB reviewer cap is unchanged, and the reviewer's
own hard limit is untouched. The guard now tells the truth (a finding) instead of a
falsehood (a crash), and lets the real gate do its job.

### (2) Splitting PR #76 — standing permission

Six rounds fixed real defects (secret custody R-081/R-082/R-083, the auth-boundary
disclosure R-085, the Sentinel wiring R-086, the size guard R-089, the import parser
R-090, the duplicate record IDs R-091, the surface-scan and log-redaction holes
R-096). Master advanced under the branch twice (#87, #88), each time forcing a merge
and consuming reviewer-cap margin. The deferred items (R-087 cardinality + `/tonight`
product defects, R-088 interpreter fallback, and the route-matcher nit) need a fresh
reviewable PR regardless of #76's outcome.

The founder grants standing permission to create a second branch and move work into
it — so the agent does not re-ask each round. Whether #76 *also* sheds content
depends on the reviewer's real size verdict once (1) lets it run; if the reviewer
runs and approves, #76 merges as-is and the second branch carries only the deferred
and product work.

## Implications and tradeoffs

- **Cost of (1):** a genuinely-too-large PR now passes `validate` as ADVISORY and is
  caught by the reviewer's hard fail instead of by `validate` first. That is correct
  — the reviewer is the authority on its own diff — but it means `validate` green no
  longer implies "the review will run". The guard's WARNING/OVER-CAP text still says
  so loudly, and `--strict` still blocks.
- **Cost of (2):** two PRs to carry one body of work, and the second inherits the
  deferred list. The benefit is that each is reviewable, and the "racing a moving
  base at 3 KB of margin" failure mode ends.

**Codified by:** `tools/pr_size_check.py` (the over-cap path now returns 3, with the
reasoning inline) + `tests/test_pr_size_check.py::test_over_cap_is_an_ADVISORY_finding_not_a_tool_crash`
and `::test_a_genuine_internal_failure_is_NOT_reported_as_a_finding` (both pin the
exit-code distinction); the split is an operational authorisation carried by this
record and enacted on the follow-up branch.
