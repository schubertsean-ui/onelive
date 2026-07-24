# External-findings policy — managing gate findings we cannot fix

**The category.** Sometimes a quality gate correctly flags a real finding that
we **cannot fix under our own control** and that **does not actually inhibit
operations** — most often an upstream dependency advisory whose only fix lives
in an unreleased version. Left alone, that finding blocks every merge
indefinitely, for a risk that is already understood and contained. The wrong
answers are (a) a manual override each time (invisible, unrepeatable, erodes the
gate) or (b) turning the gate off (loses all future protection). This policy is
the right answer: a **managed, self-maintaining exception** — visible, scoped,
time-boxed, and automatically re-blocking the moment the excuse expires.

This was founder-directed (2026-07-24): *"Create a mechanism to manage these
kinds of, categories of, issues that do not inhibit operations."*

## What qualifies (all three, or it does not qualify)

1. **Not fixable under our control** — no released fix exists (an unreleased
   preview/canary does not count as available), or the fix is pinned shut by
   another dependency we cannot move yet.
2. **Does not inhibit operations** — the finding is not exploitable in how we
   actually run, with a written, specific exposure rationale (not "seems fine").
3. **Not a trust invariant.** This mechanism is **forbidden** for the trust
   gates — `trust_gate`, the independent evaluator verdict, the eval-harness
   thresholds, and RLS. Those are physics (CLAUDE.md prime directive 1); an
   exception there is never an engineering decision and is founder-crucial.
   External findings are dependency/tooling/scanner findings only.

## The guarantees (enforced mechanically, never by good intentions)

Every enforcer built to this policy MUST provide, and prove with tests:

| Property | Meaning |
|---|---|
| **Scoped** | An exception names an exact finding id (advisory/rule) + subject. No wildcards, no "ignore this package". |
| **Fail-closed** | An unreadable/malformed allowlist, or unparseable scanner output, **fails** the gate. Absence of proof is never a pass. |
| **Auto-re-block** | An exception holds **only while the finding is genuinely unfixable**. The instant the scanner reports a fix is available, the gate **fails** — forcing the upgrade. Exceptions cannot rot into permanent blindness. |
| **Time-boxed** | Every exception has an `expires` date. Past it, the gate **fails** and a human + the evaluator must re-review. |
| **Reviewed** | Every allowlist change is a diff that rides the mandatory adversarial review (every PR, no path filter). Adding an exception is a reviewed act, not a quiet edit. |
| **Auditable** | Every entry carries reason, exposure rationale, owner, added date, and a concrete resolution trigger. |

A finding that is **not** covered by a valid exception blocks exactly as it did
before the mechanism existed. The gate is not weakened for anything unlisted.

## Reference implementation — the SCA (npm audit) gate

The first gate built to this policy:

- **Allowlist (data):** `security/sca_allowlist.json` — scoped `(package, ghsa)`
  entries with reason, exposure, owner, `expires`, and resolution trigger.
- **Enforcer (code):** `tools/sca_gate.py` — runs `npm audit --omit=dev --json`,
  and **fails** on any high/critical production advisory that is not covered by a
  valid, unexpired entry whose package the scanner still reports as
  `fixAvailable: false`. Replaces the raw `npm audit --audit-level=high` step in
  `.github/workflows/adversarial-review.yml`.
- **Tests (proof):** `tests/test_sca_gate.py` — unlisted → fail; suppressed →
  pass; expired → fail; fix-now-available → fail; malformed/unreadable → fail.

### Adding an SCA exception (the whole procedure)

1. First try to actually fix it: `cd web && npm audit fix` (in-range) — only
   things with **no** available fix belong in the allowlist.
2. Confirm it is genuinely unfixable: `npm audit --omit=dev --json` shows the
   package's `fixAvailable: false`.
3. Add a scoped entry to `security/sca_allowlist.json` with a real exposure
   rationale and an `expires` no more than ~30–60 days out.
4. Open the PR. The evaluator reviews the exception like any gate-custody change.
5. Record the deferral in `docs/RECORD.md` with the resolution trigger.

## Extending the pattern to other gates

Other scanners will hit the same category (a linter rule with no clean fix, a
license checker flagging an unavoidable transitive license, a perf budget an
upstream regressed). Reuse this pattern, do **not** invent a bespoke override:
a per-gate scoped+expiring+fail-closed+auto-re-block allowlist, a small enforcer
with the same guarantees, and tests that prove them. Keep each gate's allowlist
separate (blast-radius isolation). The trust gates remain out of scope, always.
