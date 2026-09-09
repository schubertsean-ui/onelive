// Frictionless-nav helpers (RATIFIED canon: docs/design/ONE_LIVE_FRICTIONLESS_NAV_v1.md,
// founder 2026-08-03). Pure functions only — the components wire them to
// history/popstate so every piece of navigation LOGIC is unit-testable.
//
// What these implement (spec §§6–8):
//   · Filters live in the URL — shareable, back-restorable, reproducible (§6).
//   · The lens is history-modeled and URL-addressable: opening it pushes the
//     event's own /tonight/<id> URL, Back closes the sheet BEFORE leaving the
//     feed, and a hard load of the same URL renders the standalone page (§6/§7).
//   · External links are labeled by intent: a terminal handoff (tickets) says
//     where it finishes and goes SAME-TAB (never a gratuitous new tab on
//     mobile); reference links keep a new tab but always carry rel=noopener +
//     a screen-reader "external" label (§8).

import type { RegionScope } from "./region";

// ── Filters ⇄ URL (§6) ────────────────────────────────────────────────────────
export type FeedFilterState = {
  tabKey: string;
  domains: Set<string>;
  areas: Set<string>;
  genres: Set<string>;
  freeOnly: boolean;
  // CAPCOG is the test view filter only (founder 2026-09-09). Default is
  // everywhere — the catalog the person asked for. CAPCOG is opt-in via
  // ?region=capcog. Views filter. They do not delete catalog rows.
  region: RegionScope;
  eveningFirst: boolean;
};

export const DEFAULT_FILTERS: FeedFilterState = {
  tabKey: "today",
  domains: new Set(),
  areas: new Set(),
  genres: new Set(),
  freeOnly: false,
  region: "everywhere",
  eveningFirst: true,
};

export function filtersToQuery(f: FeedFilterState): string {
  const p = new URLSearchParams();
  if (f.tabKey !== "today") p.set("when", f.tabKey);
  if (f.domains.size) p.set("domain", [...f.domains].sort().join(","));
  if (f.areas.size) p.set("area", [...f.areas].sort().join(","));
  if (f.genres.size) p.set("genre", [...f.genres].sort().join(","));
  if (f.freeOnly) p.set("free", "1");
  if (f.region === "capcog") p.set("region", "capcog");
  if (!f.eveningFirst) p.set("order", "time");
  const s = p.toString();
  return s ? `?${s}` : "";
}

function csv(v: string | null): Set<string> {
  return new Set((v ?? "").split(",").map((x) => x.trim()).filter(Boolean));
}

export function queryToFilters(search: string): FeedFilterState {
  let p: URLSearchParams;
  try {
    p = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  } catch {
    return { ...DEFAULT_FILTERS, domains: new Set(), areas: new Set(), genres: new Set() };
  }
  const raw = p.get("region");
  return {
    tabKey: p.get("when") || "today",
    domains: csv(p.get("domain")),
    areas: csv(p.get("area")),
    genres: csv(p.get("genre")),
    freeOnly: p.get("free") === "1",
    region: raw === "capcog" ? "capcog" : "everywhere",
    eveningFirst: p.get("order") !== "time",
  };
}

export function isDefaultFilters(f: FeedFilterState): boolean {
  return (
    f.tabKey === "today" && !f.domains.size && !f.areas.size && !f.genres.size &&
    !f.freeOnly && f.region === "everywhere" && f.eveningFirst
  );
}

export const LENS_HISTORY_MARKER = "onelive-lens";

export type LensHistoryState = { [LENS_HISTORY_MARKER]: true; id: string; side: "artist" | "venue" };

export function lensHistoryState(id: string, side: "artist" | "venue"): LensHistoryState {
  return { [LENS_HISTORY_MARKER]: true, id, side };
}

export function isLensHistoryState(s: unknown): s is LensHistoryState {
  return typeof s === "object" && s !== null && (s as Record<string, unknown>)[LENS_HISTORY_MARKER] === true;
}

export function externalHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const h = new URL(url).hostname.replace(/^www\./, "");
    return h || null;
  } catch {
    return null;
  }
}

export function externalAriaLabel(action: string, url: string | null | undefined): string {
  const host = externalHost(url);
  return host ? `${action} — external link, opens ${host}` : `${action} — external link`;
}

export function handoffCaption(url: string | null | undefined): string | null {
  const host = externalHost(url);
  return host ? `finishes on ${host}` : null;
}
