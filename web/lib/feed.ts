// Pure feed-shaping logic — unit-tested so the "nothing is silently hidden"
// invariant holds structurally, not by inspection of the JSX.
//
// The trust rule (evaluator PR #59) applies to the RENDERED surface, not just
// the query: every fetched event must land in a rendered domain bucket, and no
// per-domain cap may drop rows. A `disputed` event in an unknown category, or
// in position 13, must still be shown.

import { DOMAINS, DOMAIN_LABEL, domainLabel, timeBand, type Band, type DomainMeta } from "./domains";
import { canonicalGenre, genreLabel, type GenreId } from "./genres";
import { applyRegionScope, type RegionScope } from "./region";
import type { LicensedEvent } from "./licensed";

// ── Timing ───────────────────────────────────────────────────────────────────
// An event is shown only if it is still to come or currently on. "Ended" events
// (start + known/assumed duration is in the past) are hidden — a TIME filter,
// never a confidence filter (disputed stays shown while it hasn't ended).
export type Timing = "upcoming" | "on-now" | "ended";
const ASSUMED_MS = 3 * 60 * 60 * 1000; // 3h assumed run when end_time is absent.

export function eventTiming(e: LicensedEvent, nowMs: number): Timing {
  const start = e.start_time ? Date.parse(e.start_time) : NaN;
  if (Number.isNaN(start)) return "upcoming"; // date TBA — never hide it
  if (start > nowMs) return "upcoming";
  const end = e.end_time ? Date.parse(e.end_time) : NaN;
  const endMs = Number.isNaN(end) ? start + ASSUMED_MS : end;
  return endMs > nowMs ? "on-now" : "ended";
}

// Live (still relevant) = upcoming OR on-now. This is the base set the feed and
// every lens operate over — the honest full night, minus only what has ended.
export function liveEvents(events: LicensedEvent[], nowMs: number): LicensedEvent[] {
  return events.filter((e) => eventTiming(e, nowMs) !== "ended");
}

// ── Date tabs (Today → next N days, in the viewer's own local time) ───────────
export type DayTab = { key: string; label: string; startMs: number; endMs: number };

// Day boundaries are the MARKET's days (America/Chicago), not the runtime's.
// The old setHours(0,0,0,0) used the process/browser timezone — on a UTC
// server (production SSR) "today" ended at 7 PM Austin time, so every show
// tonight after 7 PM was bucketed "Tomorrow" in the server-rendered HTML
// (caught 2026-08-04 while chasing the founder's "1 event today"). The
// viewer's real clock still decides NOW (what has ended); Austin's calendar
// decides what "Today" means — deterministic on server and client alike.
const MARKET_TZ = "America/Chicago";
function startOfLocalDay(ms: number): number {
  const [mo, day, y] = new Intl.DateTimeFormat("en-US", {
    timeZone: MARKET_TZ, year: "numeric", month: "2-digit", day: "2-digit",
  }).format(new Date(ms)).split("/").map(Number);
  // Midnight in the market TZ is 05:00 or 06:00 UTC depending on DST — probe.
  for (const off of [5, 6]) {
    const cand = Date.UTC(y, mo - 1, day, off);
    const h = new Intl.DateTimeFormat("en-US", { timeZone: MARKET_TZ, hour: "2-digit", hour12: false })
      .format(new Date(cand));
    if (h === "00" || h === "24") return cand;
  }
  return Date.UTC(y, mo - 1, day, 6);
}

// Today + the next `days` market days, then "All upcoming". Each tab is a
// [start,end) window over start_time. Today spans the WHOLE market day, not
// [now, midnight): the feed's base is liveEvents (ended shows are already
// gone), so a started-but-ON-NOW show must stay in the default Today view —
// with Today as the default (founder-directed), a [nowMs,…) start boundary
// hid on-now events from the opening feed, and a disputed on-now show being
// hidden is a trust-invariant break (adversarial-review catch, 2026-08-04).
export function dayTabs(nowMs: number, days = 7): DayTab[] {
  // Founder-directed order (2026-08-04): "Start with today … move All
  // upcoming to be last." Today leads and is the DEFAULT (the brief's own
  // choice architecture: "default view is tonight"); the catch-all closes
  // the row instead of opening it.
  const tabs: DayTab[] = [];
  let s = startOfLocalDay(nowMs);
  for (let i = 0; i <= days; i++) {
    // Each day's END is the NEXT market midnight, derived per-day — never
    // start + 24h. Chicago days are 23 or 25 hours across DST transitions
    // (adversarial-review r3, 2026-08-04): a fixed-width day drifts every
    // boundary after the transition by an hour, mis-bucketing late shows.
    // 30h past this midnight lands safely inside the next market day whether
    // this one is 23, 24, or 25 hours long; startOfLocalDay snaps it back.
    const e = startOfLocalDay(s + 30 * 3_600_000);
    const label =
      i === 0 ? "Today" : i === 1 ? "Tomorrow" : new Date(s).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "America/Chicago" });
    tabs.push({ key: i === 0 ? "today" : `d${i}`, label, startMs: s, endMs: e });
    s = e;
  }
  tabs.push({ key: "all", label: "All upcoming", startMs: 0, endMs: Infinity });
  return tabs;
}

// ── Day part: let the evening LEAD without deleting the morning ──────────────
// Founder directive (2026-09-01, Session 2 VIEW): "Default or control so
// evening/upcoming can lead without deleting morning rows from the catalog."
//
// The split is an ORDERING, never a filter. Both halves render; their lengths
// always sum to the input (proven in tests), so the day-part control can never
// become a second, invisible way to drop a row — the exact failure the Coverage
// Law names ("views must not delete catalog rows").
export const EVENING_HOUR = 17; // 5pm in the MARKET's clock, not the runtime's

/** The event's start hour in the market timezone (0–23), or null when the row
 *  carries no usable start time. Uses the market clock for the same reason
 *  dayTabs does: a UTC server would otherwise call an 8pm Austin show "next
 *  day" and sort it into the wrong half. */
export function marketHour(iso: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  const h = Number(
    new Intl.DateTimeFormat("en-US", {
      timeZone: MARKET_TZ, hour: "2-digit", hour12: false,
    }).format(new Date(t)),
  );
  if (Number.isNaN(h)) return null;
  return h === 24 ? 0 : h; // en-US hour12:false renders midnight as "24"
}

export type DayPartSplit = { evening: LicensedEvent[]; earlier: LicensedEvent[] };

/** Split a day's events into the leading evening/night block and the earlier
 *  (daytime) block. A row with NO usable start time leads with the evening
 *  block rather than being buried under it — a date-TBA row must not be
 *  demoted by a clock we do not have. */
export function splitByDayPart(events: LicensedEvent[]): DayPartSplit {
  const evening: LicensedEvent[] = [];
  const earlier: LicensedEvent[] = [];
  for (const e of events) {
    const h = marketHour(e.start_time);
    (h === null || h >= EVENING_HOUR ? evening : earlier).push(e);
  }
  return { evening, earlier };
}

/** How many of `events` fall in the selected day tab — the M of "Showing N of
 *  M known listings". Deliberately counted BEFORE any lens filter (domain,
 *  genre, area, free) and AFTER the region scope, so the line answers the
 *  question a reader actually has: how much of what we hold for this window is
 *  this view showing me. */
export function countInWindow(events: LicensedEvent[], tab: DayTab): number {
  return events.reduce((n, e) => (inDayTab(e, tab) ? n + 1 : n), 0);
}

/** The three numbers the completeness line is built from, derived in ONE place
 *  so the sentence a reader sees and the river they scroll cannot disagree:
 *
 *    shown            N — rows this view renders (after every lens filter)
 *    windowTotal      M — catalog rows in the same window, under the SAME
 *                     region scope, before any lens. Clearing the region
 *                     raises M: "M is not CAPCOG-only" (founder 2026-09-01).
 *    heldBackByRegion how many catalog rows in this window the CAPCOG scope is
 *                     holding back — 0 once the reader clears it. This is the
 *                     number that keeps a view filter from reading as a
 *                     catalog border.
 *
 *  `live` is the catalog side (time-filtered only, never region- or
 *  trust-filtered), so the arithmetic is measured against what we actually
 *  hold rather than against what an earlier stage already discarded. */
export type ViewCounts = {
  shown: number;
  windowTotal: number;
  heldBackByRegion: number;
};

export function viewCounts(
  live: LicensedEvent[],
  shown: LicensedEvent[],
  tab: DayTab,
  region: RegionScope,
): ViewCounts {
  const catalogTotal = countInWindow(live, tab);
  const windowTotal = region === "everywhere"
    ? catalogTotal
    : countInWindow(applyRegionScope(live, region), tab);
  return {
    shown: shown.length,
    windowTotal,
    heldBackByRegion: catalogTotal - windowTotal,
  };
}

export function inDayTab(e: LicensedEvent, tab: DayTab): boolean {
  if (tab.key === "all") return true;
  if (!e.start_time) return false; // date-TBA only shows under "All"
  const t = Date.parse(e.start_time);
  if (Number.isNaN(t)) return false;
  if (t >= tab.startMs && t < tab.endMs) return true;
  // Today only: a show that STARTED before the market midnight but whose
  // running window reaches into today still belongs to the default view.
  // After midnight, liveEvents still carries it (it hasn't ended), but pure
  // start-time bucketing pushed it to no day tab at all — leaving "All
  // upcoming" the only place an on-now, possibly DISPUTED, show appeared:
  // a trust-invariant break (adversarial-review r3, 2026-08-04). Future
  // tabs keep pure start-time semantics — a Friday-night show lists under
  // Friday, not Friday and Saturday.
  if (tab.key === "today" && t < tab.startMs) {
    const end = e.end_time ? Date.parse(e.end_time) : NaN;
    const endMs = Number.isNaN(end) ? t + ASSUMED_MS : end;
    return endMs > tab.startMs;
  }
  return false;
}

// ── Filters (lenses — they narrow the user's view, never touch confidence) ────
export type FeedFilters = {
  tab?: DayTab;
  domains?: Set<string>; // category ids; empty/undefined = all
  areas?: Set<string>; // venue_area values
  genreIds?: Set<string>; // canonical Layer-1 genre ids (see lib/genres.ts)
  freeOnly?: boolean;
};

export function applyFilters(events: LicensedEvent[], f: FeedFilters): LicensedEvent[] {
  return events.filter((e) => {
    if (f.tab && !inDayTab(e, f.tab)) return false;
    if (f.domains && f.domains.size && !f.domains.has(normalizeDomain(e.category))) return false;
    if (f.areas && f.areas.size && !(e.venue_area && f.areas.has(e.venue_area))) return false;
    // Genre is a LENS over the canonical taxonomy: match the row's raw genre
    // words normalized to a Layer-1 id. A row that doesn't canonicalize (null)
    // simply isn't in any selected genre — narrowed out, never hidden by trust.
    if (f.genreIds && f.genreIds.size) {
      const g = musicGenreOf(e);
      if (!(g && f.genreIds.has(g))) return false;
    }
    if (f.freeOnly && !(e.is_free || e.price_min === 0)) return false;
    return true;
  });
}

// Distinct venue AREAS present in a set, with counts, most-common first.
export function facet(events: LicensedEvent[], key: "venue_area" | "subsegment"): Array<{ value: string; n: number }> {
  const m = new Map<string, number>();
  for (const e of events) {
    const v = e[key];
    if (v) m.set(v, (m.get(v) ?? 0) + 1);
  }
  return [...m.entries()].map(([value, n]) => ({ value, n })).sort((a, b) => b.n - a.n);
}

// Genre is a MUSIC concept — only music-domain events carry a meaningful genre.
// Running the lexicon over EVERY event mislabels e.g. a dance PERFORMANCE (a
// performing-arts row whose subsegment "Dance" hits the electronic-dance
// keyword) as a music genre, producing a fabricated chip and a misleading
// filter result (adversarial-review #100). So genre is scoped to music domains;
// a non-music row canonicalizes to null and contributes to no chip.
const MUSIC_DOMAINS = new Set(["live-music", "nightlife"]);

export function musicGenreOf(e: LicensedEvent): GenreId | null {
  if (!MUSIC_DOMAINS.has(normalizeDomain(e.category))) return null;
  return canonicalGenre(e.subsegment);
}

// The Layer-0 UI rail, DERIVED from local inventory: the canonical genres
// actually present among MUSIC events in this set, most-common first, with
// counts. A row that doesn't canonicalize (non-music, or an unknown label)
// contributes to no chip — it's "Other", a growth signal, never a fabricated
// genre. The caller slices to 8–12 chips.
export function genreFacet(
  events: LicensedEvent[],
): Array<{ id: GenreId; label: string; n: number }> {
  const m = new Map<GenreId, number>();
  for (const e of events) {
    const g = musicGenreOf(e);
    if (g) m.set(g, (m.get(g) ?? 0) + 1);
  }
  return [...m.entries()]
    .map(([id, n]) => ({ id, label: genreLabel(id), n }))
    .sort((a, b) => b.n - a.n);
}

// ── The Ask layer — "what are you feeling?" desire lenses ─────────────────────
// EVERY desire here is backed by a real column. A lens never gates: it re-orders
// the honest set and says WHY each match qualifies. Unbacked desires ("dinner",
// "outside") are deliberately absent — recorded as deferrals (docs/RECORD.md),
// never shipped as empty or fabricated results.
const _DANCE = new Set(["Cumbia", "Salsa", "Country", "Honky-tonk", "Tejano", "Latin", "Dance/Electronic", "House", "Techno", "Disco"]);
const _QUIET = new Set(["Jazz", "Classical", "Acoustic", "Folk", "Singer-Songwriter", "Blues", "Americana", "Bluegrass", "Ambient"]);
const _LOUD = new Set(["Rock", "Punk", "Metal", "Hard Rock", "Hardcore", "Alternative", "Alternative Rock", "Nu-Metal", "Metalcore", "Emo", "Grunge"]);

export type Desire = {
  key: string;
  label: string; // spoken-search phrasing
  note?: string; // honest caveat when the match is a proxy, not a hard attribute
  match: (e: LicensedEvent, nowMs: number) => boolean;
  why: (e: LicensedEvent) => string;
};

function localHour(iso: string | null): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return new Date(t).getHours();
}
function subOf(e: LicensedEvent): string {
  return (e.subsegment ?? "").split(" · ")[0];
}

export const DESIRES: Desire[] = [
  {
    key: "free", label: "Something free",
    match: (e) => !!e.is_free || e.price_min === 0,
    why: () => "free to attend",
  },
  {
    key: "cheap", label: "Easy on the wallet",
    match: (e) => e.price_max != null && e.price_max <= 20,
    why: (e) => (e.price_max != null ? `tickets up to $${Math.round(e.price_max)}` : "budget-friendly"),
  },
  {
    key: "late", label: "Starting late",
    match: (e) => { const h = localHour(e.start_time); return h != null && h >= 22; },
    why: (e) => `starts ${new Date(e.start_time as string).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}`,
  },
  {
    key: "dance", label: "Somewhere to dance",
    match: (e) => _DANCE.has(subOf(e)) || e.category === "dance" || e.category === "nightlife",
    why: (e) => `${subOf(e) || domainLabel(e.category)} — made for moving`,
  },
  {
    key: "quiet", label: "Quiet & intimate",
    note: "Matched by genre — a mood proxy, not a verified attribute.",
    match: (e) => _QUIET.has(subOf(e)),
    why: (e) => `${subOf(e)} — an easier-going room`,
  },
  {
    key: "loud", label: "Loud & live",
    note: "Matched by genre — a mood proxy, not a verified attribute.",
    match: (e) => _LOUD.has(subOf(e)),
    why: (e) => `${subOf(e)} — turn it up`,
  },
  {
    key: "laugh", label: "Make me laugh",
    match: (e) => e.category === "comedy",
    why: () => "comedy tonight",
  },
  {
    key: "family", label: "Bring the kids",
    match: (e) => e.category === "family",
    why: () => "family & youth friendly",
  },
  {
    key: "arts", label: "Culture & the arts",
    match: (e) => ["performing-arts", "theater", "visual-arts", "dance", "literary"].includes(e.category ?? ""),
    why: (e) => domainLabel(e.category).toLowerCase(),
  },
];

export const DESIRE_BY_KEY = new Map(DESIRES.map((d) => [d.key, d]));

// Apply a desire as a LENS: return the matches (sorted by start time) — the
// caller always keeps the full set one tap away.
export function applyDesire(events: LicensedEvent[], key: string, nowMs: number): LicensedEvent[] {
  const d = DESIRE_BY_KEY.get(key);
  if (!d) return [];
  return events.filter((e) => d.match(e, nowMs)).sort(byStart);
}

// ── Plan a Day / Night / Weekend ─────────────────────────────────────────────
// A plan is a SUGGESTION built from the honest live set — never a gate. Each slot
// is the soonest-in-block event, biased to cluster by neighborhood and vary the
// domain, so it reads like a night out. Provenance ("why") on every slot.
export type PlanScope = "day" | "night" | "weekend";
export type PlanSlot = { block: string; event: LicensedEvent; why: string };

function byStart(a: LicensedEvent, b: LicensedEvent): number {
  const ta = a.start_time ? Date.parse(a.start_time) : Infinity;
  const tb = b.start_time ? Date.parse(b.start_time) : Infinity;
  return ta - tb;
}

// Returns block windows [label, startHour, endHour) in local time for a scope.
export function planBlocks(scope: PlanScope): Array<{ label: string; from: number; to: number }> {
  if (scope === "day") return [
    { label: "Afternoon", from: 12, to: 17 },
    { label: "Evening", from: 17, to: 20 },
    { label: "Night", from: 20, to: 24 + 3 },
  ];
  if (scope === "weekend") return [
    { label: "Friday night", from: 24 * 0 + 17, to: 24 * 1 + 3 },
    { label: "Saturday", from: 24 * 1 + 12, to: 24 * 1 + 20 },
    { label: "Saturday night", from: 24 * 1 + 20, to: 24 * 2 + 3 },
    { label: "Sunday", from: 24 * 2 + 12, to: 24 * 2 + 22 },
  ];
  return [ // night
    { label: "Early", from: 17, to: 20 },
    { label: "Main", from: 20, to: 22.5 },
    { label: "Late", from: 22.5, to: 24 + 3 },
  ];
}

// Hours since the plan's anchor midnight (weekend anchors on Friday 00:00).
function anchor(scope: PlanScope, nowMs: number): number {
  const d = new Date(nowMs);
  d.setHours(0, 0, 0, 0);
  if (scope === "weekend") {
    // Move back to the most recent Friday (Fri=5). If already Sat/Sun, keep it.
    const dow = d.getDay(); // 0=Sun..6=Sat
    const back = dow === 0 ? 2 : dow === 6 ? 1 : (dow + 2) % 7; // days since Friday
    d.setDate(d.getDate() - back);
  }
  return d.getTime();
}

export function buildPlan(events: LicensedEvent[], scope: PlanScope, nowMs: number): PlanSlot[] {
  const base = anchor(scope, nowMs);
  const hoursFrom = (e: LicensedEvent): number | null => {
    if (!e.start_time) return null;
    const t = Date.parse(e.start_time);
    if (Number.isNaN(t) || t < nowMs) return null; // only still-upcoming picks
    return (t - base) / 3_600_000;
  };
  const slots: PlanSlot[] = [];
  const usedIds = new Set<string>();
  let prevArea: string | null = null;
  let prevDomain: string | null = null;

  for (const block of planBlocks(scope)) {
    const candidates = events
      .filter((e) => { const h = hoursFrom(e); return h != null && h >= block.from && h < block.to && !usedIds.has(e.licensed_event_id); })
      .sort((a, b) => {
        // bias: same neighborhood as prev, different domain than prev, then soonest
        const sa = (prevArea && a.venue_area === prevArea ? -2 : 0) + (prevDomain && normalizeDomain(a.category) === prevDomain ? 1 : 0);
        const sb = (prevArea && b.venue_area === prevArea ? -2 : 0) + (prevDomain && normalizeDomain(b.category) === prevDomain ? 1 : 0);
        return sa - sb || byStart(a, b);
      });
    const pick = candidates[0];
    if (!pick) continue;
    usedIds.add(pick.licensed_event_id);
    const near = prevArea && pick.venue_area === prevArea ? ` · same area as your last stop` : "";
    slots.push({
      block: block.label,
      event: pick,
      why: `${domainLabel(pick.category)}${pick.venue_area ? ` in ${pick.venue_area}` : ""}${near}`,
    });
    prevArea = pick.venue_area ?? prevArea;
    prevDomain = normalizeDomain(pick.category);
  }
  return slots;
}

// Fold any category that is null or outside the taxonomy into "unmapped"
// ("Other") — taxonomy drift can never silently omit a row.
export function normalizeDomain(category: string | null): string {
  return category && DOMAIN_LABEL.has(category) ? category : "unmapped";
}

export type DomainGroup = { domain: DomainMeta; items: LicensedEvent[] };

// Group every event under a rendered domain, in DOMAINS order, preserving count:
// the sum of items across groups always equals events.length (proven in tests).
export function groupByDomain(events: LicensedEvent[]): DomainGroup[] {
  const byId = new Map<string, LicensedEvent[]>();
  for (const e of events) {
    const id = normalizeDomain(e.category);
    const arr = byId.get(id);
    if (arr) arr.push(e);
    else byId.set(id, [e]);
  }
  const groups: DomainGroup[] = [];
  for (const d of DOMAINS) {
    const items = byId.get(d.id);
    if (items && items.length) groups.push({ domain: d, items });
  }
  return groups;
}

// ── Date buckets (the three-tier density) ────────────────────────────────────
// Longer-dated events don't deserve the same tall card as tonight's — a founder
// directive. Events split by time-to-start into three descending densities,
// each with a plain scannable header. The three bands are exactly timeBand's
// (rich ≤7d, compact 8–30d, line >30d), so the density IS the date bucket.
// Sum-preserving like groupByDomain: every event lands in exactly one bucket
// (proven in tests) — the "nothing hidden" invariant holds across the split.
export type DateBucket = { key: Band; label: string; blurb: string; items: LicensedEvent[] };

export function bucketByDate(events: LicensedEvent[], nowMs: number): DateBucket[] {
  const rich: LicensedEvent[] = [];
  const compact: LicensedEvent[] = [];
  const line: LicensedEvent[] = [];
  for (const e of events) {
    const b = timeBand(e.start_time, nowMs);
    (b === "rich" ? rich : b === "compact" ? compact : line).push(e);
  }
  // Labels are RELATIVE durations, not calendar claims: "Later this month" was
  // false for an 8–30-day event that actually falls in the next calendar month
  // (adversarial-review #100). "In the coming weeks" is true regardless of where
  // the month boundary sits.
  const buckets: DateBucket[] = [
    { key: "rich", label: "This week", blurb: "the next seven days", items: rich },
    { key: "compact", label: "In the coming weeks", blurb: "the next few weeks", items: compact.sort(byStart) },
    // The line bucket also holds date-TBA rows (timeBand maps a null/invalid
    // start_time here), which render as "Date TBA" — so the blurb must NOT claim
    // dates are set (adversarial-review #100), it names both far-dated and TBA.
    { key: "line", label: "Further out", blurb: "beyond a month out, and dates to be announced", items: line.sort(byStart) },
  ];
  return buckets.filter((b) => b.items.length);
}
