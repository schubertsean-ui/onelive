// Tasting Trail — the always-on breweries / wineries / distilleries directory.
//
// Venue records come from the curated, first-party source catalog, generated
// into ./tasting_venues.generated.ts by tools/gen_tasting_venues.py. This module
// is the typed read path the Tasting Trail section consumes. It carries only
// venue-identity fields (name, kind, county, first-party url) — a venue's live
// events still join from the pipeline when present and are NEVER fabricated here.
import { TASTING_VENUES } from "./tasting_venues.generated";

export type TastingKind =
  | "winery"
  | "brewery"
  | "distillery"
  | "beer-garden"
  | "restaurant"
  | "tasting-room";

export interface TastingVenue {
  id: string;
  name: string;
  kind: TastingKind;
  county: string;
  url: string;
}

/** All tasting venues in the directory (deterministic order: county, then name). */
export function tastingVenues(): TastingVenue[] {
  return TASTING_VENUES;
}

/** Venues of a single kind (winery / brewery / distillery / …). */
export function tastingVenuesByKind(kind: TastingKind): TastingVenue[] {
  return TASTING_VENUES.filter((v) => v.kind === kind);
}

/** Venues in a single county (case-insensitive). */
export function tastingVenuesByCounty(county: string): TastingVenue[] {
  const c = county.toLowerCase();
  return TASTING_VENUES.filter((v) => v.county === c);
}

/** The distinct counties represented, sorted — for a county filter/chooser. */
export function tastingCounties(): string[] {
  return [...new Set(TASTING_VENUES.map((v) => v.county))].sort();
}

/** The distinct kinds represented, sorted — for a kind filter/chooser. */
export function tastingKinds(): TastingKind[] {
  return [...new Set(TASTING_VENUES.map((v) => v.kind))].sort();
}
