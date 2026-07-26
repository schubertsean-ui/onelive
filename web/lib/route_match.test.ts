import { describe, expect, it } from "vitest";
import { createRouteMatcher, RouteMatcherError } from "./route_match";

// The matcher exists so `middleware.ts` need not import the auth provider on
// deployments that do not use it. That import — and the `clerkMiddleware()` call
// at module scope — made every non-Clerk deployment return HTTP 500
// MIDDLEWARE_INVOCATION_FAILED on Vercel's Edge runtime, including /api/health,
// the one endpoint whose job is to stay diagnosable. See middleware.ts's header.

const req = (pathname: string) => ({ nextUrl: { pathname } });

describe("createRouteMatcher", () => {
  it("matches an exact path and nothing longer", () => {
    const match = createRouteMatcher(["/access"]);
    expect(match(req("/access"))).toBe(true);
    expect(match(req("/access/nested"))).toBe(false);
    expect(match(req("/accessible"))).toBe(false);
    expect(match(req("/"))).toBe(false);
  });

  it("matches a prefix wildcard including the bare prefix", () => {
    const match = createRouteMatcher(["/sign-in(.*)"]);
    expect(match(req("/sign-in"))).toBe(true);
    expect(match(req("/sign-in/factor-one"))).toBe(true);
    expect(match(req("/sign-out"))).toBe(false);
  });

  it("matches any pattern in the set", () => {
    const match = createRouteMatcher(["/access", "/sign-in(.*)", "/api/health"]);
    for (const path of ["/access", "/sign-in/x", "/api/health"]) {
      expect(match(req(path))).toBe(true);
    }
    expect(match(req("/tonight"))).toBe(false);
  });

  it("guards the ops surface exactly as middleware relies on", () => {
    // A miss here would expose /ops on a deployment with no auth provider.
    const isOps = createRouteMatcher(["/ops(.*)"]);
    expect(isOps(req("/ops"))).toBe(true);
    expect(isOps(req("/ops/inbox"))).toBe(true);
    expect(isOps(req("/ops/candidate/abc-123"))).toBe(true);
    expect(isOps(req("/tonight"))).toBe(false);
    expect(isOps(req("/"))).toBe(false);
  });

  it("throws on an empty pattern set rather than matching nothing", () => {
    // Every caller uses the answer for an access decision, so "no patterns" is
    // a programming error, not a permissive default.
    expect(() => createRouteMatcher([])).toThrow(RouteMatcherError);
  });

  it("throws on a pattern shape it does not support", () => {
    // Silently never matching is how an ops surface gets exposed.
    for (const bad of ["/ops(.*)/x", "^/ops", "/ops/[id]", "(.*)"]) {
      expect(() => createRouteMatcher([bad])).toThrow(RouteMatcherError);
    }
  });
});

describe("middleware's provider independence", () => {
  it("does not import the auth provider at module scope", async () => {
    // The regression that produced HTTP 500 on every preview. A top-level
    // `import ... from "@clerk/nextjs/server"` means the module is EVALUATED on
    // every deployment, including those with no Clerk keys.
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../middleware.ts", import.meta.url),
      "utf-8",
    );
    const topLevelClerkImport =
      /^\s*import\s[^;]*from\s+["']@clerk\/nextjs/m.test(src);
    expect(topLevelClerkImport).toBe(false);
    // ...and it must still be reachable lazily, or the stealth gate is broken.
    expect(src).toContain('await import("@clerk/nextjs/server")');
  });

  it("does not construct the Clerk gate at module scope", async () => {
    const fs = await import("node:fs/promises");
    const src = await fs.readFile(
      new URL("../middleware.ts", import.meta.url),
      "utf-8",
    );
    // `const gate = clerkMiddleware(...)` at the top level was the exact shape
    // that ran on every deployment regardless of mode.
    expect(/^\s*const\s+\w+\s*=\s*clerkMiddleware\(/m.test(src)).toBe(false);
  });
});
