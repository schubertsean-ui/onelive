// Canonical genre taxonomy — the ratified Layer-1 eighteen (founder 2026-07-29).
// The "today's 8 map losslessly" and "R&B/Soul now has an exact home" claims are
// assertions here, not sentences in a doc.

import { describe, expect, it } from "vitest";
import {
  GENRES,
  TODAY_8_TO_18,
  canonicalGenre,
  isGenreId,
  genreLabel,
} from "./genres";

describe("the canonical 18", () => {
  it("is exactly 18 genres with unique ids", () => {
    expect(GENRES).toHaveLength(18);
    const ids = GENRES.map((g) => g.id);
    expect(new Set(ids).size).toBe(18);
  });

  it("includes the four states today's 8 lacked, incl. the R&B/Soul gap", () => {
    const ids = new Set<string>(GENRES.map((g) => g.id));
    for (const id of ["rnb-soul", "blues", "folk-americana", "punk", "reggae", "classical", "world", "singer-songwriter", "indie-alternative", "pop"]) {
      expect(ids.has(id)).toBe(true);
    }
  });

  it("genreLabel returns the human label", () => {
    expect(genreLabel("rnb-soul")).toBe("R&B/Soul");
    expect(genreLabel("hip-hop")).toBe("Hip-Hop/Rap");
  });
});

describe("today's 8 map losslessly into the 18", () => {
  it("every legacy key resolves to a real canonical id", () => {
    for (const [legacy, canon] of Object.entries(TODAY_8_TO_18)) {
      expect(isGenreId(canon)).toBe(true);
      expect(canonicalGenre(legacy)).toBe(canon);
    }
  });
});

describe("canonicalGenre", () => {
  it("resolves exact canonical labels and ids", () => {
    expect(canonicalGenre("Rock")).toBe("rock");
    expect(canonicalGenre("jazz")).toBe("jazz");
    expect(canonicalGenre("Country")).toBe("country");
  });

  it("gives R&B / Soul an EXACT home (the voice-persona #7 gap)", () => {
    expect(canonicalGenre("R&B")).toBe("rnb-soul");
    expect(canonicalGenre("RnB")).toBe("rnb-soul");
    expect(canonicalGenre("Neo-Soul")).toBe("rnb-soul");
    expect(canonicalGenre("Soul")).toBe("rnb-soul");
    expect(canonicalGenre("Funk")).toBe("rnb-soul");
  });

  it("lets the LONGEST/most-specific keyword win over the broad parent", () => {
    expect(canonicalGenre("Alternative Rock")).toBe("indie-alternative");
    expect(canonicalGenre("Hard Rock")).toBe("rock");
    expect(canonicalGenre("dancehall")).toBe("reggae"); // not electronic's "dance"
    expect(canonicalGenre("Dubstep")).toBe("electronic-dance"); // not reggae's "dub"
    expect(canonicalGenre("Western Swing")).toBe("country"); // not jazz's "swing"
    expect(canonicalGenre("Swing")).toBe("jazz"); // bare swing is jazz
    expect(canonicalGenre("Metalcore")).toBe("metal");
    expect(canonicalGenre("Hardcore")).toBe("punk");
  });

  it("maps the Central-Texas vocabulary explicitly", () => {
    expect(canonicalGenre("Cumbia")).toBe("latin");
    expect(canonicalGenre("Tejano")).toBe("latin");
    expect(canonicalGenre("Conjunto")).toBe("latin");
    expect(canonicalGenre("Honky-tonk")).toBe("country");
    expect(canonicalGenre("Bluegrass")).toBe("folk-americana");
    expect(canonicalGenre("Americana")).toBe("folk-americana");
  });

  it("resolves real provider genre strings", () => {
    expect(canonicalGenre("Hip-Hop")).toBe("hip-hop");
    expect(canonicalGenre("Alternative")).toBe("indie-alternative");
    expect(canonicalGenre("Electronic")).toBe("electronic-dance");
    expect(canonicalGenre("Singer-Songwriter")).toBe("singer-songwriter");
    expect(canonicalGenre("Classical")).toBe("classical");
  });

  it("returns null for the unknown/empty — honest 'Other', never a guess", () => {
    expect(canonicalGenre("Polka")).toBeNull();
    expect(canonicalGenre("")).toBeNull();
    expect(canonicalGenre("   ")).toBeNull();
    expect(canonicalGenre(null)).toBeNull();
    expect(canonicalGenre(undefined)).toBeNull();
  });
});
