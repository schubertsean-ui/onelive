// EXECUTABLE tests of the access decisions middleware.ts actually makes.
//
// The middleware rewrite (stop importing Clerk at module scope, which 500'd every
// non-Clerk deployment) touched the auth boundary in six places and shipped with
// only STATIC tests — route-pattern units plus a grep for an absent import.
// `CLASS:missing-auth-behavior-tests`, PR #80: a check that a file lacks a string
// proves nothing about what the file DECIDES, and auth is an invariant.
//
// `middleware.ts` resolves `authMode()` once at module load, deliberately, so each
// mode needs a fresh module — hence `vi.resetModules()` and a dynamic `import()`
// per case, with the environment set BEFORE the import.
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
      // Evaluator PR #59: declaring the consumer feed public must never publish
      // the admin surface, and an ungated /ops is what must not follow from it.
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
    // The endpoint reporting why a deployment is broken must not be taken down by
    // the deployment being broken — the exemption that failed on 2026-07-26.
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
    // Both halves at once: the provider is reachable when the mode needs it (else
    // the gate is silently dead), and not imported until a request arrives (else
    // every non-Clerk deployment 500s).
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
    // the FIRST request, so later requests were judged against a stale URL.
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
    // /access and Clerk's own routes must be reachable, or a signed-out user can
    // never reach a page from which to act.
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
    // The worst reading of a catch on an auth path is "let it through": a crash
    // would become a silent bypass of the whole gate.
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
    expect(body).toContain("Resolved auth mode: clerk");
  });

  it("does NOT leak the exception text to the client", async () => {
    // `CLASS:internal-error-disclosure` (PR #76 r4). This assertion previously ran
    // the other way — it required the body to CONTAIN "boom from the provider" —
    // so the test was pinning the leak in place. A test can enforce a defect as
    // firmly as it enforces a fix, and this is what that looks like: written to
    // prove the catch block said something useful, it made raw provider text at a
    // public auth boundary a contract.
    //
    // The detail belongs in the log, which the operator reads and an anonymous
    // requester does not. Asserted as ABSENCE from the body, with the presence of
    // the useful parts asserted above so this cannot be satisfied by an empty
    // response.
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    vi.doMock("@clerk/nextjs/server", () => ({
      clerkMiddleware: () => { throw new Error("boom from the provider"); },
      clerkClient: async () => ({ users: { getUser: async () => ({}) } }),
    }));

    const middleware = await loadMiddleware();
    const res = await middleware(request("/tonight"));
    expect(res?.status).toBe(500);
    const body = await res!.text();
    expect(body).not.toContain("boom from the provider");
    // Still distinguishable from a normal deny — "we failed" must never look
    // identical to "you may not" (CLAUDE.md's founding anti-pattern).
    expect(body).toContain("refused rather than allowed");
    expect(body).toContain("server logs");
  });
});

describe("the matcher excludes /api/health and nothing it should not", () => {
  it("is a single pattern that skips health and Next internals", async () => {
    // `"/api/(?!health)(.*)"` is not a valid Next matcher and FAILED THE BUILD
    // (deployment 2fMJR3Q); the count keeps it from being "improved" back.
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

  it("exempts ONLY /api/health, never a path that merely starts with it", async () => {
    // An auth fail-open reachable by naming a route. The lookahead was a PREFIX
    // test, so `/api/healthz` and `/api/health-admin` skipped this middleware —
    // MEASURED against a real `next start` build in fail-closed mode, where they
    // were served by Next's 404 handler with no auth check at all. Two seats, #80.
    const mod = await import("./middleware");
    const pattern = new RegExp(`^${mod.config.matcher[0]}$`);
    for (const path of [
      "/api/healthz",
      "/api/health-admin",
      "/api/health/reset",
      "/api/health/admin",
      "/api/healthcheck",
    ]) {
      expect(pattern.test(path)).toBe(true);   // true = middleware DOES run
    }
    // ...and the one genuinely exempt path stays exempt, or /api/health dies with
    // the deployment it is supposed to diagnose.
    expect(pattern.test("/api/health")).toBe(false);
  });

  it("denies a health look-alike at RUNTIME, not just in the pattern", async () => {
    // The pattern test above proves middleware is invoked; this proves what it
    // then decides. Unconfigured mode = deny everything except /api/health.
    const middleware = await loadMiddleware();
    for (const path of ["/api/healthz", "/api/health-admin", "/api/health/reset"]) {
      const res = await middleware(request(path));
      expect(res?.status).toBe(503);
    }
  });
});
