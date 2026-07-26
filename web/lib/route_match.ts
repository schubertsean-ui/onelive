// Path matching for middleware, with NO dependency on the auth provider.
//
// WHY THIS EXISTS. `middleware.ts` used Clerk's `createRouteMatcher` for all
// three of its modes, which meant `@clerk/nextjs/server` was imported — and
// `clerkMiddleware()` constructed — at module scope on EVERY deployment,
// including previews that have no Clerk keys and never run the Clerk gate.
// On Vercel's Edge runtime that produced `MIDDLEWARE_INVOCATION_FAILED`: the
// whole site, including `/api/health`, returned HTTP 500. The bug was invisible
// for as long as Vercel's Deployment Protection sat in front of it, and it
// surfaced the moment the protection bypass was configured (v1 criterion 5).
//
// `lib/auth.ts` describes the stealth gate as "a config-driven OPTIONAL module".
// Optional has to mean the code is not loaded when it is not used, so route
// matching lives here instead — a few lines, no provider, Edge-safe by
// construction.
//
// The patterns accepted are the small subset middleware actually uses:
//   "/access"       exact path
//   "/sign-in(.*)"  prefix, with an explicit trailing wildcard group
// Anything else is rejected loudly at construction rather than silently never
// matching, because a route matcher that quietly matches nothing is how an ops
// surface gets exposed.

export class RouteMatcherError extends Error {}

const _EXACT = /^\/[A-Za-z0-9._~\-/]*$/;
const _PREFIX_WILDCARD = /^(\/[A-Za-z0-9._~\-/]*)\(\.\*\)$/;

/**
 * Build a predicate that reports whether a request's pathname matches any
 * pattern. Mirrors the semantics middleware.ts relied on, and nothing more.
 */
export function createRouteMatcher(
  patterns: string[],
): (req: { nextUrl: { pathname: string } }) => boolean {
  if (patterns.length === 0) {
    // A matcher over no patterns can only ever answer "no". Every caller here
    // uses the answer to make an access decision, so an empty set is a
    // programming error, not a permissive default.
    throw new RouteMatcherError("createRouteMatcher requires at least one pattern");
  }

  const exact: string[] = [];
  const prefixes: string[] = [];
  for (const pattern of patterns) {
    const wildcard = _PREFIX_WILDCARD.exec(pattern);
    if (wildcard) {
      prefixes.push(wildcard[1]);
      continue;
    }
    if (_EXACT.test(pattern)) {
      exact.push(pattern);
      continue;
    }
    throw new RouteMatcherError(
      `unsupported route pattern ${JSON.stringify(pattern)} — this matcher ` +
        `deliberately supports only "/path" and "/path(.*)", so an unexpected ` +
        `pattern fails loudly instead of matching nothing`,
    );
  }

  return (req) => {
    const path = req.nextUrl.pathname;
    if (exact.includes(path)) return true;
    // `prefix + "/"`, not a bare startsWith: a bare prefix test made
    // `/sign-inevil` match `/sign-in(.*)`, which is a PUBLIC route — so an
    // attacker-chosen path became exempt from the gate (PR #80). Over-matching
    // `/ops(.*)` was harmless only because denying more is safe, and a rule that
    // is safe only for some callers is not a rule.
    return prefixes.some(
      (prefix) => path === prefix || path.startsWith(`${prefix}/`),
    );
  };
}
