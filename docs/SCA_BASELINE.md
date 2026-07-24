# SCA_BASELINE — reviewed dependency-vulnerability exceptions

Greppable summary: the supply-chain (npm audit / SCA) policy and the current
reviewed-exception baseline. Policy: **production dependencies must audit clean
at high/critical**. As of 2026-07-24 this is enforced by a **managed exception
gate**, not a raw audit: `tools/sca_gate.py` (blocking CI step in
`.github/workflows/adversarial-review.yml`) fails on any high/critical
production advisory not covered by a **scoped, expiring, auto-re-blocking**
entry in **`security/sca_allowlist.json`**. The general mechanism and its
guarantees live in **`docs/EXTERNAL_FINDINGS_POLICY.md`** — read that before
adding any exception. Dev-dependency and moderate findings are surfaced in the
evaluator's web log and must either be fixed in-change or recorded. An entry is
temporary debt with a review trigger, never a permanent allowlist. (Origin:
evaluator finding, PR #11 round 2 — "npm ci succeeded is not security review.")

> The machine-readable allowlist (`security/sca_allowlist.json`) is now the
> source of truth for HIGH/CRITICAL exceptions; the table below is human
> narrative kept in sync with it. The moderate row predates the gate and stays
> here because the gate blocks only high/critical.

## Current baseline

HIGH/CRITICAL (machine-enforced — see `security/sca_allowlist.json`), reviewed 2026-07-24, founder-directed:

| Advisory | Severity | Chain | Why accepted | Clears when |
|---|---|---|---|---|
| GHSA-6g55-p6wh-862q (postcss arbitrary file read via sourceMappingURL) | high | `postcss ≤8.5.11` ← `next` ← (`@clerk/nextjs`, `@sentry/nextjs`) | **No fix available upstream** (npm `fixAvailable:false`); postcss runs at build time over our own authored CSS, never attacker-controlled input. Expires 2026-08-24. | `next` publishes a release depending on postcss ≥ 8.5.12 — the gate auto-fails (fix now available); bump `next`, delete the entry. |
| GHSA-f88m-g3jw-g9cj (sharp / libvips CVEs) | high | `sharp <0.35.0` ← `next` (optional image dep) | **No fix available upstream** (npm `fixAvailable:false`); the consumer feed uses CSS `background-image`, not `next/image`, so `sharp` is never in the runtime path. Expires 2026-08-24. | `next` publishes a release depending on sharp ≥ 0.35.0 — the gate auto-fails; bump `next`, delete the entry. |

MODERATE (below the high/critical gate — not machine-blocked; tracked here), reviewed 2026-07-13, PR #11:

| Advisory | Severity | Chain | Why accepted | Clears when |
|---|---|---|---|---|
| GHSA-qx2v-qp2m-jg93 (postcss XSS via unescaped `</style>` in stringify output) | moderate | `postcss` ← `next` ← (`@clerk/nextjs`, `@sentry/nextjs`) | **No fix available upstream** — pinned by `next`; not directly exploitable in our usage (we do not stringify user-controlled CSS). Below the high/critical gate. | `next` publishes a release depending on a patched postcss — re-checked on every web dependency PR. |

## Resolved (kept for the record)

- 2026-07-13 (PR #11): `vitest`/`vite`/`esbuild` chain — 1 critical (Vitest UI
  arbitrary file read/execute), 1 high (Vite path traversal), 3 moderate.
  Dev-only tooling, but fixed rather than baselined: upgraded `vitest` 3 → 4
  (semver-major of a devDependency; 25/25 tests pass unchanged).
