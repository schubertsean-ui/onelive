// Canonical music-genre taxonomy — the ratified Layer-1 EIGHTEEN.
//
// Founder-ratified 2026-07-29 ("ratify-and-wire the 18 genres"), from
// docs/strategy/ONE_LIVE_GENRE_TAXONOMY_v1.md. Three-layer design:
//   * LAYER 1 (here): 18 canonical top genres, the working intersection of
//     Apple Music, Spotify's browse layer, and Bandsintown's live tags — the
//     tier every major platform's chooser converges on.
//   * LAYER 2: open curated sub-styles (two-step, house, corridos…) — later,
//     as config; each maps up to a Layer-1 parent.
//   * LAYER 0: the per-market UI rail (8–12 chips by local inventory) — the
//     feed derives it from what's actually present (genreFacet, in feed.ts).
//
// TRUTH-FIRST: extraction/import captures the artist's or venue's OWN words
// (the raw `subsegment`); mapping those words to canon is DETERMINISTIC config
// (canonicalGenre, below) — a lens over the data, never a rewrite of it, and
// never a ranking. An unmatched term returns null: it is "Other" to the user
// and a logged signal for taxonomy growth (the voice-persona H5 loop), never a
// silent guess.

export type GenreId =
  | "rock"
  | "pop"
  | "hip-hop"
  | "rnb-soul"
  | "electronic-dance"
  | "country"
  | "latin"
  | "jazz"
  | "blues"
  | "folk-americana"
  | "metal"
  | "punk"
  | "reggae"
  | "classical"
  | "world"
  | "singer-songwriter"
  | "indie-alternative"
  | "experimental";

export type Genre = { id: GenreId; label: string };

// The canonical 18, in the order the taxonomy doc lists them.
export const GENRES: Genre[] = [
  { id: "rock", label: "Rock" },
  { id: "pop", label: "Pop" },
  { id: "hip-hop", label: "Hip-Hop/Rap" },
  { id: "rnb-soul", label: "R&B/Soul" },
  { id: "electronic-dance", label: "Electronic/Dance" },
  { id: "country", label: "Country" },
  { id: "latin", label: "Latin" },
  { id: "jazz", label: "Jazz" },
  { id: "blues", label: "Blues" },
  { id: "folk-americana", label: "Folk/Americana" },
  { id: "metal", label: "Metal" },
  { id: "punk", label: "Punk" },
  { id: "reggae", label: "Reggae" },
  { id: "classical", label: "Classical" },
  { id: "world", label: "World" },
  { id: "singer-songwriter", label: "Singer-Songwriter" },
  { id: "indie-alternative", label: "Indie/Alternative" },
  { id: "experimental", label: "Experimental" },
];

export const GENRE_LABEL = new Map<GenreId, string>(GENRES.map((g) => [g.id, g.label]));
const GENRE_IDS = new Set<string>(GENRES.map((g) => g.id));

export function isGenreId(v: string): v is GenreId {
  return GENRE_IDS.has(v);
}

export function genreLabel(id: GenreId): string {
  return GENRE_LABEL.get(id) ?? "Other";
}

// Today's flat 8 map LOSSLESSLY into the 18 (no migration pain) — proven in the
// tests. Kept explicit so the "lossless" claim is mechanical, not asserted.
export const TODAY_8_TO_18: Record<string, GenreId> = {
  rock: "rock",
  "hip-hop": "hip-hop",
  jazz: "jazz",
  electronic: "electronic-dance",
  country: "country",
  metal: "metal",
  experimental: "experimental",
  latin: "latin",
};

// ── The synonym lexicon (Layer-1 seed) ───────────────────────────────────────
// Raw provider/venue genre WORDS → canonical id. This is the "closest to R&B"
// problem made mechanical: the vocabulary artists use is far larger than 18, so
// every entry here is a spoken/typed synonym that resolves to a Layer-1 parent.
// Matching is by keyword CONTAINMENT, and the LONGEST matching keyword wins
// (most-specific), so "Alternative Rock" resolves to indie-alternative (not
// rock), "dancehall" to reggae (not electronic's "dance"), and "western swing"
// to country (not jazz's "swing"). A term matched by nothing returns null and
// is recorded for growth. List order only breaks exact-length ties, so the
// specific families are listed before the broad parents.
const LEXICON: Array<[string[], GenreId]> = [
  // R&B / Soul — the gap voice persona #7 exposed; now an exact home.
  [["r&b", "rnb", "r and b", "rhythm and blues", "neo-soul", "neo soul", "soul", "motown", "funk"], "rnb-soul"],
  // Electronic / Dance — before "rock"/others; dance vocabulary is broad.
  [["electronic", "electronica", "edm", "dance", "house", "techno", "trance", "dubstep", "drum & bass", "drum and bass", "dnb", "disco", "dj", "rave"], "electronic-dance"],
  // Hip-Hop / Rap.
  [["hip-hop", "hip hop", "hiphop", "rap", "trap", "drill"], "hip-hop"],
  // Latin — cover the Central-Texas vocabulary explicitly.
  [["latin", "cumbia", "salsa", "tejano", "norteño", "norteno", "conjunto", "corrido", "reggaeton", "mariachi", "bachata", "merengue", "banda"], "latin"],
  // Reggae family — before the bare "ska"/"dub".
  [["reggae", "ska", "dancehall", "dub"], "reggae"],
  // Metal (metalcore/nu-metal read as metal) — before "core"/"rock".
  [["metal", "metalcore", "nu-metal", "nu metal", "death metal", "doom", "thrash"], "metal"],
  // Punk (hardcore/emo/grunge lean punk).
  [["punk", "hardcore", "emo", "grunge", "riot grrrl", "ska-punk"], "punk"],
  // Country (honky-tonk, two-step, western swing, outlaw).
  [["country", "honky-tonk", "honky tonk", "two-step", "two step", "western swing", "outlaw", "bluegrass-country"], "country"],
  // Folk / Americana / roots — bluegrass, acoustic-roots.
  [["americana", "folk", "bluegrass", "roots", "alt-country", "alt country"], "folk-americana"],
  // Singer-Songwriter.
  [["singer-songwriter", "singer songwriter", "songwriter"], "singer-songwriter"],
  // Blues.
  [["blues", "delta blues"], "blues"],
  // Jazz.
  [["jazz", "swing", "bebop", "big band"], "jazz"],
  // Classical / orchestral / opera-as-genre.
  [["classical", "orchestral", "symphony", "chamber", "opera", "choral", "baroque"], "classical"],
  // World / global.
  [["world", "afrobeat", "afrobeats", "celtic", "flamenco", "klezmer", "gospel"], "world"],
  // Indie / Alternative — AFTER the specific families, BEFORE bare "rock".
  [["alternative", "indie", "shoegaze", "post-rock", "new wave", "britpop"], "indie-alternative"],
  // Rock — the broad parent, last among rock-adjacent so qualifiers win first.
  [["rock", "hard rock", "classic rock", "psychedelic", "garage", "surf"], "rock"],
  // Pop — last, since "pop" appears inside many compounds ("pop-punk" already
  // caught by punk above; "synth-pop" leans electronic but we keep it pop).
  [["pop", "synth-pop", "synthpop", "power pop", "k-pop", "indie pop"], "pop"],
];

// Normalize a raw genre/subsegment string to a canonical Layer-1 id, or null if
// we do not (yet) recognize it. Null is honest: the UI shows "Other" and the
// term is a candidate for the lexicon, never a fabricated classification.
export function canonicalGenre(raw: string | null | undefined): GenreId | null {
  if (!raw) return null;
  const t = raw.toLowerCase().trim();
  if (!t) return null;
  // Exact id or exact today's-8 key (cheap, unambiguous) first.
  if (isGenreId(t)) return t;
  if (t in TODAY_8_TO_18) return TODAY_8_TO_18[t];
  // Then the lexicon: the LONGEST matching keyword wins (most-specific), so a
  // qualified term ("dancehall", "western swing", "alternative rock") beats the
  // broad parent it contains. Ties keep the earlier-listed (more specific) id.
  let bestId: GenreId | null = null;
  let bestLen = 0;
  for (const [keywords, id] of LEXICON) {
    for (const kw of keywords) {
      if (kw.length > bestLen && t.includes(kw)) {
        bestLen = kw.length;
        bestId = id;
      }
    }
  }
  return bestId;
}
