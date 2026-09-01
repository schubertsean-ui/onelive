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
  // The REGION scope (Coverage Law 2026-09-01): "capcog" is the default test
  // view, "everywhere" is the reader having cleared it. It travels in the URL
  // like every other filter so a shared link reproduces what the sender saw —
  // including the un-scoped catalog view, which is the whole point of making
  // the boundary clearable rather than silent.
  region: RegionScope;
  // Whether the evening/night block LEADS a single-day river (the default) or
  // the day runs plainly by category/time. An ordering, never a filter.
  eveningFirst: boolean;
};

export const DEFAULT_FILTERS: FeedFilterState = {
  tabKey: "today", // founder-directed default 2026-08-04: start with today
  domains: new Set(),
  areas: new Set(),
  genres: new Set(),
  freeOnly: false,
  region: "capcog", // founder-directed default 2026-09-01: CAPCOG is the test view
  eveningFirst: true, // founder-directed default 2026-09-01: the evening leads
};

// Compact, human-readable query: /tonight?when=today&domain=live-music,comedy
// &area=East+Austin&genre=rock&free=1 — absent keys mean the default, so the
// bare /tonight URL stays canonical and clean.
export function filtersToQuery(f: FeedFilterState): string {
  const p = new URLSearchParams();
  if (f.tabKey !== "today") p.set("when", f.tabKey); // "today" is the default (founder-directed 2026-08-04); "All upcoming" now travels as when=all
  if (f.domains.size) p.set("domain", [...f.domains].sort().join(","));
  if (f.areas.size) p.set("area", [...f.areas].sort().join(","));
  if (f.genres.size) p.set("genre", [...f.genres].sort().join(","));
  if (f.freeOnly) p.set("free", "1");
  if (f.region === "everywhere") p.set("region", "all"); // absent = the CAPCOG default
  if (!f.eveningFirst) p.set("order", "time"); // absent = evening leads
  const s = p.toString();
  return s ? `?${s}` : "";
}

function csv(v: string | null): Set<string> {
  return new Set((v ?? "").split(",").map((x) => x.trim()).filter(Boolean));
}

// Tolerant inverse: unknown keys are ignored, malformed values degrade to the
// default (a bad shared link must render the honest full feed, never break).
export function queryToFilters(search: string): FeedFilterState {
  let p: URLSearchParams;
  try {
    p = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  } catch {
    return { ...DEFAULT_FILTERS, domains: new Set(), areas: new Set(), genres: new Set() };
  }
  return {
    tabKey: p.get("when") || "today",
    domains: csv(p.get("domain")),
    areas: csv(p.get("area")),
    genres: csv(p.get("genre")),
    freeOnly: p.get("free") === "1",
    // Only the exact opt-out token widens the region; anything else (absent,
    // misspelled, injected) falls back to the CAPCOG default. A malformed
    // shared link must never silently change what market a reader is looking
    // at — it renders the default view, exactly like a bare /tonight.
    region: p.get("region") === "all" ? "everywhere" : "capcog",
    eveningFirst: p.get("order") !== "time",
  };
}

export function isDefaultFilters(f: FeedFilterState): boolean {
  return (
    f.tabKey === "today" && !f.domains.size && !f.areas.size && !f.genres.size &&
    !f.freeOnly && f.region === "capcog" && f.eveningFirst
  );
}

// ── History-modeled lens (§6/§7) ─────────────────────────────────────────────
// The marker stored in history.state when the lens pushes an entry, so a
// popstate handler can tell "Back closed the lens" apart from any other
// navigation, and a UI close knows whether history.back() is the right undo.
export const LENS_HISTORY_MARKER = "onelive-lens";

export type LensHistoryState = { [LENS_HISTORY_MARKER]: true; id: string; side: "artist" | "venue" };

export function lensHistoryState(id: string, side: "artist" | "venue"): LensHistoryState {
  return { [LENS_HISTORY_MARKER]: true, id, side };
}

export function isLensHistoryState(s: unknown): s is LensHistoryState {
  return typeof s === "object" && s !== null && (s as Record<string, unknown>)[LENS_HISTORY_MARKER] === true;
}

// ── External links by intent (§8) ────────────────────────────────────────────
// Host shown to humans/screen readers for a handoff label. Unparseable URLs
// yield null — the caller renders its generic label rather than a wrong claim.
export function externalHost(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const h = new URL(url).hostname.replace(/^www\./, "");
    return h || null;
  } catch {
    return null;
  }
}

// Screen-reader label for ANY true outbound link (spec §8: an unannounced
// context change is a defect): "Get tickets — external link, opens ticketmaster.com".
export function externalAriaLabel(action: string, url: string | null | undefined): string {
  const host = externalHost(url);
  return host ? `${action} — external link, opens ${host}` : `${action} — external link`;
}

// Visible caption for the TERMINAL (transactional) handoff — the honest
// "you'll finish over there" wording, same-tab (§8 table, row 2).
export function handoffCaption(url: string | null | undefined): string | null {
  const host = externalHost(url);
  return host ? `finishes on ${host}` : null;
}
