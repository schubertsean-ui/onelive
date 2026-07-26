// EXECUTABLE tests of the access decisions middleware.ts actually makes.
//
// WHY THIS FILE EXISTS. The middleware was rewritten on 2026-07-26 to stop
// importing Clerk at module scope (that import returned HTTP 500 on every
// non-Clerk deployment, including `/api/health`). The change touched the auth
// boundary in six places — clerk-mode dispatch, disabled-mode `/ops` denial,
// the unconfigured fail-closed path, the health exemption, the catch block, and
// the matcher — and shipped with only STATIC tests: route-pattern unit tests plus
// a grep asserting no top-level Clerk import. The openai/absence-only seat blocked
// it on PR #80 as `CLASS:missing-auth-behavior-tests`, correctly: a static check
// that a file does not contain a string proves nothing about what the file
// decides. Auth is an invariant, so it needs tests that run the code.
//
// The load-bearing constraint on how these are written: `middleware.ts` resolves
// `authMode()` ONCE at module load, deliberately (env is fixed for a deployment's
// lifetime). So each mode needs a fresh module instance — hence `vi.resetModules()`
// and a dynamic `import()` per case, with the environment set BEFORE the import.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const AUTH_KEYS = [
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_AUTH_DISABLED",
  "AUTH_DISABLED",
  "VERCEL_ENV",
  "ONELIVE_ALLOWLIST",
];

const saved: Record<string, string | undefined> = {};

beforeEach(() => {
  for (const key of AUTH_KEYS) {
    saved[key] = process.env[key];
    delete process.env[key];
  }
  vi.resetModules();
});

afterEach(() => {
  for (const key of AUTH_KEYS) {
    if (saved[key] === undefined) delete process.env[key];
    else process.env[key] = saved[key];
  }
  vi.restoreAllMocks();
  vi.resetModules();
  vi.doUnmock("@clerk/nextjs/server");
});

/** A NextRequest-shaped stub: middleware reads only `nextUrl` and `url`. */
function request(pathname: string) {
  const url = new URL(`https://onelive.test${pathname}`);
  return {
    url: url.toString(),
    nextUrl: {
      pathname,
      clone: () => new URL(url.toString()),
    },
  } as unknown as import("next/server").NextRequest;
}

/** Load a FRESH middleware module against the env currently in place. */
async function loadMiddleware() {
  const mod = await import("./middleware");
  return mod.default;
}

describe("disabled mode — the consumer surface is public, ops is not", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "1";
  });

  it.each(["/", "/tonight", "/access", "/api/anything", "/artist/foo"])(
    "lets %s through",
    async (path) => {
      const middleware = await loadMiddleware();
      const res = await middleware(request(path));
      // NextResponse.next() carries no error status.
      expect(res?.status).not.toBe(404);
      expect(res?.status).not.toBe(503);
      expect(res?.status).not.toBe(500);
    },
  );

  it.each(["/ops", "/ops/inbox", "/ops/candidate/abc-123"])(
    "DENIES %s with a 404, because no provider can gate it",
    async (path) => {
      // The invariant from evaluator PR #59: declaring the consumer feed public
      // must never publish the admin surface. `disabled` means "no app-level
      // gate", and an ungated /ops is the one thing that must not follow from it.
      const middleware = await loadMiddleware();
      const res = await middleware(request(path));
      expect(res?.status).toBe(404);
      await expect(res?.text()).resolves.toContain("Not found");
    },
  );

  it("does not leak that /ops exists — the denial is 404, never 401 or 403", async () => {
    const middleware = await loadMiddleware();
    const res = await middleware(request("/ops"));
    expect([401, 403]).not.toContain(res?.status);
  });
});

describe("unconfigured mode — fail closed, but stay diagnosable", () => {
  // No provider, no declared disable, not a Vercel preview. This is the state a
  // production deployment lands in if its config is stripped, and the rule is
  // that missing configuration must NEVER become a public passthrough.

  it.each(["/", "/tonight", "/ops", "/api/feed", "/access"])(
    "refuses %s with 503 rather than serving it",
    async (path) => {
      const middleware = await loadMiddleware();
      const res = await middleware(request(path));
      expect(res?.status).toBe(503);
    },
  );

  it("explains how to fix it and points at the contract", async () => {
    // "We failed" must never be indistinguishable from anything else.
    const middleware = await loadMiddleware();
    const res = await middleware(request("/"));
    const body = await res!.text();
    expect(body).toContain("no access gate is configured");
    expect(body).toContain("NEXT_PUBLIC_AUTH_DISABLED=1");
    expect(body).toContain("docs/DEPLOY.md");
  });

  it("keeps /api/health reachable so the misconfiguration can be READ", async () => {
    // The endpoint that reports why the deployment is broken must not be taken
    // down by the deployment being broken. This is the exemption that failed on
    // 2026-07-26 and cost the session hours of guessing.
    const middleware = await loadMiddleware();
    const res = await middleware(request("/api/health"));
    expect(res?.status).not.toBe(503);
  });
});

describe("clerk mode — the gate runs, and only the gate decides", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
  });

  it("dispatches to the Clerk gate, loading the provider LAZILY", async () => {
    // Proves both halves of the fix at once: the provider is reachable when the
    // mode needs it (otherwise the stealth gate is silently dead), and it was not
    // imported until a request arrived (otherwise every non-Clerk deployment 500s).
    let constructedAt: "module-load" | "first-request" = "module-load";
    let calls = 0;
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: (handler: unknown) => {
        constructedAt = "first-request";
        return async (req: unknown) => {
          calls += 1;
          return (handler as (a: unknown, r: unknown) => Promise<Response>)(
            async () => ({ userId: null, sessionClaims: null,
                            redirectToSignIn: () => new Response(null, { status: 307 }) }),
            req,
          );
        };
      },
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));

    const middleware = await loadMiddleware();
    // Module is loaded; nothing has constructed the gate yet.
    expect(constructedAt).toBe("module-load");
    await middleware(request("/tonight"));
    expect(constructedAt).toBe("first-request");
    expect(calls).toBe(1);
  });

  it("memoises the gate but decides on EACH request's own path", async () => {
    // The closure bug caught during the rewrite: the memoised handler referenced
    // the FIRST request's object, so every later request was judged against a
    // stale URL. A gate that answers about the wrong path is worse than no gate.
    const seen: string[] = [];
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: (handler: unknown) => async (req: unknown) => {
        seen.push((req as { nextUrl: { pathname: string } }).nextUrl.pathname);
        return (handler as (a: unknown, r: unknown) => Promise<Response>)(
          async () => ({ userId: "user_1", sessionClaims: { email: "a@b.c" },
                          redirectToSignIn: () => new Response(null, { status: 307 }) }),
          req,
        );
      },
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));
    process.env.ONELIVE_ALLOWLIST = "a@b.c";

    const middleware = await loadMiddleware();
    await middleware(request("/tonight"));
    await middleware(request("/ops/inbox"));
    expect(seen).toEqual(["/tonight", "/ops/inbox"]);
  });

  it("sends a non-allowlisted signed-in user to /access, never through", async () => {
    // The per-user fail-closed: an empty or non-matching allowlist matches nobody.
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: (handler: unknown) => async (req: unknown) =>
        (handler as (a: unknown, r: unknown) => Promise<Response>)(
          async () => ({ userId: "user_1",
                          sessionClaims: { email: "stranger@example.com" },
                          redirectToSignIn: () => new Response(null, { status: 307 }) }),
          req,
        ),
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));
    process.env.ONELIVE_ALLOWLIST = "friend@example.com";

    const middleware = await loadMiddleware();
    const res = await middleware(request("/tonight"));
    expect(res?.status).toBe(307);
    expect(res?.headers.get("location")).toContain("/access");
  });

  it("redirects a signed-OUT user to sign-in rather than serving the page", async () => {
    let redirected = false;
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: (handler: unknown) => async (req: unknown) =>
        (handler as (a: unknown, r: unknown) => Promise<Response>)(
          async () => ({
            userId: null, sessionClaims: null,
            redirectToSignIn: () => { redirected = true; return new Response(null, { status: 307 }); },
          }),
          req,
        ),
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));

    const middleware = await loadMiddleware();
    await middleware(request("/tonight"));
    expect(redirected).toBe(true);
  });

  it("lets the public routes through WITHOUT consulting the session", async () => {
    // /access and Clerk's own routes must be reachable, or a signed-out or
    // non-allowlisted user can never reach a page from which to act.
    let authCalls = 0;
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: (handler: unknown) => async (req: unknown) =>
        (handler as (a: unknown, r: unknown) => Promise<Response>)(
          async () => { authCalls += 1; return { userId: null, sessionClaims: null,
            redirectToSignIn: () => new Response(null, { status: 307 }) }; },
          req,
        ),
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));

    const middleware = await loadMiddleware();
    for (const path of ["/access", "/sign-in", "/sign-in/factor-one", "/sign-up",
                        "/api/health"]) {
      await middleware(request(path));
    }
    expect(authCalls).toBe(0);
  });
});

describe("the catch block fails CLOSED", () => {
  it("returns 500 — never next() — when the gate itself throws", async () => {
    // The worst possible reading of a catch on an auth path is "let it through".
    // If this ever regresses, a crash becomes a silent bypass of the whole gate.
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: () => { throw new Error("boom from the provider"); },
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));

    const middleware = await loadMiddleware();
    const res = await middleware(request("/tonight"));
    expect(res?.status).toBe(500);
    const body = await res!.text();
    expect(body).toContain("refused rather than allowed");
    expect(body).toContain("boom from the provider");
    expect(body).toContain("Resolved auth mode: clerk");
  });
});

describe("the matcher excludes /api/health and nothing it should not", () => {
  it("is a single pattern that skips health and Next internals", async () => {
    // `"/api/(?!health)(.*)"` is not a valid Next matcher and FAILED THE BUILD
    // (deployment 2fMJR3Q). Asserting the count keeps the fix from being
    // "improved" back into a build break.
    const mod = await import("./middleware");
    expect(mod.config.matcher).toHaveLength(1);
    const pattern = new RegExp(`^${mod.config.matcher[0]}$`);
    expect(pattern.test("/api/health")).toBe(false);
    expect(pattern.test("/_next/static/chunk.js")).toBe(false);
    expect(pattern.test("/favicon.ico")).toBe(false);
    for (const path of ["/", "/tonight", "/ops", "/ops/inbox", "/api/feed"]) {
      expect(pattern.test(path)).toBe(true);
    }
  });
});
