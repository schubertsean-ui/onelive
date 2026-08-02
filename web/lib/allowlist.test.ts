import { describe, it, expect } from "vitest";
import { parseAllowlist, isAllowlisted, allowlistFromEnv } from "./allowlist";

describe("parseAllowlist", () => {
  it("splits, trims, and lowercases entries", () => {
    expect(parseAllowlist(" A@x.com , B@Y.com ")).toEqual(["a@x.com", "b@y.com"]);
  });

  it("drops empty segments", () => {
    expect(parseAllowlist("a@x.com,,  ,b@x.com")).toEqual(["a@x.com", "b@x.com"]);
  });

  it("returns an empty list for null/undefined/empty", () => {
    expect(parseAllowlist(null)).toEqual([]);
    expect(parseAllowlist(undefined)).toEqual([]);
    expect(parseAllowlist("")).toEqual([]);
    expect(parseAllowlist("   ")).toEqual([]);
  });
});

describe("isAllowlisted (fail-closed)", () => {
  const list = parseAllowlist("ops@1live.test, founder@1live.test");

  it("passes an allowlisted email", () => {
    expect(isAllowlisted("ops@1live.test", list)).toBe(true);
  });

  it("matches case-insensitively", () => {
    expect(isAllowlisted("OPS@1Live.TEST", list)).toBe(true);
    expect(isAllowlisted("  Founder@1live.test  ", list)).toBe(true);
  });

  it("fails a non-allowlisted email", () => {
    expect(isAllowlisted("stranger@evil.test", list)).toBe(false);
  });

  it("denies ALL when the allowlist is empty (fail-closed)", () => {
    expect(isAllowlisted("ops@onelive.test", [])).toBe(false);
    expect(isAllowlisted("anyone@anywhere.test", parseAllowlist(""))).toBe(false);
  });

  it("denies a missing email even against a populated allowlist", () => {
    expect(isAllowlisted(null, list)).toBe(false);
    expect(isAllowlisted(undefined, list)).toBe(false);
    expect(isAllowlisted("", list)).toBe(false);
  });
});

describe("allowlistFromEnv", () => {
  it("parses an explicitly passed raw value", () => {
    expect(allowlistFromEnv("a@x.com,b@x.com")).toEqual(["a@x.com", "b@x.com"]);
  });

  it("denies all when the env value is empty", () => {
    expect(isAllowlisted("a@x.com", allowlistFromEnv(""))).toBe(false);
  });
});
