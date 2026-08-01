// Contextual preview ("the preview hook") — the polymorphic, type-aware version
// of "Hear them". Design canon §3/§4 (founder directive 2026-07-31): the preview
// adapts to what the event actually IS — music → tracks, a talk → lectures,
// comedy → a set, film → the trailer, an artist → their work.
//
// HONEST BY CONSTRUCTION (Option A, the same bar the music links already ship
// under): every link is a SEARCH by the entity's own name on a service the user
// already uses — never a claim that a specific result "is" them, no API key, no
// fabricated content. A type we can't preview well returns null (an honest gap,
// never generic filler — "honest gaps beat filler", canon §1.7).
//
// Option B — the *verified specific* media (the real speaker's actual talk
// embedded, real past-year event photos/write-ups) — needs a media-service API
// + credentials and provenance verification. That is money/new-service =
// FOUNDER-CRUCIAL, and is deliberately NOT built here.

import type { LicensedEvent } from "./licensed";
import { listenLinks, type ListenLink } from "./listen";

export type ContextualPreview = { label: string; links: ListenLink[] };

// The name we search on: the performer when we have one, else the event title.
// Mirrors the card's `headline` so the preview searches what the card shows.
function subject(e: LicensedEvent): string | null {
  const s = e.performer && e.performer.length <= 80 ? e.performer : e.title;
  const t = (s ?? "").trim();
  return t.length ? t : null;
}

function ytSearch(query: string): ListenLink {
  return { service: "YouTube", url: `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}` };
}
function webSearch(query: string): ListenLink {
  return { service: "Search", url: `https://www.google.com/search?q=${encodeURIComponent(query)}` };
}

// Map an event's cultural domain to its honest preview. Music keeps the existing
// three-service listen row; everything else gets a single, well-scoped search
// framed by the label so the affordance is never mistaken for a verified clip.
export function contextualPreview(e: LicensedEvent): ContextualPreview | null {
  const name = subject(e);
  if (!name) return null;

  switch (e.category) {
    case "live-music":
    case "nightlife":
      return { label: "Hear them", links: listenLinks(name) };
    case "ideas":       // Lectures · Debates · Ideas
    case "literary":
      return { label: "Watch a talk", links: [ytSearch(`${name} talk lecture`)] };
    case "comedy":
      return { label: "See a set", links: [ytSearch(`${name} comedy`)] };
    case "film":
      // The title is the searchable thing for a screening, not a performer.
      return { label: "Watch the trailer", links: [ytSearch(`${(e.title ?? name).trim()} trailer`)] };
    case "theater":
    case "performing-arts":
    case "dance":
      return { label: "See a clip", links: [ytSearch(name)] };
    case "visual-arts":
      return { label: "See their work", links: [webSearch(`${name} artist work`)] };
    default:
      return null; // honest gap — no preview we can stand behind for this type
  }
}
