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
//   'disabled'     — AUTH_DISABLED (or NEXT_PUBLIC_AUTH_DISABLED) is truthy: the
//                    operator has EXPLICITLY DECLARED this deployment runs with
//                    no app-level gate (e.g. behind host deployment protection,
//                    or a post-launch public build). Passthrough, but declared.
//   'unconfigured' — neither: misconfiguration, and middleware FAILS CLOSED
//                    (denies) rather than opening the door.
//
// Deliberately NOT inferred from VERCEL_ENV: a preview's privacy depends on the
// host's Deployment Protection being ON, which the app cannot verify — inferring
// "open" from an environment name would silently publish a preview whose
// protection was disabled/misconfigured (evaluator PR #59). The disable must be
// an explicit, checkable declaration. Ops routes stay denied in 'disabled' mode
// regardless (middleware.ts).
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
  // Accept the plain runtime form (works even when marked "Sensitive") or the
  // NEXT_PUBLIC_ form (build-inlined).
  return (
    _isTruthy(process.env.AUTH_DISABLED) ||
    _isTruthy(process.env.NEXT_PUBLIC_AUTH_DISABLED)
  );
}

// Resolve the gate mode. Clerk (a configured provider) wins; an explicit disable
// is honored next; otherwise we are unconfigured and callers must fail closed.
export function authMode(): AuthMode {
  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return "clerk";
  if (_explicitlyDisabled()) return "disabled";
  return "unconfigured";
}

// True only when a real auth provider is wired up (drives ClerkProvider).
export function authProviderActive(): boolean {
  return authMode() === "clerk";
}
