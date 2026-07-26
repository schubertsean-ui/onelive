# Why this lives inside the OneLive repo (staging, not its home)

**Status:** staged pending transport to `schubertsean-ui/universal-kernel`
(the founder created that repo 2026-07-26; owner Sean Schubert, PRIVATE).

This directory is the founder-ratified universal kernel (v1, ratified
2026-07-24, incl. the K-LOOP-5 amendment). It is a COMPLETE, self-contained
template — 57 files — that was built and verified in an agent session:
its own test suite passes and `tools/validate` runs green on a fresh copy.

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
pipeline, gates, and product surfaces are untouched.

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
