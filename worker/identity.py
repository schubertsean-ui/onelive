"""A listing's own identity, and the ladder that decides whether two are one.

THE PROBLEM THIS EXISTS FOR, in the words of the four records that all end at
the same trigger: `worker/listing_update.py` has to answer "is this parsed
listing the row we published?" and today it can only ask about the title and
the clock. R-095 (a title is never rewritten), R-097 (a recurring series is
never retimed), R-099 (`start_time` is unwritable BY CONSTRUCTION) and R-102 (a
published hole is never filled) are not four defects. They are one missing fact
read four ways, and every one of them names the SAME objective trigger: "a
stable per-listing identifier on the candidate row."

Title and time are not an identity. A venue puts two bands on at 8pm; a series
repeats its exact title every week; a page renames a show. Each of those makes
one of the two anchors lie, and there is no third anchor to break the tie — so
the honest answer has been to refuse, over and over. An identifier the SOURCE
ITSELF states is that third anchor: an ICS `UID`, a schema.org Event `url` or
`@id`, the listing's own anchor on the page, a claimant's own row url.

WHERE THEY COME FROM (every producer, so the list is auditable rather than
implied): `worker/importers/structured_feed.parse_ics`/`parse_jsonld` for the
licensed store, `worker/claim/intake.py` for a claimant's own row url, and —
since the crawl path had none, which is what R-103 recorded — `worker/segment.py`,
which now hands each block the identity the block's OWN markup stated (a JSON-LD
Event's `url`/`@id`, or an HTML container's own `<a href>`) via `carry_identity`.
`worker/candidate_store.create_candidate` canonicalizes whichever of those a
producer supplied onto `extracted["_identity"]`.

THE ORDER IS THE FOUNDER'S, and each rung means something different:

    adopt      -> the source stated an id and the ids agree: one listing
    composite  -> nobody stated an id: (source, normalized title, start DATE)
    refuse     -> anything else

WHAT THIS MODULE WILL NOT DO, because doing it would be worse than refusing:

  * It never MINTS an identity. A hash of (source | title | start) is the weak
    key wearing a strong key's clothes: it would make the composite rung look
    like the adopt rung and license writes the evidence does not support.
    `worker/importers/structured_feed._stable_external_id` mints exactly such a
    hash for the licensed store's `external_id`, which is why a licensed
    `external_id` is NOT read here as an identity — only the raw `uid`/`url`
    the parse actually found.
  * It never INFERS a url. The candidate's `source_url` is the PAGE, shared by
    every listing on it, so adopting it would make forty shows one show. The
    model's `ticket_link` is a GUESS from block text (`worker/ai_extract.py`),
    and laundering a guess into an identity would rewrite public rows from it.
    Founder, verbatim: "Do not invent a URL."
  * It never decides a MUTATION. It answers identity and nothing else; what a
    given identity licenses is `worker/listing_update.py`'s question.

Pure: stdlib only, no DB, no clock, no network, and no import from the
pipeline. `normalize_title` deliberately stays in `worker/listing_update.py`
and is passed IN — one home for the reduction that decides whether two names
are one name, so the publish side and the mutation side can never drift apart
(the defect that cost PR #214 three rounds).
"""
from __future__ import annotations

import datetime as _dt
import urllib.parse
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

#: The keys an identity is read from, and the ONLY ones. Named as a constant so
#: a caller can assert on the set rather than re-derive it, and so adding a
#: fourth carrier is a deliberate edit with a test behind it.
IDENTITY_FIELDS: Tuple[str, ...] = ("uid", "listing_url", "source_href")

#: Where a canonicalized identity lives on `event_candidate.extracted`. The
#: `_provenance` key on the same jsonb is the precedent: a namespaced sub-object
#: for a machine-read fact, so no migration and no new column is needed to carry
#: one, and nothing that reads the extraction's own fields can collide with it.
IDENTITY_KEY = "_identity"

#: The verdicts the adopt rung can reach. SAME and DIFFERENT are both POSITIVE
#: answers from stated ids; UNKNOWN means nobody stated a comparable one.
SAME = "same"
DIFFERENT = "different"
UNKNOWN = "unknown"


def _clean(value: Any) -> Optional[str]:
    """A stated string, or None. Never a fabricated empty-string identity."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def normalize_url(url: Optional[str]) -> Optional[str]:
    """A url reduced to what an IDENTITY comparison may turn on — and no more.

    Only the two components HTTP itself defines as case-insensitive are folded:
    the scheme and the host. Everything after them is left byte-exact, and that
    restraint is the whole design:

      * the PATH is case-sensitive by spec, and `/events/Wake` and
        `/events/wake` are two different pages on any case-sensitive server;
      * the QUERY carries the id on plenty of calendars (`?event=8817`), so
        dropping or reordering it would merge unrelated listings;
      * the FRAGMENT is frequently the per-listing anchor this stack is FOR
        (`/calendar#event-8817`). A normalizer that strips fragments — which
        most do, because for a page fetch a fragment is noise — would erase
        exactly the identity being captured and silently collapse every listing
        on a calendar into one. (A FRAGMENT-ONLY value never reaches here, and
        neither does a page-relative one: `identity_address` refuses both,
        because neither names a page.)

    A trailing slash is NOT removed either: `/events` and `/events/` are the
    same page on most servers and different ones on some, and being wrong here
    means a false SAME, which writes to a published row. Under-matching costs a
    refusal; over-matching costs a wrong public listing.
    """
    raw = _clean(url)
    if raw is None:
        return None
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        # An unparseable url is still a stated string; compare it verbatim
        # rather than dropping it (dropping would silently widen the ladder to
        # the weak rung, which is the fail-OPEN direction).
        return raw
    if not parts.scheme and not parts.netloc:
        return raw  # a bare path/anchor: nothing case-insensitive to fold
    return urllib.parse.urlunsplit((
        parts.scheme.lower(), parts.netloc.lower(),
        parts.path, parts.query, parts.fragment,
    ))


@dataclass(frozen=True)
class ListingIdentity:
    """What a source SAID identifies one listing. Every field is optional and
    an absent field is a hole, never a guess.

    * `uid` — the source's own id: an ICS `UID`, a JSON-LD `identifier`, or a
      JSON-LD `@id` that NAMES ITSELF (an `@id` is an IRI against the document
      base AND may be a compact IRI against the document's `@context`, so a
      page-relative one and a compact-IRI-shaped one are both refused while a
      URN is kept — see `jsonld_identity`). Compared verbatim
      (case-SENSITIVE): a UID is an opaque token and folding its case would
      merge two ids a source deliberately distinguished.
    * `listing_url` — the listing's own address, as the source published it
      (an ICS `URL`, a schema.org `Event.url`, a claimant's row url).
    * `source_href` — the listing's anchor on the page it was read from, as
      the page wrote it. `worker/segment.py` produces it: a block cut from an
      HTML container carries that container's own `<a href>`, VERBATIM — a
      relative href stays relative, because resolving one against a page url
      the segmenter is not given would be inventing an address. It is compared
      exactly like the other two (see `normalize_url`, which folds only what
      HTTP itself calls case-insensitive), and comparisons are source-scoped by
      `worker/listing_update.py`, so two sources' `/events/1` never meet.
    """

    uid: Optional[str] = None
    listing_url: Optional[str] = None
    source_href: Optional[str] = None

    @property
    def stated(self) -> bool:
        """True when the source stated at least one identity field."""
        return any((self.uid, self.listing_url, self.source_href))

    def as_dict(self) -> Dict[str, str]:
        """The stated fields only — an absent field is absent from the jsonb,
        never stored as an empty string that would later read as 'stated'."""
        out: Dict[str, str] = {}
        if self.uid:
            out["uid"] = self.uid
        if self.listing_url:
            out["listing_url"] = self.listing_url
        if self.source_href:
            out["source_href"] = self.source_href
        return out


#: An identity with nothing stated. Shared so callers do not each build one.
NO_IDENTITY = ListingIdentity()


def read_identity(payload: Optional[Mapping[str, Any]]) -> ListingIdentity:
    """The identity a payload STATES, reading only IDENTITY_FIELDS.

    Accepts the shape `worker/importers/structured_feed.parse_ics` and
    `parse_jsonld` already return (both set `uid`, and both set `url` for the
    listing's own address), the canonicalized `extracted["_identity"]`
    sub-object, and a raw `extracted` payload. Nothing else is consulted — in
    particular `source_url`, `ticket_link` and `rsvp_link` are NOT identity:
    the first is the page every listing on it shares, and the other two are
    fields the model fills from block text.

    A payload that states nothing returns NO_IDENTITY, which is a hole and
    routes the ladder to its composite rung — never a match.
    """
    if not isinstance(payload, Mapping):
        return NO_IDENTITY
    nested = payload.get(IDENTITY_KEY)
    if isinstance(nested, Mapping):
        # Already canonicalized (a stored candidate). Read it directly rather
        # than re-deriving, so a stored identity cannot drift from itself.
        payload = nested
    listing_url = _clean(payload.get("listing_url"))
    if listing_url is None:
        # `url` is the key BOTH structured parses use for the listing's own
        # address (ICS URL:, schema.org Event.url), so it is accepted as the
        # same field under its other name. It is read only when `listing_url`
        # is absent, so a canonicalized payload always wins over a raw one.
        listing_url = _clean(payload.get("url"))
    return ListingIdentity(
        uid=_clean(payload.get("uid")),
        listing_url=listing_url,
        source_href=_clean(payload.get("source_href")),
    )


def identity_verdict(a: ListingIdentity, b: ListingIdentity) -> str:
    """SAME / DIFFERENT / UNKNOWN for two identities. The ADOPT rung.

    Compares only the fields BOTH sides state — a field one side is missing is
    a hole and says nothing, which is the trust doctrine's own rule (existence
    with holes) applied to identity.

    Where a field is comparable it is DECISIVE IN BOTH DIRECTIONS, and the
    negative direction is the half that matters most: two listings whose source
    gave them different UIDs are two listings, whatever their titles and clocks
    agree about. Without that, a stated id could only ever ADD matches, and the
    8pm collision the founder names would still be resolvable by the weak rung
    on a page that had already told us the answer.

    Any single agreeing field is enough for SAME; any single disagreeing field
    is enough for DIFFERENT, and DIFFERENT wins over SAME when a page states
    both (a source that gives one listing another's url has contradicted
    itself, and a contradiction is never an identity).
    """
    verdicts = []
    for left, right in (
        (a.uid, b.uid),
        (normalize_url(a.listing_url), normalize_url(b.listing_url)),
        (normalize_url(a.source_href), normalize_url(b.source_href)),
    ):
        if left is None or right is None:
            continue
        verdicts.append(SAME if left == right else DIFFERENT)
    if DIFFERENT in verdicts:
        return DIFFERENT
    if SAME in verdicts:
        return SAME
    return UNKNOWN


def weak_key(
    source_id: Optional[Any],
    normalized_title: Optional[str],
    start: Optional[_dt.datetime],
) -> Optional[Tuple[str, str, _dt.date]]:
    """The COMPOSITE rung: (source_id, normalized title, start DATE), or None.

    The founder's own key, and the DATE rather than the minute is deliberate on
    both sides of the trade. Looser: a listing whose clock moved within the day
    still keys to the same row, which is exactly the maintenance case a
    minute-exact key cannot see. Weaker: a venue with an early and a late show
    of the same name on one night keys to ONE value twice — which is why this
    rung is a key and not a licence. `worker/listing_update.py` resolves the
    cardinality across the whole page and refuses when two rows claim one
    listing, and no field is written on this rung at all.

    None when any part is missing. A key with a hole in it is not a key: two
    untitled listings from one source on one day would otherwise collide into
    a match, and the extraction prompt makes a null title common
    (`ai/prompts.py`).

    `start` may be tz-aware or naive; the DATE is taken in UTC either way, the
    same reading `worker/listing_update._as_utc` uses because these values come
    from the same `timestamptz` columns.
    """
    sid = _clean(str(source_id) if source_id is not None else None)
    title = _clean(normalized_title)
    if sid is None or title is None or start is None:
        return None
    when = start if start.tzinfo is not None else start.replace(tzinfo=_dt.timezone.utc)
    return (sid, title, when.astimezone(_dt.timezone.utc).date())


#: Schemes that are not the address of anything a calendar lists. A value
#: naming one is not an address, whichever carrier states it — an `href`, a
#: `<meta content>`, or a JSON-LD `url`.
NON_ADDRESS_SCHEMES: Tuple[str, ...] = (
    "javascript:", "mailto:", "tel:", "sms:", "data:",
)

#: The schemes a LISTING can live at. An allow-list, because "which schemes are
#: wrong?" is an open question and "which are right?" is a closed one — see
#: `identity_address`, where a denylist let `ftp://` and `webcal://` through.
WEB_SCHEMES: Tuple[str, ...] = ("http", "https")

#: The schemes an `@id` can NAME ITSELF with. Also an allow-list, and for a
#: sharper reason than `identity_address`'s: in JSON-LD a `prefix:suffix` token
#: is a COMPACT IRI whenever the active `@context` defines `prefix` as a term,
#: and it then means whatever that context says — `event:8817` under one
#: context and the same string under another are two different resources.
#: `urlsplit` cannot tell a compact IRI from an absolute one (both report a
#: scheme), and nothing on this path reads `@context`, so "does it have a
#: scheme?" is the wrong question: these are the schemes that mean the same
#: thing no matter what context surrounds them. Everything else is treated as
#: possibly-compact and REFUSED — fail closed, per the round-7 finding.
SELF_NAMING_SCHEMES: Tuple[str, ...] = WEB_SCHEMES + ("urn",)


def identity_token(value: Any) -> Optional[str]:
    """An OPAQUE id a source stated, or None. For `uid` only.

    A uid is a token, not an address: an ICS `UID` is `abc123@venue.example`, a
    JSON-LD `identifier` is often just `8818`. So this refuses only what cannot
    be an identity at all:

      * empty / whitespace — a source that stated nothing stated nothing;
      * a non-address scheme (`javascript:`, `mailto:`, `tel:`, `sms:`,
        `data:`) — no source identifies a listing by one, and a placeholder
        repeated across ticks must not read as one listing;
      * a FRAGMENT-ONLY value (`#`, `#event-1`) — with no page to anchor into,
        the same fragment on two pages of one source compares equal.

    `identity_address` is the stricter door every URL-VALUED carrier goes
    through. The two are separate because collapsing them would either reject
    `8818` (an id) or accept `details` (an address that names no page) — three
    review rounds arrived at that split, and it is the whole reason this
    function does not also demand a host or a leading slash.
    """
    raw = _clean(value)
    if raw is None:
        return None
    if raw.startswith("#"):
        return None
    if raw.lower().startswith(NON_ADDRESS_SCHEMES):
        return None
    return raw


def identity_iri(value: Any) -> Optional[str]:
    """An identifier that names itself, or None. For a JSON-LD `@id`.

    An `@id` is an IRI resolved against the DOCUMENT BASE, so a page-relative
    one (`event-1`, `details`, `?id=1`) means something different on every page
    that states it — and this path has no base url to resolve it against, so
    the same raw string on two pages of a source would be stored as one uid and
    could license a write from the wrong occurrence. That is the round-6
    finding, and it is why `@id` cannot share the opaque-token door with
    `identifier`.

    But it does not belong in `identity_address` either, and the difference is
    the point: a `url` must be FETCHABLE, so its scheme is restricted to the
    web; an `@id` only has to NAME something, so `urn:venue:the-deer-2026-09-15`
    qualifies — a calendar whose events have no separate pages uses exactly that
    because it is stable and belongs to nobody's page. Refusing it would have
    thrown away the case `tests/test_identity_stack.py` was built for, which is
    how this rule was caught being too strict before it shipped.

    "Names itself" is a stronger demand than "has a scheme", and round 7 is why
    the two were not the same question. In JSON-LD a `prefix:suffix` token is a
    COMPACT IRI whenever the active `@context` defines `prefix`, so `event:8817`
    means whatever that context says it means — and this path never sees the
    context. `urlsplit` reports a scheme for it exactly as it does for a real
    IRI, so an accept-anything-with-a-colon rule silently readmits the very
    property round 6 closed: a value whose meaning is decided elsewhere. The
    scheme is therefore checked against `SELF_NAMING_SCHEMES`, and anything
    outside it is treated as possibly-compact and refused.

    The residual, named rather than implied: a context MAY define `urn` (or
    `http`) as a prefix term, which would make even an allow-listed value
    compact. That is a source deliberately publishing an id that means one
    thing and reads as another — the same "a source we cannot believe" class as
    a source publishing one constant id for every show, which no per-value rule
    can detect either. It is not what this door claims to close.

    Accepted: an allow-listed scheme WITH a non-empty remainder (`http:` names
    nothing), the protocol-relative form (a host), and a root-relative path.
    Refused: page-relative values, compact-IRI-shaped values, plus everything
    `identity_token` already refuses.
    """
    raw = identity_token(value)
    if raw is None:
        return None
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        return None
    if parts.scheme:
        if parts.scheme.lower() not in SELF_NAMING_SCHEMES:
            return None
        # A scheme alone names nothing: `http:` and `urn:` are not ids.
        return raw if (parts.netloc or parts.path) else None
    if parts.netloc:
        return raw
    if raw.startswith("/"):
        return raw
    return None


def identity_address(value: Any) -> Optional[str]:
    """An address that names a PAGE-INDEPENDENT location, or None. For every
    url-valued carrier: an `href`, a `<meta content>`, a JSON-LD `Event.url`.

    `worker/segment.py` is handed a page's CONTENT and never its url, so it
    cannot resolve a relative address and must not invent one (founder,
    verbatim: "Do not invent URLs"). That makes page-RELATIVE values unusable
    as identities, not merely imprecise: `href="details"`, `href="event-1"`,
    `href="?id=1"` and `href="../e/1"` are resolved by the browser against
    whatever page they appeared on, so the SAME string on two pages of one
    source points at two different shows — and stored verbatim, it would let a
    later tick call them one listing and rewrite a published row with the wrong
    occurrence's title and clock. The adversarial panel found exactly that at
    round 4, on both openai seats.

    Accepted, because each names its own location without a page to lean on:

      * an absolute WEB url (`https://v.example/e/8817`), and the
        protocol-relative form (`//v.example/e/8817`), which names the host;
      * a ROOT-relative path (`/events/8817`), which names the path from the
        host's root — still relative to the source, which is exactly the scope
        every identity comparison already runs in.

    The scheme rule is an ALLOW-LIST — `http`, `https`, or none — and that
    inversion is the round-5 finding. A denylist of obviously-wrong schemes
    left `ftp://`, `webcal://` and any other authority-bearing scheme through:
    each has a `netloc`, so each looked like an address, and a repeated
    non-listing one would satisfy the identity rung on a later occurrence.
    Listing the schemes a listing CAN live at is a closed question; listing the
    ones it cannot is an open one, and open questions are how this defect kept
    coming back. (`identity_token` keeps a denylist because a uid is opaque —
    there is no set of schemes an id must be drawn from.)

    Anything else is refused. Under-matching costs a refusal; over-matching
    costs a wrong public listing.
    """
    raw = identity_token(value)
    if raw is None:
        return None
    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        # Unparseable: it cannot be shown to name a page-independent location,
        # so it does not get to be one. (The identity ladder's other rungs are
        # unaffected — a refusal here is a hole, never a match.)
        return None
    if parts.scheme and parts.scheme.lower() not in WEB_SCHEMES:
        return None
    if parts.netloc:
        return raw
    if not parts.scheme and raw.startswith("/"):
        return raw
    return None


def ld_scalar(v: Any) -> Optional[str]:
    """A JSON-LD scalar string, or None — never a fabricated value.

    Unwraps the two shapes JSON-LD writers actually emit for a value that could
    have been a bare string: the ``{"@value": ...}`` box, and a list (the first
    element). A nested node is read through its ``name``/``url`` so a
    ``{"@type": "Place", "name": "Wren Hall"}`` reads as its name.

    One home, deliberately: `worker/importers/structured_feed.py` imports this
    as its own scalar reader, so the licensed-feed importer and the crawl path
    can never drift apart about what a JSON-LD value says.
    """
    if isinstance(v, str):
        return v or None
    if isinstance(v, dict):
        return ld_scalar(v.get("@value") or v.get("name") or v.get("url"))
    if isinstance(v, list) and v:
        return ld_scalar(v[0])
    return None


def _ld_single(v: Any) -> Optional[str]:
    """The one value a JSON-LD field states, or None when it states several.

    `ld_scalar` takes the FIRST element of a list, which is right for a fact
    (a name, a start date) and wrong for an identity: a source listing several
    urls has not said which one is the listing's, and silently taking the first
    would adopt whichever the page happened to put first — an artist page, a
    vendor page. Two distinct values are a contradiction, and a contradiction
    is never an identity; the HTML path already refuses the same shape (two
    `itemprop="url"` declarations), and this is that rule's sibling carrier.
    """
    if isinstance(v, list):
        stated = {s for s in (ld_scalar(item) for item in v) if s}
        if len(stated) != 1:
            return None
        return stated.pop()
    return ld_scalar(v)


def jsonld_identity(obj: Optional[Mapping[str, Any]]) -> ListingIdentity:
    """The identity ONE schema.org Event object states, and nothing else.

    The single place in the tree that answers "which JSON-LD keys are an
    identity": ``url`` is the listing's own address (`listing_url`), and
    ``@id`` / ``identifier`` is the source's own opaque id (`uid`) — the same
    reading `worker/importers/structured_feed.parse_jsonld` has always used for
    the licensed store, now shared rather than mirrored.

    Everything else on the object is a FACT about the listing, not a handle on
    it: ``name`` and ``startDate`` are the weak key's own ingredients, and
    ``offers.url`` is a ticket vendor's page — a different resource, often
    shared across several listings, and never the listing's identity.

    Every value is read with `_ld_single` and passes the validator its KIND
    calls for: `url` must be fetchable (`identity_address`), `@id` must name
    itself (`identity_iri` — a URN qualifies, a page-relative string does not),
    and `identifier` is opaque (`identity_token`, so `"8818"` is kept). A field
    stating several different values states none. An object stating none
    returns NO_IDENTITY.
    """
    if not isinstance(obj, Mapping):
        return NO_IDENTITY
    # Three carriers, three kinds, three doors — and the round-6 finding was
    # that `@id` and `identifier` had been sharing one:
    #   url        must be FETCHABLE   -> identity_address (web schemes only)
    #   @id        must NAME ITSELF    -> identity_iri (a self-naming scheme,
    #                                     protocol- or root-relative; never
    #                                     page-relative and never compact-IRI
    #                                     shaped, because an @id resolves
    #                                     against a document base AND an
    #                                     @context this path never sees)
    #   identifier is OPAQUE           -> identity_token (`8818` is a fine id)
    uid = identity_iri(_ld_single(obj.get("@id")))
    if uid is None:
        uid = identity_token(_ld_single(obj.get("identifier")))
    return ListingIdentity(
        uid=uid,
        listing_url=identity_address(_ld_single(obj.get("url"))),
    )


class IdentifiedBlock(str):
    """A segmented block of text that also remembers the identity ITS OWN
    markup stated.

    It IS a `str` — the same characters, comparing, slicing, hashing and
    serializing exactly as the plain block does — because the block travels
    through `worker/ai_extract.py` untouched (as the extractor's input, as the
    evidence quote, and as `create_candidate`'s `raw_text`), and the certified
    extraction surface must receive byte-identical input to what it received
    before this carrier existed. The identity is a SIDECAR on the object, never
    a change to the text.

    That sidecar is the whole reason no extraction file is opened to build the
    producer: the block is already the one per-listing object that reaches the
    persist seam, so the fact the segmenter knew (this listing's own anchor)
    can ride with it instead of being discarded at the strip-to-text step.
    """

    __slots__ = ("identity",)

    def __new__(cls, text: str, identity: ListingIdentity) -> "IdentifiedBlock":
        obj = super().__new__(cls, text)
        obj.identity = identity
        return obj

    def __getnewargs__(self) -> Tuple[str, ListingIdentity]:
        """Both constructor arguments, so `copy` and `pickle` can rebuild one.

        Without this a `str` subclass whose `__new__` takes a second argument
        raises `TypeError` the moment anything copies it — and `copy.deepcopy`
        is already used on the per-event payloads beside this block in
        `worker/ai_extract.py`. The block is not copied there today, which is
        exactly why this had to be fixed rather than left: a landmine that only
        goes off when someone later moves a line is worse than one that goes
        off now. Rebuilding carries the identity with the text, because a copy
        of a listing that forgot which listing it was would be a hole invented
        by a copy.
        """
        return (str(self), self.identity)


def carry_identity(text: str, identity: ListingIdentity) -> str:
    """`text` carrying `identity`, or `text` UNCHANGED when nothing is stated.

    The no-identity case stays a plain `str` on purpose: a page whose markup
    names no listing url must produce blocks that are identical in type and in
    value to the ones it produced before this module had a carrier, so "we
    captured nothing" and "there was nothing to capture" cannot be told apart
    downstream — because they are the same thing.
    """
    if not identity.stated:
        return text
    return IdentifiedBlock(text, identity)


def carried_identity(value: Any) -> ListingIdentity:
    """The identity an object CARRIES, or NO_IDENTITY.

    Reads only an `identity` attribute that is genuinely a `ListingIdentity`,
    so an unrelated object that happens to have an `identity` attribute (a DB
    row wrapper, a mock) can never be mistaken for a stated id. A plain string
    — every block from a page that stated nothing, and every `raw_text` from a
    producer that does not segment — carries nothing.
    """
    identity = getattr(value, "identity", None)
    return identity if isinstance(identity, ListingIdentity) else NO_IDENTITY
