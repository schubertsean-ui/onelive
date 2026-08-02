// Spark Line read path (migration 0018; UI Canon §4). Resolves APPROVED Spark
// Lines by performer key and attaches them to feed cards. A Spark Line is
// display only: this path NEVER reorders, filters, or gates the feed, and a
// missing line is an honest gap (never a fabricated stand-in). The union with
// the feed is additive — any read failure returns an empty map so the feed
// renders exactly as it would without Spark Lines.
import { supaEnv, type LicensedEvent, type SparkLine } from "./licensed";

// The join key: lower-cased, trimmed performer name. Mirrors
// worker/descriptor/store.artist_key so a line written for an act resolves to
// the same act on the licensed feed (`performer`) and the promoted feed
// (resolved `artist.name`, joined as a comma list — matched whole here).
export function sparkKey(name: string | null | undefined): string {
  return (name ?? "").trim().toLowerCase();
}

// PostgREST parses `in.(...)` AFTER percent-decoding the whole value, so the
// list is built as one string and encoded once by the caller. Values contain
// spaces (artist keys), so each is double-quoted; an embedded quote is doubled.
export function buildSparkInList(keys: string[]): string {
  return `in.(${keys.map((k) => `"${k.replace(/"/g, '""')}"`).join(",")})`;
}

// Pure: attach resolved Spark Lines onto events by performer key. Order and
// length are preserved exactly (display-only, never a ranking input); a missing
// key leaves the event untouched (spark stays undefined/null).
export function attachSparkLines(
  events: LicensedEvent[],
  byKey: Map<string, SparkLine>,
): LicensedEvent[] {
  return events.map((e) => {
    const spark = byKey.get(sparkKey(e.performer));
    return spark ? { ...e, spark } : e;
  });
}

// Fetch APPROVED Spark Lines for the given performers in ONE request. RLS
// already restricts reads to approved rows; `status=eq.approved` is
// belt-and-suspenders. Never throws — a failure yields an empty map.
export async function fetchApprovedSparkLines(
  performers: Array<string | null>,
): Promise<Map<string, SparkLine>> {
  const byKey = new Map<string, SparkLine>();
  const { url, key } = supaEnv();
  if (!url || !key) return byKey;
  const keys = [...new Set(performers.map(sparkKey).filter((k) => k.length > 0))];
  if (!keys.length) return byKey;
  const endpoint =
    `${url}/rest/v1/spark_line?select=artist_key,text,tier,attribution` +
    `&status=eq.approved&artist_key=${encodeURIComponent(buildSparkInList(keys))}`;
  try {
    const res = await fetch(endpoint, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      cache: "no-store",
    });
    if (!res.ok) return byKey;
    const rows = (await res.json()) as Array<{
      artist_key: string;
      text: string;
      tier: string;
      attribution: string | null;
    }>;
    for (const r of rows) {
      if (r.artist_key && r.text) {
        byKey.set(r.artist_key, { text: r.text, tier: r.tier, attribution: r.attribution });
      }
    }
  } catch {
    return byKey;
  }
  return byKey;
}

// Convenience for the server read: resolve + attach in one call. ADDITIVE by
// contract — any failure returns the feed UNCHANGED, never blanking or altering
// it (mirrors the promoted-union fallback in page.tsx: a Spark Line problem must
// never cost a working feed).
export async function withSparkLines(events: LicensedEvent[]): Promise<LicensedEvent[]> {
  try {
    const byKey = await fetchApprovedSparkLines(events.map((e) => e.performer));
    return attachSparkLines(events, byKey);
  } catch {
    return events;
  }
}
