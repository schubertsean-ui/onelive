// Locale is a query (Locale Launch Law §1–2).
//
// A typed place, or ?place=, is a VIEW over the catalog. It is not a tenant,
// not a crawl trigger, and not a reason to invent an empty city page.
//
//   garbage / empty  → fail closed to the default view (never a fake city)
//   known rows       → Show them instantly (disputed included)
//   well-formed, none → gathering state, never "0 events in this city"
//
// Page load MUST NOT crawl, extract, or gather. This module is pure.

import { normalizePlace } from "./region";

export type PlaceRow = {
  venue_city?: string | null;
  city?: string | null;
  confidence?: string | null;
};

export type PlaceResolution =
  | { kind: "default" }
  | { kind: "show"; key: string; label: string }
  | { kind: "gathering"; key: string; label: string };

const MAX_LEN = 80;
const HAS_LETTER = /[a-zA-Z]/;
const GARBAGE = /https?:|www\.|@|<|javascript:|[{}[\]\\]/i;

/** A typed token is a place if it normalizes to a name. Anything else is
 *  garbage and must fail closed — never an empty fake city page. */
export function parsePlaceToken(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  const trimmed = String(raw).trim();
  if (!trimmed || trimmed.length > MAX_LEN) return null;
  if (!HAS_LETTER.test(trimmed)) return null;
  if (GARBAGE.test(trimmed)) return null;
  return normalizePlace(trimmed);
}

export function placeLabel(raw: string, key: string): string {
  const trimmed = String(raw).trim().replace(/\s+/g, " ");
  if (trimmed) return trimmed;
  return key
    .split(" ")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

export function rowMatchesPlace(row: PlaceRow, key: string): boolean {
  const cities = [row.venue_city, row.city];
  return cities.some((c) => normalizePlace(c) === key);
}

export function filterToPlace<T extends PlaceRow>(rows: T[], key: string): T[] {
  return rows.filter((r) => rowMatchesPlace(r, key));
}

/** Resolve a typed place against catalog rows we already have.
 *  Never starts a crawl. Never drops a disputed row that matches. */
export function resolvePlace<T extends PlaceRow>(
  raw: string | null | undefined,
  rows: T[],
): PlaceResolution {
  const key = parsePlaceToken(raw);
  if (!key) return { kind: "default" };
  const label = placeLabel(String(raw ?? ""), key);
  const matched = filterToPlace(rows, key);
  if (matched.length === 0) return { kind: "gathering", key, label };
  return { kind: "show", key, label };
}

/** True when this module (and any caller) would have to hit a network to
 *  answer. Always false — Show is catalog-only; gather is a separate job. */
export function placeQueryStartsCrawl(): false {
  return false;
}
