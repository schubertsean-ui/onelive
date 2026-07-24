// Read the REAL licensed events straight from Supabase (PostgREST), server-side.
// No SDK dependency — a plain fetch with the publishable (anon) key, which the
// RLS `public_read` policy + column grant scope to the public listing columns
// (never `raw`). Errors propagate so the UI renders an honest error state, never
// a fake-empty feed.

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

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
  return !!SUPABASE_URL && !!SUPABASE_KEY;
}

export type LicensedQueryOpts = {
  category?: string;
  fromISO?: string; // start_time >= this
  toISO?: string; // start_time <= this
  limit?: number;
};

// Pure PostgREST query-string builder (no env, no network) — unit-tested. The
// TRUST-CRITICAL rule: this never filters on `confidence`, so no confidence
// state (disputed included) is ever dropped from the result set.
export function buildLicensedQuery(opts?: LicensedQueryOpts): string {
  const p = new URLSearchParams();
  p.set("select", COLUMNS);
  // status: show scheduled + moved; never hide anything by confidence.
  p.append("status", "in.(scheduled,moved)");
  if (opts?.category) p.append("category", `eq.${opts.category}`);
  if (opts?.fromISO) p.append("start_time", `gte.${opts.fromISO}`);
  if (opts?.toISO) p.append("start_time", `lte.${opts.toISO}`);
  p.set("order", "start_time.asc");
  p.set("limit", String(opts?.limit ?? 1000));
  return p.toString();
}

export async function fetchLicensedEvents(
  opts?: LicensedQueryOpts,
): Promise<LicensedEvent[]> {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error(
      "Supabase read env not set — configure NEXT_PUBLIC_SUPABASE_URL and " +
      "NEXT_PUBLIC_SUPABASE_ANON_KEY (the publishable key).",
    );
  }
  const url = `${SUPABASE_URL}/rest/v1/licensed_event?${buildLicensedQuery(opts)}`;
  const res = await fetch(url, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
    },
    // Always fresh — the feed reflects the latest import.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Supabase read failed (${res.status}): ${await res.text()}`);
  }
  const data = (await res.json()) as unknown;
  if (!Array.isArray(data)) throw new Error("Unexpected Supabase response shape");
  return data as LicensedEvent[];
}
