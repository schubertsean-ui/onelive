import { describe, it, expect } from "vitest";
import { domainLabel, normalizePack, PACK_KIND_ALIAS, resolveDomain } from "./domains";

// resolveDomain is the alias. feed.normalizeDomain must call it.
void PACK_KIND_ALIAS;

describe("pack kind words print as feed chips", () => {
  it("music is Live Music, not Other", () => {
    expect(resolveDomain("music")).toBe("live-music");
    expect(domainLabel("music")).toBe("Live Music");
    expect(domainLabel("Music")).toBe("Live Music");
  });

  it("live-music stays Live Music", () => {
    expect(resolveDomain("live-music")).toBe("live-music");
    expect(domainLabel("live-music")).toBe("Live Music");
  });

  it("other pack words land on real chips", () => {
    expect(domainLabel("art")).toBe("Visual Arts & Museums");
    expect(domainLabel("sport")).toBe("Sports & Spectacle");
    expect(domainLabel("food")).toBe("Food & Drink");
    expect(domainLabel("civic")).toBe("Community & Block Parties");
    expect(domainLabel("class")).toBe("Lectures · Debates · Ideas");
    expect(domainLabel("market")).toBe("Fairs · Expos · Cons");
    expect(domainLabel("outdoors")).toBe("Wellness & Outdoor");
  });

  it("unknown stays Other", () => {
    expect(domainLabel("not-a-kind")).toBe("Other");
    expect(domainLabel(null)).toBe("Other");
  });
});
