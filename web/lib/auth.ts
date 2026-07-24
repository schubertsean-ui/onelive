// The stealth gate as a config-driven optional module — FAIL-CLOSED by default.
//
// One source of truth for "is the auth/allowlist gate active, and how?" so the
// decision lives in exactly one place instead of being re-derived in layout.tsx
// and middleware.ts.
//
// The load-bearing rule (evaluator PR #59): the absence of configuration must
// NEVER silently publish the app. "Gate off" is a real, sometimes-correct state
// (an intentionally public build, or a preview already fenced by the host's own
// deployment protection) — but it must be DECLARED, never the accidental
// fallback of a missing/stripped env var. So there are three explicit modes:
//
//   'clerk'        — NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set: the Clerk +
//                    allowlist stealth gate is active (middleware.ts).
//   'disabled'     — an app-level gate is intentionally absent. This is DECLARED,
//                    two ways: (a) NEXT_PUBLIC_AUTH_DISABLED / AUTH_DISABLED is
//                    truthy, or (b) the deployment is a NON-production Vercel
//                    environment (VERCEL_ENV = preview/development), which Vercel
//                    fences behind Deployment Protection by default — so a
//                    preview needs no flag. Passthrough, but intentional.
//   'unconfigured' — none of the above (e.g. PRODUCTION with no provider and no
//                    declared disable): misconfiguration, and middleware FAILS
//                    CLOSED (denies) rather than opening the door.
//
// Note production is the ONLY publicly-reachable target that ever lands in
// 'unconfigured' — previews/dev auto-resolve to 'disabled' because they are
// host-protected; production must be explicitly configured or it denies. Ops
// routes stay denied in 'disabled' mode regardless (middleware.ts).
//
// Swapping providers (Clerk today, Supabase Auth / custom next) means adding a
// mode here and a middleware branch — never touching the consumer feed. The
// per-user fail-closed (an empty allowlist matches nobody) still lives in
// lib/allowlist.ts.

export type AuthMode = "clerk" | "disabled" | "unconfigured";

const _TRUTHY = new Set(["1", "true", "yes", "on"]);

function _isTruthy(v: string | undefined): boolean {
  return typeof v === "string" && _TRUTHY.has(v.trim().toLowerCase());
}

function _explicitlyDisabled(): boolean {
  // Accept the NEXT_PUBLIC_ form (build-inlined) or the plain runtime form.
  return (
    _isTruthy(process.env.NEXT_PUBLIC_AUTH_DISABLED) ||
    _isTruthy(process.env.AUTH_DISABLED)
  );
}

// A non-production Vercel deployment is host-protected (Deployment Protection),
// so it is treated as an intentional no-app-gate state without a flag.
function _hostProtectedPreview(): boolean {
  const v = process.env.VERCEL_ENV;
  return v === "preview" || v === "development";
}

// Resolve the gate mode. Clerk (a configured provider) wins; an explicit or
// host-implied disable is honored next; otherwise we are unconfigured and
// callers must fail closed.
export function authMode(): AuthMode {
  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return "clerk";
  if (_explicitlyDisabled() || _hostProtectedPreview()) return "disabled";
  return "unconfigured";
}

// True only when a real auth provider is wired up (drives ClerkProvider).
export function authProviderActive(): boolean {
  return authMode() === "clerk";
}
