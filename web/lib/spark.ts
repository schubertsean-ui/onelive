// Spark Line read path (migrations 0018 + 0019; UI Canon §4). Attaches an
// APPROVED Spark Line to a feed card ONLY by a stable ACT IDENTITY (`artist_ref`),
// never by display name. A performer NAME is not an identity: two different acts
// can share the same name, so a name-keyed join could put one act's descriptor —
// including the tier-C "drafted from the artist's own materials" attribution — on
// a same-name act's card (adversarial-review #148, attacker-smuggle lens).
// Requiring an identity ref on BOTH sides makes that misattribution impossible by
// construction.
//
// Until the ratified identity-resolution enrichment (MusicBrainz/Wikidata; gated,
// founder-crucial) populates `artist_ref` on both licensed_event rows and approved
// spark_line rows, events carry no ref and this path attaches NOTHING — fail closed
// by construction, not by the accident of empty tables. Display only: this path
// NEVER reorders, filters, or gates the feed, and any read failure returns an
// empty map so the feed renders exactly as it would without Spark Lines.
import { supaEnv, type LicensedEvent, type SparkLine } from "./licensed";

// The identity join key: an event's resolved stable act ref (e.g. a MusicBrainz
// id), trimmed. Absent/blank = no identity resolved yet, so the event is never
// eligible to receive a Spark Line — a name is deliberately NOT accepted here.
export function eventRef(e: LicensedEvent): string {
  return (e.artist_ref ?? "").trim();
}

// PostgREST parses `in.(...)` AFTER percent-decoding the whole value, so the list
// is built as one string and encoded once by the caller. Each ref is double-quoted
// and an embedded quote is doubled, so a value can never break out of the list.
export function buildSparkInList(refs: string[]): string {
  return `in.(${refs.map((r) => `"${r.replace(/"/g, '""')}"`).join(",")})`;
}

// Pure: attach resolved Spark Lines onto events by IDENTITY ref. Order and length
// are preserved exactly (display-only, never a ranking input); an event with no
// ref, or no row for its ref, is left untouched (spark stays undefined). Name is
// never consulted, so a same-name act cannot inherit another act's line.
export function attachSparkLines(
  events: LicensedEvent[],
  byRef: Map<string, SparkLine>,
): LicensedEvent[] {
  return events.map((e) => {
    const ref = eventRef(e);
    const spark = ref ? byRef.get(ref) : undefined;
    return spark ? { ...e, spark } : e;
  });
}

// Fetch APPROVED Spark Lines for the given events' resolved identity refs in ONE
// request, keyed by `artist_ref`. RLS already restricts reads to approved rows;
// `status=eq.approved` is belt-and-suspenders. Never throws — a failure, OR no
// resolved refs at all, yields an empty map so nothing is attached.
export async function fetchApprovedSparkLines(
  events: LicensedEvent[],
): Promise<Map<string, SparkLine>> {
  const byRef = new Map<string, SparkLine>();
  const { url, key } = supaEnv();
  if (!url || !key) return byRef;
  const refs = [...new Set(events.map(eventRef).filter((r) => r.length > 0))];
  if (!refs.length) return byRef; // no identity resolved → fail closed, no query
  const endpoint =
    `${url}/rest/v1/spark_line?select=artist_ref,text,tier,attribution` +
    `&status=eq.approved&artist_ref=${encodeURIComponent(buildSparkInList(refs))}`;
  try {
    const res = await fetch(endpoint, {
      headers: { apikey: key, Authorization: `Bearer ${key}` },
      cache: "no-store",
    });
    if (!res.ok) return byRef;
    const rows = (await res.json()) as Array<{
      artist_ref: string | null;
      text: string;
      tier: string;
      attribution: string | null;
    }>;
    for (const r of rows) {
      if (r.artist_ref && r.text) {
        byRef.set(r.artist_ref, { text: r.text, tier: r.tier, attribution: r.attribution });
      }
    }
  } catch {
    return byRef;
  }
  return byRef;
}

// Convenience for the server read: resolve + attach in one call. ADDITIVE by
// contract — any failure returns the feed UNCHANGED, never blanking or altering
// it (mirrors the promoted-union fallback in page.tsx: a Spark Line problem must
// never cost a working feed).
export async function withSparkLines(events: LicensedEvent[]): Promise<LicensedEvent[]> {
  try {
    const byRef = await fetchApprovedSparkLines(events);
    return attachSparkLines(events, byRef);
  } catch {
    return events;
  }
}
