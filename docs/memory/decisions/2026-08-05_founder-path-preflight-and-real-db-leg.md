# Decision: founder-path preflight + real-database leg (founder-ratified 2026-08-05)

**Context.** In one day the founder personally discovered two defects the
agent's checks structurally could not see: (1) the /ops sign-in walkthrough
sent the founder to OAuth buttons that had been broken in production since
go-live (Google: "Missing required parameter: client_id") — the agent had
described the path from code, not exercised it; (2) earlier, the artist_ids
uuid[]/text[] insert refusal shipped through 2,000+ green hermetic tests
because fake cursors cannot perform server-side type checks (219 failed
publishes across two runs). Founder, verbatim: **"I'm tired of all these
fixes because you don't code properly"**, then, on whether the mechanical
changes were codified: **"Are these codified in the canon and repo? Should
anything be added/modified to the operating rules?"**

**Proposed rule texts** (presented 2026-08-05, in-session, verbatim):

> **§ Founder-path preflight.** Nothing that asks the founder to touch the
> product — a walkthrough, a runbook step, a "go try X" — is sent until the
> exact path has been exercised against the LIVE deployment by a mechanical
> probe (ops-diagnostics), with the probe run linked in the message. A step
> that cannot be probed is labeled UNPROBED in the message itself. The
> founder discovering a broken path the agent described is an ESCAPED
> defect, ledger row mandatory.

> **§ Real-database leg for publish-path changes.** Any change to code that
> writes the canonical public tables (promote, importers, migrations) must
> pass a CI test against a real PostgreSQL with the repo's migrations
> applied — hermetic fake-cursor tests cannot see server-side
> types/constraints and never satisfy this rule alone.

**Founder ratification, verbatim:** **"Ratified"** (2026-08-05).

**Landed in this commit** (rule-stronger-than-mechanism: the rule ships with
its mechanism or carries a RECORD row — both mechanisms ship here):
- OPERATING_RULES §6b (founder-path preflight) + §6c (real-database leg).
- ops-diagnostics mode `auth-probe`: hosted sign-in page + every enabled
  OAuth provider walked to its authorization redirect; missing/empty
  client_id fails loud.
- `.github/workflows/db-integration.yml` + `tests/integration/test_promote_pg.py`:
  the actual promote path against PostgreSQL 15 with migrations 0001→0020
  applied — proven locally against a real PostgreSQL 16 before commit
  (uuid[] insert with two distinct artists; registry-bound provenance;
  0020 backfill idempotence).
- RED_CLASSES index rows: `founder-path-unprobed`,
  `db-type-mismatch-invisible-to-hermetic-tests`.
- KAIZEN ledger: ESCAPED row (founder-caught unprobed walkthrough,
  2026-08-05) alongside the existing uuid[] class row.

**Scope note (governance-ambiguity discipline):** these rules ADD gates and
relax nothing; adding further named exceptions to either is a
gate-threshold relaxation — founder-crucial.
