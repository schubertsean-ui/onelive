import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { authMode, authProviderActive } from "./auth";

const KEYS = [
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
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

  it("a configured Clerk key -> clerk (even in production)", () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.VERCEL_ENV = "production";
    expect(authMode()).toBe("clerk");
    expect(authProviderActive()).toBe(true);
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

  // The preview-500 regression: a preview that INHERITED the project's Clerk
  // publishable key must still resolve to 'disabled', never 'clerk' — running
  // the Clerk gate on a preview URL throws MIDDLEWARE_INVOCATION_FAILED (500).
  it("a preview with the Clerk key present still -> disabled (no 500)", () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.VERCEL_ENV = "preview";
    expect(authMode()).toBe("disabled");
    expect(authProviderActive()).toBe(false); // ClerkProvider is NOT rendered
  });

  // The documented escape hatch must work even with a Clerk key present.
  it("an explicit disable flag beats a present Clerk key -> disabled", () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.VERCEL_ENV = "production";
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "1";
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
});
