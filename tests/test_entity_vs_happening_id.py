"""A profile url is an ENTITY id, never a happening id — founder Session
Contract #59 (2026-09-04).

THE HARM, in the founder's words: "artist.com (or chef.com, professor page,
venue homepage) used as listing_url makes every gig the same row and licenses a
write onto the wrong night."

It is an ADOPT-RUNG harm, which is why it is worse than it sounds.
`worker/identity.identity_verdict` treats a stated address as decisive in BOTH
directions on purpose — a stated id is meant to outrank a title and a clock,
because that is what lets a renamed, re-timed listing still be recognised as
itself (R-095/R-097/R-099/R-102). Give that rung an address belonging to a
PRESENTER rather than to a NIGHT and its strength becomes the shortest path in
the tree to writing one night's facts onto another night's public row: rung 1
answers SAME, and every guard the composite rung carries — the collision check,
the untitled check, the source scoping — is skipped, because those only ever
run when nobody stated an id.

WHAT SHIPPED, and the two tests are FACTS rather than guesses about authorship:

  1. ORIGIN — a bare site root in any spelling is a door (`door_address`).
  2. THE PAGE ITSELF — a block-carried address naming the page it was read from
     is a door (`demote_door_addresses`, applied at the persist seam, the only
     place holding both the block and its `source_url`).

A door is RECORDED on `_identity.entity_url` rather than dropped — the founder
asked for it to be stored, it is how we got to the listing, and it is outside
`IDENTITY_FIELDS`, so no comparison can ever read it.

NO OWNERSHIP HEURISTIC IS ADDED, because the founder's Must-not for this
contract forbids one: no card-type test, no path-shape or slug scoring, no
"whose page is this". Four rounds on PR #218 deleted four conventions of that
family. The residual is named in `worker/identity.py` rather than papered over:
a per-entity path that is neither the origin nor the page (`/artists/x` on a
venue calendar) is refused WITHIN a page by `_drop_shared_identities`, and
ACROSS ticks is evidentially identical to a reschedule — the write this stack
exists to license.

Hermetic: the REAL segmenter over REAL fixture pages and the REAL
`create_candidate` canonicalisation. No model, no DB, no network. Nothing here
stubs an extractor, so an identity that arrives could only have come from the
page's own markup.
"""
import pathlib
from datetime import datetime, timedelta, timezone

from worker.candidate_store import _with_identity
from worker.identity import (
    DIFFERENT,
    IDENTITY_FIELDS,
    IDENTITY_KEY,
    NO_IDENTITY,
    SAME,
    UNKNOWN,
    ENTITY_FIELDS,
    ListingIdentity,
    address_identity,
    demote_door_addresses,
    door_address,
    identity_address,
    identity_verdict,
    jsonld_identity,
    read_identity,
    same_location,
    weak_key,
)
from worker.listing_update import (
    MATCH_COLLISION,
    MATCH_IDENTITY,
    ParsedListing,
    PublishedListing,
    adjudicate_page,
    match_kind,
    normalize_title,
)
from worker.segment import segment_events
from worker.crawl_state import VERIFIED_PRESENT

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "entity_vs_happening"
ALWAYS_PASSES = lambda _cid: True        # noqa: E731 — a one-line test double

PRESENTER_URL = "https://marisol-kitchen.example/upcoming"
VENUE_URL = "https://wrenhall.example/calendar"
BAND_URL = "https://castlecreek.band/shows"

SEP_12 = datetime(2026, 9, 12, 19, 0, tzinfo=timezone.utc)
OCT_3 = datetime(2026, 10, 3, 19, 0, tzinfo=timezone.utc)


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def blocks_of(name: str):
    return segment_events(page(name), content_type="text/html")


def stored(name: str, index: int, source_url: str, **payload) -> ListingIdentity:
    """The identity a candidate ends up with, through the real persist seam."""
    block = blocks_of(name)[index]
    return read_identity(_with_identity(payload, block, source_url=source_url))


# --- MUST-DO 1 + 4(1): a profile-only url never SAMEs two different dates -----

def test_the_page_a_listing_was_read_from_is_a_door_not_its_identity():
    """The card declares the very page it sits on. That address belongs to
    every listing on the page, so it is stored as a door and is not comparable.

    THIS IS THE FAILING CASE THE CONTRACT WAS OPENED FOR. Before it shipped,
    `identity_address` accepted the url (it is not a bare root), only ONE card
    on the page declared it — so `_drop_shared_identities` never saw two
    carriers and never fired — and it was stored as `source_href`."""
    identity = stored("presenter_upcoming", 0, PRESENTER_URL,
                      title="Autumn Tasting Menu")
    assert identity.source_href is None and identity.listing_url is None
    assert identity.entity_url == PRESENTER_URL
    assert identity.stated is False, "a door must not read as a stated identity"
    assert identity.stated_any is True, "…but it must still be recorded"


def test_a_door_does_not_make_two_different_nights_one_row():
    """The founder's harm, end to end. The page's own url is what a later tick
    re-reads on a DIFFERENT night's card — which is exactly the case the
    page-wide shared-address rule cannot see, because each tick states it once.

    Both directions are pinned: the verdict is UNKNOWN (not SAME), the match is
    not MATCH_IDENTITY, and no field is written onto the September row from the
    October listing."""
    september = stored("presenter_upcoming", 0, PRESENTER_URL,
                       title="Autumn Tasting Menu")
    october = stored("presenter_upcoming", 0, PRESENTER_URL,
                     title="Guest Chef Night")
    assert identity_verdict(september, october) is UNKNOWN

    row = PublishedListing(event_id="e1", title="Autumn Tasting Menu",
                           start_time=SEP_12, identity=september, source_id="s1")
    hit = ParsedListing(candidate_id="c1", title="Guest Chef Night",
                        start_time=OCT_3, end_time=OCT_3 + timedelta(hours=3),
                        identity=october, source_id="s1")
    assert match_kind(row, hit) != MATCH_IDENTITY
    for decision in adjudicate_page(
            verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
            gate_passes=ALWAYS_PASSES,
            page_text="Autumn Tasting Menu and Guest Chef Night"):
        assert "title" not in decision.fields
        assert "start_time" not in decision.fields


def test_a_homepage_declaration_is_a_door_in_every_spelling():
    """The site ROOT was already refused (PR #218 r11). It is now RECORDED as
    the door it is rather than dropped, which is the constructive half of the
    founder's rule — and it still never reaches a comparable field."""
    identity = stored("presenter_upcoming", 1, PRESENTER_URL,
                      title="Guest Chef Night")
    assert identity.comparable() == {}
    assert identity.entity_url == "https://marisol-kitchen.example/"

    for root in ("https://castlecreek.band", "https://castlecreek.band/",
                 "//castlecreek.band", "/"):
        assert identity_address(root) is None, root
        assert door_address(root) == root, root
        assert address_identity(root, field="source_href").source_href is None
        assert address_identity(root, field="source_href").entity_url == root


def test_the_jsonld_url_is_binned_by_the_same_rule():
    """A band's own JSON-LD stating the band's homepage on every Event — the
    founder's sentence in its most literal form. The two gigs must not collapse
    into one row, and the homepage is kept as the door it is."""
    identities = [read_identity(_with_identity({}, b, source_url=BAND_URL))
                  for b in blocks_of("presenter_jsonld_homepage")]
    assert len(identities) == 2
    for identity in identities:
        assert identity.listing_url is None
        assert identity.entity_url == "https://castlecreek.band"
    assert identity_verdict(*identities) is UNKNOWN
    assert jsonld_identity({"url": "https://castlecreek.band/"}).listing_url is None


# --- MUST-DO 4(5): a person-typed card does not donate a homepage ------------

def test_a_person_card_on_another_entitys_page_donates_no_happening_id():
    """The refusal the presenter ruling KEEPS: a presenter's homepage on
    another entity's card is not that card's listing_url. The card is read (the
    ruling struck the Event-only rule that would have refused it outright) —
    what it declared is simply a door."""
    identity = stored("venue_page_person_card", 0, VENUE_URL, title="Castle Creek")
    assert identity.stated is False
    assert identity.entity_url == "https://castlecreek.band/"

    other = stored("venue_page_person_card", 0, VENUE_URL, title="Castle Creek")
    assert identity_verdict(identity, other) is UNKNOWN


# --- MUST-DO 2 + 4(2): uid and a dated path still match ----------------------

def test_a_dated_path_still_identifies_its_listing():
    """Rung 2 is unchanged. The card that declares a per-listing dated path
    keeps it, and the renamed/re-timed write stays licensed."""
    identity = stored("presenter_upcoming", 2, PRESENTER_URL, title="Harvest Dinner")
    assert identity.source_href == "/upcoming/2026-11-08-harvest-dinner"
    assert identity.entity_url is None

    row = PublishedListing(event_id="e1", title="Harvest Dinner",
                           start_time=SEP_12, identity=identity, source_id="s1")
    hit = ParsedListing(candidate_id="c1", title="Harvest Dinner (Sold Out)",
                        start_time=SEP_12 + timedelta(hours=1),
                        end_time=SEP_12 + timedelta(hours=4),
                        identity=identity, source_id="s1")
    assert match_kind(row, hit) == MATCH_IDENTITY


def test_a_dated_path_beside_a_door_on_one_page_is_untouched():
    """The venue page carries both shapes. The door is binned; the neighbouring
    event card's dated path is not, so one sloppy card never costs the page its
    real identities."""
    identity = stored("venue_page_person_card", 1, VENUE_URL, title="River Delta")
    assert identity.source_href == "/events/2026-08-02-river-delta"
    assert identity.entity_url is None


def test_a_stated_uid_still_matches():
    """Rung 1's other carrier, pinned here because the contract's Must-do 2
    lists the whole ladder as unchanged. The JSON-LD fixture states real
    per-listing urls and ids; neither is a door and both still compare."""
    blocks = segment_events(
        (pathlib.Path(__file__).parent / "fixtures" / "block_identity"
         / "jsonld_two_events.html").read_text(encoding="utf-8"),
        content_type="text/html")
    identities = {i.uid: i for i in (
        read_identity(_with_identity({}, block,
                                     source_url="https://wrenhall.example/events"))
        for block in blocks)}
    assert set(identities) == {"https://wrenhall.example/id/8817", "8818"}
    a, b = identities["https://wrenhall.example/id/8817"], identities["8818"]
    assert a.listing_url == "https://wrenhall.example/events/8817"
    assert a.entity_url is None and b.entity_url is None
    assert identity_verdict(a, a) is SAME
    assert identity_verdict(a, b) is DIFFERENT


# --- MUST-DO 4(3)+(4): composite still works, collision still refuses --------

def test_the_composite_rung_still_works_when_nobody_states_an_id():
    """A page whose cards declare only doors falls to the composite rung, and
    that rung is exactly as it was: (source_id, normalized title, start DATE),
    None when any part is missing."""
    identity = stored("presenter_upcoming", 0, PRESENTER_URL,
                      title="Autumn Tasting Menu")
    assert identity.stated is False, "the composite rung is reached, not skipped"

    key = weak_key("s1", normalize_title("Autumn Tasting Menu!"), SEP_12)
    assert key == ("s1", normalize_title("Autumn Tasting Menu"), SEP_12.date())
    assert key == weak_key("s1", normalize_title("autumn tasting menu"),
                           SEP_12 + timedelta(hours=2))
    assert weak_key("s1", None, SEP_12) is None
    assert weak_key(None, "autumn tasting menu", SEP_12) is None
    assert weak_key("s1", "autumn tasting menu", None) is None


def test_a_collision_on_one_minute_still_refuses():
    """Two differently-titled listings on one minute, neither stating an id:
    still MATCH_COLLISION, still no write. A door on both sides must not make
    them agree — which is why `stated` stays blind to `entity_url`."""
    a = stored("presenter_upcoming", 0, PRESENTER_URL, title="Autumn Tasting Menu")
    b = stored("presenter_upcoming", 1, PRESENTER_URL, title="Guest Chef Night")
    row = PublishedListing(event_id="e1", title="Autumn Tasting Menu",
                           start_time=SEP_12, identity=a, source_id="s1")
    hit = ParsedListing(candidate_id="c1", title="Guest Chef Night",
                        start_time=SEP_12, end_time=SEP_12 + timedelta(hours=3),
                        identity=b, source_id="s1")
    assert match_kind(row, hit) == MATCH_COLLISION
    for decision in adjudicate_page(
            verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
            gate_passes=ALWAYS_PASSES,
            page_text="Autumn Tasting Menu and Guest Chef Night"):
        assert decision.fields == {} or "title" not in decision.fields


# --- The split itself, and what it must never leak ---------------------------

def test_an_entity_field_is_never_a_comparable_one():
    """The safety property stated as an assertion rather than as a comment: the
    two field lists are disjoint, `identity_verdict` reads only the comparable
    ones, and no pairing of doors can reach SAME or DIFFERENT."""
    assert set(IDENTITY_FIELDS).isdisjoint(ENTITY_FIELDS)
    assert set(IDENTITY_FIELDS) == {"uid", "listing_url", "source_href"}

    door = ListingIdentity(entity_url="https://castlecreek.band/")
    assert identity_verdict(door, door) is UNKNOWN
    assert identity_verdict(door, ListingIdentity(entity_url="https://other/")) is UNKNOWN
    assert door.stated is False and door.stated_any is True
    assert door.as_dict() == {"entity_url": "https://castlecreek.band/"}
    assert door.comparable() == {}
    assert read_identity(door.as_dict()) == door

    with_both = ListingIdentity(source_href="/e/1", entity_url="https://x/")
    assert identity_verdict(with_both, ListingIdentity(source_href="/e/1")) is SAME


def test_a_caller_payload_is_never_demoted():
    """A per-event detail feed states its own page as the listing's url, and
    there the page IS the listing. Demoting a CALLER's payload would delete the
    strongest identities in the tree, so the demotion is block-only."""
    payload = {"uid": "evt-1@venue.example", "url": "https://v.example/e/8817"}
    out = _with_identity(payload, None, source_url="https://v.example/e/8817")
    assert out[IDENTITY_KEY] == {"uid": "evt-1@venue.example",
                                 "listing_url": "https://v.example/e/8817"}


def test_same_location_folds_only_what_is_safe_to_fold():
    """A trailing slash and the scheme are folded (a false 'this is the page'
    costs a refusal); a QUERY or a FRAGMENT is not (both are how a calendar
    names one listing on a shared path, and folding them would delete exactly
    the identities this stack captures)."""
    for same in ("https://v.example/tour", "http://v.example/tour",
                 "https://V.EXAMPLE/tour/", "//v.example/tour", "/tour", "/tour/"):
        assert same_location(same, "https://v.example/tour"), same
    for different in ("https://v.example/tour?event=8817",
                      "https://v.example/tour#2026-09-15",
                      "https://other.example/tour", "https://v.example/tours",
                      "/tour/8817", "tour"):
        assert not same_location(different, "https://v.example/tour"), different
    assert not same_location("/tour", None)
    assert not same_location(None, "https://v.example/tour")

    # A demotion needs a page url; without one nothing moves.
    kept = ListingIdentity(source_href="https://v.example/tour")
    assert demote_door_addresses(kept, None) == kept
    assert demote_door_addresses(NO_IDENTITY, "https://v.example/tour") == NO_IDENTITY
