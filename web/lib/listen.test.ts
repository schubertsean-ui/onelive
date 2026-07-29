import { describe, it, expect } from "vitest";
import { listenLinks } from "./listen";

describe("listenLinks — search the act on the major services (music player, A)", () => {
  it("builds Spotify / Apple Music / YouTube search links from the name", () => {
    const links = listenLinks("Sister Neon");
    expect(links.map((l) => l.service)).toEqual(["Spotify", "Apple Music", "YouTube"]);
    expect(links[0].url).toBe("https://open.spotify.com/search/Sister%20Neon");
    expect(links[1].url).toBe("https://music.apple.com/us/search?term=Sister%20Neon");
    expect(links[2].url).toBe("https://www.youtube.com/results?search_query=Sister%20Neon");
  });

  it("encodes special characters in the artist name", () => {
    const links = listenLinks("Café Tacvba & Friends");
    for (const l of links) {
      expect(l.url).toContain(encodeURIComponent("Café Tacvba & Friends"));
      expect(l.url.startsWith("https://")).toBe(true);
    }
  });

  it("returns nothing for an empty/blank/absent name (never a dead link)", () => {
    expect(listenLinks("")).toEqual([]);
    expect(listenLinks("   ")).toEqual([]);
    expect(listenLinks(null)).toEqual([]);
    expect(listenLinks(undefined)).toEqual([]);
  });
});
