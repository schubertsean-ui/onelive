// The CAPCOG market boundary, enforced on the READ path.
//
// Why this file exists: the founder's report was "if you show San Antonio you've
// failed". The cause was upstream — importers requested a 75-mile circle around
// downtown Austin, and San Antonio sits about 75 miles away, so Bexar County was
// inside the query by construction. That is fixed at the source, but fixing
// acquisition is not the same as protecting the reader: rows already in the
// database, rows from any future source, and rows from a mis-tagged feed would
// all still reach the page. So the boundary is enforced HERE too, at the last
// step before a person sees a listing.
//
// ONE source of truth: capcog-boundary.json is GENERATED from
// worker/region/capcog.py by tools/gen_region_boundary.py, and a test asserts
// the committed file still matches. A hand-maintained TypeScript copy of the
// county tables would drift from the Python one, and then the server and the
// site would be enforcing two different markets — the incomplete-enumeration
// class, in the place it would do the most damage.
import boundary from "./capcog-boundary.json";

const PLACES: Record<string, string> = boundary.places;
const OUTSIDE: Record<string, string> = boundary.known_outside;

export type RegionVerdict = true | false | null;

/** Lowercase/trim a place name, dropping a trailing ZIP and state suffix.
 *  Venue cities arrive as "Austin", "Austin, TX" and "Austin, TX 78701". */
export function normalizePlace(value: string | null | undefined): string | null {
  if (!value) return null;
  let text = String(value).trim().toLowerCase();
  if (!text) return null;
  text = text.replace(/[\s,]+\d{5}(?:-\d{4})?$/, "").trim();
  for (const suffix of [", tx", ", texas", " tx", " texas"]) {
    if (text.endsWith(suffix)) text = text.slice(0, -suffix.length).trim();
  }
  text = text.replace(/^[,\s]+|[,\s]+$/g, "");
  return text || null;
}

/** TRI-STATE membership: true (in CAPCOG) / false (known outside) / null
 *  (unrecognised). Null is deliberate — see filterToCapcog for what we do with
 *  it, and why guessing in either direction is a defect. */
export function inCapcog(city: string | null | undefined): RegionVerdict {
  const key = normalizePlace(city);
  if (key === null) return null;
  if (key in PLACES) return true;
  if (key in OUTSIDE) return false;
  return null;
}

export interface RegionFilterResult<T> {
  kept: T[];
  /** Rows we refused to show: known-outside places. This is the defect count. */
  droppedOutside: T[];
  /** Rows we could not classify. KEPT — see below. */
  unknown: T[];
}

/**
 * Keep only what a person in the CAPCOG area could actually attend.
 *
 * The asymmetry here is deliberate and is the whole design decision:
 *
 *   known OUTSIDE  -> DROPPED. San Antonio, New Braunfels, Seguin, Killeen.
 *                     Showing these is the reported defect.
 *   known INSIDE   -> kept.
 *   UNRECOGNISED   -> KEPT, and counted.
 *
 * Dropping the unrecognised ones would be the easy call and it would be wrong.
 * The place table is a floor, not a census: a small Bastrop or Llano venue we
 * have not catalogued yet is exactly the long-tail coverage this product is
 * trying to win, and silently deleting it would turn a data gap into an
 * invisible one — while making the feed look cleaner. Seven of the ten counties
 * currently have zero coverage; a filter that quietly discards anything it does
 * not recognise would help hide that.
 *
 * So the unknowns are shown and counted, and the count is the worklist for
 * extending the table. That is the same tri-state discipline the server uses.
 */
export function filterToCapcog<T extends { venue_city?: string | null; city?: string | null }>(
  rows: T[],
): RegionFilterResult<T> {
  const kept: T[] = [];
  const droppedOutside: T[] = [];
  const unknown: T[] = [];
  for (const row of rows) {
    const verdict = inCapcog(row.venue_city ?? row.city);
    if (verdict === false) {
      droppedOutside.push(row);
      continue;
    }
    if (verdict === null) unknown.push(row);
    kept.push(row);
  }
  return { kept, droppedOutside, unknown };
}
