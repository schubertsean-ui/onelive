# Decision — raise the adversarial-review diff cap from 800 KB to 900 KB (founder, 2026-07-27)

**Status:** RATIFIED by the founder. A gate-threshold change (the reviewer accepts a
larger diff = easier to pass), which is founder-crucial and never an agent decision. It
amends, additively, the 800 KB cap ratified on 2026-07-16/17
(`docs/memory/decisions/2026-07-16_review-diff-cap-800k.md`,
`2026-07-17_diff-cap-approval.md`).

## The directive (verbatim)

Offered three options after the split was proven non-viable — raise the cap, keep
pruning/moving files, or a one-time merge exception. Founder: **"Raise cap to 900 KB"**.

## Why the agent could not resolve this without the founder

PR #76 — the deep audit + canon rewrite + six rounds of security hardening — reached
**~802 KB**, past the 800 KB reviewer cap, so `adversarial-review` HARD-FAILS before
reviewing. The agent exhausted every in-authority path first, and each was proven, not
asserted:

- **The split** (founder-authorized 2026-07-27) is not mechanically viable for this PR.
  A history-split re-introduces master's own #87/#88 content into the diff and, worse,
  the early half re-hits #88's duplicate-R-number collision whose fix (R-091,
  renumbering to R-092..R-095) lives only in the late commits — the branch's records
  describe the branch's own rounds, so it cannot be cut at a historical commit. A
  content-split fails because every new tool is wired into the `tools/validate` hub, and
  moving any test out would ship code without its test (a coding-standards violation).
- **Pruning does not converge.** The exit-code commit alone added ~8 KB; each round's
  mandatory records (RECORD rows, ledger rows, `[S3:]` citations) regrow the diff faster
  than non-substance can be cut, and master advanced twice mid-effort, each time forcing
  a merge that consumed margin. Pruning a historical audit to pointers still left ~2 KB
  over.

The reviewer's own hard-fail message lists "raise the limit deliberately" as one of
three legitimate responses. The content is all legitimate, reviewed-in-pieces work;
the cap, not the content, is what needs to move.

## What changed

`--max-diff-bytes 800000 → 900000` in `.github/workflows/adversarial-review.yml`. Because
`on: pull_request` runs the workflow from the PR head (the workflow is PR-owned; only the
reviewer *script* is fetched from base), this applies to #76's own next review.
`tools/pr_size_check.py::evaluator_cap_bytes()` greps the same line, so the early-warning
guard tracks the new cap automatically.

## Implications and tradeoffs

- **NOT a softer gate.** `--require` is unchanged: the reviewer still HARD-FAILS rather
  than truncating past the (now higher) cap, and every lens still runs. The window is
  bigger; the physics are identical.
- **Cost of yes:** the reviewer ingests up to ~100 KB more per run for every future PR
  (more tokens), and a genuinely-bloated PR has more room before the cap catches it.
- **Cost of no:** #76 — six rounds of real security and canon fixes — could never be
  reviewed or merged, and v1 stays blocked on a mechanical limit rather than on quality.
- **Reversible:** the cap can return to 800 KB once #76 merges and the follow-up PRs are
  small again. That is the R-097 trigger, so the raise is not silently permanent.

**Codified by:** `.github/workflows/adversarial-review.yml` (`--max-diff-bytes 900000`
and the additive ratification comment) + `docs/RECORD.md` R-097 (the
restore-or-ratify-permanent trigger).
