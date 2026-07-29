# RECORD — the deviations-from-world-class register ("Recording")

> **KERNEL DOC — project-agnostic, inherited verbatim.** The RULES below are
> kernel and never change; the ROWS are project data and start empty. Bars cited
> in a row point at the project's own standards doc via `OVERLAY.md`. Text in
> `[square brackets]` is a placeholder the overlay must bind.

Greppable summary: the ledger of EVERY deferral, hold, or watch — any "for now",
"check later", "revisit", "ok for now", noticed-but-not-fixed. The standard is
that such moments should not exist (everything checked against the documented
world-class bar for that item); when one does exist it is recorded HERE in the
same commit, naming the bar it deviates from and the objective trigger that
resolves it. Silent deferral is a violation. Mechanical enforcement in code:
`tools/deferral_scan.py` (wired into `tools/validate`) — a deferral-language comment must carry
an `[R-###]` tag pointing at a live entry. Prose (docs, PR text, chat) is
covered by the charter rule + the Independent Evaluator review. Entries are never deleted:
resolved entries flip status to RESOLVED with the resolving commit/PR.

Format: `R-### · opened · what is deferred/held · world-class bar it
deviates from (cite) · resolution trigger · status`.

| # | Opened | What | Bar deviated from | Resolution trigger | Status |
|---|---|---|---|---|---|
| R-001 | 2026-07-24 | No project trust gate is registered: `tools/project_checks.d/` holds only its README, so the `project_checks` step of `tools/validate` runs the kernel's portable checks and NOTHING enforcing this project's own physics. | Kernel invariant I1/I2: the trusted surface must be guarded by a gate the generator cannot bypass, and it must fail closed. | OVERLAY.md binding 7's "[project trust gate]" row is filled AND its script is executable in `tools/project_checks.d/`. Then flip this row RESOLVED in the same commit. | OPEN |
| R-002 | 2026-07-24 | The independent evaluator is not yet wired — no API key, so no pull request is adversarially reviewed. | Kernel invariant I3: verifier independence, mandatory on every pull request with no path filter. | The evaluator key exists as a CI secret and `.github/workflows/adversarial-review.yml` has completed one real run on a pull request. | OPEN |

**Adding an entry:** same commit as the deferral it records; cite the bar
section (or "n.a. — bar gap", which itself is a finding); give an objective
trigger, never "someday". **Resolving:** flip status to
`RESOLVED (<commit/PR>)`; leave the row. **Session close:** review OPEN
rows — resolve, re-affirm (trigger still pending), or escalate; a row whose
trigger has fired but wasn't acted on is a defect.

**Writing a good trigger (the part that decays first):** a trigger is objective
when a third party could tell, without asking you, whether it has fired. "When we
have time", "before launch-ish", "when it matters" are not triggers. "The next PR
that touches `[path]`", "the first deployed preview URL exists", "sample size
crosses N", "the founder answers question X" are.
