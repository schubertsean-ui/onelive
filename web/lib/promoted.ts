// Read PROMOTED (pipeline-gated) events from the canonical `event` table and
// reshape them into the same LicensedEvent card shape the feed already renders,
// so the consumer feed can show `event ∪ licensed_event` — the union the schema
// (migration 0010) documents as the consumer read path. This is the read half
// of "put reviewed events on the site": the crawl pipeline promotes long-tail
// events (venue calendars, festivals, university feeds) into `event`; without
// this reader they were written but never displayed.
//
// TRUST RULES (identical to licensed.ts, held structurally):
//   * NEVER filter on `confidence` — a `disputed` promoted event is read and
//     shown (shown-never-hidden). The only filters are time/status, never trust.
//   * Row privacy is enforced upstream by RLS (migration 0007: anon reads only
//     non-private events); this reader adds no privacy logic of its own and the
//     anon key physically cannot see private rows.
//   * `event` stores venue via a FK and artists via an id array, so we join
//     `venue` (PostgREST embed) and resolve `artist_ids` → names for `performer`.
//     No fabrication: fields absent on a promoted row stay null.

import { exactlyOneOrNull, supaEnv, type LicensedEvent } from "./licensed";

// Event listing columns granted to anon in migration 0012 (privacy/internal
// columns are deliberately NOT granted). `venue:venue_id(...)` is a PostgREST
// embed over the event→venue FK; `artist_ids` is resolved separately.
const EVENT_SELECT = [
  "event_id",
  "title",
  "category",
  "subsegment",
  "start_time",
  "end_time",
  "status",
  "confidence",
  "price_min",
  "price_max",
  "currency",
  "is_free",
  "ticket_url",
  "image_url",
  "artist_ids",
  "venue:venue_id(name,city,area,address,lat,lng)",
].join(",");

// The raw shape PostgREST returns for the query above (before reshape).
export type PromotedRow = {
  event_id: string;
  title: string | null;
  category: string | null;
  subsegment: string | null;
  start_time: string | null;
  end_time: string | null;
  status: string;
  confidence: string;
  price_min: number | null;
  price_max: number | null;
  currency: string | null;
  is_free: boolean | null;
  ticket_url: string | null;
  image_url: string | null;
  artist_ids: string[] | null;
  venue: {
    name: string | null;
    city: string | null;
    area: string | null;
    address: string | null;
    lat: number | null;
    lng: number | null;
  } | null;
};

export type PromotedQueryOpts = {
  category?: string;
  fromISO?: string; // start_time >= this
  toISO?: string; // start_time <= this
  eventId?: string;   // detail surface: one row by id (raw uuid, no prefix)
  anyStatus?: boolean; // detail surface: a cancelled event says so, never 404s
};

// Pure PostgREST query-string builder (no env, no network) — unit-tested. Same
// two trust-critical rules as the licensed builder: it never filters on
// `confidence` (disputed included), and it bakes in NO row limit (the fetch loop
// pages by Range). Order carries a unique tiebreaker (event_id) for stable paging.
export function buildPromotedQuery(opts?: PromotedQueryOpts): string {
  const p = new URLSearchParams();
  p.set("select", EVENT_SELECT);
  // never hide anything by confidence; anyStatus is the detail surface only
  // (see LicensedQueryOpts.anyStatus for why one event by id is not a feed).
  if (!opts?.anyStatus) p.append("status", "in.(scheduled,moved)");
  if (opts?.eventId) p.append("event_id", `eq.${opts.eventId}`);
  if (opts?.category) p.append("category", `eq.${opts.category}`);
  if (opts?.fromISO) p.append("start_time", `gte.${opts.fromISO}`);
  if (opts?.toISO) p.append("start_time", `lte.${opts.toISO}`);
  p.set("order", "start_time.asc,event_id.asc");
  return p.toString();
}

// ONE artist-name resolution, used by the feed read and the single-event read
// (PR #87 r4, gemini nit). The two had byte-identical copies of this block, and
// a duplicated query is a place where two read paths can silently diverge.
// Missing ids are simply absent from the map; reshapePromoted omits them rather
// than inventing a name.
async function resolveArtistNames(
  url: string,
  key: string,
  rows: PromotedRow[],
): Promise<Map<string, string>> {
  const ids = [...new Set(rows.flatMap((r) => r.artist_ids ?? []))];
  const byId = new Map<string, string>();
  if (!ids.length) return byId;
  // PostgREST parses the filter AFTER percent-decoding the parameter value, so
  // the whole `in.("a","b")` expression is encoded as one value. Exercised by a
  // test with non-empty artist_ids asserting both the request shape and the
  // resolved name — this encoding was reported broken in two rounds, and a test
  // settles it where prose could not.
  const inList = `in.(${ids.map((id) => `"${id}"`).join(",")})`;
  const aEndpoint =
    `${url}/rest/v1/artist?select=artist_id,name&artist_id=${encodeURIComponent(inList)}`;
  const aRows = (await fetchAllRows(url, key, aEndpoint)) as Array<{
    artist_id: string;
    name: string | null;
  }>;
  for (const a of aRows) if (a.name) byId.set(a.artist_id, a.name);
  return byId;
}


// Pure reshape of raw `event` rows into the LicensedEvent card shape. `performer`
// is resolved from the id→name map (missing ids are simply omitted — never a
// fabricated name). Provenance is preserved as source_provider = "promoted" so
// the UI can render it as a listing (not a ticketing source) and so it is
// distinguishable from licensed rows. Pure ⇒ unit-tested without a network.
export function reshapePromoted(
  rows: PromotedRow[],
  artistNameById: Map<string, string>,
): LicensedEvent[] {
  return rows.map((r) => {
    const names = (r.artist_ids ?? [])
      .map((id) => artistNameById.get(id))
      .filter((n): n is string => !!n);
    const v = r.venue;
    return {
      // Key the feed on the event id (feed logic keys on licensed_event_id); the
      // "promoted:" prefix guarantees it can never collide with a licensed id.
      licensed_event_id: `promoted:${r.event_id}`,
      source_provider: "promoted",
      external_id: r.event_id,
      title: r.title ?? (names.length ? names.join(", ") : "Live event"),
      category: r.category,
      subsegment: r.subsegment,
      performer: names.length ? names.join(", ") : null,
      start_time: r.start_time,
      end_time: r.end_time,
      status: r.status,
      on_sale_status: null,
      price_min: r.price_min,
      price_max: r.price_max,
      currency: r.currency,
      is_free: r.is_free,
      ticket_url: r.ticket_url,
      image_url: r.image_url,
      venue_name: v?.name ?? null,
      venue_city: v?.city ?? null,
      venue_area: v?.area ?? null,
      venue_address: v?.address ?? null,
      venue_lat: v?.lat ?? null,
      venue_lng: v?.lng ?? null,
      confidence: r.confidence,
    };
  });
}

const PAGE = 1000; // Range window per request (matches licensed.ts).
const SAFETY_MAX = 100_000; // loud stop, never a silent truncation.

async function fetchAllRows(
  url: string,
  key: string,
  endpoint: string,
): Promise<unknown[]> {
  const all: unknown[] = [];
  for (let from = 0; ; ) {
    const to = from + PAGE - 1;
    const res = await fetch(endpoint, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Range-Unit": "items",
        Range: `${from}-${to}`,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`Supabase promoted read failed (${res.status}): ${await res.text()}`);
    }
    const batch = (await res.json()) as unknown;
    if (!Array.isArray(batch)) throw new Error("Unexpected Supabase response shape");
    all.push(...batch);
    if (batch.length === 0) break;
    from += batch.length; // advance by ACTUAL rows — robust to any server cap
    if (all.length > SAFETY_MAX) {
      throw new Error(
        `promoted feed exceeded ${SAFETY_MAX} rows — refusing to silently truncate.`,
      );
    }
  }
  return all;
}

// Fetch all promoted events matching opts, joined + reshaped into LicensedEvent[].
// Resolves artist names in ONE batched follow-up query. Returns [] (never throws)
// when Supabase env is unset so the licensed feed still renders — the promoted
// union is additive and its absence must never blank the whole page. A real
// read/HTTP error DOES throw, surfaced as an honest error like the licensed feed.
export async function fetchPromotedEvents(
  opts?: PromotedQueryOpts,
): Promise<LicensedEvent[]> {
  const { url, key } = supaEnv();
  if (!url || !key) return [];

  const endpoint = `${url}/rest/v1/event?${buildPromotedQuery(opts)}`;
  const rows = (await fetchAllRows(url, key, endpoint)) as PromotedRow[];
  if (rows.length === 0) return [];

  return reshapePromoted(rows, await resolveArtistNames(url, key, rows));
}


// ── Detail surface (SPRINT Step 9, Contract #28) ─────────────────────────────
// One event by id. The `promoted:` prefix is the id shape reshapePromoted
// assigns, so it is also the dispatch key: it says which TABLE the row lives in
// without a lookup. Splitting on the first colon only — a uuid contains none,
// and a stricter parse would reject ids this module itself produced.

export const PROMOTED_ID_PREFIX = "promoted:";

export type EventIdRoute =
  | { kind: "promoted"; id: string }
  | { kind: "licensed"; id: string };

/** Pure dispatch — which read serves this id, and what to ask it for. */
export function routeForEventId(rawId: string): EventIdRoute | null {
  const id = rawId.trim();
  if (!id) return null;
  if (id.startsWith(PROMOTED_ID_PREFIX)) {
    const inner = id.slice(PROMOTED_ID_PREFIX.length);
    return inner ? { kind: "promoted", id: inner } : null;
  }
  return { kind: "licensed", id };
}

/** ONE promoted event, or null when no such row exists. Errors are NOT
 *  swallowed: a failed read throws, because an empty page dressed as
 *  "no such event" is the swallowed-corrupt-data class. */
export async function fetchPromotedEventById(
  id: string,
): Promise<LicensedEvent | null> {
  const { url, key } = supaEnv();
  if (!url || !key) {
    throw new Error(
      "Supabase read env not set — configure NEXT_PUBLIC_SUPABASE_URL and " +
      "NEXT_PUBLIC_SUPABASE_ANON_KEY (the publishable key).",
    );
  }
  const endpoint =
    `${url}/rest/v1/event?${buildPromotedQuery({ eventId: id, anyStatus: true })}`;
  const rows = (await fetchAllRows(url, key, endpoint)) as PromotedRow[];
  if (rows.length === 0) return null;

  const names = await resolveArtistNames(url, key, rows);
  return exactlyOneOrNull(reshapePromoted(rows, names), id, "event");
}
