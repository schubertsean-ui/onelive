// The stealth gate as a config-driven optional module.
//
// One source of truth for "is the auth/allowlist gate active, and who provides
// it?" so the decision lives in exactly one place instead of being re-derived
// in layout.tsx and middleware.ts. This keeps the app build-and-run-anywhere:
//  * No provider configured -> the gate is OFF (passthrough). The app builds and
//    renders with only the Supabase read key (early private preview on an
//    unguessable, non-indexed URL).
//  * A provider IS configured -> the gate is ON and every route requires an
//    authenticated + allowlisted user (see middleware.ts).
//
// The gate is a MODULE, not a hard dependency: swapping providers (Clerk today,
// Supabase Auth / custom later) means adding a case here and a middleware branch,
// never touching the consumer feed. Fail-closed lives one layer down in
// lib/allowlist.ts (an empty allowlist matches nobody).

export type AuthProvider = "clerk";

export type AuthConfig =
  | { enabled: false; provider: null }
  | { enabled: true; provider: AuthProvider };

// Resolve the gate configuration from the environment. Today the only provider
// is Clerk, keyed off its publishable key (the same value the client SDK needs),
// so "the key is present" is exactly "Clerk is wired up".
export function authConfig(): AuthConfig {
  if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return { enabled: true, provider: "clerk" };
  }
  return { enabled: false, provider: null };
}

// Convenience predicate for the two call sites that only need on/off.
export function authEnabled(): boolean {
  return authConfig().enabled;
}
