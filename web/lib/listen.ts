// "Hear them" — Option A of the music player (founder: "ship A now, treat B as
// an upgrade"). A row of links that SEARCH the act on the major music services,
// so a user can preview the artist without us embedding a player yet (Option B,
// which needs a music-service API + credentials).
//
// Honest by construction: these are SEARCHES by the performer's name, opened on
// the user's own service — never a claim that a specific track "is" them, and
// no key, no redirect to fabricated content. Only shown for MUSIC events with a
// named performer (see the detail page), because "hear them on Spotify" makes no
// sense for a lecture or an exhibition.

export type ListenLink = { service: string; url: string };

// Stable public search URLs (no API key, no auth). The query is the artist name.
export function listenLinks(name: string | null | undefined): ListenLink[] {
  const q = (name ?? "").trim();
  if (!q) return [];
  const e = encodeURIComponent(q);
  return [
    { service: "Spotify", url: `https://open.spotify.com/search/${e}` },
    { service: "Apple Music", url: `https://music.apple.com/us/search?term=${e}` },
    { service: "YouTube", url: `https://www.youtube.com/results?search_query=${e}` },
  ];
}
