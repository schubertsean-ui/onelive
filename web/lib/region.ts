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

// Generated from the Python source of truth, not hand-listed here. The data
// tables were already generated while this LOGIC was hand-copied, and that is
// exactly where the two normalizers drifted: the Python side learned to strip a
// country suffix and this side did not.
const TRAILING_QUALIFIERS: string[] = boundary.trailing_qualifiers;

const ZIP_RE = /[\s,]+\d{5}(?:-\d{4})?$/;

// "San Antonio, Bexar County, TX", and also a field holding ONLY "Bexar County".
// The leading separator was once required, so a bare county name matched
// nothing and came back unknown — which filterToCapcog KEEPS and renders.
// Evaluator finding, PR #74 r15. Mirrors _COUNTY_RE in the Python source of
// truth; the generated vectors below prove the two agree.
const COUNTY_RE = /(?:^|[\s,]+)([a-z][a-z .'-]*?)\s+county$/;

const COUNTIES: string[] = boundary.counties;
const OUTSIDE_COUNTIES: string[] = Array.from(new Set(Object.values(OUTSIDE)));

// Object.hasOwn, not `key in obj`. `"constructor" in {}` is TRUE — every plain
// object inherits Object.prototype — so an externally-supplied venue city of
// "constructor", "toString" or "valueOf" was classified as a real CAPCOG place.
// Evaluator finding, PR #74 r12 (dataflow-taint). The lookup tables are plain
// JSON objects and the keys come from feed data, so ownership must be checked.
const owns = (obj: Record<string, string>, key: string) => Object.hasOwn(obj, key);

// Strip leading/trailing commas, whitespace AND periods. A trailing period —
// "San Antonio, TX." — is a common scraped shape that otherwise left "…tx."
// unmatched by the " tx" qualifier, so the string normalized to nothing
// recognisable and the read path kept a known-outside city (PR #107 r4).
const trimPunct = (s: string) => s.replace(/^[.,\s]+|[.,\s]+$/g, "");

/** Lowercase/trim a place name, dropping trailing ZIP, state and country
 *  qualifiers. Venue cities arrive as "Austin", "Austin, TX",
 *  "Austin, TX 78701" and "Austin, TX, USA".
 *
 *  Stripping runs to a FIXED POINT. A single pass left "San Antonio, TX, USA"
 *  as-is, so it matched neither table, came back null (unrecognised), and
 *  filterToCapcog KEEPS unrecognised rows — a known-outside city reaching the
 *  page through nothing but a formatting difference. */
export function normalizePlace(value: string | null | undefined): string | null {
  if (!value) return null;
  const text = trimPunct(String(value).trim().toLowerCase());
  if (!text) return null;
  return stripQualifiers(text, true) || null;
}

/**
 * Strip trailing qualifiers to a FIXED POINT.
 *
 * `dropCounty` exists because the two callers want different things from the
 * same string. Lookup wants the bare city, so it drops the county. Reading the
 * county EVIDENCE out of a city string must keep it — and must still remove
 * everything AFTER it, because COUNTY_RE is anchored at the end. Running the
 * county match on the raw string missed "Unlisted Spot, Bexar County, TX"
 * entirely: the ", tx" defeated the anchor, so the decisive fact was dropped
 * and an out-of-market row came back UNKNOWN — which filterToCapcog keeps and
 * renders. Evaluator finding, PR #74 r13.
 */
function stripQualifiers(input: string, dropCounty: boolean): string {
  let text = input;
  let changed = true;
  while (changed) {
    changed = false;
    const stripped = trimPunct(text.replace(ZIP_RE, ""));
    if (stripped !== text) {
      text = stripped;
      changed = true;
    }
    if (dropCounty) {
      const decounty = trimPunct(text.replace(COUNTY_RE, ""));
      if (decounty !== text && decounty) {
        text = decounty;
        changed = true;
      }
    }
    for (const suffix of TRAILING_QUALIFIERS) {
      if (text.endsWith(suffix)) {
        text = trimPunct(text.slice(0, -suffix.length));
        changed = true;
        break;
      }
    }
  }
  return trimPunct(text);
}

/** The county named INSIDE a place string, if it names one. "San Antonio,
 *  Bexar County, TX" carries the decisive fact in the middle of the city
 *  field; this reads it out with the trailing qualifiers removed first. */
export function countyInPlace(value: string | null | undefined): string | null {
  if (!value) return null;
  const text = stripQualifiers(String(value).trim().toLowerCase(), false);
  const match = COUNTY_RE.exec(text);
  return match ? match[1] : null;
}

/** TRI-STATE membership: true (in CAPCOG) / false (known outside) / null
 *  (unrecognised). Null is deliberate — see filterToCapcog for what we do with
 *  it, and why guessing in either direction is a defect. */
export function inCapcog(city: string | null | undefined): RegionVerdict {
  const key = normalizePlace(city);
  if (key === null) return null;
  if (owns(PLACES, key)) return true;
  if (owns(OUTSIDE, key)) return false;
  return null;
}

/** A county name, lowercased, with the word "county" and any state/country
 *  qualifier dropped. "Bexar County, TX" and "bexar" are the same fact. */
export function normalizeCounty(value: string | null | undefined): string | null {
  let key = normalizePlace(value);
  if (key === null) return null;
  if (key.endsWith(" county")) key = trimPunct(key.slice(0, -" county".length));
  return key || null;
}

/** TRI-STATE membership from a COUNTY — what CAPCOG is actually defined by.
 *  The place table is a convenience over this; a row carrying its county
 *  carries the decisive fact, so it must not be ignored just because the city
 *  field is blank or unrecognised. */
export function inCapcogCounty(county: string | null | undefined): RegionVerdict {
  const key = normalizeCounty(county);
  if (key === null) return null;
  if (COUNTIES.includes(key)) return true;
  if (OUTSIDE_COUNTIES.includes(key)) return false;
  return null;
}

export interface RegionRow {
  venue_city?: string | null;
  city?: string | null;
  venue_county?: string | null;
  county?: string | null;
}

// Every location field a row can carry. The boundary reads ALL of them — see
// rowVerdict for why the "first usable field" shortcut was itself the bug.
const LOCATION_FIELDS: (keyof RegionRow)[] = ["venue_county", "county", "venue_city", "city"];

/** TRI-STATE membership for a whole row. Read EVERY location field EVERY way,
 *  then let a KNOWN-OUTSIDE reading from any of them win in the DROP direction.
 *
 *  A boundary whose whole job is "never show San Antonio" must treat a
 *  CONTRADICTION as a drop, never a keep. Three evaluator findings on PR #107
 *  are all the same shape — a known-outside value hidden behind an in-market
 *  one — and are all closed by the same rule:
 *    - county-first precedence let `{ venue_county:"Travis", venue_city:
 *      "San Antonio" }` through (r1);
 *    - a bare outside county name in the city field ("Bexar", no word "County")
 *      leaked as unknown (r2);
 *    - taking only the FIRST usable field let a known-outside value hide in the
 *      OTHER field — `{ venue_county:"Travis", county:"Bexar" }` and
 *      `{ venue_city:"Austin", city:"San Antonio" }` (r3).
 *
 *  So there is no "preferred field" and no early return: gather a verdict from
 *  every field, read each value THREE ways — as a place, as a bare county name,
 *  and as a county embedded in a string ("…, Bexar County, TX") — and combine:
 *  any `false` (known outside) → drop; else any `true` (known inside) → keep;
 *  else `null` (unrecognised) → kept-and-counted. Consequences preserved:
 *  county evidence still RESCUES a merely-unrecognised city (true beats null),
 *  a known-outside county still drops an in-market-looking city (false beats
 *  true), and an EMPTY preferred field can no longer hide a real value in the
 *  fallback field (PR #74 r12) because every field is read, not just the first. */
/** One field VALUE, resolved PLACE-FIRST. A known city is decisive for its own
 *  token, so `"Taylor"` — an in-market Williamson city — is NOT overridden by
 *  the outside Taylor-County reading of the same string (PR #107 r4: reading
 *  every value as a bare county too made a real in-market city collide with a
 *  same-named outside county, and `false` wrongly won). Only when the value is
 *  not a known place do we read it as a county — embedded in a string first
 *  ("…, Bexar County, TX"), then as a bare county name ("Bexar"). */
function tokenVerdict(value: string | null | undefined): RegionVerdict {
  const asPlace = inCapcog(value);
  if (asPlace !== null) return asPlace;
  const embedded = inCapcogCounty(countyInPlace(value));
  if (embedded !== null) return embedded;
  return inCapcogCounty(value);
}

export function rowVerdict(row: RegionRow): RegionVerdict {
  const verdicts = LOCATION_FIELDS.map((field) => tokenVerdict(row[field]));
  if (verdicts.some((v) => v === false)) return false;
  if (verdicts.some((v) => v === true)) return true;
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
export function filterToCapcog<T extends RegionRow>(
  rows: T[],
): RegionFilterResult<T> {
  const kept: T[] = [];
  const droppedOutside: T[] = [];
  const unknown: T[] = [];
  for (const row of rows) {
    const verdict = rowVerdict(row);
    if (verdict === false) {
      droppedOutside.push(row);
      continue;
    }
    if (verdict === null) unknown.push(row);
    kept.push(row);
  }
  return { kept, droppedOutside, unknown };
}
