# Why this lives inside the OneLive repo (staging, not its home)

**Status:** staged pending transport to `schubertsean-ui/universal-kernel`
(the founder created that repo 2026-07-26; owner Sean Schubert, PRIVATE).

This directory is the founder-ratified universal kernel (v1, ratified
2026-07-24, incl. the K-LOOP-5 amendment). It is a COMPLETE, self-contained
template that was built and verified in an agent session:
its own test suite AND its `tools/validate` both run green — proven in CI by
`tests/test_staged_template_selftests.py`, which executes both inside this
staged copy, so the claim is produced by the evidence bundle rather than
asserted beside it. No file count is quoted here: a number in prose drifts
the moment a file is added, and the git tree is the authority.

**Why it is here instead of in its own repo:** the agent session's GitHub
access is scoped to `schubertsean-ui/onelive`, and the mechanism for
attaching another repository failed repeatedly (an approval prompt that
never cleared — root-cause note below). The agent sandbox is ephemeral, so
leaving finished, verified work only in session memory would have destroyed
it. Staging inside a private repo the founder already owns follows this
project's own precedent: `ventures/promise_ledger/` lives here for gate
coverage until its extraction is a founder call.

**Nothing in OneLive imports or depends on this directory.** It is inert
template content: docs, portable tools, and one workflow file. OneLive's
pipeline and PRODUCT surfaces are untouched.

**Its GATES are not** — correcting an overstatement this note carried from r1.
The same pull request also hardened OneLive's live `.github/workflows/
adversarial-review.yml` (a three-job split closing a key-exfiltration path),
added `pytest.ini` collection scoping, and extended the governance lint. That
work is not staging: the evaluator found the hole in the very workflow this
template copies, so fixing it here and shipping it unfixed there was not an
option. What stays untouched is the product path — ingestion, extraction,
gate→candidate→promote, `/tonight`, auth.

## Transport (the remaining step, ~1 minute at a laptop)

```bash
cd templates/universal-kernel
git init && git add -A && git commit -m "Kernel v1"
git branch -M main
git remote add origin https://github.com/schubertsean-ui/universal-kernel.git
git push -u origin main
```

Then delete this directory from OneLive in a follow-up PR, leaving a
pointer in `docs/strategy/UNIVERSAL_DEV_OPERATING_MODEL_v1.md`.

## Root-cause note (OPERATING_RULES §1: a repeated error is a finding)

The repo-attach call returned `MCP error -32003: requires approval` five
times across the session, and the founder reported tapping the approval
repeatedly without it clearing — i.e. the approval round-trip is not
completing, on the harness side, not ours. Determination: NOT our defect,
NOT fixable from the session; the deliberate workaround is this staging
directory plus the manual transport above, with the accepted cost stated
(the kernel is versioned in the wrong repo until someone runs five commands).
Recorded so the repetition never normalizes into "just retry the prompt."
