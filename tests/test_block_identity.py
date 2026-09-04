"""A block carries the identity its OWN markup DECLARES — founder Session
Contract #58 (2026-09-03), the R-103 cheap path.

R-103 recorded the identity stack's honest headline: #217 built the ladder, the
persist seam and the match preference, and shipped them with NO producer on the
crawl path. The measured reason was `worker/segment.py` reducing every listing
to text: a card's own `<a href>` was discarded at segmentation, a JSON-LD `@id`
never appeared at all, and the only per-listing url that could reach a candidate
was the model's guessed `ticket_link` — which `worker/identity.py` refuses to
read as an identity, because laundering a guess into an identity rewrites public
rows from it.

DECLARED, NEVER CONVENTIONAL, and that line was drawn by the adversarial panel
rather than by us. The first round of this producer also read two conventions —
a card's heading anchor and a card's sole link — and both openai seats blocked
on the same defect from opposite lenses: an ordinary venue card links the ARTIST
from its title as readily as the event, so a later tick could read that same
address on a DIFFERENT occurrence, answer SAME, and rewrite a published listing
with another show's title and clock. They were right, and the residual had been
RECORDED (R-104) instead of fixed — the exact mistake R-096 is the standing
lesson for. The conventional rungs are gone; only a declaration is read.

Every test here runs the REAL segmenter over a REAL fixture page and the REAL
`create_candidate` canonicalization, WITH NO MODEL ANYWHERE: nothing calls,
stubs, or fakes an extractor, so an identity that arrives could only have come
from the page's own markup. Hermetic — no DB, no network, no AI.

The refusals are pinned as hard as the captures, because the failure this
feature can cause is adopting an address that is not the listing's own: an
undeclared card, an address two listings share, a contradicted declaration, the
anchor-split path and the whole-page fallback all state NOTHING, and a page url
or a ticket link is never an identity at any rung.
"""
import contextlib
import copy
import json
import pathlib
import pickle
from datetime import datetime, timedelta, timezone

from worker.candidate_store import _with_identity
import worker.candidate_store as candidate_store
from worker.identity import (
    IDENTITY_KEY,
    NO_IDENTITY,
    IdentifiedBlock,
    carried_identity,
    identity_address,
    identity_iri,
    identity_token,
    jsonld_identity,
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


# --- MUST-DO 1: a declared href, and a JSON-LD url/@id, reach the candidate ----

def test_a_block_keeps_the_address_its_own_card_declared():
    """MUST-DO 3(1) — "href kept". Each card labels one link `itemprop="url"`,
    and each block comes back carrying exactly that address.

    The fixture is adversarial around the declaration on purpose: every card's
    HEADING links the artist and two carry a "Tickets" link to a vendor. Those
    are the conventional links the panel blocked, and none of them appears
    here."""
    blocks = blocks_of("cards_with_hrefs")
    assert len(blocks) == 3
    assert [carried_identity(b).source_href for b in blocks] == [
        "/events/8817-castle-creek",
        "/events/8818-river-delta",
        "/events/8819-tin-sparrow",
    ]


def test_the_address_could_not_have_come_from_the_block_text():
    """The proof that this is a SEGMENTATION capture and not something a model
    could have read: the address is nowhere in the text the extractor sees.

    Before this contract the block was exactly this string and nothing else,
    which is precisely why R-103 said the crawl path had no producer."""
    for block in blocks_of("cards_with_hrefs"):
        assert "href" not in block
        assert "8817" not in block and "8818" not in block and "8819" not in block
        assert carried_identity(block).source_href is not None


def test_a_declared_address_populates_listing_identity_without_the_model():
    """MUST-DO 1, end to end: page bytes -> segmenter -> the real
    `create_candidate` canonicalization -> `extracted["_identity"]`.

    The `extracted` payload here is what the model produces for such a card,
    guessed `ticket_link` and all. The stored identity is the page's declared
    address; the guess is stored as the ordinary field it is and is NOT read as
    an id."""
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
    """MUST-DO 1's other carrier, and the strongest one: a JSON-LD Event states
    its own `url` and `@id`/`identifier` as fields, which is a declaration by
    construction. Read by the ONE reader (`worker.identity.jsonld_identity`)
    the licensed importer also uses."""
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


# --- the panel's blocking finding, pinned as a page ----------------------------

def test_a_conventional_link_is_never_an_identity():
    """THE ADVERSARIAL PANEL'S BLOCKING FINDING, as a committed page.

    The ordinary venue card: a title link and a "Tickets" link, and nothing in
    the markup saying which is the listing. An earlier round adopted the title
    link — `/artists/castle-creek` — which is the ARTIST's page, so next
    month's different Castle Creek show would have matched this published row
    and rewritten its title and clock from another occurrence's facts.

    Both blocks state NOTHING now, and the second card (one link, no ticket
    link) pins that a card's SOLE link is not adopted either: "only link" is
    not a statement about what the link is."""
    blocks = blocks_of("cards_with_undeclared_hrefs")
    assert len(blocks) == 2
    for block in blocks:
        assert carried_identity(block) == NO_IDENTITY
        assert IDENTITY_KEY not in _with_identity({"title": "Castle Creek"}, block)


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


def test_with_a_declared_address_the_same_listing_is_recognized_across_ticks():
    """The point of the producer, proved rather than asserted: with the card's
    DECLARED address on the row, the same listing renamed and moved by two
    hours is recognized as itself, and the write R-095/R-099 had to refuse is
    licensed.

    The published row's identity is the one a previous tick stored through this
    same path, so this is the maintenance case end to end — and it is safe here
    for the reason the conventional rungs were removed: the source said this
    address IS the listing, so a different occurrence would carry a different
    one."""
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


# --- the refusals ---------------------------------------------------------------

def test_an_address_two_listings_share_is_not_either_listing_s_identity():
    """The page-wide cardinality guard, on DECLARED addresses. Both cards
    declare the same series page as their url, so that address identifies what
    they have in common — not either of them — and it is dropped from both
    rather than adopted twice. A source can contradict itself; a contradiction
    is never an identity."""
    html = ("<div class='calendar'>"
            "<article class='event'>Fri Aug 1, 8pm Castle Creek "
            "<a itemprop='url' href='/series/revue'>details</a></article>"
            "<article class='event'>Fri Aug 8, 8pm Castle Creek "
            "<a itemprop='url' href='/series/revue'>details</a></article></div>")
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert all(carried_identity(b) == NO_IDENTITY for b in blocks)


def test_a_shared_field_is_dropped_without_taking_a_distinct_one_with_it():
    """Only the SHARED value is dropped: two JSON-LD events that (wrongly) give
    the same `url` but distinct `@id`s keep their ids. A contradiction about one
    field is not a reason to discard a field the source got right."""
    html = ("<script type='application/ld+json'>"
            '[{"@type":"Event","name":"A","startDate":"2026-08-01T20:00:00Z",'
            '"url":"https://v.example/shared","@id":"https://v.example/id/a-1"},'
            '{"@type":"Event","name":"B","startDate":"2026-08-02T20:00:00Z",'
            '"url":"https://v.example/shared","@id":"https://v.example/id/b-2"}]</script>')
    ids = {carried_identity(b).uid: carried_identity(b).listing_url
           for b in segment_events(html, content_type="text/html")}
    assert ids == {"https://v.example/id/a-1": None,
                   "https://v.example/id/b-2": None}


def test_a_card_declaring_two_different_urls_states_no_identity():
    """A card that labels TWO different addresses `itemprop="url"` has disagreed
    with itself. Refused outright — and there is no weaker rung to fall to,
    which is the point of removing them."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek "
            "<a itemprop='url' href='/e/8817'>details</a> "
            "<a itemprop='url' href='/e/9999'>also details</a></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta "
            "<a itemprop='url' href='/e/8818'>details</a></div></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == [None, "/e/8818"]


def test_a_declaration_pointing_at_a_non_address_is_refused():
    """`mailto:`/`tel:`/`javascript:` and a bare `#` are not addresses of
    anything a calendar lists, so a declaration naming one states nothing —
    a fact about the schemes, not a preference between links."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek "
            "<a itemprop='url' href='mailto:box@v.example'>email</a></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta "
            "<a itemprop='url' href='#'>more</a></div></div>")
    assert all(carried_identity(b) == NO_IDENTITY
               for b in segment_events(html, content_type="text/html"))


def test_a_fragment_only_address_is_never_an_identity():
    """THE PANEL'S ROUND-3 FINDING. The segmenter deliberately never resolves a
    relative address against the page url — it is not given one — so a
    fragment-only `#event-1` is stored verbatim, and the SAME anchor on a
    DIFFERENT page of the same source would compare equal and license a write
    from another occurrence's facts.

    A fragment WITH a path is a different thing entirely: it names the page AND
    the anchor, which is exactly the per-listing address `normalize_url`
    preserves fragments for. Both halves are pinned here, because deleting the
    wrong one would either re-open the alias or throw away real ids."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek<a itemprop='url' href='#event-1'>details</a></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta"
            "<a itemprop='url' href='/calendar#event-2'>details</a></div></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == [None, "/calendar#event-2"]


def test_the_jsonld_carrier_answers_to_the_same_checks_as_the_html_one():
    """The round-3 sibling: the HTML declaration was validated and the JSON-LD
    one was not, both feeding the same sink. `jsonld_identity` now routes
    through the same `identity_value`, and reads a field stating SEVERAL
    different values as stating none — a source that lists an artist url and an
    event url has not said which is the listing's, and taking the first would
    adopt whichever the page happened to put first.

    Asserted on the reader directly rather than through a page, because the
    defect is in what the reader accepts, and a fixture would only prove one
    spelling of it."""
    assert jsonld_identity({"url": "javascript:alert(1)"}) == NO_IDENTITY
    assert jsonld_identity({"url": "#e1"}) == NO_IDENTITY
    assert jsonld_identity({"@id": "#frag"}) == NO_IDENTITY
    # ROUND 6: `@id` is an IRI resolved against the DOCUMENT BASE, so a
    # page-relative one means something different on every page that states it
    # — and this path has no base url. It goes through the IRI door, which
    # demands a name, not a fetchable address. `identifier` is schema.org's
    # opaque property and keeps the token door.
    assert jsonld_identity({"@id": "event-1"}).uid is None
    assert jsonld_identity({"@id": "https://v.example/id/1"}).uid == "https://v.example/id/1"
    assert jsonld_identity({"@id": "/id/1"}).uid == "/id/1"
    # A URN @id NAMES ITSELF and is kept: an `@id` only has to identify, while
    # a `url` has to be fetchable, so they do not share a scheme rule. A
    # calendar whose events have no separate pages states exactly this.
    assert jsonld_identity({"@id": "urn:uuid:abc"}).uid == "urn:uuid:abc"
    # ROUND 7: a COMPACT IRI is not self-naming. `event:8817` means whatever
    # the document's `@context` says `event` is, and this path never sees the
    # context — `urlsplit` reports a scheme for it exactly as for a real IRI,
    # so "has a scheme" readmits the property round 6 closed.
    assert jsonld_identity({"@id": "event:8817"}).uid is None
    assert jsonld_identity({"@id": "schema:Event"}).uid is None
    # An unusable @id does not suppress a usable identifier beside it: they are
    # two fields, and the source stated both. True of a compact one too.
    assert jsonld_identity({"@id": "details", "identifier": "8818"}).uid == "8818"
    assert jsonld_identity({"@id": "event:1", "identifier": "8818"}).uid == "8818"
    # Several DIFFERENT values is a contradiction; the same value twice is not.
    assert jsonld_identity({"url": ["https://a/1", "https://b/2"]}) == NO_IDENTITY
    assert jsonld_identity({"identifier": ["x", "y"]}) == NO_IDENTITY
    assert jsonld_identity({"url": ["https://a/1", "https://a/1"]}).listing_url == "https://a/1"
    # An opaque, non-url identifier is untouched — it is an id, not an address,
    # and the two carriers deliberately go through DIFFERENT doors (round 4).
    stated = jsonld_identity({"identifier": "8818", "url": "https://v.example/e/8818"})
    assert stated.uid == "8818"
    assert stated.listing_url == "https://v.example/e/8818"
    # `url` must name a page; `@id` need not. Collapsing the two would either
    # reject an ICS-style opaque id or accept an address that names no page.
    relative = jsonld_identity({"identifier": "8818", "url": "details"})
    assert relative.uid == "8818"
    assert relative.listing_url is None
    assert jsonld_identity(
        {"identifier": "abc123@venue.example"}).uid == "abc123@venue.example"


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


# --- the two rungs, each pinned separately -------------------------------------

def test_a_card_that_is_itself_a_link_still_states_nothing():
    """THE PANEL'S ROUND-4 FINDING, and the third convention to be deleted.

    An Event container that happens to be an `<a>` looks like it declares
    where the listing lives, and it does not: the markup says "this is an
    Event", never "this href is this event's url". Such a card can wrap event
    text while pointing at an artist or series page, and then a later
    occurrence with the same target would match and rewrite a published row.

    Only a labelled `itemprop="url"` survives."""
    html = ("<div>"
            "<a itemscope itemtype='https://schema.org/MusicEvent' href='/e/1'>"
            "Fri Aug 1, 8pm Castle Creek <span>at Wren Hall</span></a>"
            "<a itemscope itemtype='https://schema.org/MusicEvent' href='/e/2'>"
            "Sat Aug 2, 9pm River Delta</a></div>")
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert all(carried_identity(b) == NO_IDENTITY for b in blocks)


def test_a_page_relative_address_is_never_an_identity():
    """ROUND 4's other finding. The segmenter is handed a page's content and
    never its url, so it cannot resolve `details` or `?id=1` — and stored
    verbatim, the SAME string on two pages of one source would compare equal
    and license a write from the wrong occurrence.

    Root-relative survives: `/e/8818` names the path from the host's root, and
    every identity comparison is already source-scoped."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek<a itemprop='url' href='details'>details</a></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta"
            "<a itemprop='url' href='/e/8818'>details</a></div></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == [None, "/e/8818"]


def test_only_a_web_scheme_can_be_a_listings_address():
    """ROUND 5. The scheme check was a DENYLIST plus "has a host", so `ftp://`
    and `webcal://` looked like addresses — each has an authority, so each
    passed, and a repeated non-listing one would satisfy the identity rung on a
    later occurrence.

    It is an ALLOW-LIST now: `http`, `https`, or no scheme at all. Which
    schemes a listing CAN live at is a closed question; which it cannot is an
    open one, and open questions are how this defect kept coming back."""
    assert identity_address("https://v.example/e/1") == "https://v.example/e/1"
    assert identity_address("http://v.example/e/1") == "http://v.example/e/1"
    assert identity_address("//v.example/e/1") == "//v.example/e/1"
    assert identity_address("/events/8817") == "/events/8817"
    for refused in ("ftp://v.example/e/1", "webcal://v.example/e.ics",
                    "custom://v.example/e/1", "details", "?id=1", "#e1", ""):
        assert identity_address(refused) is None, refused
    # Three kinds, three doors. An `@id` must NAME ITSELF but need not be
    # fetchable, so a URN passes the IRI door and fails the address door; an
    # `identifier` is opaque and passes neither but keeps its own.
    assert identity_iri("urn:venue:the-deer") == "urn:venue:the-deer"
    assert identity_address("urn:venue:the-deer") is None
    assert identity_iri("event-1") is None
    assert identity_token("8818") == "8818"
    assert identity_token("abc123@venue.example") == "abc123@venue.example"
    assert identity_iri("8818") is None


def test_an_at_id_must_name_itself_not_merely_carry_a_colon():
    """ROUND 7 — the door asks whether a value NAMES ITSELF, and "has a scheme"
    is not that question.

    In JSON-LD a `prefix:suffix` token is a COMPACT IRI whenever the active
    `@context` defines `prefix` as a term, so `event:8817` denotes whatever
    that context maps `event` to. Nothing on this path reads `@context`, and
    `urlsplit` reports a scheme for a compact IRI exactly as it does for an
    absolute one — so an accept-anything-with-a-colon rule silently readmits
    the round-6 property: a value whose meaning is decided somewhere this code
    cannot see. The scheme is checked against an allow-list instead, the same
    shape round 5 gave `identity_address`, because "which schemes mean the same
    thing in every context?" is a closed question and "which do not?" is not.
    """
    # Self-naming in every context: the web schemes, and URNs — the form a
    # calendar with no per-event pages publishes, which round 6 exists to keep.
    for kept in ("https://v.example/id/1", "http://v.example/id/1",
                 "urn:uuid:abc", "urn:venue:the-deer-2026-09-15",
                 "//v.example/id/1", "/id/1"):
        assert identity_iri(kept) == kept, kept
    # Compact-IRI shaped: refused, whatever the prefix looks like.
    for refused in ("event:8817", "schema:Event", "ev:1", "x:y"):
        assert identity_iri(refused) is None, refused
    # A scheme with nothing after it names nothing at all.
    for empty in ("http:", "https:", "urn:"):
        assert identity_iri(empty) is None, empty
    # The scheme check is case-insensitive, like every other scheme rule here,
    # but the VALUE is never folded — a uid is compared verbatim.
    assert identity_iri("URN:uuid:abc") == "URN:uuid:abc"
    # And the three doors still disagree in the ways they are meant to: a URN
    # names but is not fetchable; an opaque id is neither; a web url is both.
    assert identity_address("urn:uuid:abc") is None
    assert identity_iri("8818") is None and identity_token("8818") == "8818"



def test_an_itemprop_with_no_enclosing_item_declares_nothing():
    """ROUND 8 — a property of NO item is not a declaration.

    Three of the four capture strategies find cards STRUCTURALLY (`<article>`,
    a cardish class, `<li>`) and those carry no microdata at all, so the
    nested-scope counter is trivially zero inside them. Before this round every
    `itemprop="url"` in such a card therefore read as that card's declaration —
    but microdata gives an `itemprop` meaning only against its nearest
    ENCLOSING item, and there is no item here for it to be a property of.

    The fixture is the shape that makes this expensive: a half-finished
    microdata template where `itemprop="url"` sits on the ARTIST link. Reading
    it would store the artist's address as the listing's identity, and an
    artist comes back next month — so the next occurrence answers SAME and
    licenses a `title`/`start_time` write onto the wrong published row. That is
    round 1's deleted convention in a fourth spelling, so it is deleted again
    rather than bounded.

    The page still LISTS: refusing an identity never costs a block.
    """
    blocks = blocks_of("cards_with_orphan_itemprop")
    assert len(blocks) == 3
    for block in blocks:
        assert "Wren Hall" in str(block)
        assert carried_identity(block) == NO_IDENTITY, str(block)
    # And the artist addresses are provably the ones NOT adopted — the failure
    # this refuses is specific, not hypothetical.
    assert "/artists/castle-creek" not in "".join(str(b) for b in blocks)


def test_a_card_that_declares_itself_an_item_is_still_read():
    """The round-8 gate refuses ORPHANS, not microdata — the over-correction
    check, because round 6 shipped one of those and only an existing test
    caught it.

    Same three cards, same `itemprop="url"` links, one difference: the card
    declares `itemscope`. Now the property has an item to belong to, so it is
    a declaration and is adopted. This is the committed fixture the rest of
    the suite uses, asserted here for the contrast."""
    blocks = blocks_of("cards_with_hrefs")
    urls = [carried_identity(b).source_href for b in blocks]
    assert urls == ["/events/8817-castle-creek",
                    "/events/8818-river-delta",
                    "/events/8819-tin-sparrow"]



def test_a_presenter_s_own_page_may_declare_its_own_listings():
    """FOUNDER RULING 2026-09-04 — an official presenter is a TRUSTED DOOR.

    Verbatim: "Official presenters are trusted doors: musician, chef, visual
    artist, professor, author, speaker, personality, company — any named person
    or group. A public list of upcoming work on their site is enough (Home,
    About, Tour, 'upcoming', plain text). Do not require a calendar UI or
    /events. Do not exclude those sites as sources. … Identity on the
    presenter's own page may use that page's Event.url / UID / per-item
    declaration."

    This REVERSED a stricter rule this file carried for about an hour, which
    required a typed card to be an Event and so refused
    `<article itemscope itemtype=".../Person">` outright. That narrowed the
    catalogue, which Coverage Law forbids, so the item's TYPE is not checked.

    What the ruling still refuses is narrower: "using a Person/presenter
    homepage url on ANOTHER entity's card as listing_url for that card." Both
    halves are pinned here.
    """
    presenter = (
        "<html><body><h1>Castle Creek — upcoming</h1>"
        '<article class="event" itemscope itemtype="https://schema.org/Person">'
        '<h2><a itemprop="url" href="/upcoming/8817">Wren Hall</a></h2>'
        "<p>Fri Aug 1, 8pm</p></article>"
        '<article class="event" itemscope itemtype="https://schema.org/Person">'
        '<h2><a itemprop="url" href="/upcoming/8818">Tin Roof</a></h2>'
        "<p>Sat Aug 2, 9pm</p></article>"
        "</body></html>"
    )
    kept = [carried_identity(b).source_href
            for b in segment_events(presenter, content_type="text/html")]
    assert kept == ["/upcoming/8817", "/upcoming/8818"]

    # THE HALF STILL REFUSED: one address standing in for more than one
    # listing. That is the shape "a presenter homepage url on another entity's
    # card" takes on a page — it describes what the cards SHARE, so it
    # identifies neither, and it is dropped from both rather than adopted.
    shared = presenter.replace("/upcoming/8818", "/upcoming/8817")
    assert [carried_identity(b).source_href
            for b in segment_events(shared, content_type="text/html")] == [None, None]

    # And an UNDECLARED artist link on a venue's card is still nothing at all —
    # round 1's rule, untouched by this ruling: there is no declaration to read.
    venue = (
        "<html><body>"
        '<article class="event" itemscope itemtype="https://schema.org/MusicEvent">'
        '<h2><a href="/artists/castle-creek">Castle Creek</a></h2>'
        "<p>Fri Aug 1, 8pm — Wren Hall</p></article>"
        '<article class="event" itemscope itemtype="https://schema.org/MusicEvent">'
        '<h2><a href="/artists/river-delta">River Delta</a></h2>'
        "<p>Sat Aug 2, 9pm — Wren Hall</p></article>"
        "</body></html>"
    )
    for block in segment_events(venue, content_type="text/html"):
        assert carried_identity(block) == NO_IDENTITY, str(block)


def test_a_nested_item_stays_closed_through_same_tag_nesting():
    """The scope stack balances by element, not by tag name. An inner `<div>`
    inside a nested `performer` item used to pop that item's scope early, so
    the performer's url became the event's — a fail-OPEN parser bug raised as a
    nit at round 3 and fixed rather than noted, because open is the direction
    that puts wrong facts on the public surface."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek"
            "<div itemprop='performer' itemscope itemtype='https://schema.org/MusicGroup'>"
            "<div></div><a itemprop='url' href='/artists/cc'>Castle Creek</a></div></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta"
            "<a itemprop='url' href='/e/8818'>details</a></div></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == [None, "/e/8818"]


def test_an_itemprop_url_is_read_wherever_it_sits_in_the_card():
    """Rung 2: the source has LABELLED the field, and that is all that is
    needed — the declaration is not required to be first, or in the heading, or
    the only link. Here it is none of those."""
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


def test_a_nested_items_url_is_not_the_events_url():
    """THE PANEL'S ROUND-2 FINDING: a well-formed Event card NESTS other items —
    `performer`, `location`, `offers` — and each has its own `url`: the artist's
    page, the venue's page, the ticket vendor's. Reading one of those as the
    EVENT's url is the deleted artist-link convention wearing microdata clothes,
    and it would do the same harm across ticks.

    An `itemprop` belongs to its nearest enclosing `itemscope` (the microdata
    spec), so a declaration is read only at the card's OWN scope. Here every
    declaration sits inside a nested item, and both cards state nothing."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek"
            "<span itemprop='performer' itemscope itemtype='https://schema.org/MusicGroup'>"
            "<a itemprop='url' href='/artists/castle-creek'>Castle Creek</a></span>"
            "<span itemprop='location' itemscope itemtype='https://schema.org/Place'>"
            "<a itemprop='url' href='/venues/wren'>Wren Hall</a></span></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta"
            "<span itemprop='performer' itemscope itemtype='https://schema.org/MusicGroup'>"
            "<a itemprop='url' href='/artists/river-delta'>River Delta</a></span></div></div>")
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert all(carried_identity(b) == NO_IDENTITY for b in blocks)


def test_the_cards_own_declaration_is_read_beside_a_nested_one():
    """The other half of the scope rule: a nested performer's url must not
    SUPPRESS the card's own. The event states `/events/8817` at its own scope
    while the performer states `/artists/castle-creek` at its own — one card,
    two scopes, and only the card's belongs to the listing."""
    html = ("<div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Fri Aug 1, 8pm Castle Creek"
            "<span itemprop='performer' itemscope itemtype='https://schema.org/MusicGroup'>"
            "<a itemprop='url' href='/artists/castle-creek'>Castle Creek</a></span>"
            "<a itemprop='url' href='/events/8817'>details</a></div>"
            "<div itemscope itemtype='https://schema.org/MusicEvent'>"
            "Sat Aug 2, 9pm River Delta"
            "<a itemprop='url' href='/events/8818'>details</a></div></div>")
    hrefs = [carried_identity(b).source_href
             for b in segment_events(html, content_type="text/html")]
    assert hrefs == ["/events/8817", "/events/8818"]


def test_a_meta_content_declaration_is_validated_like_an_href():
    """`<meta itemprop="url" content="...">` is the microdata spelling of the
    same declaration, so it passes the SAME address check. A placeholder
    repeated across ticks would otherwise read as one listing and license a
    public write — the panel's round-2 second finding."""
    def cards(first, second):
        return ("<div>"
                "<div itemscope itemtype='https://schema.org/MusicEvent'>"
                f"Fri Aug 1, 8pm Castle Creek<meta itemprop='url' content='{first}'></div>"
                "<div itemscope itemtype='https://schema.org/MusicEvent'>"
                f"Sat Aug 2, 9pm River Delta<meta itemprop='url' content='{second}'></div></div>")

    refused = segment_events(cards("javascript:alert(1)", "#"), content_type="text/html")
    assert len(refused) == 2
    assert all(carried_identity(b) == NO_IDENTITY for b in refused)

    kept = segment_events(cards("https://v.example/e/1", "https://v.example/e/2"),
                          content_type="text/html")
    assert [carried_identity(b).source_href for b in kept] == [
        "https://v.example/e/1", "https://v.example/e/2"]


# --- the carrier changes nothing the extraction surface can see ---------------

def test_the_carrier_leaves_the_block_text_byte_identical():
    """The reason no extraction file is opened: an `IdentifiedBlock` IS its
    text. The certified extractor, the evidence quote and the stored `raw_text`
    receive the same characters they received before this carrier existed —
    pinned as literals rather than derived, so a change to the text is a
    failing test and not a silently re-baselined one."""
    blocks = blocks_of("cards_with_hrefs")
    assert blocks == [
        "Castle Creek Fri Aug 1, 8pm — Wren Hall Event details Tickets",
        "River Delta Sat Aug 2, 9pm — Wren Hall Event details Tickets",
        "Tin Sparrow Sun Aug 3, 7pm — Wren Hall Event details",
    ]
    block = blocks[0]
    assert isinstance(block, str) and isinstance(block, IdentifiedBlock)
    assert json.dumps(block) == json.dumps(str(block))
    assert type(block[:500]) is str          # the evidence quote stays a plain str
    assert hash(block) == hash(str(block))


def test_a_block_survives_being_copied_and_pickled_with_its_identity():
    """A `str` subclass whose `__new__` takes a second argument raises
    TypeError the moment anything copies it, and `copy.deepcopy` is already in
    use on the per-event payloads beside the block in `worker/ai_extract.py`.

    Pinned because the trap only springs when someone later moves a line, and
    because a copy that forgot which listing it was would be a hole invented by
    a copy rather than by a source."""
    block = blocks_of("cards_with_hrefs")[0]
    for clone in (copy.copy(block), copy.deepcopy(block),
                  pickle.loads(pickle.dumps(block))):
        assert clone == str(block)
        assert carried_identity(clone).source_href == "/events/8817-castle-creek"
    # A plain block stays plain through the same round trip.
    plain = blocks_of("cards_without_hrefs")[0]
    assert type(copy.deepcopy(plain)) is str


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
