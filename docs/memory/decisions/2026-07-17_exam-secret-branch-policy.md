# Exam-secret protection rests on the environment deployment-branch policy; #25 merges with that as a documented, runtime-proven constraint.

**Decided:** 2026-07-17, founder: "Merge #25" (informed — the specific evaluator finding below was explained first).

## The finding (evaluator, on PR #25)

`extraction-exam-dispatch.yml` is the only secret-bearing exam entry point. Its
fail-closed guard (a runtime step that PROVES the `extraction-exam` environment's
deployment-branch policy is `master`-only before any secret step) lives inside the
workflow file. A malicious branch-copy of the workflow could delete that guard and
still request the environment. Therefore the guard, as code, cannot fully close
the hole: the ONLY mechanical protection is GitHub itself refusing to inject the
environment secret into a workflow run from a non-default branch — i.e. the
environment's deployment-branch policy being configured. The evaluator reviews the
code diff and cannot verify a GitHub settings value, so it holds the finding open.

## The decision

- The environment deployment-branch policy (`extraction-exam` → Selected branches
  → `master` only) is the security boundary. It is configured out-of-band and
  verified fail-closed at runtime by the dispatch workflow's proof step.
- #25 merges with this as a **documented design constraint**, not a code defect —
  code cannot close it further. Recorded as `docs/RECORD.md` R-018 with an
  objective trigger.
- Current residual risk is nil in practice: no `ANTHROPIC_API_KEY_EXAM` secret is
  configured yet, and the golden-exam check is red-by-design (bootstrap, PR #11
  pattern) — no exam can run until the harness is on `master`.

## Why this, not the alternatives

- **More code hardening** — impossible; the branch-copy controls its own code. The
  session already wrote the maximal runtime proof.
- **Block the merge until the evaluator is satisfied** — the evaluator cannot be
  satisfied by code here (it cannot see the GitHub setting), so this would block
  #25 permanently on an unfixable-in-code point. Founder (Red hat / final
  authority) accepted the documented constraint instead.

## Guardrail

R-018's trigger: the `master`-only deployment-branch policy MUST be set before
`ANTHROPIC_API_KEY_EXAM` is ever configured; the runtime proof step keeps every
exam run fail-closed until it is.
