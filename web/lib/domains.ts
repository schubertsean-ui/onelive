// The 22 cultural domains for display — id → label + accent hue. Mirrors
// docs/strategy/ONE_LIVE_CATEGORY_TAXONOMY_v1.md / worker/importers/domain_map.py.
// `unmapped` renders as "Other" (honest catch-all, never a fabricated domain).
//
// FL-014: desk kind maps write short words (music, art, sport). Chips look
// for live-music / visual-arts / sports. Alias here so Other is not the dump.

export type DomainMeta = { id: string; label: string; hue: number };

export const DOMAINS: DomainMeta[] = [
  { id: "live-music", label: "Live Music", hue: 28 },
  { id: "performing-arts", label: "Symphony · Opera · Ballet", hue: 280 },
  { id: "theater", label: "Theater", hue: 350 },
  { id: "comedy", label: "Comedy", hue: 48 },
  { id: "visual-arts", label: "Visual Arts & Museums", hue: 200 },
  { id: "film", label: "Film & Cinema", hue: 220 },
  { id: "literary", label: "Literary & Readings", hue: 160 },
  { id: "ideas", label: "Lectures · Debates · Ideas", hue: 190 },
  { id: "festivals", label: "Festivals", hue: 12 },
  { id: "food-drink", label: "Food & Drink", hue: 36 },
  { id: "nightlife", label: "Nightlife & Clubs", hue: 300 },
  { id: "dance", label: "Dance", hue: 320 },
  { id: "community", label: "Community & Block Parties", hue: 150 },
  { id: "heritage", label: "Heritage & Identity", hue: 340 },
  { id: "family", label: "Family & Youth", hue: 90 },
  { id: "place-based", label: "Place-based & Tours", hue: 130 },
  { id: "sports", label: "Sports & Spectacle", hue: 8 },
  { id: "library", label: "Library Programs", hue: 170 },
  { id: "fairs-expos", label: "Fairs · Expos · Cons", hue: 250 },
  { id: "seasonal", label: "Seasonal & Ritual", hue: 60 },
  { id: "wellness", label: "Wellness & Outdoor", hue: 110 },
  { id: "fashion-design", label: "Fashion · Design · Maker", hue: 310 },
  { id: "unmapped", label: "Other", hue: 0 },
];

export const DOMAIN_LABEL = new Map(DOMAINS.map((d) => [d.id, d.label]));
export const DOMAIN_HUE = new Map(DOMAINS.map((d) => [d.id, d.hue]));

/** Desk our_kind → feed domain id. Print map. No ingest. */
export const PACK_KIND_ALIAS: Record<string, string> = {
  music: "live-music",
  art: "visual-arts",
  sport: "sports",
  food: "food-drink",
  civic: "community",
  class: "ideas",
  market: "fairs-expos",
  outdoors: "wellness",
};

export function packKind(id: string | null): string | null {
  if (!id) return null;
  const raw = id.trim().toLowerCase();
  if (!raw) return null;
  return PACK_KIND_ALIAS[raw] ?? raw;
}

export function domainLabel(id: string | null): string {
  if (!id) return "Other";
  const mapped = packKind(id);
  return DOMAIN_LABEL.get(mapped ?? "") ?? "Other";
}
export function domainHue(id: string | null): number {
  if (!id) return 0;
  const mapped = packKind(id);
  return DOMAIN_HUE.get(mapped ?? "") ?? 0;
}

// Time-band density (founder's time-tiered card idea): rich ≤7d, compact 8–30d,
// line >30d. Thresholds are the founder dial.
export type Band = "rich" | "compact" | "line";
export function timeBand(startISO: string | null, nowMs: number): Band {
  if (!startISO) return "line";
  const t = Date.parse(startISO);
  if (Number.isNaN(t)) return "line";
  const days = (t - nowMs) / 86_400_000;
  if (days <= 7) return "rich";
  if (days <= 30) return "compact";
  return "line";
}
