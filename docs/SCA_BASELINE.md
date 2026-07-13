# SCA_BASELINE — reviewed dependency-vulnerability exceptions

Greppable summary: the supply-chain (npm audit / SCA) policy and the current
reviewed-exception baseline. Policy (enforced in `.github/workflows/
adversarial-review.yml`): **production dependencies must audit clean at
high/critical** (`npm audit --omit=dev --audit-level=high` is a blocking CI
step); dev-dependency and moderate findings are surfaced in the evaluator's
web log and must either be fixed in-change or recorded here with a reason and
an owner. An entry here is temporary debt with a review trigger, not a
permanent allowlist. (Origin: evaluator finding, PR #11 round 2 — "npm ci
succeeded is not security review.")

## Current baseline (reviewed 2026-07-13, PR #11)

| Advisory | Severity | Chain | Why accepted | Clears when |
|---|---|---|---|---|
| GHSA-qx2v-qp2m-jg93 (postcss XSS via unescaped `</style>` in stringify output) | moderate ×4 | `postcss < 8.5.10` ← `next` ← (`@clerk/nextjs`, `@sentry/nextjs`) | **No fix available upstream** — every Next.js release in range pins the vulnerable postcss; not directly exploitable in our usage (we do not stringify user-controlled CSS). Production-facing but moderate. | `next` publishes a release depending on postcss ≥ 8.5.10 — bump `next` and delete this row. Re-check on every web dependency PR (`npm audit` runs in CI each time). |

## Resolved (kept for the record)

- 2026-07-13 (PR #11): `vitest`/`vite`/`esbuild` chain — 1 critical (Vitest UI
  arbitrary file read/execute), 1 high (Vite path traversal), 3 moderate.
  Dev-only tooling, but fixed rather than baselined: upgraded `vitest` 3 → 4
  (semver-major of a devDependency; 25/25 tests pass unchanged).
