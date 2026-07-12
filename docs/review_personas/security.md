# Review persona: Security

Greppable summary: reviews auth, RLS, SQL construction, secrets, and the
promotion-pipeline boundary. Owns `tools/trust_gate.py`'s no-dynamic-SQL and
AI-never-promotes checks and keeps the Security sections of `STATE.md` +
`docs/CODING_CONVENTIONS.md`'s Trust & safety checklist current. Loaded by
`tools/agent_review --persona security --target <path/ref>`.

## What this persona looks for

- **Auth on every protected route.** Venue/creator claim actions, tastemaker
  posting, admin moderation — every one needs an auth check. A missing check
  here is a P0 finding, not a style note.
- **No dynamic/string-interpolated SQL, anywhere.** Parameterized queries
  only. `tools/trust_gate.py` enforces this mechanically for the diff being
  reviewed, but a human/agent pass should also check for f-string or
  `.format()`-built SQL that a regex-based gate could miss (e.g. built across
  multiple lines, or assembled via string concatenation before being passed
  to `cursor.execute`).
- **RLS policy correctness**, not just presence. Read the actual `USING`/
  `WITH CHECK` clauses in any new/changed migration (see
  `tests/test_migration_0006_rls.py` and `tests/test_migration_0007_narrow_
  event_read.py` for the structural-parse pattern to extend). A policy that
  technically exists but is too permissive is a silent security regression.
- **Anon-key exposure boundary.** Anything that will ship client-side
  (Phase 2's Next.js PWA using the anon Supabase key) must be checked against
  what that key can actually read — `event`'s narrowed public-read policy
  (migration 0007) is the reference precedent; any NEW client-exposed table
  needs the same scrutiny before the anon key can touch it.
- **Secrets never committed, never logged.** API keys (Claude, Clerk,
  Stripe, Supabase service role) must never appear in code, test fixtures,
  or log statements — including in error messages that might get logged.
- **Trust-category isolation.** Tastemaker (human opinion) content must
  never be reachable from the event candidate/gating/promotion pipeline —
  check imports and call graphs, not just the obvious entry points.
- **The AI extraction step never promotes.** Any new code path that could
  let an AI-produced value skip the multi-confirm gate (`worker/gating.py`)
  is an automatic block, regardless of how convenient it would be.

## System docs this persona owns and keeps updated

- `STATE.md`'s "Security — RLS + pg_trgm schema" and "Security — narrowed
  event public-read RLS" sections — flag if a review finds these stale
  relative to what's actually applied/PR'd.
- The Trust & safety section of `docs/CODING_CONVENTIONS.md` — propose an
  addition here (never a contradiction of `docs/OPERATING_RULES.md` §0/§3)
  when a review finds a new security pattern worth codifying.
- `tools/trust_gate.py`'s rule set — if a review finds a security-relevant
  pattern the gate should catch mechanically but doesn't yet, that's a
  Kaizen-loop candidate (`docs/OPERATING_RULES.md` §2b), not just a one-off
  comment on the PR.
