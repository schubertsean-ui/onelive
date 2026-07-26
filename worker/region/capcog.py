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


def normalize_place(value: Optional[str]) -> Optional[str]:
    """Lowercase/trim a place name for lookup, or None when there is nothing to
    look up. Strips a trailing state suffix ('Austin, TX') because feeds write
    the city field both ways."""
    if not value:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    # 'austin, tx' / 'austin, texas' -> 'austin'
    for suffix in (", tx", ", texas", " tx", " texas"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text or None


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
    missing = 0
    for row in rows:
        city = row.get("venue_city") or row.get("city")
        key = normalize_place(city)
        if key is None:
            missing += 1
            continue
        verdict = in_capcog(key)
        if verdict is True:
            inside[key] = inside.get(key, 0) + 1
        elif verdict is False:
            outside[key] = outside.get(key, 0) + 1
        else:
            unknown[key] = unknown.get(key, 0) + 1
    return {
        "inside_count": sum(inside.values()),
        "outside_count": sum(outside.values()),
        "unknown_count": sum(unknown.values()),
        "missing_city_count": missing,
        "inside_by_place": dict(sorted(inside.items())),
        "outside_by_place": dict(sorted(outside.items())),
        "unknown_by_place": dict(sorted(unknown.items())),
        "counties_covered": sorted({CAPCOG_PLACES[p] for p in inside}),
        "counties_absent": sorted(CAPCOG_COUNTIES - {CAPCOG_PLACES[p] for p in inside}),
    }
