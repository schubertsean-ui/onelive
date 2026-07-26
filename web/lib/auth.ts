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
//   'clerk'        — BOTH NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY
//                    are set: the Clerk + allowlist stealth gate is active
//                    (middleware.ts).
//   'disabled'     — an app-level gate is intentionally absent, declared EITHER
//                    by an explicit flag (AUTH_DISABLED / NEXT_PUBLIC_AUTH_DISABLED
//                    truthy) OR by being a NON-production Vercel deployment
//                    (VERCEL_ENV = preview/development), which Vercel fences
//                    behind Deployment Protection by default — so a preview needs
//                    no flag. Passthrough, but not a silent one.
//   'unconfigured' — none of the above (e.g. PRODUCTION with no provider and no
//                    declared disable): misconfiguration, and middleware FAILS
//                    CLOSED (denies) rather than opening the door.
//
// FOUNDER-DIRECTED (2026-07-24, "fix this — tired of all this wasted time"):
// previews auto-resolve to 'disabled' so they need ZERO auth config. The
// evaluator's standing concern (a preview whose Deployment Protection was turned
// OFF would be public) is accepted and bounded: (1) PRODUCTION is never
// auto-opened — it is the only publicly-reachable target and stays fail-closed;
// (2) the /ops admin surface is ALWAYS denied without a real provider, in every
// mode (middleware.ts), so auto-open never exposes anything sensitive; (3) the
// consumer feed is public licensed listings, and preview privacy rests on
// Vercel's own protection — a founder-owned go-live posture, not a data control.
// See docs/DEPLOY.md.
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

// A non-production Vercel deployment (preview/development) is host-protected by
// Vercel Deployment Protection — treated as an intentional no-app-gate state so
// previews need no flag. PRODUCTION is never covered by this.
function _hostProtectedPreview(): boolean {
  const v = process.env.VERCEL_ENV;
  return v === "preview" || v === "development";
}

// Clerk needs BOTH keys, and this is the fix for a real 500 (2026-07-26).
//
// The publishable key alone used to select 'clerk'. But clerkMiddleware(),
// auth() and clerkClient() are SERVER calls that require CLERK_SECRET_KEY — so a
// deployment carrying only the publishable key resolved to 'clerk' and then THREW
// inside the middleware. Vercel surfaced that as
// `500: MIDDLEWARE_INVOCATION_FAILED`, which took the whole site down: not the
// diagnosable 503 this module carefully produces for misconfiguration, but an
// opaque crash on every route, including the /api/health endpoint that exists to
// explain such failures.
//
// The class: a mode must not claim a capability its environment cannot deliver.
// Checking half the precondition is the same defect as checking none — it just
// fails later and louder. Requiring both keys means a partially-configured
// deployment falls through to the NEXT honest state instead of crashing:
//   * a PREVIEW keeps working (host-protected 'disabled'), which is what a
//     half-set-up preview should do;
//   * PRODUCTION still refuses ('unconfigured' -> fail-closed 503), because a
//     missing secret key must never be read as "no gate wanted".
function _clerkFullyConfigured(): boolean {
  const pk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const sk = process.env.CLERK_SECRET_KEY;
  if (pk && !sk) {
    // Say it out loud rather than resolving quietly to a different mode — a
    // half-configured gate is an operator error someone must see (§1).
    console.error(
      "[auth] NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is set but CLERK_SECRET_KEY is " +
        "not. Clerk's server middleware cannot run without the secret key, so " +
        "the Clerk gate is NOT active. Set CLERK_SECRET_KEY (same Clerk " +
        "instance) or remove the publishable key. See docs/DEPLOY.md.",
    );
  }
  return Boolean(pk && sk);
}

// Resolve the gate mode. Clerk (a fully configured provider) wins; an explicit or
// preview-implied disable is honored next; otherwise we are unconfigured and
// callers must fail closed. Production never auto-opens.
export function authMode(): AuthMode {
  if (_clerkFullyConfigured()) return "clerk";
  if (_explicitlyDisabled() || _hostProtectedPreview()) return "disabled";
  return "unconfigured";
}

// True only when a real auth provider is wired up (drives ClerkProvider).
export function authProviderActive(): boolean {
  return authMode() === "clerk";
}
