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

// Resolve the gate mode. Precedence (fixed 2026-07-29 after a preview 500):
//   1. an EXPLICIT disable flag wins — it is a declared operator choice, and the
//      documented preview escape hatch (NEXT_PUBLIC_AUTH_DISABLED) must actually
//      work even when a Clerk publishable key is present in the env;
//   2. a preview/development Vercel deployment is host-protected and a declared
//      no-app-gate state — it must NOT run the Clerk gate even if it inherited
//      the project's Clerk publishable key, because the preview URL is not an
//      authorized Clerk domain (and may lack the secret key), so clerkMiddleware
//      THROWS -> MIDDLEWARE_INVOCATION_FAILED (a 500 on every route). Founder-
//      directed: previews need ZERO auth config;
//   2. a configured Clerk key gates the deployment (production). A PRESENT
//      provider is NEVER overridden by a disable flag — otherwise
//      NEXT_PUBLIC_AUTH_DISABLED could flip a correctly-configured PRODUCTION
//      deployment to public and expose protected user/ops surfaces (adversarial-
//      review #102, a production fail-open). The disable flag is honored ONLY
//      where there is no provider to override;
//   3. an explicit disable with NO provider is a declared "intentionally public"
//      choice (the go-live / no-provider case);
//   4. otherwise unconfigured — callers FAIL CLOSED.
// PRODUCTION is never a preview, and a present Clerk key wins over the flag, so
// a configured production stays gated — the no-silent-publish and no-fail-open
// invariants (evaluator PR #59) are preserved.
export function authMode(): AuthMode {
  if (_hostProtectedPreview()) return "disabled";
  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return "clerk";
  if (_explicitlyDisabled()) return "disabled";
  return "unconfigured";
}

// True only when a real auth provider is wired up (drives ClerkProvider).
export function authProviderActive(): boolean {
  return authMode() === "clerk";
}
