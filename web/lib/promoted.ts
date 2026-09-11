import {
  exactlyOneOrNull,
  supaEnv,
  windowBound,
  windowFilter,
  type LicensedEvent,
} from "./licensed";

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
  "source_name",
  "source_url",
  "venue:venue_id(name,city,area,address,lat,lng)",
].join(",");

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
  source_name: string | null;
  source_url: string | null;
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
  fromISO?: string;
  toISO?: string;
  eventId?: string;
  anyStatus?: boolean;
  includeNullClock?: boolean;
};

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export const PROMOTED_ID_PREFIX = "promoted:";

export type EventIdRoute =
  | { kind: "promoted"; id: string }
  | { kind: "licensed"; id: string };

export function decodeEventId(raw: string): string {
  let id = (raw ?? "").trim();
  if (id.startsWith('"') && id.endsWith('"') && id.length > 1) {
    id = id.slice(1, -1).trim();
  }
  for (let i = 0; i < 2; i++) {
    if (!/%[0-9A-Fa-f]{2}/.test(id)) break;
    try {
      const next = decodeURIComponent(id);
      if (next === id) break;
      id = next;
    } catch {
      break;
    }
  }
  return id;
}

export function routeForEventId(rawId: string): EventIdRoute | null {
  const id = decodeEventId(rawId);
  if (!id) return null;
  if (id.startsWith(PROMOTED_ID_PREFIX)) {
    const inner = id.slice(PROMOTED_ID_PREFIX.length);
    return inner ? { kind: "promoted", id: inner } : null;
  }
  return { kind: "licensed", id };
}

export function eventIdForQuery(raw: string): string | null {
  const route = routeForEventId(raw);
  const candidate = route?.kind === "promoted" ? route.id : decodeEventId(raw);
  if (!candidate) return null;
  if (/%[0-9A-Fa-f]{2}/.test(candidate)) return null;
  if (candidate.toLowerCase().includes("promoted:")) return null;
  if (!UUID_RE.test(candidate)) return null;
  return candidate;
}

export function buildPromotedQuery(opts?: PromotedQueryOpts): string {
  const p = new URLSearchParams();
  p.set("select", EVENT_SELECT);
  if (!opts?.anyStatus) p.append("status", "in.(scheduled,moved)");
  if (opts?.eventId) {
    const qid = eventIdForQuery(opts.eventId);
    if (qid) p.append("event_id", `eq.${qid}`);
  }
  if (opts?.category) p.append("category", `eq.${opts.category}`);
  const window = windowFilter(opts?.fromISO, opts?.toISO);
  if (opts?.includeNullClock === false) {
    const from = opts.fromISO ? windowBound(opts.fromISO, "fromISO") : null;
    const to = opts.toISO ? windowBound(opts.toISO, "toISO") : null;
    if (from) p.append("start_time", `gte.${from}`);
    if (to) p.append("start_time", `lte.${to}`);
  } else if (window) {
    p.append("or", window);
  }
  p.set("order", "start_time.asc,event_id.asc");
  return p.toString();
}

async function resolveArtistNames(
  url: string,
  key: string,
  rows: PromotedRow[],
): Promise<Map<string, string>> {
  const ids = [...new Set(rows.flatMap((r) => r.artist_ids ?? []))];
  const byId = new Map<string, string>();
  if (!ids.length) return byId;
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
      venue_url: null,
      venue_phone: null,
      confidence: r.confidence,
      origin_name: r.source_name,
      origin_url: r.source_url,
    };
  });
}

const PAGE = 1000;
const SAFETY_MAX = 100_000;

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
      signal: AbortSignal.timeout(8_000),
    });
    if (!res.ok) {
      throw new Error(`Supabase promoted read failed (${res.status}): ${await res.text()}`);
    }
    const batch = (await res.json()) as unknown;
    if (!Array.isArray(batch)) throw new Error("Unexpected Supabase response shape");
    all.push(...batch);
    if (batch.length === 0) break;
    from += batch.length;
    if (all.length > SAFETY_MAX) {
      throw new Error(
        `promoted feed exceeded ${SAFETY_MAX} rows — refusing to silently truncate.`,
      );
    }
  }
  return all;
}

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

export async function fetchPromotedEventById(
  id: string,
): Promise<LicensedEvent | null> {
  const queryId = eventIdForQuery(id);
  if (!queryId) return null;
  const { url, key } = supaEnv();
  if (!url || !key) {
    throw new Error(
      "Supabase read env not set — configure NEXT_PUBLIC_SUPABASE_URL and " +
      "NEXT_PUBLIC_SUPABASE_ANON_KEY (the publishable key).",
    );
  }
  const endpoint =
    `${url}/rest/v1/event?${buildPromotedQuery({ eventId: queryId, anyStatus: true })}`;
  const rows = (await fetchAllRows(url, key, endpoint)) as PromotedRow[];
  if (rows.length === 0) return null;
  const names = await resolveArtistNames(url, key, rows);
  return exactlyOneOrNull(reshapePromoted(rows, names), queryId, "event");
}
