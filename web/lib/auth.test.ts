import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { authMode, authProviderActive } from "./auth";

const KEYS = [
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "CLERK_SECRET_KEY",
  "NEXT_PUBLIC_AUTH_DISABLED",
  "AUTH_DISABLED",
  "VERCEL_ENV",
];

describe("authMode — the fail-closed gate resolver", () => {
  const saved: Record<string, string | undefined> = {};
  beforeEach(() => {
    for (const k of KEYS) {
      saved[k] = process.env[k];
      delete process.env[k];
    }
  });
  afterEach(() => {
    for (const k of KEYS) {
      if (saved[k] === undefined) delete process.env[k];
      else process.env[k] = saved[k];
    }
  });

  it("BOTH Clerk keys -> clerk (even in production)", () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.CLERK_SECRET_KEY = "sk_test_x";
    process.env.VERCEL_ENV = "production";
    expect(authMode()).toBe("clerk");
    expect(authProviderActive()).toBe(true);
  });

  it("publishable key WITHOUT the secret key never claims clerk mode", () => {
    // THE 500. clerkMiddleware/auth/clerkClient are server calls needing
    // CLERK_SECRET_KEY; selecting 'clerk' on the publishable key alone made the
    // middleware THROW (500 MIDDLEWARE_INVOCATION_FAILED) on every route
    // instead of failing closed with a diagnosable 503.
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.VERCEL_ENV = "production";
    expect(authMode()).toBe("unconfigured");   // production refuses, never opens
    expect(authProviderActive()).toBe(false);
  });

  it("a half-configured PREVIEW falls through to host-protected disabled", () => {
    // The preview keeps working instead of 500-ing, which is the whole point:
    // a half-set-up preview is fenced by Vercel Deployment Protection.
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.VERCEL_ENV = "preview";
    expect(authMode()).toBe("disabled");
  });

  it("the secret key ALONE is not a configured gate either", () => {
    process.env.CLERK_SECRET_KEY = "sk_test_x";
    process.env.VERCEL_ENV = "production";
    expect(authMode()).toBe("unconfigured");
  });

  it("explicit disable (either name, any truthy) -> disabled", () => {
    process.env.AUTH_DISABLED = "1";
    expect(authMode()).toBe("disabled");
    delete process.env.AUTH_DISABLED;
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "true";
    expect(authMode()).toBe("disabled");
  });

  it("a non-production Vercel deployment auto-opens (zero-config preview)", () => {
    process.env.VERCEL_ENV = "preview";
    expect(authMode()).toBe("disabled");
    process.env.VERCEL_ENV = "development";
    expect(authMode()).toBe("disabled");
  });

  it("PRODUCTION never auto-opens — no provider, no flag -> unconfigured (fail closed)", () => {
    process.env.VERCEL_ENV = "production";
    expect(authMode()).toBe("unconfigured");
    expect(authProviderActive()).toBe(false);
  });

  it("nothing configured at all -> unconfigured (fail closed)", () => {
    expect(authMode()).toBe("unconfigured");
  });

  it("a falsey disable value does not open the gate", () => {
    process.env.VERCEL_ENV = "production";
    process.env.AUTH_DISABLED = "0";
    expect(authMode()).toBe("unconfigured");
  });

  it("a whitespace-only secret key is NOT a configured provider", () => {
    // r12 fail-open-on-custody-misconfig: " " is truthy, so this selected
    // 'clerk' mode and drove the middleware into the exact runtime failure the
    // two-key rule exists to prevent. Blank-after-trim must read as absent.
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.CLERK_SECRET_KEY = "   ";
    expect(authMode()).toBe("unconfigured");
    process.env.CLERK_SECRET_KEY = "sk_test_x";
    expect(authMode()).toBe("clerk");
    // and a blank publishable key is equally not a configuration
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = " ";
    expect(authMode()).toBe("unconfigured");
  });
});
