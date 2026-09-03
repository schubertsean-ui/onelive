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
        on a calendar into one.

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

    * `uid` — the source's own opaque id: an ICS `UID`, a JSON-LD `@id` or
      `identifier`. Compared verbatim (case-SENSITIVE): a UID is an opaque
      token and folding its case would merge two ids a source deliberately
      distinguished.
    * `listing_url` — the listing's own address, as the source published it
      (an ICS `URL`, a schema.org `Event.url`, a claimant's row url).
    * `source_href` — the listing's anchor on the page it was read from. NO
      CAPTURE PATH EXISTS TODAY (see the module docstring's stop condition);
      the field is here so a producer has somewhere to put one, and it is read
      exactly like the other two when something states it.
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
