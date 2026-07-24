import { clerkMiddleware, createRouteMatcher, clerkClient } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { allowlistFromEnv, isAllowlisted } from "./lib/allowlist";
import { authMode } from "./lib/auth";

// Stealth gate layer 1 (Next.js). The whole app is private during the preview:
// EVERY route requires an authenticated AND allowlisted user, EXCEPT the
// branded /access screen and Clerk's own sign-in/up routes (otherwise a
// non-allowlisted or signed-out user could never reach a page to act on).
// Fail-closed: an unset/empty ONELIVE_ALLOWLIST matches nobody (see
// lib/allowlist.ts), so a misconfigured deploy denies everyone rather than
// silently opening the door.
const isPublicRoute = createRouteMatcher([
  "/access",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/health",
]);

// The health endpoint is ALWAYS reachable, in every mode (incl. the fail-closed
// "unconfigured" state) — it reports resolved config so a deploy problem can be
// diagnosed from truth instead of guessed. It exposes no secret (see route).
const isHealthRoute = createRouteMatcher(["/api/health"]);

// The ops/admin console ALWAYS requires a real authenticated + allowlisted user.
// It is never covered by the "consumer public" declaration — declaring the feed
// public must not publish the admin surface (evaluator PR #59). When no auth
// provider is configured, ops cannot authenticate anyone, so it is denied and
// hidden (404), never opened.
const isOpsRoute = createRouteMatcher(["/ops(.*)"]);

async function resolveEmail(
  userId: string,
  sessionClaims: Record<string, unknown> | null,
): Promise<string | undefined> {
  // Prefer the email carried in the session token (present when the Clerk JWT
  // template includes it — the zero-latency path).
  const claimEmail = sessionClaims?.["email"];
  if (typeof claimEmail === "string" && claimEmail.length > 0) return claimEmail;

  // Fall back to a server-side user lookup so the allowlist decision is always
  // made against a real email even without a custom JWT template.
  try {
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    return user.primaryEmailAddress?.emailAddress ?? undefined;
  } catch (err) {
    // Never swallow silently (docs/OPERATING_RULES.md §1): log, then fail
    // closed — an unresolved email yields `undefined`, which is denied below.
    console.error("[stealth-gate] could not resolve user email; denying:", err);
    return undefined;
  }
}

// Response for the misconfigured ("unconfigured") state — FAIL CLOSED. A missing
// provider must never become a public passthrough (evaluator PR #59): if nobody
// declared how this deployment is protected, we deny rather than open the door.
function accessNotConfigured(): NextResponse {
  return new NextResponse(
    "OneLive is not accepting traffic in this environment: no access gate is " +
      "configured. For a preview set NEXT_PUBLIC_AUTH_DISABLED=1 (NOT marked " +
      "Sensitive), or set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY for the stealth " +
      "gate, then redeploy. Open /api/health to see exactly what the app " +
      "resolved. Full contract: docs/DEPLOY.md.",
    { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } },
  );
}

// Ops is denied + hidden when no real auth provider can gate it.
function opsDenied(): NextResponse {
  return new NextResponse("Not found", {
    status: 404,
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}

const gate = clerkMiddleware(async (auth, req) => {
  if (isPublicRoute(req)) return NextResponse.next();

  const { userId, sessionClaims, redirectToSignIn } = await auth();

  // Not signed in -> Clerk sign-in, returning here afterward. If the freshly
  // signed-in user is not allowlisted, this middleware then routes them to
  // /access on the next pass (they are never let through).
  if (!userId) {
    return redirectToSignIn({ returnBackUrl: req.url });
  }

  const allowlist = allowlistFromEnv();
  const email = await resolveEmail(userId, sessionClaims as Record<string, unknown> | null);

  if (!isAllowlisted(email, allowlist)) {
    const url = req.nextUrl.clone();
    url.pathname = "/access";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
});

// Resolved once at module load (env is fixed for the deployment's lifetime).
//   clerk        -> run the Clerk + allowlist stealth gate.
//   disabled     -> DECLARED public/no-app-gate: passthrough (intentional).
//   unconfigured -> misconfiguration: FAIL CLOSED (deny every route).
const _mode = authMode();

export default _mode === "clerk"
  ? gate
  : _mode === "disabled"
    ? function middleware(req: import("next/server").NextRequest) {
        // Consumer surface is intentionally public; ops stays denied (no auth
        // provider can gate it, so it must never be exposed by this switch).
        return isOpsRoute(req) ? opsDenied() : NextResponse.next();
      }
    : function middleware(req: import("next/server").NextRequest) {
        // Even fully unconfigured, the health endpoint stays reachable so the
        // misconfiguration is diagnosable; everything else fails closed.
        return isHealthRoute(req) ? NextResponse.next() : accessNotConfigured();
      };

export const config = {
  // Run on everything except Next internals and files with an extension (static
  // assets), plus always run for API routes. Mirrors Clerk's recommended matcher.
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
