# PASTE THIS AS YOUR FIRST MESSAGE IN CLAUDE CODE (from the onelive repo root)

Read CLAUDE.md and docs/LOOPS, then run tools/session_reconcile.py and give me the reconciled state in 5 lines.

Then write Session Contract #1 to STATE.md with exactly this scope and confirm it back to me before writing any code:

GOAL: Stand up the autonomous build loop and take the first two steps toward the live site.
1. VERIFY: independently confirm repo + database state (tables, migrations, row counts, test suite green) and reconcile any drift with STATE.md — report discrepancies, don't fix silently.
2. EVALUATOR ONLINE: create tools/adversarial_review.py (posts raw git diff + pytest/vitest output to the OpenAI API, demands APPROVE or REQUEST-CHANGES with file:line issues; exits nonzero on REQUEST-CHANGES). Test it on the last merged PR's diff. It becomes a required step for every trust-critical PR.
3. FRICTION GATE ONLINE: create docs/FRICTION_LOG.md and wire the pre-work friction prompt (in CLAUDE.md) into the workflow for deploys/migrations/spend/prompt changes.
4. SENTINEL MINIMUM: add Sentry SDK to web + API + worker behind SENTRY_DSN env (no-op if unset), and a healthchecks ping wrapper for any scheduled entrypoint.
5. PLAN ONLY (no execution yet): write docs/SPRINT_LIVE_SITE.md — the step-by-step plan for critical-path Steps 5→10 (scheduled ingestion with budget caps first, extraction thresholds, gate flow, design implementation from design/inbox per the brief, allowlist gate, Vercel deploy), each step with its done-criterion and which agent gates it.

DONE-CRITERIA: reconcile clean · verification report delivered · adversarial_review.py green on a real diff · friction log exists with entry #1 (this sprint plan itself, attacked) · Sentry/no-op wired · sprint plan written. NOTHING deploys, migrates, or spends in this session.

Escalate to me only per the founder-crucial list in CLAUDE.md.
