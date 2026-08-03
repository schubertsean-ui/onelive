import { describe, it, expect } from "vitest";
import {
  DEFAULT_FILTERS,
  filtersToQuery,
  queryToFilters,
  isDefaultFilters,
  lensHistoryState,
  isLensHistoryState,
  externalHost,
  externalAriaLabel,
  handoffCaption,
} from "./nav";

describe("filters ⇄ URL (nav canon §6 — every meaningful view is a URL)", () => {
  it("default state produces the bare, canonical URL (no query noise)", () => {
    expect(filtersToQuery(DEFAULT_FILTERS)).toBe("");
    expect(isDefaultFilters(DEFAULT_FILTERS)).toBe(true);
  });

  it("round-trips a full filter state through the query string", () => {
    const state = {
      tabKey: "today",
      domains: new Set(["live-music", "comedy"]),
      areas: new Set(["East Austin"]),
      genres: new Set(["rock"]),
      freeOnly: true,
    };
    const q = filtersToQuery(state);
    const back = queryToFilters(q);
    expect(back.tabKey).toBe("today");
    expect([...back.domains].sort()).toEqual(["comedy", "live-music"]);
    expect([...back.areas]).toEqual(["East Austin"]);
    expect([...back.genres]).toEqual(["rock"]);
    expect(back.freeOnly).toBe(true);
  });

  it("is deterministic regardless of set insertion order (shareable = stable)", () => {
    const a = filtersToQuery({ ...DEFAULT_FILTERS, domains: new Set(["b", "a"]) });
    const b = filtersToQuery({ ...DEFAULT_FILTERS, domains: new Set(["a", "b"]) });
    expect(a).toBe(b);
  });

  it("degrades a malformed/unknown query to the honest full feed, never a crash", () => {
    for (const bad of ["?domain=,,&free=maybe&junk=1", "?when=", "%%%", ""]) {
      const f = queryToFilters(bad);
      expect(f.freeOnly).toBe(false);
      expect(f.domains.size).toBe(0);
    }
  });
});

describe("history-modeled lens (§6/§7 — Back closes the sheet before leaving)", () => {
  it("marks and recognizes its own history entries, nothing else's", () => {
    const s = lensHistoryState("qa-4", "artist");
    expect(isLensHistoryState(s)).toBe(true);
    expect(s.id).toBe("qa-4");
    expect(isLensHistoryState(null)).toBe(false);
    expect(isLensHistoryState({})).toBe(false);
    expect(isLensHistoryState({ id: "x" })).toBe(false);
    // Next.js writes its own history state objects — they must never read as a lens.
    expect(isLensHistoryState({ __NA: true, key: "abc" })).toBe(false);
  });
});

describe("external links by intent (§8 — labeled, honest handoffs)", () => {
  it("extracts a human host, dropping www", () => {
    expect(externalHost("https://www.ticketmaster.com/e/123?x=1")).toBe("ticketmaster.com");
    expect(externalHost("https://tickets.example.com/qa-1")).toBe("tickets.example.com");
  });

  it("never fabricates a host from an unparseable URL — generic label instead", () => {
    expect(externalHost("not a url")).toBeNull();
    expect(externalHost(null)).toBeNull();
    expect(externalAriaLabel("Tickets", "not a url")).toBe("Tickets — external link");
    expect(handoffCaption("not a url")).toBeNull();
  });

  it("announces the destination to screen readers (an unannounced context change is a defect)", () => {
    expect(externalAriaLabel("Get tickets", "https://www.ticketmaster.com/e/1"))
      .toBe("Get tickets — external link, opens ticketmaster.com");
  });

  it("captions the terminal handoff with where it finishes", () => {
    expect(handoffCaption("https://www.ticketmaster.com/e/1")).toBe("finishes on ticketmaster.com");
  });
});
