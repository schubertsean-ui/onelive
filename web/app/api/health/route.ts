import { authMode } from "../../../lib/auth";
import { supabaseConfigured, supabaseSource, probeLicensed } from "../../../lib/licensed";

// GET /api/health — the deployment's resolved config state, ALWAYS reachable
// (exempt from the stealth gate in middleware.ts), and NEVER leaking a secret
// value. This exists so a config problem is OBSERVABLE — you (or the agent) open
// it and see exactly what the running app resolved, instead of guessing from a
// generic 503 and redeploying to test. See docs/DEPLOY.md.
export const dynamic = "force-dynamic";

export async function GET() {
  const mode = authMode();
  const supa = supabaseConfigured();
  const db = supa ? await probeLicensed() : { reachable: false, count: null, error: "supabase env not set" };
  const ok = mode !== "unconfigured" && supa && db.reachable;

  const body = {
    ok,
    auth: {
      mode, // "clerk" | "disabled" | "unconfigured"
      // WHAT ACTUALLY OPENED THE GATE (name only, never the value) — null unless
      // the gate is genuinely open.
      //
      // This field used to report the mere PRESENCE of a disable flag, whatever
      // the resolved mode was. The deployed preview therefore answered
      // `{"mode":"clerk","disabledBy":"NEXT_PUBLIC_AUTH_DISABLED"}` on
      // 2026-07-26: a payload asserting both that the Clerk gate is running and
      // that a flag disabled it. Only one can be true — `authMode()` gives Clerk
      // priority — so the endpoint whose entire job is to be diagnosable was
      // publishing a contradiction, and a founder reading it would believe the
      // preview was open when the stealth gate was live.
      disabledBy: mode !== "disabled" ? null
        : process.env.AUTH_DISABLED ? "AUTH_DISABLED"
        : process.env.NEXT_PUBLIC_AUTH_DISABLED ? "NEXT_PUBLIC_AUTH_DISABLED"
        // A preview needs no flag: VERCEL_ENV=preview|development resolves to
        // 'disabled' on its own (lib/auth.ts). Reporting null here would read as
        // "disabled for no reason", so name the real cause.
        : `VERCEL_ENV=${process.env.VERCEL_ENV ?? ""}`,
      // A flag that was SET and LOST. Silence here is the trap: the founder sets
      // NEXT_PUBLIC_AUTH_DISABLED expecting an open preview, a Clerk key is also
      // present, Clerk wins, and nothing says so.
      overriddenDisableFlag: mode === "clerk" &&
        (process.env.AUTH_DISABLED || process.env.NEXT_PUBLIC_AUTH_DISABLED)
        ? "a disable flag is set but a Clerk publishable key takes priority, so " +
          "the stealth gate IS active — remove NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY " +
          "to open this deployment (docs/DEPLOY.md)"
        : undefined,
      note: mode === "unconfigured"
        ? "Access gate is not configured — the app denies traffic. Set NEXT_PUBLIC_AUTH_DISABLED=1 (non-Sensitive) for a preview, or a Clerk key. See docs/DEPLOY.md."
        : undefined,
    },
    supabase: {
      configured: supa,
      source: supabaseSource(), // which env NAME supplied the URL (no value)
      reachable: db.reachable,
      eventCount: db.count,
      error: db.error,
    },
    vercelEnv: process.env.VERCEL_ENV ?? null,
    checkedAt: new Date().toISOString(),
  };

  return Response.json(body, { status: ok ? 200 : 503 });
}
