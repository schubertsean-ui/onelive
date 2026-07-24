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
      // Which flag opened the gate (name only, never the value):
      disabledBy:
        process.env.AUTH_DISABLED ? "AUTH_DISABLED"
        : process.env.NEXT_PUBLIC_AUTH_DISABLED ? "NEXT_PUBLIC_AUTH_DISABLED"
        : null,
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
