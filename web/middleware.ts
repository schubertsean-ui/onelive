// NO top-level Clerk import. `@clerk/nextjs/server` is loaded ONLY when the mode
// is actually 'clerk', via dynamic import inside clerkGate() below.
//
// It used to be imported here, and `clerkMiddleware()` was constructed at module
// scope, on every deployment — including previews with no Clerk keys that never
// run the Clerk gate. On Vercel's EDGE runtime that threw
// MIDDLEWARE_INVOCATION_FAILED, so the entire site returned HTTP 500 including
// `/api/health`, the one endpoint whose whole job is to stay diagnosable. Vercel's
// Deployment Protection hid it until the automation bypass was configured
// (v1 done-criterion 5). `lib/auth.ts` calls this gate "a config-driven OPTIONAL
// module"; optional has to mean not loaded when not used.
import { NextResponse } from "next/server";
import { allowlistFromEnv, isAllowlisted } from "./lib/allowlist";
import { authMode } from "./lib/auth";
import { createRouteMatcher } from "./lib/route_match";

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
    const { clerkClient } = await import("@clerk/nextjs/server");
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

// Built on FIRST REQUEST in clerk mode only, then memoised. Constructing this at
// module scope is what broke every non-Clerk deployment.
type EdgeMiddleware = (
  req: import("next/server").NextRequest,
) => Promise<Response | undefined> | Response | undefined;

let _clerkGate: EdgeMiddleware | null = null;

async function clerkGate(
  req: import("next/server").NextRequest,
): Promise<Response | undefined> {
  if (_clerkGate === null) {
    const { clerkMiddleware } = await import("@clerk/nextjs/server");
    // Every reference below is to `request`, the handler's OWN argument — never
    // to the outer `req`. The gate is memoised, so closing over the first
    // request's path would match every later request against a stale URL.
    _clerkGate = clerkMiddleware(async (auth, request) => {
      if (isPublicRoute(request)) return NextResponse.next();

      const { userId, sessionClaims, redirectToSignIn } = await auth();

      // Not signed in -> Clerk sign-in, returning here afterward. If the freshly
      // signed-in user is not allowlisted, this middleware then routes them to
      // /access on the next pass (they are never let through).
      if (!userId) {
        return redirectToSignIn({ returnBackUrl: request.url });
      }

      const allowlist = allowlistFromEnv();
      const email = await resolveEmail(
        userId,
        sessionClaims as Record<string, unknown> | null,
      );

      if (!isAllowlisted(email, allowlist)) {
        const url = request.nextUrl.clone();
        url.pathname = "/access";
        url.search = "";
        return NextResponse.redirect(url);
      }

      return NextResponse.next();
    }) as unknown as EdgeMiddleware;
  }
  return _clerkGate(req) as Promise<Response | undefined>;
}

// Resolved once at module load (env is fixed for the deployment's lifetime).
//   clerk        -> run the Clerk + allowlist stealth gate.
//   disabled     -> DECLARED public/no-app-gate: passthrough (intentional).
//   unconfigured -> misconfiguration: FAIL CLOSED (deny every route).
const _mode = authMode();

export default async function middleware(
  req: import("next/server").NextRequest,
): Promise<Response | undefined> {
  try {
    if (_mode === "clerk") return await clerkGate(req);
    if (_mode === "disabled") {
      // Consumer surface is intentionally public; ops stays denied (no auth
      // provider can gate it, so it must never be exposed by this switch).
      return isOpsRoute(req) ? opsDenied() : NextResponse.next();
    }
    // Fully unconfigured: the health endpoint stays reachable so the
    // misconfiguration is diagnosable; everything else fails closed.
    return isHealthRoute(req) ? NextResponse.next() : accessNotConfigured();
  } catch (err) {
    // A throw here previously surfaced as Vercel's opaque
    // MIDDLEWARE_INVOCATION_FAILED with no way to tell WHICH failure it was.
    // "We failed" must never be indistinguishable from anything else
    // (CLAUDE.md), so say what broke.
    //
    // FAIL CLOSED, not open: this returns an error, never `NextResponse.next()`.
    // A catch that let the request through would turn a crash into a silent
    // bypass of the gate — the worst possible reading of this block.
    const detail = err instanceof Error ? err.message : String(err);
    console.error("[middleware] threw; failing closed:", err);
    return new NextResponse(
      "OneLive middleware failed while deciding access, so this request is " +
        "refused rather than allowed. Resolved auth mode: " +
        `${_mode}. Error: ${detail}\n` +
        "Open /api/health (deliberately NOT routed through middleware) for the " +
        "resolved configuration. Contract: docs/DEPLOY.md.",
      { status: 500, headers: { "content-type": "text/plain; charset=utf-8" } },
    );
  }
}

export const config = {
  // Run on everything except Next internals and files with an extension (static
  // assets), plus API routes — BUT NEVER `/api/health`.
  //
  // `/api/health` is deliberately EXCLUDED from middleware. Its entire purpose is
  // to stay reachable and truthful when a deployment is broken, and routing it
  // through middleware meant a middleware fault took it down too: on 2026-07-26
  // the whole site answered HTTP 500 MIDDLEWARE_INVOCATION_FAILED and the one
  // endpoint that could have explained why was 500 as well. A diagnostic that
  // dies with the thing it diagnoses is not a diagnostic.
  //
  // Nothing is opened by this: the route itself returns only resolved config and
  // never a secret value (see app/api/health/route.ts), and it was already listed
  // as public in every mode including the fail-closed one.
  //
  // THE `$` IS LOAD-BEARING. Without it the lookahead excluded any path merely
  // BEGINNING `api/health`, so a future `/api/healthz`, `/api/health-admin` or
  // `/api/health/reset` would have skipped this middleware entirely and served with
  // no auth check at all — an auth fail-open reachable by naming a route. Two
  // independent reviewer seats caught it on PR #80 (`CLASS:auth-prefix-exemption`
  // and `CLASS:auth-bypass-overwide-matcher-exclusion`), and they were right that
  // the diff added segment-boundary tests to `lib/route_match.ts` while leaving the
  // middleware's OWN exemption without the same invariant. Exactly one path is
  // exempt, and it is spelled out. Negative cases: middleware.test.ts.
  // ONE pattern, because a second entry cannot express "api except health":
  // `"/api/(?!health)(.*)"` is not a valid Next middleware matcher and FAILED THE
  // BUILD when tried (deployment 2fMJR3Q, 2026-07-26). The single catch-all below
  // already covers extensionless routes including `/api/*` and `/trpc/*`, and the
  // negative lookahead is where the exclusions belong.
  matcher: [
    "/((?!_next|api/health$|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
