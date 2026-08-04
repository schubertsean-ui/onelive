import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { authMode, authProviderActive, consumerSurfacePublic } from "./auth";

const KEYS = [
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_AUTH_DISABLED",
  "AUTH_DISABLED",
  "VERCEL_ENV",
  "ONELIVE_CONSUMER_PUBLIC",
  "NEXT_PUBLIC_ONELIVE_CONSUMER_PUBLIC",
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

  // NO production fail-open: a present Clerk provider is NEVER overridden by a
  // disable flag, so NEXT_PUBLIC_AUTH_DISABLED cannot flip a configured
  // production deployment to public (adversarial-review #102).
  it("a present Clerk key beats a disable flag in production -> clerk (no fail-open)", () => {
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.VERCEL_ENV = "production";
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "1";
    expect(authMode()).toBe("clerk");
    expect(authProviderActive()).toBe(true);
  });

  // The disable flag is honored only where there is NO provider to override — a
  // deliberate public deploy (go-live / no-provider), still an explicit choice.
  it("an explicit disable with no provider (non-preview) -> disabled", () => {
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

// ── consumerSurfacePublic — the ops door on a public deploy ──────────────────
// The declaration is honored ONLY with a real provider configured: it exempts
// consumer routes from the sign-in wall while /ops keeps the full stealth
// gate. Every fail-closed edge is pinned here because middleware trusts this
// function as its single decision point.
describe("consumerSurfacePublic — declared public consumer + gated ops", () => {
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

  it("Clerk key + declaration (production) -> public consumer, clerk mode intact", () => {
    process.env.VERCEL_ENV = "production";
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.ONELIVE_CONSUMER_PUBLIC = "1";
    expect(authMode()).toBe("clerk");
    expect(consumerSurfacePublic()).toBe(true);
    delete process.env.ONELIVE_CONSUMER_PUBLIC;
    process.env.NEXT_PUBLIC_ONELIVE_CONSUMER_PUBLIC = "true";
    expect(consumerSurfacePublic()).toBe(true); // either env form works
  });

  it("the declaration ALONE opens nothing — no provider means the flag is inert", () => {
    process.env.VERCEL_ENV = "production";
    process.env.ONELIVE_CONSUMER_PUBLIC = "1";
    expect(authMode()).toBe("unconfigured"); // still fail-closed
    expect(consumerSurfacePublic()).toBe(false);
  });

  it("declaration + disable flag (no provider) stays plain 'disabled' — ops keeps its 404, no ops door appears", () => {
    process.env.VERCEL_ENV = "production";
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "1";
    process.env.ONELIVE_CONSUMER_PUBLIC = "1";
    expect(authMode()).toBe("disabled");
    expect(consumerSurfacePublic()).toBe(false); // not clerk mode -> never true
  });

  it("Clerk key WITHOUT the declaration -> today's gate-everything behavior", () => {
    process.env.VERCEL_ENV = "production";
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    expect(authMode()).toBe("clerk");
    expect(consumerSurfacePublic()).toBe(false);
  });

  it("a preview never runs the clerk gate, so the declaration is false there too", () => {
    process.env.VERCEL_ENV = "preview";
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.ONELIVE_CONSUMER_PUBLIC = "1";
    expect(authMode()).toBe("disabled");
    expect(consumerSurfacePublic()).toBe(false);
  });

  it("a falsey declaration value does not declare anything", () => {
    process.env.VERCEL_ENV = "production";
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = "pk_test_x";
    process.env.ONELIVE_CONSUMER_PUBLIC = "0";
    expect(consumerSurfacePublic()).toBe(false);
  });
});
