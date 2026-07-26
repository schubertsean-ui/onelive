// Read the REAL licensed events straight from Supabase (PostgREST), server-side.
// No SDK dependency — a plain fetch with the publishable (anon) key, which the
// RLS `public_read` policy + column grant scope to the public listing columns
// (never `raw`). Errors propagate so the UI renders an honest error state, never
// a fake-empty feed.

// Built-in PUBLIC defaults so the read path works with ZERO deployment config
// (founder-directed 2026-07-24). These are NOT secrets: the Supabase URL and the
// PUBLISHABLE (anon) key are designed to ship in client code — every visitor's
// browser already carries them — and the real security boundary is row-level
// security (RLS on `licensed_event`: public read of listing columns only, `raw`
// revoked, the guarded event/promote path untouched), never the key's secrecy.
// A real secret (service_role, Clerk secret) is NEVER committed. Any env var
// OVERRIDES these, so production can point elsewhere without a code change.
// See docs/DEPLOY.md.
const _DEFAULT_SUPABASE_URL = "https://vqipjlvzfiwnandjumvx.supabase.co";
const _DEFAULT_SUPABASE_ANON_KEY = "sb_publishable_cWk_eNqbMWGIIFQf5B5hIg_CFqjAyac";

// Read at call time (not module load) so values are correct per request and the
// functions are testable. Server-side read, so it prefers the plain runtime
// names (Sensitive-safe), then the NEXT_PUBLIC_ forms, then the public default.
export function supaEnv(): { url?: string; key?: string } {
  return {
    url: process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL ?? _DEFAULT_SUPABASE_URL,
    key: process.env.SUPABASE_ANON_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? _DEFAULT_SUPABASE_ANON_KEY,
  };
}

// Exactly the columns the migration grants to anon/authenticated (raw excluded).
const COLUMNS = [
  "licensed_event_id", "source_provider", "external_id", "title", "category",
  "subsegment", "performer", "start_time", "end_time", "status", "on_sale_status",
  "price_min", "price_max", "currency", "is_free", "ticket_url", "image_url",
  "venue_name", "venue_city", "venue_area", "venue_address", "venue_lat",
  "venue_lng", "confidence",
].join(",");

export type LicensedEvent = {
  licensed_event_id: string;
  source_provider: string;
  external_id: string;
  title: string;
  category: string | null;
  subsegment: string | null;
  performer: string | null;
  start_time: string | null;
  end_time: string | null;
  status: string;
  on_sale_status: string | null;
  price_min: number | null;
  price_max: number | null;
  currency: string | null;
  is_free: boolean | null;
  ticket_url: string | null;
  image_url: string | null;
  venue_name: string | null;
  venue_city: string | null;
  venue_area: string | null;
  venue_address: string | null;
  venue_lat: number | null;
  venue_lng: number | null;
  confidence: string;
};

export function supabaseConfigured(): boolean {
  const { url, key } = supaEnv();
  return !!url && !!key;
}

// Where the Supabase URL resolved from (for the health endpoint — only the
// SOURCE name, never the value). "built-in-default" = the committed public
// fallback (no env override present).
export function supabaseSource(): "SUPABASE_URL" | "NEXT_PUBLIC_SUPABASE_URL" | "built-in-default" {
  if (process.env.SUPABASE_URL) return "SUPABASE_URL";
  if (process.env.NEXT_PUBLIC_SUPABASE_URL) return "NEXT_PUBLIC_SUPABASE_URL";
  return "built-in-default";
}

// Lightweight reachability probe for /api/health: confirms the publishable key
// can read `licensed_event` through RLS and returns the row COUNT only (no rows,
// no secret). Never throws — reports the failure so config problems are visible.
export async function probeLicensed(): Promise<{ reachable: boolean; count: number | null; error?: string }> {
  const { url, key } = supaEnv();
  if (!url || !key) return { reachable: false, count: null, error: "supabase env not set" };
  try {
    const res = await fetch(`${url}/rest/v1/licensed_event?select=licensed_event_id`, {
      headers: { apikey: key, Authorization: `Bearer ${key}`, "Range-Unit": "items", Range: "0-0", Prefer: "count=exact" },
      cache: "no-store",
    });
    if (!res.ok) return { reachable: false, count: null, error: `HTTP ${res.status}` };
    const cr = res.headers.get("content-range"); // e.g. "0-0/755"
    const n = cr && cr.includes("/") ? Number.parseInt(cr.split("/")[1], 10) : NaN;
    return { reachable: true, count: Number.isFinite(n) ? n : null };
  } catch (e) {
    return { reachable: false, count: null, error: e instanceof Error ? e.message : "fetch failed" };
  }
}

export type LicensedQueryOpts = {
  category?: string;
  fromISO?: string; // start_time >= this
  toISO?: string; // start_time <= this
  // Detail surface: select ONE row by id. Same builder, same trust rules — the
  // detail page must not become a second read shape with its own behaviour.
  eventId?: string;
  // Detail surface only. The feed shows `scheduled` + `moved`, which is a
  // relevance filter over a list nobody asked for by name. A visitor who
  // followed a LINK to one event asked for that event: telling them it was
  // cancelled is the honest answer, and 404-ing it is the feed's filter
  // silently deciding an event they can see a link to does not exist.
  anyStatus?: boolean;
};

// Pure PostgREST query-string builder (no env, no network) — unit-tested. Two
// TRUST-CRITICAL rules: it never filters on `confidence` (no state, disputed
// included, is dropped), and it bakes in NO row limit — windowing is done by the
// pagination loop below via Range headers, so nothing is capped by position. The
// order carries a unique tiebreaker (licensed_event_id) so paging is stable.
export function buildLicensedQuery(opts?: LicensedQueryOpts): string {
  const p = new URLSearchParams();
  p.set("select", COLUMNS);
  // status: show scheduled + moved; never hide anything by confidence.
  if (!opts?.anyStatus) p.append("status", "in.(scheduled,moved)");
  if (opts?.eventId) p.append("licensed_event_id", `eq.${opts.eventId}`);
  if (opts?.category) p.append("category", `eq.${opts.category}`);
  if (opts?.fromISO) p.append("start_time", `gte.${opts.fromISO}`);
  if (opts?.toISO) p.append("start_time", `lte.${opts.toISO}`);
  p.set("order", "start_time.asc,licensed_event_id.asc");
  return p.toString();
}

const PAGE = 1000; // Range window per request.
const SAFETY_MAX = 100_000; // loud stop, never a silent truncation.

// Fetch ALL matching rows, paginating with Range headers until a page comes
// back empty. PostgREST caps a single response server-side (Supabase default
// 1000 rows), so a single request WOULD silently drop everything past that cap —
// including a `disputed` row at position 1001. We advance by the actual rows
// returned, so no event is ever hidden by position. If the catalog ever exceeds
// the safety bound we THROW (surfaced as an honest error), never truncate.
export async function fetchLicensedEvents(
  opts?: LicensedQueryOpts,
): Promise<LicensedEvent[]> {
  const { url, key } = supaEnv();
  if (!url || !key) {
    throw new Error(
      "Supabase read env not set — configure NEXT_PUBLIC_SUPABASE_URL and " +
      "NEXT_PUBLIC_SUPABASE_ANON_KEY (the publishable key).",
    );
  }
  const query = buildLicensedQuery(opts);
  const endpoint = `${url}/rest/v1/licensed_event?${query}`;
  const all: LicensedEvent[] = [];
  for (let from = 0; ; ) {
    const to = from + PAGE - 1;
    const res = await fetch(endpoint, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Range-Unit": "items",
        Range: `${from}-${to}`,
      },
      cache: "no-store", // always fresh — reflects the latest import
    });
    if (!res.ok) {
      throw new Error(`Supabase read failed (${res.status}): ${await res.text()}`);
    }
    const batch = (await res.json()) as unknown;
    if (!Array.isArray(batch)) throw new Error("Unexpected Supabase response shape");
    all.push(...(batch as LicensedEvent[]));
    if (batch.length === 0) break; // exhausted
    from += batch.length; // advance by ACTUAL rows — robust to any server cap
    if (all.length > SAFETY_MAX) {
      throw new Error(
        `licensed feed exceeded ${SAFETY_MAX} rows — refusing to silently ` +
        `truncate; add narrower filters or paginate the UI.`,
      );
    }
  }
  return all;
}


// ── Detail surface (SPRINT Step 9, Contract #28) ─────────────────────────────
/** ONE licensed event by id, or null when no such row exists. A failed read
 *  THROWS — the page must be able to say "couldn't load" instead of showing an
 *  empty result that reads as "no such event". */
export async function fetchLicensedEventById(
  id: string,
): Promise<LicensedEvent | null> {
  const rows = await fetchLicensedEvents({ eventId: id, anyStatus: true });
  return rows[0] ?? null;
}
