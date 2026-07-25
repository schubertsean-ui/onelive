"""Proof that the category resolver classifies from what the SOURCE and VENUE
actually are — the event's own schema.org type, the provider taxonomy, and the
venue's business type — with title keywords only as a last resort, and provenance
on every decision. Real Austin examples. Pure: no network, no DB."""
from worker.classify import resolve_category
from worker.importers.domain_map import UNMAPPED


# ── Signal 1: the event's OWN schema.org @type wins over everything ───────────

def test_schema_type_is_authoritative():
    # A JSON-LD MusicEvent at Mohawk is live-music by its OWN declared type —
    # even if the title said nothing musical.
    r = resolve_category(schema_type="http://schema.org/MusicEvent", title="Friday at Mohawk")
    assert r.domain == "live-music"
    assert r.signal == "schema.org @type"

    assert resolve_category(schema_type="TheaterEvent").domain == "theater"
    assert resolve_category(schema_type="schema:ComedyEvent").domain == "comedy"
    assert resolve_category(schema_type="ScreeningEvent").domain == "film"
    assert resolve_category(schema_type="FoodEvent").domain == "food-drink"
    assert resolve_category(schema_type="ExhibitionEvent").domain == "visual-arts"


def test_schema_type_beats_a_misleading_title():
    # Title looks like a lecture; the declared type says it's a comedy show.
    r = resolve_category(schema_type="ComedyEvent", title="A Serious Talk About Physics")
    assert r.domain == "comedy" and r.signal == "schema.org @type"


# ── Signal 2: provider taxonomy (already-mapped licensed feeds) ───────────────

def test_provider_domain_used_when_no_schema_type():
    r = resolve_category(provider_domain="performing-arts", title="Gala")
    assert r.domain == "performing-arts" and r.signal == "provider taxonomy"


# ── Signal 3: what KIND of business hosts it ("you know what the business is") ──

def test_curated_venue_domain_hint_classifies_without_a_title_signal():
    # Cap City Comedy is catalogued as a comedy venue → its shows are comedy,
    # even when the event title carries no comedy keyword.
    r = resolve_category(venue_domain_hint="comedy", title="An Evening With Jordan")
    assert r.domain == "comedy" and r.signal == "venue business type"


def test_venue_business_type_from_places_primarytype():
    # No @type, no curated hint — but we know the venue's business type.
    assert resolve_category(venue_business_type="museum").domain == "visual-arts"
    assert resolve_category(venue_business_type="brewery").domain == "food-drink"
    assert resolve_category(venue_business_type="movie_theater").domain == "film"
    assert resolve_category(venue_business_type="library").domain == "library"
    r = resolve_category(venue_business_type="comedy_club", title="Open Mic")
    assert r.domain == "comedy" and r.signal == "venue business type"


def test_curated_hint_beats_raw_places_type():
    # A curated source domain (human-vetted) outranks a raw Places token.
    r = resolve_category(venue_domain_hint="theater", venue_business_type="bar")
    assert r.domain == "theater" and "source domain=theater" in (r.evidence or "")


# ── Signal 4: title keywords are the LAST resort, and say so in provenance ────

def test_title_is_last_resort_with_honest_provenance():
    r = resolve_category(title="Austin Symphony: Mahler 2")
    assert r.domain == "performing-arts"
    assert r.signal == "title keywords"  # not dressed up as a stronger signal


def test_priority_order_schema_over_provider_over_venue_over_title():
    r = resolve_category(
        schema_type="MusicEvent",
        provider_domain="comedy",
        venue_domain_hint="theater",
        title="Poetry Night",
    )
    assert r.domain == "live-music" and r.signal == "schema.org @type"


# ── Honesty: no signal → UNMAPPED, never a fabricated domain ──────────────────

def test_no_signal_stays_unmapped_never_guessed():
    r = resolve_category(title="XZ Event 9910")
    assert r.domain == UNMAPPED and r.signal == "none" and not r.mapped


def test_genre_attached_only_when_it_agrees_with_the_domain():
    # domain=dance + title "Nutcracker" → genre Ballet (classify_from_title agrees).
    r = resolve_category(schema_type="DanceEvent", title="The Nutcracker")
    assert r.domain == "dance" and r.genre == "Ballet"
    # domain from venue, title genre belongs to a DIFFERENT domain → no genre graft.
    r2 = resolve_category(venue_domain_hint="food-drink", title="Jazz Brunch")
    assert r2.domain == "food-drink" and r2.genre is None
