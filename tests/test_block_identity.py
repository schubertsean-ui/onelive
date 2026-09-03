"""A block carries the identity its OWN markup stated — founder Session
Contract #58 (2026-09-03), the R-103 cheap path.

R-103 recorded the identity stack's honest headline: #217 built the ladder, the
persist seam and the match preference, and shipped them with NO producer on the
crawl path. The measured reason was `worker/segment.py` reducing every listing
to text: a card's own `<a href>` was discarded at segmentation, a JSON-LD `@id`
never appeared at all, and the only per-listing url that could reach a candidate
was the model's guessed `ticket_link` — which `worker/identity.py` refuses to
read as an identity, because laundering a guess into an identity rewrites public
rows from it.

These tests are the founder's must-do 1 and 3. Every one of them runs the REAL
segmenter over a REAL fixture page and the REAL `create_candidate`
canonicalization, WITH NO MODEL ANYWHERE: nothing here calls, stubs, or fakes an
extractor, so an identity that arrives could only have come from the page's own
markup. Hermetic — no DB, no network, no AI.

The guard tests are not decoration. The failure this feature can cause is
adopting an address that is not the listing's own, which licenses a later tick
to rewrite one published listing from another's facts (R-095/R-097/R-099). So
the refusals are pinned as hard as the captures: an ambiguous card, an address
two listings share, the anchor-split path, and the whole-page fallback all state
NOTHING, and a page url or a ticket link is never an identity at any rung.
"""
import contextlib
import json
import pathlib
from datetime import datetime, timedelta, timezone

from worker.candidate_store import _with_identity
import worker.candidate_store as candidate_store
from worker.identity import (
    IDENTITY_KEY,
    NO_IDENTITY,
    IdentifiedBlock,
    carried_identity,
    read_identity,
)
from worker.listing_update import (
    ACTION_UPDATE,
    MATCH_IDENTITY,
    ParsedListing,
    PublishedListing,
    adjudicate_page,
    match_kind,
)
from worker.segment import segment_events
from worker.crawl_state import VERIFIED_PRESENT

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "block_identity"
ALWAYS_PASSES = lambda _cid: True        # noqa: E731 — a one-line test double
EIGHT_PM = datetime(2026, 8, 1, 20, 0, tzinfo=timezone.utc)


def page(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def blocks_of(name: str):
    return segment_events(page(name), content_type="text/html")


# --- MUST-DO 1: an href, and a JSON-LD url/@id, reach the candidate -----------

def test_a_block_keeps_the_href_its_own_card_stated():
    """MUST-DO 3(1) — "href kept". The three cards each state their own listing
    url in a heading anchor, and each block comes back carrying it."""
    blocks = blocks_of("cards_with_hrefs")
    assert len(blocks) == 3
    assert [carried_identity(b).source_href for b in blocks] == [
        "/events/8817-castle-creek",
        "/events/8818-river-delta",
        "/events/8819-tin-sparrow",
    ]


def test_the_href_could_not_have_come_from_the_block_text():
    """The proof that this is a SEGMENTATION capture and not something a model
    could have read: the address is nowhere in the text the extractor sees.

    Before this contract the block was exactly this string and nothing else,
    which is precisely why R-103 said the crawl path had no producer."""
    for block in blocks_of("cards_with_hrefs"):
        assert "href" not in block
        assert "8817" not in block and "8818" not in block and "8819" not in block
        assert carried_identity(block).source_href is not None


def test_a_href_bearing_block_populates_listing_identity_without_the_model():
    """MUST-DO 1, end to end: page bytes -> segmenter -> the real
    `create_candidate` canonicalization -> `extracted["_identity"]`.

    The `extracted` payload here is what the model produces for such a card,
    guessed `ticket_link` and all. The stored identity is the page's href; the
    guess is stored as the ordinary field it is and is NOT read as an id."""
    block = blocks_of("cards_with_hrefs")[0]
    extracted = {"title": "Castle Creek", "venue_name": "Wren Hall",
                 "ticket_link": "https://tix.example/8817"}
    stored = _with_identity(extracted, block)
    assert stored[IDENTITY_KEY] == {"source_href": "/events/8817-castle-creek"}
    assert stored["ticket_link"] == "https://tix.example/8817"
    assert read_identity(stored).source_href == "/events/8817-castle-creek"
    # The caller's own dict is never mutated (a payload shared across a page's
    # fan-out must not grow one listing's id and carry it onto the next).
    assert IDENTITY_KEY not in extracted


def test_jsonld_url_and_id_reach_the_candidate_without_the_model():
    """MUST-DO 1's other carrier. `url` is the listing's address and
    `@id`/`identifier` its opaque id — both read by the ONE reader
    (`worker.identity.jsonld_identity`) the licensed importer also uses."""
    stored = [_with_identity({"title": "x"}, b) for b in blocks_of("jsonld_two_events")]
    by_uid = {s[IDENTITY_KEY]["uid"]: s[IDENTITY_KEY] for s in stored}
    assert by_uid["https://wrenhall.example/id/8817"]["listing_url"] == \
        "https://wrenhall.example/events/8817"
    assert by_uid["8818"]["listing_url"] == "https://wrenhall.example/events/8818"


def test_two_blocks_two_hrefs():
    """MUST-DO 3(2), stated as its own test because it is the property the
    whole feature turns on: N listings on one page produce N DISTINCT ids, not
    one id N times. A page url would have produced the latter."""
    for name in ("cards_with_hrefs", "jsonld_two_events"):
        stored = [_with_identity({}, b).get(IDENTITY_KEY) for b in blocks_of(name)]
        assert all(s for s in stored), name
        keys = [json.dumps(s, sort_keys=True) for s in stored]
        assert len(set(keys)) == len(keys), name


# --- MUST-DO 3(3): no href -> still a list, and still no mutation -------------

def test_without_a_href_the_page_still_lists_and_nothing_is_invented():
    """The class_b corpus's actual shape. Segmentation is UNCHANGED — three
    listings, three blocks — and no identity is manufactured for any of them.

    The blocks come back as plain `str`, byte-identical in type and value to
    what this fixture produced before a carrier existed: "we captured nothing"
    and "there was nothing to capture" are the same thing and must look it."""
    blocks = blocks_of("cards_without_hrefs")
    assert len(blocks) == 3
    for block in blocks:
        assert type(block) is str
        assert carried_identity(block) == NO_IDENTITY
        payload = {"title": "Castle Creek"}
        assert _with_identity(payload, block) == payload
        assert IDENTITY_KEY not in _with_identity(payload, block)


def test_without_a_href_no_mutation_is_licensed():
    """MUST-DO 3(3) — "still refuse mutation". A candidate off the no-href page
    carries no identity, so the ladder falls to its composite rung, and that
    rung licenses NOTHING: no title write and no start_time write, for any
    combination of renamed/retimed/untitled. #214's refusals stand."""
    blocks = blocks_of("cards_without_hrefs")
    identity = read_identity(_with_identity({"title": "Castle Creek"}, blocks[0]))
    assert identity == NO_IDENTITY
    for published_title in ("Castle Creek", None):
        for parsed_title in ("Renamed Revue", "Castle Creek", None):
            for shift in (0, 2, 30):
                row = PublishedListing(event_id="e1", title=published_title,
                                       start_time=EIGHT_PM, identity=identity,
                                       source_id="s1")
                hit = ParsedListing(
                    candidate_id="c1", title=parsed_title,
                    start_time=EIGHT_PM + timedelta(hours=shift),
                    end_time=EIGHT_PM + timedelta(hours=shift + 3),
                    identity=identity, source_id="s1")
                for decision in adjudicate_page(
                        verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
                        gate_passes=ALWAYS_PASSES,
                        page_text="Castle Creek and Renamed Revue"):
                    assert "title" not in decision.fields
                    assert "start_time" not in decision.fields


def test_with_a_href_the_same_listing_is_recognized_across_ticks():
    """The point of the producer, proved rather than asserted: with the card's
    own href on the row, the SAME listing renamed and moved by two hours is
    recognized as itself, and the write R-095/R-099 had to refuse is licensed.

    The published row's identity is the one a previous tick stored through this
    same path, so this is the maintenance case end to end."""
    block = blocks_of("cards_with_hrefs")[0]
    identity = read_identity(_with_identity({"title": "Castle Creek"}, block))
    row = PublishedListing(event_id="e1", title="Castle Creek",
                           start_time=EIGHT_PM, identity=identity, source_id="s1")
    hit = ParsedListing(candidate_id="c1", title="Castle Creek Revue",
                        start_time=EIGHT_PM + timedelta(hours=2),
                        end_time=EIGHT_PM + timedelta(hours=5),
                        identity=identity, source_id="s1")
    assert match_kind(row, hit) == MATCH_IDENTITY
    [decision] = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[row], parsed=[hit],
        gate_passes=ALWAYS_PASSES, page_text="Castle Creek Revue tonight")
    assert decision.action == ACTION_UPDATE
    assert decision.fields["title"] == "Castle Creek Revue"
    assert decision.fields["start_time"] == hit.start_time


# --- the refusals that bound the conventional rungs ---------------------------

def test_an_ambiguous_card_states_no_identity():
    """Two links, neither marked as the listing's own and neither in a heading:
    the card has not said which address it lives at, so nothing is adopted.
    Picking the first would be a guess with a published row on the other end."""
    html = ("<div class='calendar'>"
            "<article class='event'>Fri Aug 1, 8pm Castle Creek "
            "<a href='/artists/castle-creek'>artist</a> "
            "<a href='https://tix.example/8817'>tickets</a></article>"
            "<article class='event'>Sat Aug 2, 9pm River Delta "
            "<a href='/artists/river-delta'>artist</a> "
            "<a href='https://tix.example/8818'>tickets</a></article></div>")
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert all(carried_identity(b) == NO_IDENTITY for b in blocks)


def test_an_address_two_listings_share_is_not_either_listing_s_identity():
    """The page-wide cardinality guard. Both cards' heading anchors point at the
    same series page, so that address identifies what they have in common — not
    either of them — and it is dropped from both rather than adopted twice."""
    html = ("<div class='calendar'>"
            "<article class='event'><h3><a href='/series/revue'>Castle Creek</a></h3>"
            "Fri Aug 1, 8pm</article>"
            "<article class='event'><h3><a href='/series/revue'>Castle Creek</a></h3>"
            "Fri Aug 8, 8pm</article></div>")
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert all(carried_identity(b) == NO_IDENTITY for b in blocks)


def test_a_shared_field_is_dropped_without_taking_a_distinct_one_with_it():
    """Only the SHARED value is dropped: two JSON-LD events that (wrongly) give
    the same `url` but distinct `@id`s keep their ids. A contradiction about one
    field is not a reason to discard a field the source got right."""
    html = ("<script type='application/ld+json'>"
            '[{"@type":"Event","name":"A","startDate":"2026-08-01T20:00:00Z",'
            '"url":"https://v.example/shared","@id":"a-1"},'
            '{"@type":"Event","name":"B","startDate":"2026-08-02T20:00:00Z",'
            '"url":"https://v.example/shared","@id":"b-2"}]</script>')
    ids = {carried_identity(b).uid: carried_identity(b).listing_url
           for b in segment_events(html, content_type="text/html")}
    assert ids == {"a-1": None, "b-2": None}


def test_the_page_s_own_url_never_becomes_a_listing_identity():
    """A single-event page falls to the whole-page block, which IS the page —
    so its nav and canonical links belong to every listing on it and to none.
    Nothing is carried, and a candidate off such a page stores no identity."""
    html = ("<html><head><link rel='canonical' href='https://v.example/show'>"
            "</head><body><a href='/'>Home</a>"
            "<p>Fri Aug 1, 8pm — Castle Creek at Wren Hall.</p></body></html>")
    [block] = segment_events(html, content_type="text/html")
    assert type(block) is str
    assert carried_identity(block) == NO_IDENTITY
    assert IDENTITY_KEY not in _with_identity({"title": "Castle Creek"}, block)


def test_the_anchor_split_path_carries_nothing():
    """Plain text split at date anchors has no structure to attribute an
    address to — the cut points are character offsets — so it states nothing."""
    text = ("Fri Aug 1, 8pm Castle Creek\n"
            "Sat Aug 2, 9pm River Delta\n"
            "Sun Aug 3, 7pm Tin Sparrow\n")
    blocks = segment_events(text)
    assert len(blocks) == 3
    assert all(type(b) is str for b in blocks)


# --- the rungs, each pinned separately ----------------------------------------

def test_a_card_that_is_itself_the_link_states_its_own_address():
    """Rung 1: the whole listing IS the anchor, so there is nothing to
    disambiguate. Reachable through the schema.org-microdata strategy, which is
    the one segmentation rule that can capture an `<a>` element; a plain
    `<a class="event-card">` calendar does not segment today and this contract
    does not widen segmentation to make it (that would move which pages split,
    which is a different change with its own exam baselines)."""
    html = ("<div>"
            "<a itemscope itemtype='https://schema.org/MusicEvent' href='/e/1'>"
            "Fri Aug 1, 8pm Castle Creek <span>at Wren Hall</span></a>"
            "<a itemscope itemtype='https://schema.org/MusicEvent' href='/e/2'>"
            "Sat Aug 2, 9pm River Delta</a></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == ["/e/1", "/e/2"]


def test_an_itemprop_url_outranks_every_other_link_in_the_card():
    """Rung 2: the source has LABELLED the field, which beats any convention.
    Here the labelled address is not the first link and not in the heading."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "<h3><a href='/artists/castle-creek'>Castle Creek</a></h3>"
            "Fri Aug 1, 8pm <a itemprop='url' href='/e/8817'>details</a></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "<h3><a href='/artists/river-delta'>River Delta</a></h3>"
            "Sat Aug 2, 9pm <a itemprop='url' href='/e/8818'>details</a></div></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == ["/e/8817", "/e/8818"]


def test_a_heading_with_two_links_is_ambiguous_at_every_rung():
    """Rung 3 refuses rather than picking: a heading naming both the artist and
    the venue has not said which one the listing lives at, and rung 4 then sees
    the same two addresses."""
    html = ("<div class='calendar'>"
            "<article class='event'><h3><a href='/a/cc'>Castle Creek</a> at "
            "<a href='/v/wren'>Wren Hall</a></h3>Fri Aug 1, 8pm</article>"
            "<article class='event'><h3><a href='/a/rd'>River Delta</a> at "
            "<a href='/v/wren'>Wren Hall</a></h3>Sat Aug 2, 9pm</article></div>")
    assert all(carried_identity(b) == NO_IDENTITY
               for b in segment_events(html, content_type="text/html"))


def test_a_mailto_or_a_menu_toggle_is_not_a_competing_address():
    """Rung 4 counts ADDRESSES OF LISTINGS. `mailto:`/`tel:`/`javascript:` and a
    bare `#` are none of those, so a card holding one plus its own link is
    unambiguous — a fact about the schemes, not a preference between links."""
    html = ("<div class='calendar'>"
            "<article class='event'>Fri Aug 1, 8pm Castle Creek "
            "<a href='/e/1'>details</a> <a href='mailto:box@v.example'>email</a> "
            "<a href='#'>more</a></article>"
            "<article class='event'>Sat Aug 2, 9pm River Delta "
            "<a href='/e/2'>details</a> <a href='tel:+15125550100'>call</a></article>"
            "</div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == ["/e/1", "/e/2"]


# --- the carrier changes nothing the extraction surface can see ---------------

def test_the_carrier_leaves_the_block_text_byte_identical():
    """The reason no extraction file is opened: an `IdentifiedBlock` IS its
    text. The certified extractor, the evidence quote and the stored `raw_text`
    receive the same characters they received before this carrier existed —
    pinned as literals rather than derived, so a change to the text is a
    failing test and not a silently re-baselined one."""
    blocks = blocks_of("cards_with_hrefs")
    assert blocks == [
        "Castle Creek Fri Aug 1, 8pm — Wren Hall Tickets",
        "River Delta Sat Aug 2, 9pm — Wren Hall Tickets",
        "Tin Sparrow Sun Aug 3, 7pm — Wren Hall",
    ]
    block = blocks[0]
    assert isinstance(block, str) and isinstance(block, IdentifiedBlock)
    assert json.dumps(block) == json.dumps(str(block))
    assert type(block[:500]) is str          # the evidence quote stays a plain str
    assert hash(block) == hash(str(block))


def test_the_driver_is_handed_a_plain_string_for_raw_text(monkeypatch):
    """`create_candidate` inserts `str(raw_text)`: an `IdentifiedBlock` never
    reaches psycopg2, so the `raw_text` column receives exactly what it always
    received and no adapter has to know about a str subclass. The identity is
    read off the block BEFORE that, into the jsonb."""
    captured = {}

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql, params):
            captured["params"] = params

        def fetchone(self):
            return ("cand-1",)

    class _Conn:
        def cursor(self):
            return _Cursor()

        def commit(self):
            captured["committed"] = True

    @contextlib.contextmanager
    def _fake_db():
        yield _Conn()

    monkeypatch.setattr(candidate_store, "db", _fake_db)
    block = blocks_of("cards_with_hrefs")[0]
    assert candidate_store.create_candidate(
        source_id="s1", source_name="Wren Hall",
        source_url="https://wrenhall.example/calendar", source_class="B",
        raw_text=block, extracted={"title": "Castle Creek"}, sxsw_mode=False,
    ) == "cand-1"
    raw_text, extracted_json = captured["params"][4], captured["params"][5]
    assert type(raw_text) is str and raw_text == str(block)
    assert json.loads(extracted_json)[IDENTITY_KEY] == {
        "source_href": "/events/8817-castle-creek"}
