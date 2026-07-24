import { clerkMiddleware, createRouteMatcher, clerkClient } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import { allowlistFromEnv, isAllowlisted } from "./lib/allowlist";
import { authConfig } from "./lib/auth";

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
]);

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

// The gate is optional and config-driven (lib/auth.ts is the single source of
// truth). When no provider is configured the middleware is a passthrough, so an
// early Supabase-only preview still deploys; the stealth allowlist gate turns on
// the moment a provider (Clerk today) is configured.
const authCfg = authConfig();

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

export default authCfg.enabled
  ? gate
  : function middleware() {
      return NextResponse.next();
    };

export const config = {
  // Run on everything except Next internals and files with an extension (static
  // assets), plus always run for API routes. Mirrors Clerk's recommended matcher.
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
