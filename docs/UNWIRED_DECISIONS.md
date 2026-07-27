# Unwired code — wire it, delete it, or freeze it

**Status: CANON (a decision queue, not a rule).** Founder-directed 2026-07-26:
*"I want a complete audit and streamline and revamp according to world class
standards."* This is the streamline half, made decidable.

`docs/BAR.md` **F5** says: *"No dead code. A module nothing can reach is not done —
wire it or delete it."* That was a rule with no mechanism until
`tools/health_check.py` gained a detector for it. The detector finds first-party
modules imported by **nothing except tests** — built, green, and reachable from no
production path.

**Warrant** (on-disk primaries, `docs/WORLD_CLASS.md`): §1.9 Beck's fourth rule of
simple design — **"Fewest elements"**; §1.10 Ousterhout — complexity is *"change
amplification, cognitive load, unknown unknowns"*, and unreachable code is pure
cognitive load with zero delivered value; §3.3 OWASP A06 — *"Remove unused
dependencies and features to minimize attack surface."*

Re-measure at any time:

```bash
python tools/health_check.py        # the "Unwired modules" row and list
```

---

## Already executed 2026-07-26 — two deletions, no permission needed

Both were unambiguous dead code under existing canon, so they were removed rather
than queued. Git history keeps them.

| Deleted | Why it was safe, and why it was worth doing |
|---|---|
| `worker/multiconfirm.py` (7 lines) | A **re-export shim** whose own docstring said *"keep this file import-only."* Imported by **nothing** — not one production module, not one test. This is the subtlest dead-code shape: it looks like infrastructure and imports something real, so it reads as load-bearing. The real logic lives in `worker/gating.py` and always did. |
| `worker/definition_of_done.py` (15 lines) | Worse than dead — **it contradicted current canon.** It required every feed event to be at least `likely` confidence, but `docs/BAR.md` P6 says nothing real is ever hidden, and the founder's 2026-07-25 auto-publish ratification **publishes single-source events at `unverified`**. A future reader could have wired it in good faith and silently suppressed exactly the events the founder asked to show. Dead code that encodes a superseded rule is a landmine, not clutter. |

Result: unwired modules **16 → 14**.

---

## The 14 remaining, classified — this is the decision

Nothing below is deleted by an agent, because every one is either founder-directed
work or carries a Record row with a live trigger. Three groups; the founder can
clear all three in one pass.

### Group A — WIRE. This is v1 Step 2 and it is the largest real engineering left.

| Module | Status |
|---|---|
| `worker/publish_policy.py` (121 lines) | The **founder-ratified auto-publish policy** (2026-07-25). Imported by nothing but its own test. R-056. |
| `worker/source_reliability.py` (27 lines) | **Safeguard 1** of that same ratification — "reliability grading is real" — called by nothing, so *"graded unreliable"* cannot gate anything. R-056. |

**These two are the reason a long-tail event still cannot reach a user without a
human click** — the thing the founder said does not scale. They are not clutter;
they are an unfinished feature. `docs/V1.md` Step 2 is the plan, and it is **gated
on founder ask 3** because it touches a trust invariant.

### Group B — FREEZE with a live trigger. Built, tested, deliberately not wired.

| Module | Protected by |
|---|---|
| `worker/fetch/render_fetch.py` (260 lines) | **R-032** — headless-render fallback for JS-widget venue calendars. Real capability, deliberately parked. |
| `worker/convergence/decisions.py` (860 lines) | The convergence spec (`ONE_LIVE_CONVERGENCE_v1`), founder-directed. The single largest unwired module in the tree. |
| `worker/source_rank.py` (114 lines) | Source ranking. **Touches the no-pay-to-rank invariant**, so it is not deleted casually and not wired casually either. |
| `brain/paths.py` (31 lines) | Part of `brain/`, frozen per `CLAUDE.md`'s mission scope. |

These have a defensible reason to exist and a trigger that will fire. **No action
requested** — they are listed so the count stays honest and so nobody mistakes
"frozen" for "forgotten".

### Group C — FOUNDER CALL. Whole subsystems, off-mission until v1 is live.

| Subsystem | Lines | How it got here |
|---|---|---|
| `social/carousel/*` — 4 unwired modules incl. `agent_loop.py`, `publish_gate.py` | ~2,750 total | Founder-directed 2026-07-24 (Meta carousel engine). **Has no posting client at all** (R-026) and no scheduled runner (R-027), so the loop cannot run end to end by construction. |
| `ventures/promise_ledger/*` — 4 unwired modules | ~1,170 total | **Founder-greenlit venture** ("Go", Contract #17). Golden set is synthetic-only (R-017). |
| `brain/*` — the wider subsystem | 5,393 total | Ratified brain architecture; five Record rows admit it is unwired (R-031/040/041/042/045). |

**Why an agent will not delete these:** each was explicitly commissioned by the
founder, and one is a greenlit venture. Deleting founder-directed strategic work on
a tidiness argument would be exactly the kind of unilateral scope decision the
charter forbids. **They are also the single largest simplification available** —
roughly **9,300 lines** that no production path reaches.

**The decision, in one question:** for each of the three, is it *(i)* frozen and
staying, *(ii)* deleted now with git history as the archive, or *(iii)* extracted
to its own repository? My recommendation is **(iii) for `ventures/promise_ledger`**
(it is a separate business and already has a staging precedent in PR #75), **(i) for
`brain/` and `social/`** until v1 is live — because both are cheap to carry once
they are *labelled* frozen and measured, and neither is on the v1 critical path.

**Carrying cost, stated honestly so the choice is real:** every one of those lines
is inside every gate run, every review diff, every refactor, and the audit's
harness-to-product ratio. That is the price of option (i), and it is not zero.

---

## How this stays solved

The detector runs with every health check (`docs/HEALTH_CHECK.md`), so the count is
measured rather than remembered:

- **A NEW unwired module appearing** is the signal to act on — it means work was
  completed and not connected, and it is cheapest to resolve in the week it appears.
  Triage it in the weekly checkup before it becomes furniture that gets defended
  later because it is "already built".
- **This file is the record of each decision**, so the same argument is not had
  twice.
- **F5 stays PROPOSED, not ENFORCED.** Making the detector blocking would fail the
  build on legitimately frozen work, and per `docs/BAR.md` every PROPOSED → ENFORCED
  transition needs its own reviewed PR.
