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
//   'disabled'     — NEXT_PUBLIC_AUTH_DISABLED is explicitly set: the operator
//                    has DECLARED this deployment runs without an app-level gate
//                    (e.g. behind Vercel Deployment Protection, or a post-launch
//                    public build). Passthrough — but an intentional, logged one.
//   'unconfigured' — neither is set: this is misconfiguration, and middleware
//                    FAILS CLOSED (denies) rather than opening the door.
//
// Swapping providers (Clerk today, Supabase Auth / custom next) means adding a
// mode here and a middleware branch — never touching the consumer feed. The
// per-user fail-closed (an empty allowlist matches nobody) still lives in
// lib/allowlist.ts.

export type AuthMode = "clerk" | "disabled" | "unconfigured";

const _TRUTHY = new Set(["1", "true", "yes", "on"]);

function _explicitlyDisabled(): boolean {
  const v = process.env.NEXT_PUBLIC_AUTH_DISABLED;
  return typeof v === "string" && _TRUTHY.has(v.trim().toLowerCase());
}

// Resolve the gate mode from the environment. Clerk (a configured provider)
// wins; an explicit disable is honored next; otherwise we are unconfigured and
// callers must fail closed.
export function authMode(): AuthMode {
  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return "clerk";
  if (_explicitlyDisabled()) return "disabled";
  return "unconfigured";
}

// True only when a real auth provider is wired up (drives ClerkProvider).
export function authProviderActive(): boolean {
  return authMode() === "clerk";
}
