"""The identity stack — founder Session Contract #57 (2026-09-03).

Must-do 5 names four tests and each has its own section below:

  1. ICS UID match          — through the REAL worker/importers/structured_feed
  2. JSON-LD url match      — through the REAL parse_jsonld
  3. two bands at 8pm       — REFUSE the write
  4. missing id             — the row still LISTS, and nothing mutates

The first two run end to end on purpose: a real calendar's bytes go through the
real parser, through the real `create_candidate` canonicalization, into the
real ladder. An identity hand-built in a fixture would prove that the ladder
compares two dataclasses, which was never in doubt; what is worth proving is
that the id a source actually publishes survives every hop to the place a
published row is decided.

Hermetic: no DB, no network, no model. `create_candidate`'s DB call is not
reached — `_with_identity` is the canonicalization it applies, and it is pure.
"""
from datetime import datetime, timedelta, timezone

from worker.candidate_store import _with_identity
from worker.claim.intake import ClaimedListing
from worker.identity import (
    DIFFERENT,
    IDENTITY_FIELDS,
    IDENTITY_KEY,
    NO_IDENTITY,
    SAME,
    UNKNOWN,
    ListingIdentity,
    identity_verdict,
    normalize_url,
    read_identity,
    weak_key,
)
from worker.importers.structured_feed import parse_ics, parse_jsonld
from worker.listing_update import (
    ACTION_NONE,
    ACTION_UPDATE,
    MATCH_COLLISION,
    MATCH_IDENTITY,
    ParsedListing,
    PublishedListing,
    adjudicate_page,
    match_kind,
    normalize_title,
)
from worker.crawl_state import VERIFIED_PRESENT

ALWAYS_PASSES = lambda _cid: True        # noqa: E731 — a one-line test double

#: A page that names both shows, so no absence branch can fire in these tests
#: and every assertion is about identity rather than about a cancellation.
PAGE = ("Copper Kettle Revue tonight, and The Deer, and Sun June, "
        "and Beethoven's Ninth and Museum Free Day and Renamed Revue")


# --- 1. ICS UID ---------------------------------------------------------------

ICS = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-timed-001@testvenue.org\r\n"
    "SUMMARY:Beethoven's Ninth\r\n"
    "DTSTART:20260915T010000Z\r\n"
    "DTEND:20260915T030000Z\r\n"
    "URL:https://testvenue.org/events/beethoven-ninth\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-other-002@testvenue.org\r\n"
    "SUMMARY:Museum Free Day\r\n"
    "DTSTART:20260915T010000Z\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


def test_an_ics_uid_survives_the_parser_and_the_candidate_write():
    """The whole hop, not a hand-built identity: parse_ics finds the UID, the
    candidate write canonicalizes it into `extracted['_identity']`, and reading
    that back gives the same id."""
    first, _second = parse_ics(ICS)
    assert first["uid"] == "evt-timed-001@testvenue.org"
    stored = _with_identity(first)
    assert stored[IDENTITY_KEY] == {
        "uid": "evt-timed-001@testvenue.org",
        "listing_url": "https://testvenue.org/events/beethoven-ninth",
    }
    assert read_identity(stored).uid == "evt-timed-001@testvenue.org"


def test_an_ics_uid_identifies_a_published_row_across_a_rename_and_a_retime():
    """MUST-DO 5(1). The source says these are one listing, so the title and the
    clock are free to have changed — which is exactly what title and time alone
    could never establish (R-095, R-099)."""
    ics_event, _ = parse_ics(ICS)
    identity = read_identity(_with_identity(ics_event))

    row = PublishedListing(
        event_id="e1", title="Beethoven's Ninth",
        start_time=datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc),
        identity=identity, source_id="s1")
    # Same UID, new name, new hour, and an end the page restates (R-098).
    hit = ParsedListing(
        candidate_id="c1", title="Renamed Revue",
        start_time=datetime(2026, 9, 15, 2, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 9, 15, 4, 0, tzinfo=timezone.utc),
        identity=identity, source_id="s1")

    assert match_kind(row, hit) == MATCH_IDENTITY
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert decision.action == ACTION_UPDATE
    assert decision.fields["title"] == "Renamed Revue"
    assert decision.fields["start_time"] == hit.start_time
    assert "the source's own id" in decision.why


def test_two_different_uids_are_two_listings_whatever_else_agrees():
    """The negative direction, which is the half that protects a published row:
    a stated id that DISAGREES blocks the fall-through, so a shared minute and
    even a shared title cannot make one listing out of two."""
    a, b = (read_identity(e) for e in parse_ics(ICS))
    assert identity_verdict(a, b) is DIFFERENT
    when = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)
    row = PublishedListing(event_id="e1", title="Same Name", start_time=when,
                           identity=a, source_id="s1")
    other = ParsedListing(candidate_id="c9", title="Same Name", start_time=when,
                          end_time=when + timedelta(hours=9),
                          identity=b, source_id="s1")
    assert match_kind(row, other) == MATCH_COLLISION
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row], parsed=[other],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert decision.action == ACTION_NONE
    assert decision.fields == {}


# --- 2. JSON-LD url -----------------------------------------------------------

JSONLD_PAGE = """<!doctype html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"MusicEvent","name":"The Deer",
 "startDate":"2026-09-15T01:00:00Z",
 "url":"https://venue.example/events/the-deer-sep-15",
 "location":{"@type":"Place","name":"Stubb's"}}
</script></head><body>The Deer</body></html>"""


def test_a_jsonld_event_url_survives_the_parser_and_the_candidate_write():
    [event] = parse_jsonld(JSONLD_PAGE)
    assert event["url"] == "https://venue.example/events/the-deer-sep-15"
    stored = _with_identity(event)
    assert stored[IDENTITY_KEY]["listing_url"] == (
        "https://venue.example/events/the-deer-sep-15")


def test_a_jsonld_url_identifies_a_published_row():
    """MUST-DO 5(2). Same listing url on both sides — one listing, and the end
    time the page now states is written."""
    [event] = parse_jsonld(JSONLD_PAGE)
    identity = read_identity(_with_identity(event))
    when = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)
    row = PublishedListing(event_id="e1", title="The Deer", start_time=when,
                           identity=identity, source_id="s1")
    hit = ParsedListing(candidate_id="c1", title="The Deer", start_time=when,
                        end_time=when + timedelta(hours=3),
                        identity=identity, source_id="s1")
    assert match_kind(row, hit) == MATCH_IDENTITY
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert decision.action == ACTION_UPDATE
    assert decision.fields == {"end_time": when + timedelta(hours=3)}


def test_a_jsonld_at_id_is_read_as_the_uid():
    """schema.org's own identifiers, not just `url` — `@id` and `identifier`
    are what a calendar states when its event pages are not separately
    addressable."""
    page = JSONLD_PAGE.replace(
        '"url":"https://venue.example/events/the-deer-sep-15",',
        '"@id":"urn:venue:the-deer-2026-09-15",')
    [event] = parse_jsonld(page)
    assert read_identity(_with_identity(event)).uid == "urn:venue:the-deer-2026-09-15"


# --- 3. two bands at 8pm ------------------------------------------------------

EIGHT_PM = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)


def test_two_bands_at_eight_with_no_unique_id_refuse_the_write():
    """MUST-DO 5(3), founder verbatim: "Collision (two titles, one minute, no
    unique id) = refuse write."

    Our published row's title still matches one of the two exactly, so #214's
    one-to-one rule sees a single clean hit and would have written it. It is
    refused because the MINUTE is contested: the other band could be the show
    that was renamed to ours, and nothing on the page can say which."""
    row = PublishedListing(event_id="e1", title="The Deer", start_time=EIGHT_PM,
                           source_id="s1")
    same_name = ParsedListing(candidate_id="c1", title="The Deer",
                              start_time=EIGHT_PM,
                              end_time=EIGHT_PM + timedelta(hours=3),
                              source_id="s1")
    other_band = ParsedListing(candidate_id="c2", title="Sun June",
                               start_time=EIGHT_PM, source_id="s1")
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row],
        parsed=[same_name, other_band],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert decision.action == ACTION_NONE
    assert decision.fields == {}
    assert "no unique id separates them" in decision.why


def test_a_unique_id_is_exactly_what_lifts_the_eight_pm_refusal():
    """The founder's clause says "no unique id", so an id must lift it — and
    the identity has to be what identifies the row, not the minute."""
    identity = ListingIdentity(uid="deer-2026-09-15")
    row = PublishedListing(event_id="e1", title="The Deer", start_time=EIGHT_PM,
                           identity=identity, source_id="s1")
    same_name = ParsedListing(candidate_id="c1", title="The Deer",
                              start_time=EIGHT_PM,
                              end_time=EIGHT_PM + timedelta(hours=3),
                              identity=identity, source_id="s1")
    other_band = ParsedListing(candidate_id="c2", title="Sun June",
                               start_time=EIGHT_PM,
                               identity=ListingIdentity(uid="sunjune-2026-09-15"),
                               source_id="s1")
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row],
        parsed=[same_name, other_band],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert decision.action == ACTION_UPDATE
    assert decision.fields == {"end_time": EIGHT_PM + timedelta(hours=3)}


def test_one_listing_with_no_id_leaves_the_whole_minute_contested():
    """A half-identified slot is still a contested one: an unidentified listing
    could be any of the shows on that minute, so a partial id set separates
    nobody."""
    row = PublishedListing(event_id="e1", title="The Deer", start_time=EIGHT_PM,
                           identity=ListingIdentity(uid="deer"), source_id="s1")
    identified = ParsedListing(candidate_id="c1", title="The Deer",
                               start_time=EIGHT_PM,
                               end_time=EIGHT_PM + timedelta(hours=3),
                               identity=ListingIdentity(uid="deer"),
                               source_id="s1")
    anonymous = ParsedListing(candidate_id="c2", title="Sun June",
                              start_time=EIGHT_PM, source_id="s1")
    # The identified pair still adopts — its id, not the minute, identifies it.
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row],
        parsed=[identified, anonymous],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert decision.action == ACTION_UPDATE
    # But a row that relies on the MINUTE there is refused.
    minute_row = PublishedListing(event_id="e2", title="Sun June",
                                  start_time=EIGHT_PM, source_id="s1")
    [minute_decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[minute_row],
        parsed=[identified, ParsedListing(
            candidate_id="c2", title="Sun June", start_time=EIGHT_PM,
            end_time=EIGHT_PM + timedelta(hours=4), source_id="s1")],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    assert minute_decision.action == ACTION_NONE


# --- 4. missing id ------------------------------------------------------------

def test_a_listing_with_no_id_exists_with_holes_and_mutates_nothing():
    """MUST-DO 5(4). Existence is the door's question (ONE-LIVE-TRUST.md): a row
    with no identity is still LISTED, still adjudicated, still reported — it is
    simply never rewritten. #214's refusals stand verbatim."""
    row = PublishedListing(event_id="e1", title="Copper Kettle Revue",
                           start_time=EIGHT_PM, source_id="s1")
    renamed = ParsedListing(candidate_id="c1", title="Copper Kettle Review",
                            start_time=EIGHT_PM + timedelta(hours=2),
                            source_id="s1")
    assert row.identity == NO_IDENTITY and renamed.identity == NO_IDENTITY
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row], parsed=[renamed],
        gate_passes=ALWAYS_PASSES, page_text=PAGE)
    # LISTED: a decision was produced for this row, and it is not a removal.
    assert decision.event_id == "e1"
    assert decision.action == ACTION_NONE
    assert decision.fields == {}


def test_without_an_identity_no_title_is_ever_written():
    """The founder's "no identity -> no start_time/title mutation", asserted
    over the combinations rather than one fixture."""
    for pub_title in ("Copper Kettle Revue", None):
        for new_title in ("Renamed Revue", "Copper Kettle Revue", None):
            for shift in (0, 2, 30):
                row = PublishedListing(event_id="e1", title=pub_title,
                                       start_time=EIGHT_PM, source_id="s1")
                hit = ParsedListing(
                    candidate_id="c1", title=new_title,
                    start_time=EIGHT_PM + timedelta(hours=shift),
                    end_time=EIGHT_PM + timedelta(hours=shift + 3),
                    source_id="s1")
                for d in adjudicate_page(
                        verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
                        gate_passes=ALWAYS_PASSES, page_text=PAGE):
                    assert "title" not in d.fields, (pub_title, new_title, shift)
                    assert "start_time" not in d.fields, (pub_title, new_title, shift)


# --- the stack's own rules ----------------------------------------------------

def test_nothing_but_the_three_carriers_is_read_as_an_identity():
    """Founder: "Do not invent a URL." The page url every listing on a calendar
    shares, and the model's guessed ticket/rsvp links, are NOT identity."""
    payload = {
        "title": "The Deer",
        "source_url": "https://venue.example/calendar",
        "ticket_link": "https://tickets.example/xyz",
        "rsvp_link": "https://rsvp.example/xyz",
        "external_id": "jsonld:9d1f0c",   # a MINTED licensed-store id
    }
    assert read_identity(payload) == NO_IDENTITY
    assert _with_identity(payload) == payload
    assert IDENTITY_KEY not in _with_identity(payload)
    assert set(IDENTITY_FIELDS) == {"uid", "listing_url", "source_href"}


def test_a_claimed_listing_carries_the_url_its_claimant_typed():
    """Class E is the one door that states a per-listing url today, and it is
    first-party: the venue's own row in their own CSV."""
    listing = ClaimedListing(title="Trivia Night", start="2026-09-15 20:00",
                             url="https://venue.example/events/trivia-9-15")
    identity = read_identity(_with_identity(listing.as_extracted()))
    assert identity.listing_url == "https://venue.example/events/trivia-9-15"
    # No url given: a hole, never an invented one.
    bare = ClaimedListing(title="Trivia Night", start="2026-09-15 20:00")
    assert read_identity(_with_identity(bare.as_extracted())) == NO_IDENTITY


def test_url_normalization_folds_only_what_http_says_is_case_insensitive():
    """A fragment IS the per-listing anchor on a one-page calendar, and a query
    carries the id on plenty of others — a normalizer that dropped either would
    collapse every listing on a page into one."""
    assert (normalize_url("HTTPS://Venue.Example/Events/The-Deer")
            == "https://venue.example/Events/The-Deer")
    for a, b in (
        ("https://v.example/c#event-1", "https://v.example/c#event-2"),
        ("https://v.example/c?event=1", "https://v.example/c?event=2"),
        ("https://v.example/Wake", "https://v.example/wake"),
        ("https://v.example/events", "https://v.example/events/"),
    ):
        assert identity_verdict(ListingIdentity(listing_url=a),
                                ListingIdentity(listing_url=b)) is DIFFERENT, (a, b)


def test_a_hole_on_one_side_says_nothing_at_all():
    """Existence with holes, applied to identity: a field only one side states
    is not evidence in either direction."""
    assert identity_verdict(ListingIdentity(uid="x"), NO_IDENTITY) is UNKNOWN
    assert identity_verdict(NO_IDENTITY, NO_IDENTITY) is UNKNOWN
    # Compared field agrees, uncompared field absent -> SAME.
    assert identity_verdict(ListingIdentity(uid="x", listing_url="https://a/1"),
                            ListingIdentity(uid="x")) is SAME
    # A source contradicting itself is never an identity, even where it agrees.
    assert identity_verdict(
        ListingIdentity(uid="x", listing_url="https://a/1"),
        ListingIdentity(uid="x", listing_url="https://a/2")) is DIFFERENT


def test_a_uid_is_an_opaque_token_and_its_case_is_not_folded():
    assert identity_verdict(ListingIdentity(uid="ABC"),
                            ListingIdentity(uid="abc")) is DIFFERENT


def test_the_composite_key_is_the_founders_three_parts_and_refuses_a_hole():
    """(source_id, normalized title, start DATE). None when any part is
    missing — a key with a hole in it would marry every untitled listing a
    source published on one day."""
    when = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)
    assert weak_key("s1", normalize_title("The Deer!"), when) == (
        "s1", "the deer", when.date())
    # The DATE, not the minute: a clock that moved inside the day keys the same.
    assert weak_key("s1", "the deer", when) == weak_key(
        "s1", "the deer", when + timedelta(hours=6))
    for missing in (weak_key(None, "the deer", when),
                    weak_key("s1", None, when),
                    weak_key("s1", "the deer", None)):
        assert missing is None
    # Naive timestamps are read as UTC, the same reading listing_update uses.
    assert weak_key("s1", "the deer", when.replace(tzinfo=None)) == weak_key(
        "s1", "the deer", when)


def test_a_different_source_is_never_the_same_listing():
    """The first element of the founder's composite key. `adjudicate_page` is
    PURE and takes whatever it is given, so the SQL scoping in the loaders is
    not a property of the policy here."""
    row = PublishedListing(event_id="e1", title="The Deer", start_time=EIGHT_PM,
                           source_id="s1")
    other_venue = ParsedListing(candidate_id="c1", title="The Deer",
                                start_time=EIGHT_PM,
                                end_time=EIGHT_PM + timedelta(hours=3),
                                source_id="s2")
    assert match_kind(row, other_venue) is None


def test_every_non_identity_update_agrees_on_the_composite_key():
    """STRUCTURAL, not a fixture: whenever a write is licensed WITHOUT an id,
    the founder's composite key holds on both sides. Enumerated over the shapes
    that can reach the writing branch, so a future loosening of the title/time
    rules fails here rather than shipping."""
    shifts = (0, 3, 11, 26)
    for pub_end in (None, EIGHT_PM + timedelta(hours=2)):
        for shift in shifts:
            for new_title in ("The Deer", "Other Band", None):
                row = PublishedListing(event_id="e1", title="The Deer",
                                       start_time=EIGHT_PM, end_time=pub_end,
                                       source_id="s1")
                hit = ParsedListing(
                    candidate_id="c1", title=new_title,
                    start_time=EIGHT_PM + timedelta(hours=shift),
                    end_time=EIGHT_PM + timedelta(hours=shift + 4),
                    source_id="s1")
                for d in adjudicate_page(
                        verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
                        gate_passes=ALWAYS_PASSES, page_text=PAGE):
                    if d.action != ACTION_UPDATE:
                        continue
                    assert match_kind(row, hit) != MATCH_IDENTITY
                    assert weak_key("s1", normalize_title(row.title),
                                    row.start_time) == weak_key(
                        "s1", normalize_title(hit.title), hit.start_time), (
                        f"a write was licensed on a pair whose composite key "
                        f"disagrees: {d.fields}")
