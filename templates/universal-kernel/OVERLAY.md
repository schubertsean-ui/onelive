# OVERLAY — [PROJECT NAME]

**This file is the project half of the operating model.** The kernel
(`CLAUDE.md`, `docs/OPERATING_RULES.md`, `docs/KAIZEN.md`, `docs/hats/`,
`tools/`) is inherited verbatim and is identical across every project. This
file is where THIS project's requirements, peculiarities, idiosyncrasies, and
tribal knowledge live.

**The one rule about overlays:** an overlay may only ADD constraints or BIND
kernel parameters. It may never weaken a kernel invariant, loop, or gate.
Loosening anything the kernel guarantees is a founder decision, not an
overlay edit — and it belongs in a decision record, not here.

Fill in all eight bindings before the first feature work. Bindings 1, 3, and
8 require explicit founder ratification (see the note under each).

---

## 1. Trusted surfaces + custody — binds kernel invariant I1

*What does "publish" mean here, what surface must never receive
unverified AI output, and who holds the key?*

- **Trusted surface(s):** [e.g. the public feed / the investor report / the
  claims ledger / the deployed API]
- **The gate the generator cannot bypass:** [name the mechanism, not the
  intention — a path the generator cannot import, a human approval step, a
  base-owned workflow]
- **Custodian:** [who holds promote/publish authority]
- **What "AI never publishes" means concretely here:** [one sentence a
  non-engineer can check]

> FOUNDER RATIFICATION REQUIRED. Record the verbatim decision in
> `docs/memory/decisions/`.

## 2. Domain invariants — additional physics, beyond the kernel's I1–I7

List the constraints that are true for THIS project and nowhere else. Each
must be stated so a test could fail on it.

- [e.g. "Confidence is a 4-state model; disputed is never deleted."]
- [e.g. "Claims are stored never-verbatim; only derived facts persist."]
- [e.g. "No AI-originated order ever reaches a broker."]

## 3. Golden sets + ratified thresholds — binds kernel gate 2

*Any AI capability feeding a trusted surface unlocks only via a passing exam
on the real provider path.*

| Capability | Golden set | Threshold (ratified) | Sample floor | Ratchet rule |
|---|---|---|---|---|
| [extraction] | [path] | [e.g. ≤1% field-level hallucination] | [e.g. ≥300 facts] | [e.g. 4 clean weeks at ≤½ bar → tighten to 2× measured] |

Injection/adversarial cases are mandatory in every golden set.

> FOUNDER RATIFICATION REQUIRED for every threshold. Thresholds only tighten
> by rule; loosening is founder-crucial (kernel I7).

## 4. Escalation additions — appended to the kernel's closed list (I7)

The kernel already escalates: money/new services · legal posture ·
trust-invariant changes · gate-threshold relaxations · go-live pushes ·
credential minting. This project adds:

- [e.g. "any change to how claims are dated"]
- [e.g. "publishing anything naming a real company"]

Everything not on the combined list: decide, log the decision record, proceed.

## 5. Key manifest — every credential this project touches

| Credential | Used by | Where it lives | Notes |
|---|---|---|---|
| [NAME] | [component] | [CI secret / env] | agents never mint keys |

## 6. Tribal knowledge — the memory that makes this project itself

- **Decisions:** `docs/memory/decisions/` — verbatim founder decisions, one
  file each. This is the ONLY home for verbatim founder instructions;
  other surfaces paraphrase (dissemination minimization).
- **Gotchas:** `docs/memory/gotchas/` — the traps that cost a session once.
- **Entity notes:** `docs/memory/entities/` — the domain's proper nouns.
- **Design/tone canon:** [path, if the project has a design brief]
- **Session arcs:** `docs/session_arcs/` — how the state got here.

## 7. Harness bindings — the project-supplied tools the kernel docs reference

The kernel ships the runner, the review, the scans, and the routing. It
cannot ship your domain's gate. Name each one here so the kernel docs'
references resolve; an unnamed row means that doc's rule has no enforcement
arm yet, which is a gap to close, not a blank to ignore.

| Kernel reference | This project's implementation | Status |
|---|---|---|
| [project trust gate] | `tools/project_checks.d/[nn_name].sh` | [ ] |
| [eval harness] | [path] | [ ] |
| [golden set] | [path] | [ ] |
| [gate test file] | [e.g. `tests/test_gates.py`] | [ ] |
| [perf test file] | [path or N/A] | [ ] |
| [test runner] | [e.g. `pytest`] | [ ] |
| [persona review runner] | [path or N/A — kernel ships the evaluator only] | [ ] |
| [autonomous run skill] | [path or N/A] | [ ] |

## 8. Adoption-step declaration — per surface, with evidence

Adoption is measured by BEHAVIOR, not tooling purchased. Different surfaces
of the same project legitimately sit at different steps (the origin project's
repo operations run at supervised autonomy while its product publish path is
deliberately human-custodied and always will be).

| Surface | Step (0–4) | Evidence justifying it | Human role today |
|---|---|---|---|
| [repo operations] | [1] | [what verification exists] | [reviews every change] |
| [product publish path] | [n/a — custodied] | [the gate] | [founder promotes] |

> FOUNDER RATIFICATION REQUIRED to move any surface UP a step. The kernel's
> gates are the PREREQUISITE for a step, never the trigger — earning trust is
> evidence, granting it is a decision. Notably, an agent merging its own work
> requires this project's own explicit ratification; inheriting the kernel
> does not inherit another project's permission.

---

## Bootstrap checklist (delete once complete)

1. [ ] Fill bindings 1–8; get founder ratification on 1, 3, 8.
2. [ ] Wire the independent evaluator (its API key + a review workflow on
       EVERY pull request, no path filter) — kernel invariant I3 from commit one.
3. [ ] Stand up `tools/validate` with whatever exists; register project-specific
       checks in `tools/project_checks.d/`; bind every skip to a Record row.
4. [ ] Write the first session contract in `STATE.md` before any feature code.
5. [ ] Only then: feature work. Verification loop first, then the agent —
       the order is the whole point.
