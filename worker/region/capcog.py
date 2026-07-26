"""The CAPCOG service area, as a BOUNDARY rather than an approximation.

Why this module exists: the importers scoped "our market" as a 75-mile circle
around downtown Austin (`ticketmaster.py`, `seatgeek.py`). San Antonio sits
about 75 miles from downtown Austin, so Bexar County was INSIDE that circle by
construction — which is why the live feed carried the Majestic Theatre and
Freeman Expo Hall. Those rows were not a data defect; they were exactly what a
circle asks for. R-025 recorded the gap and deferred it; the founder flagged
the user-visible result (2026-07-26), which fires that trigger.

CAPCOG is the Capital Area Council of Governments: TEN counties, enumerated
below. Bexar (San Antonio), Comal (New Braunfels), Guadalupe (Seguin), Bell
(Killeen/Temple/Belton) and Lampasas are NOT members, however close they fall
to a radius drawn from Austin.

DESIGN, and it is the same discipline the importer arc paid for: membership is
TRI-STATE, never boolean.

    True   the place is in a CAPCOG county
    False  the place is known to be OUTSIDE it
    None   we do not know this place

`None` is the important one. A boolean predicate has to guess, and a guess in
either direction is a defect: guessing True publishes San Antonio events to an
Austin audience, guessing False silently deletes real CAPCOG coverage. So an
unknown place is neither admitted nor discarded quietly — it is REPORTED, and
`region_report()` exists to make the unknowns a visible worklist rather than an
invisible loss. That is the failure-reads-as-empty lesson applied to geography.
"""
from __future__ import annotations

import re
from typing import Optional

# The ten member counties. This is the boundary; everything else derives.
CAPCOG_COUNTIES: frozenset = frozenset({
    "bastrop", "blanco", "burnet", "caldwell", "fayette",
    "hays", "lee", "llano", "travis", "williamson",
})

# Places within the member counties, keyed to their county. Incorporated cities,
# towns, villages and the notable unincorporated communities a venue address
# actually uses. Kept as data, not code, so extending coverage is a data edit
# whose effect a test can measure.
CAPCOG_PLACES: dict = {
    # --- Travis -------------------------------------------------------------
    "austin": "travis", "pflugerville": "travis", "lakeway": "travis",
    "bee cave": "travis", "bee caves": "travis", "west lake hills": "travis",
    "rollingwood": "travis", "sunset valley": "travis", "manor": "travis",
    "lago vista": "travis", "jonestown": "travis", "briarcliff": "travis",
    "the hills": "travis", "point venture": "travis", "san leanna": "travis",
    "mustang ridge": "travis", "volente": "travis", "webberville": "travis",
    "creedmoor": "travis", "garfield": "travis", "del valle": "travis",
    "manchaca": "travis", "spicewood": "travis",
    # --- Williamson ---------------------------------------------------------
    "round rock": "williamson", "georgetown": "williamson",
    "cedar park": "williamson", "leander": "williamson", "hutto": "williamson",
    "taylor": "williamson", "liberty hill": "williamson",
    "granger": "williamson", "bartlett": "williamson", "florence": "williamson",
    "jarrell": "williamson", "thrall": "williamson", "weir": "williamson",
    "coupland": "williamson", "walburg": "williamson", "andice": "williamson",
    "serenada": "williamson", "brushy creek": "williamson",
    # --- Hays ---------------------------------------------------------------
    "san marcos": "hays", "kyle": "hays", "buda": "hays",
    "dripping springs": "hays", "wimberley": "hays", "woodcreek": "hays",
    "niederwald": "hays", "uhland": "hays", "mountain city": "hays",
    "driftwood": "hays", "bear creek": "hays", "hays": "hays",
    # --- Bastrop ------------------------------------------------------------
    "bastrop": "bastrop", "elgin": "bastrop", "smithville": "bastrop",
    "cedar creek": "bastrop", "red rock": "bastrop", "paige": "bastrop",
    "wyldwood": "bastrop", "mcdade": "bastrop",
    # --- Caldwell -----------------------------------------------------------
    "lockhart": "caldwell", "luling": "caldwell", "martindale": "caldwell",
    "dale": "caldwell", "maxwell": "caldwell", "fentress": "caldwell",
    # --- Burnet -------------------------------------------------------------
    "burnet": "burnet", "marble falls": "burnet", "bertram": "burnet",
    "granite shoals": "burnet", "cottonwood shores": "burnet",
    "highland haven": "burnet", "meadowlakes": "burnet",
    "horseshoe bay": "burnet",   # straddles Burnet/Llano; both are CAPCOG
    # --- Blanco -------------------------------------------------------------
    "johnson city": "blanco", "blanco": "blanco", "round mountain": "blanco",
    "hye": "blanco",
    # --- Llano --------------------------------------------------------------
    "llano": "llano", "sunrise beach village": "llano", "kingsland": "llano",
    "buchanan dam": "llano", "tow": "llano",
    # --- Lee ----------------------------------------------------------------
    "giddings": "lee", "lexington": "lee", "dime box": "lee",
    # --- Fayette ------------------------------------------------------------
    "la grange": "fayette", "schulenburg": "fayette", "flatonia": "fayette",
    "fayetteville": "fayette", "round top": "fayette", "carmine": "fayette",
    "warrenton": "fayette", "ellinger": "fayette",
}

# Places we KNOW are outside CAPCOG. Not required for correctness — anything
# absent from CAPCOG_PLACES already fails to be True — but naming the near
# neighbours turns the single most likely error from an "unknown" into a
# definite NO, so the report distinguishes "we wrongly ingested San Antonio"
# from "we have never heard of this town".
KNOWN_OUTSIDE: dict = {
    # Bexar — the 75-mile-radius casualty this module exists to stop.
    "san antonio": "bexar", "alamo heights": "bexar", "converse": "bexar",
    "helotes": "bexar", "leon valley": "bexar", "live oak": "bexar",
    "selma": "bexar", "terrell hills": "bexar", "universal city": "bexar",
    "windcrest": "bexar", "kirby": "bexar", "shavano park": "bexar",
    "balcones heights": "bexar", "china grove": "bexar",
    # Comal / Guadalupe — the I-35 corridor south of Hays.
    "new braunfels": "comal", "bulverde": "comal", "garden ridge": "comal",
    "canyon lake": "comal", "spring branch": "comal",
    "seguin": "guadalupe", "schertz": "guadalupe", "cibolo": "guadalupe",
    "marion": "guadalupe", "santa clara": "guadalupe",
    # Bell / Lampasas / Kendall — the northern and western near-misses.
    "killeen": "bell", "temple": "bell", "belton": "bell", "harker heights": "bell",
    "copperas cove": "coryell", "salado": "bell", "nolanville": "bell",
    "lampasas": "lampasas", "boerne": "kendall", "comfort": "kendall",
    # Other Texas metros that appear in statewide feeds.
    "houston": "harris", "dallas": "dallas", "fort worth": "tarrant",
    "el paso": "el paso", "corpus christi": "nueces", "waco": "mclennan",
    "lubbock": "lubbock", "amarillo": "potter", "laredo": "webb",
    "brownsville": "cameron", "mcallen": "hidalgo", "galveston": "galveston",
    "college station": "brazos", "bryan": "brazos", "victoria": "victoria",
    "san angelo": "tom green", "abilene": "taylor", "midland": "midland",
    "odessa": "ector", "tyler": "smith", "beaumont": "jefferson",
    "wichita falls": "wichita", "denton": "denton", "plano": "collin",
    "arlington": "tarrant", "irving": "dallas", "frisco": "collin",
    "sugar land": "fort bend", "the woodlands": "montgomery",
    "fredericksburg": "gillespie", "kerrville": "kerr", "gruene": "comal",
}


# Trailing location qualifiers feeds append to a city. Stripped REPEATEDLY, not
# once: "San Antonio, TX, USA" carries two of them, and a single pass left the
# country attached, so the string matched neither the CAPCOG table nor the
# known-outside table and came back UNKNOWN — which the read path KEEPS. That is
# the founder's invariant failing open: San Antonio reaching the page through a
# formatting difference alone. Two-letter forms require a comma so a city whose
# name merely ends in those letters is untouched.
TRAILING_QUALIFIERS = (
    ", tx", ", texas", " tx", " texas",
    ", usa", ", u.s.a.", ", u.s.", ", us", ", united states",
    " usa", " united states",
)

_ZIP_RE = re.compile(r"[\s,]+\d{5}(?:-\d{4})?$")

# "San Antonio, Bexar County, TX" — a county qualifier between the city and the
# state. Found by the evaluator on PR #74 r12: stripping ZIP/state/country was
# not enough, so this shape matched neither table, came back UNKNOWN, and the
# read path KEEPS unknowns. A known-outside city was therefore still reachable
# by writing its county. Requires a leading comma or space so it can never eat
# a place whose own name ends in the word (there is no such CAPCOG place, but
# the guard costs nothing and the alternative fails silently).
_COUNTY_RE = re.compile(r"[\s,]+([a-z][a-z .'-]*?)\s+county$")

# The counties we can decide on directly. Everything in KNOWN_OUTSIDE names the
# county it sits in, so the outside set is derived rather than hand-listed —
# a second hand-maintained list is the incomplete-enumeration class again.
KNOWN_OUTSIDE_COUNTIES: frozenset = frozenset(KNOWN_OUTSIDE.values())


def normalize_place(value: Optional[str]) -> Optional[str]:
    """Lowercase/trim a place name for lookup, or None when there is nothing to
    look up.

    Strips trailing ZIP, state and country qualifiers because feeds write the
    city field every way: 'Austin', 'Austin, TX', 'Austin, TX 78701',
    'Austin, TX, USA'. Stripping runs to a FIXED POINT — one pass per qualifier
    is not enough when a string carries several, and a leftover qualifier makes
    a known place unrecognisable, which is worse than useless: an unrecognised
    place is kept on the read path, so a known-outside city would be shown.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    changed = True
    while changed:
        changed = False
        stripped = _ZIP_RE.sub("", text).strip(" ,")
        if stripped != text:
            text, changed = stripped, True
        stripped = _COUNTY_RE.sub("", text).strip(" ,")
        if stripped != text and stripped:
            text, changed = stripped, True
        for suffix in TRAILING_QUALIFIERS:
            if text.endswith(suffix):
                text = text[: -len(suffix)].strip(" ,")
                changed = True
                break
    return text.strip(" ,") or None


def county_for_place(city: Optional[str]) -> Optional[str]:
    """The CAPCOG county containing `city`, or None when it is not a known
    CAPCOG place (which includes both 'known to be outside' and 'unknown')."""
    key = normalize_place(city)
    if key is None:
        return None
    return CAPCOG_PLACES.get(key)


def in_capcog(city: Optional[str]) -> Optional[bool]:
    """TRI-STATE membership. True / False / None — see the module docstring for
    why None is not collapsed into either answer.

    A missing city is None, not False: an event with no city recorded has not
    been shown to be outside the region, and silently dropping it would be the
    same silent-data-loss class in a different coat.
    """
    key = normalize_place(city)
    if key is None:
        return None
    if key in CAPCOG_PLACES:
        return True
    if key in KNOWN_OUTSIDE:
        return False
    return None


def normalize_county(value: Optional[str]) -> Optional[str]:
    """Lowercase a county name for lookup, dropping the word 'county' and any
    state/country qualifier. 'Bexar County, TX' and 'bexar' are the same fact."""
    key = normalize_place(value)
    if key is None:
        return None
    if key.endswith(" county"):
        key = key[: -len(" county")].strip(" ,")
    return key or None


def in_capcog_county(county: Optional[str]) -> Optional[bool]:
    """TRI-STATE membership from a COUNTY, which is what CAPCOG is actually
    defined by. The place tables are a convenience over this; a row that
    carries its county carries the decisive fact directly."""
    key = normalize_county(county)
    if key is None:
        return None
    if key in CAPCOG_COUNTIES:
        return True
    if key in KNOWN_OUTSIDE_COUNTIES:
        return False
    return None


def _first_usable(row: dict, fields: tuple) -> Optional[str]:
    """The first field whose value survives normalization.

    NOT `a or b`: an empty or whitespace-only `venue_city` is truthy enough to
    beat a perfectly good `city` in Python's `or` (and in JavaScript's `??` an
    empty string wins outright), so `{"venue_city": "   ", "city":
    "San Antonio"}` was reported as a row with no city instead of a row that is
    out of market. Evaluator finding, PR #74 r12 — the boundary was defeatable
    by writing a blank into the preferred field.
    """
    for field in fields:
        if normalize_place(row.get(field)) is not None:
            return row.get(field)
    return None


CITY_FIELDS = ("venue_city", "city")
COUNTY_FIELDS = ("venue_county", "county")


def row_verdict(row: dict) -> Optional[bool]:
    """TRI-STATE membership for a whole row, county evidence first.

    County beats city because CAPCOG *is* ten counties: if a row says Bexar, no
    amount of city ambiguity should let it through. A row is UNKNOWN only when
    neither field decides it, and unknown is still never a guess.
    """
    verdict = in_capcog_county(_first_usable(row, COUNTY_FIELDS))
    if verdict is not None:
        return verdict
    # A city string can itself carry the county ("San Antonio, Bexar County").
    city_raw = _first_usable(row, CITY_FIELDS)
    if city_raw is not None:
        match = _COUNTY_RE.search(str(city_raw).strip().lower())
        if match:
            verdict = in_capcog_county(match.group(1))
            if verdict is not None:
                return verdict
    return in_capcog(city_raw)


def region_report(rows: list) -> dict:
    """Partition rows by CAPCOG membership and return the counts an operator
    needs, INCLUDING the unknowns by name.

    `rows` are dicts carrying a city under `venue_city` or `city`. The report is
    deliberately shaped for the question "what are we getting wrong?": the
    outside/unknown lists are the worklist, not a footnote.
    """
    inside: dict = {}
    outside: dict = {}
    unknown: dict = {}
    by_county: dict = {"inside": {}, "outside": {}}
    missing = 0
    credited: set = set()
    for row in rows:
        key = normalize_place(_first_usable(row, CITY_FIELDS))
        verdict = row_verdict(row)
        county = normalize_county(_first_usable(row, COUNTY_FIELDS))
        if verdict is True and county in CAPCOG_COUNTIES:
            credited.add(county)
        if key is None:
            # No usable city. The row is still decidable if it names its
            # county — and a county-decided row must NOT be filed under
            # "missing city", which reads as "nothing to see here".
            if verdict is True and county:
                by_county["inside"][county] = by_county["inside"].get(county, 0) + 1
            elif verdict is False and county:
                by_county["outside"][county] = by_county["outside"].get(county, 0) + 1
            else:
                missing += 1
            continue
        if verdict is True:
            inside[key] = inside.get(key, 0) + 1
        elif verdict is False:
            outside[key] = outside.get(key, 0) + 1
        else:
            unknown[key] = unknown.get(key, 0) + 1
    covered = {CAPCOG_PLACES[p] for p in inside if p in CAPCOG_PLACES}
    covered |= set(by_county["inside"]) | credited
    return {
        "inside_count": sum(inside.values()) + sum(by_county["inside"].values()),
        "outside_count": sum(outside.values()) + sum(by_county["outside"].values()),
        "unknown_count": sum(unknown.values()),
        "missing_city_count": missing,
        "inside_by_place": dict(sorted(inside.items())),
        "outside_by_place": dict(sorted(outside.items())),
        "unknown_by_place": dict(sorted(unknown.items())),
        "inside_by_county": dict(sorted(by_county["inside"].items())),
        "outside_by_county": dict(sorted(by_county["outside"].items())),
        "counties_covered": sorted(covered),
        "counties_absent": sorted(CAPCOG_COUNTIES - covered),
    }
