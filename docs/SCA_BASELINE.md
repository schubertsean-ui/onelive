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

**CLEAN as of 2026-07-31.** `npm audit --omit=dev` reports **zero** advisories at
any severity, so `security/sca_allowlist.json` carries **no exceptions** (empty
`entries`). The postcss and sharp advisories that previously required exceptions
were removed at the root rather than suppressed: `web/package.json` pins
`overrides` forcing `postcss` ≥ 8.5.12 (resolves 8.5.25) and `sharp` ≥ 0.35.0
(resolves 0.35.3), so the patched packages replace the versions `next` pins.
This is the real fix the exceptions' resolution triggers pointed to — because
`next` still pins the vulnerable `postcss 8.4.31` / `sharp ^0.34.x` even at
15.5.x and 16.x, a `next` bump alone was insufficient; the override reaches the
patched packages deterministically (same result in CI and locally, ending the
`fixAvailable` nondeterminism). Retained the SCA gate and its anti-rot rules
unchanged; only the (now dead) exception rows were deleted.

## Resolved (kept for the record)

- 2026-07-31: postcss/sharp advisories cleared by upgrading past them via
  `overrides` (postcss ≥ 8.5.12 → 8.5.25, sharp ≥ 0.35.0 → 0.35.3). Removed
  all three high/critical allowlist entries (GHSA-6g55-p6wh-862q,
  GHSA-r28c-9q8g-f849, GHSA-f88m-g3jw-g9cj — R-048) and cleared the moderate
  postcss row (GHSA-qx2v-qp2m-jg93 — R-003). `npm run build` + `typecheck` pass
  unchanged; the SCA gate reports clean. Founder directive 2026-07-31 ("Do 1"):
  upgrade to patched postcss/sharp, retire the exceptions.

- 2026-07-13 (PR #11): `vitest`/`vite`/`esbuild` chain — 1 critical (Vitest UI
  arbitrary file read/execute), 1 high (Vite path traversal), 3 moderate.
  Dev-only tooling, but fixed rather than baselined: upgraded `vitest` 3 → 4
  (semver-major of a devDependency; 25/25 tests pass unchanged).
