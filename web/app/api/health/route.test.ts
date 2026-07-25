import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { GET } from "./route";

const KEYS = [
  "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_AUTH_DISABLED",
  "AUTH_DISABLED",
  "VERCEL_ENV",
  "SUPABASE_URL",
  "SUPABASE_ANON_KEY",
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
];

describe("/api/health — resolved config is observable, never guessed", () => {
  const saved: Record<string, string | undefined> = {};
  beforeEach(() => { for (const k of KEYS) { saved[k] = process.env[k]; delete process.env[k]; } });
  afterEach(() => {
    for (const k of KEYS) { if (saved[k] === undefined) delete process.env[k]; else process.env[k] = saved[k]; }
    vi.restoreAllMocks();
  });

  it("with no auth config -> not-ok + unconfigured; supabase uses the built-in default (never leaks a value)", async () => {
    // Supabase reads a committed PUBLIC default, so it's always "configured";
    // stub fetch so the probe doesn't hit the network in a unit test.
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, headers: new Headers({ "content-range": "0-0/805" }), text: async () => "",
    }) as unknown as Response));
    const res = await GET();
    const b = await res.json();
    expect(b.ok).toBe(false); // auth is still unconfigured -> not ok
    expect(b.auth.mode).toBe("unconfigured");
    expect(b.supabase.configured).toBe(true);
    expect(b.supabase.source).toBe("built-in-default");
    expect(JSON.stringify(b)).not.toContain("sb_publishable"); // no value, only the source name
  });

  it("names which flag opened the gate (name only) and which var supplied the URL", async () => {
    process.env.NEXT_PUBLIC_AUTH_DISABLED = "1";
    process.env.SUPABASE_URL = "https://example.supabase.co";
    process.env.SUPABASE_ANON_KEY = "sb_publishable_secret";
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, headers: new Headers({ "content-range": "0-0/755" }), text: async () => "",
    }) as unknown as Response));

    const res = await GET();
    const b = await res.json();
    expect(b.auth.mode).toBe("disabled");
    expect(b.auth.disabledBy).toBe("NEXT_PUBLIC_AUTH_DISABLED");
    expect(b.supabase.source).toBe("SUPABASE_URL");
    expect(b.supabase.reachable).toBe(true);
    expect(b.supabase.eventCount).toBe(755);
    expect(b.ok).toBe(true);
    expect(res.status).toBe(200);
    expect(JSON.stringify(b)).not.toContain("sb_publishable_secret"); // still no value
  });

  it("surfaces a DB reachability failure instead of hiding it", async () => {
    process.env.AUTH_DISABLED = "1";
    process.env.SUPABASE_URL = "https://example.supabase.co";
    process.env.SUPABASE_ANON_KEY = "k";
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, status: 401, text: async () => "no" }) as unknown as Response));

    const b = await (await GET()).json();
    expect(b.supabase.reachable).toBe(false);
    expect(b.supabase.error).toContain("401");
    expect(b.ok).toBe(false);
  });
});
