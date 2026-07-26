# universal-kernel

A project-agnostic development and operating model for building with AI
agents: the invariants, loops, gates, roles, and tooling that make agent
output trustworthy — packaged so any new project inherits them on day one
instead of rediscovering them through its own defects.

**Kernel v1 — founder-ratified 2026-07-24** (including the K-LOOP-5
amendment on context-specific counter-measures). Extracted from a production
build's harness after roughly sixty adversarially-reviewed pull requests.
Every rule here was paid for by a defect the review caught; the origin
project's Kaizen ledger is the receipt.

## The architecture: kernel + overlay

**Kernel** (this repo, inherited verbatim): seven trust-invariant classes,
five loops, five gates, the agent org, the cost and communication rules, and
the portable tools. Identical in every adopting project.

**Overlay** (`OVERLAY.md`, filled per project): trusted surfaces and custody
· domain invariants · golden sets and ratified thresholds · escalation
additions · key manifest · tribal knowledge · harness bindings · declared adoption step.

An overlay may only ADD constraints or BIND kernel parameters. Weakening a
kernel guarantee is a founder decision recorded as such — never an overlay
edit. Editing kernel text inside a project is a fork: fix it here and pull
it down, or record the divergence deliberately.

## What's in the box

| Path | What it is |
|---|---|
| `CLAUDE.md` | The charter an agent reads first — kernel text, overlay placeholders |
| `OVERLAY.md` | The eight per-project bindings, with a bootstrap checklist |
| `docs/OPERATING_RULES.md` | The quality bar and the loops — how work actually proceeds |
| `docs/KAIZEN.md` + `docs/metrics/KAIZEN_LEDGER.md` | The improvement engine and its (empty) ledger |
| `docs/RECORD.md` | The no-silent-deferrals ledger (empty template) |
| `docs/SESSION_START.md` | Session bookends: reconcile → work → close |
| `docs/hats/` | Six standing thinking agents with custody rules |
| `docs/review_personas/` | Cross-agent review lenses |
| `tools/` | The portable harness — see `tools/README.md` |

## The one idea worth stating plainly

Adoption maturity is bounded by **trust in the verification loop**, not by
model capability or token budget. The failure mode is scaling agent count
before the loop has earned that trust — more agents against weak gates just
produce unverified work faster. So the order is fixed and non-negotiable:

> **Verification loop first. Then the agent.**

Everything in this repo exists to make that order cheap to follow.

## Bootstrap a project (~1 session)

1. Create the project repo from this template; fill `OVERLAY.md`'s eight
   bindings. Bindings 1 (trusted surfaces/custody), 3 (thresholds), and 8
   (adoption step) need explicit founder ratification, recorded verbatim in
   `docs/memory/decisions/`.
2. **Wire the independent evaluator before any other code lands** — its API
   key plus a review workflow on every pull request, no path filter. Kernel
   invariant I3 from commit one.
3. Stand up `tools/validate` with whatever exists (a nearly-empty test suite
   runs green honestly); register project-specific checks as executable
   scripts in `tools/project_checks.d/`; bind every skip to a Record row.
4. Declare the adoption step per surface, with evidence, in binding 8.
5. Only now: feature work, contract-first.

## Honest limits

- **The kernel is process, not correctness.** It makes overclaims hard to
  ship and defects expensive to hide. It cannot make a wrong design right.
- **Propagation is manual.** Template updates reach existing projects only
  by a deliberate, evaluator-reviewed pull. This is chosen over a shared
  submodule so each project keeps sovereign gate custody — the cost is that
  this repo needs an owner or it rots.
- **The portable tools are a floor.** Every project must add its own
  trust-invariant gate; the kernel supplies the runner, the review, the
  deferral scan, the Kaizen meter, and the routing — not your domain's
  physics.
- **Adoption steps describe behavior, not tooling.** Buying a tier does not
  advance a step; a supervised single session is still a supervised single
  session.
