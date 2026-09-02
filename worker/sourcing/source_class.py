"""Source-class taxonomy A–F (ONE-LIVE-COVERAGE-LAW.md, "Source classes").

Coverage Law defines six classes and one hard rule: class D (login / paywall /
bot wall) is NEVER fetched — it gets a claim/submit path instead. Every other
class may be ingested in any locale without asking permission for the locale.

    A  structured open   ICS, RSS, public API, CSV, JSON-LD
    B  public HTML       loads without login
    C  public visual     flyer / PDF / poster — later, not this module's job
    D  closed door       login / paywall / bot wall — DO NOT FETCH
    E  first party       claimed ICS / calendar / CSV upload
    F  human report      link or photo submit

This module answers ONE question mechanically: given a source-catalog entry,
which class is it, and on what evidence? The verdict is derived ONLY from the
catalog's own declared fields (`access_method`, `allowed`,
`explicitly_disallowed`) — never from a guess about the site, and never from
the URL string. That matters because the catalog is the thing a human curates:
if a classification is wrong, the fix is a data edit, not a code edit, and the
reason string names the exact token that decided it.

Two-stage by design:

  * classify_entry() reads the DECLARED access posture before any network
    contact. It is pure, offline, and total — every entry gets a class.
  * demote_on_response() reads what the site ACTUALLY did on first contact.
    A login redirect, a 401/402/403, or a rate-limit refusal is a wall we only
    learn about by knocking once politely; when we see one, the source becomes
    class D and goes to the claim queue. We do not knock twice, and we never
    try to get around it (charter: no login/paywall/bot-protection bypass).

Fail direction: UNKNOWN access posture classifies as D, not as B. Refusing to
fetch a source we cannot vouch for costs us one row in a queue; fetching a wall
we were not invited through is a trust-invariant breach. Coverage Law's greedy
catalog widens what we KEEP, never what we FORCE.

Pure/deterministic, stdlib-only (no network, no DB) → unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

# The six Coverage Law classes. Kept as module constants so callers compare
# against a symbol rather than a bare letter that a typo could silently break.
CLASS_A_STRUCTURED_OPEN = "A"
CLASS_B_PUBLIC_HTML = "B"
CLASS_C_PUBLIC_VISUAL = "C"
CLASS_D_CLOSED_DOOR = "D"
CLASS_E_FIRST_PARTY = "E"
CLASS_F_HUMAN_REPORT = "F"

#: Classes this session's ingest path is allowed to fetch. C is deferred by
#: Coverage Law ("later"); D is never fetched by anyone, ever.
FETCHABLE_CLASSES = frozenset({CLASS_A_STRUCTURED_OPEN, CLASS_B_PUBLIC_HTML})

#: Every class letter classify_entry may return. Callers that accept a letter
#: from a human (a workflow input, a CLI flag) validate against THIS set so an
#: unknown letter fails closed instead of silently matching nothing.
CLASS_LETTERS = frozenset({
    CLASS_A_STRUCTURED_OPEN, CLASS_B_PUBLIC_HTML, CLASS_C_PUBLIC_VISUAL,
    CLASS_D_CLOSED_DOOR, CLASS_E_FIRST_PARTY, CLASS_F_HUMAN_REPORT,
})

# --- Declared-posture vocabulary (read off the catalog, not invented) ---------
#
# Every token below appears in sources/master_sources_catalog_120.json. When the
# catalog grows a NEW token, it lands in neither set and the entry classifies D
# with reason "unrecognized access posture" — a visible queue row a human
# resolves, never a silent fetch of something nobody vetted.

#: access_method values that need a credential, a partnership, or a human step —
#: there is no public URL we may simply read. Closed door.
_CLOSED_ACCESS = frozenset({
    "oauth_api", "oauth_connect", "api_key_oauth", "api_key",
    "partner_preferred", "manual_only",
})

#: access_method values that advertise a machine-readable open feed.
_STRUCTURED_ACCESS = frozenset({
    "public_web_or_ics", "public_web_or_feed", "localist_feed",
    "official_feed_or_partner", "api_open", "api_or_public",
})

#: access_method values with a plain public read path (HTML we may fetch).
_PUBLIC_ACCESS = frozenset({
    "public_web", "public_pages", "partner_or_public", "public_web_or_partner",
    "api_or_partner",
})

#: `allowed` tokens that advertise a structured feed at the far end.
_STRUCTURED_ALLOWED = frozenset({
    "ics_feed_if_offered", "localist_json_feed", "official_feed", "partner_export",
    "open_data_lucene_search", "jsonld_if_offered", "feed_if_offered",
})

#: `allowed` tokens that grant a public HTML read.
_PUBLIC_ALLOWED = frozenset({
    "public_calendar_pages", "public_pages", "public_event_pages",
    "structured_feed_verify",
})

#: First-party claimed intake — the venue hands US the file. Class E.
_FIRST_PARTY_ACCESS = frozenset({"claimed_upload", "opt_in_email_forward"})
_FIRST_PARTY_ALLOWED = frozenset({
    "ics_upload", "csv_upload", "opt_in_email_parse", "opt_in_links",
})

#: `explicitly_disallowed` tokens that forbid automated reading outright. The
#: catalog is stating the site's own rule; we honor it by never fetching and
#: routing the source to a claim path instead.
_NO_AUTOMATED_READ = frozenset({"automated_ingest"})

# --- Runtime wall signals -----------------------------------------------------
#
# A bot wall is not declarable in advance — it announces itself on contact.
# These are the HTTP statuses that mean "you are not invited": 401/407 auth,
# 402 payment, 403 forbidden, 429 rate-limit refusal. A 404/500 is a broken or
# missing page, NOT a wall — those stay in their declared class so a transient
# outage never permanently demotes a legitimate public source.
WALL_STATUSES = frozenset({401, 402, 403, 407, 429})


@dataclass(frozen=True)
class ClassVerdict:
    """A class letter plus the evidence that produced it.

    `reason` names the deciding token verbatim so a human reading the claim
    queue can audit the call without re-deriving it, and `fetchable` is the
    single boolean the ingest path branches on — no caller re-implements the
    "may I fetch this?" rule.
    """

    source_class: str
    reason: str
    fetchable: bool

    @property
    def is_closed_door(self) -> bool:
        return self.source_class == CLASS_D_CLOSED_DOOR


def _tokens(entry: Dict[str, Any], key: str) -> frozenset:
    """Lower-cased token set for a catalog list field, tolerating None/absent."""
    return frozenset(str(t).lower() for t in (entry.get(key) or []))


def classify_entry(entry: Dict[str, Any]) -> ClassVerdict:
    """Classify one source-catalog entry from its DECLARED access posture.

    Total by construction: every entry returns a verdict. Order matters — the
    checks run most-restrictive first, so a source that both forbids automated
    ingest and offers public pages resolves to D (the restriction wins).
    """
    access = str(entry.get("access_method") or "").lower()
    allowed = _tokens(entry, "allowed")
    disallowed = _tokens(entry, "explicitly_disallowed")

    # 1. The site's own "no automated reading" rule outranks everything.
    forbidden = disallowed & _NO_AUTOMATED_READ
    if forbidden:
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            f"explicitly_disallowed contains {sorted(forbidden)[0]!r} — the source "
            "forbids automated ingest; claim/submit path only",
            fetchable=False,
        )

    # 2. First party BEFORE every other check, INCLUDING the missing-URL check:
    #    a claimed upload or an email opt-in legitimately has no base_url — the
    #    venue hands us the file, so there is nothing for us to go and fetch.
    #    Ordering this after the URL check would misfile the two intake lanes as
    #    closed doors and put "go find their calendar URL" in the claim queue,
    #    which is the wrong ask for a source that is already inviting us in.
    if access in _FIRST_PARTY_ACCESS:
        return ClassVerdict(
            CLASS_E_FIRST_PARTY,
            f"access_method {access!r} — first-party claimed intake",
            fetchable=False,
        )
    first_party = allowed & _FIRST_PARTY_ALLOWED
    if first_party:
        return ClassVerdict(
            CLASS_E_FIRST_PARTY,
            f"allowed contains {sorted(first_party)[0]!r} — first-party claimed intake",
            fetchable=False,
        )

    # 3. No URL to read is the same practical wall as a login: nothing to fetch.
    if not entry.get("base_url"):
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            "no base_url in the catalog entry — nothing public to fetch",
            fetchable=False,
        )

    # 4. Credential / partnership / manual-only: closed door.
    if access in _CLOSED_ACCESS:
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            f"access_method {access!r} — needs a credential, a partnership, or a "
            "human step; no public URL to read",
            fetchable=False,
        )

    # 5. Structured open feed advertised → class A.
    structured = allowed & _STRUCTURED_ALLOWED
    if access in _STRUCTURED_ACCESS:
        return ClassVerdict(
            CLASS_A_STRUCTURED_OPEN,
            f"access_method {access!r} — advertises a machine-readable open feed",
            fetchable=True,
        )
    if structured:
        return ClassVerdict(
            CLASS_A_STRUCTURED_OPEN,
            f"allowed contains {sorted(structured)[0]!r} — advertises a "
            "machine-readable open feed",
            fetchable=True,
        )

    # 6. Public HTML read path → class B.
    public = allowed & _PUBLIC_ALLOWED
    if access in _PUBLIC_ACCESS or public:
        deciding = (
            f"access_method {access!r}" if access in _PUBLIC_ACCESS
            else f"allowed contains {sorted(public)[0]!r}"
        )
        return ClassVerdict(
            CLASS_B_PUBLIC_HTML,
            f"{deciding} — public HTML, loads without login",
            fetchable=True,
        )

    # 7. Unrecognized posture. Fail toward "do not fetch" (see module docstring).
    return ClassVerdict(
        CLASS_D_CLOSED_DOOR,
        f"unrecognized access posture (access_method={access!r}, "
        f"allowed={sorted(allowed)}) — not vetted as publicly readable, so it is "
        "queued rather than fetched",
        fetchable=False,
    )


def demote_on_response(
    verdict: ClassVerdict,
    *,
    status: Optional[int] = None,
    final_url: Optional[str] = None,
    error: Optional[str] = None,
) -> ClassVerdict:
    """Re-class a source to D when first contact reveals a wall.

    Coverage Law lets us knock once. If the answer is "you are not invited" —
    an auth/payment/forbidden/rate-limit status, or a redirect that lands on a
    login page — the source is class D from that moment: we stop, and it goes
    to the claim queue. Anything else (404, 5xx, a timeout, a DNS failure)
    leaves the declared class intact, because a broken page is not a wall and a
    transient outage must not permanently shrink coverage.

    Returns `verdict` unchanged when nothing wall-like was seen, so callers can
    apply it unconditionally.
    """
    if status is not None and status in WALL_STATUSES:
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            f"HTTP {status} on first contact — the source refused an "
            "unauthenticated read; queued for a claim path, not retried",
            fetchable=False,
        )

    if final_url and _looks_like_login(final_url):
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            f"redirected to a sign-in URL ({final_url}) — login wall; queued for "
            "a claim path, not retried",
            fetchable=False,
        )

    if error and _looks_like_login(error):
        return ClassVerdict(
            CLASS_D_CLOSED_DOOR,
            f"fetch reported a sign-in requirement ({error}) — login wall; queued "
            "for a claim path, not retried",
            fetchable=False,
        )

    return verdict


def wall_signals_from_exception(exc: BaseException) -> Tuple[Optional[int], Optional[str]]:
    """The (http_status, final_url) a fetch adapter's exception carries.

    worker.fetch.http_fetch.fetch_url calls raise_for_status(), so a wall
    arrives as an EXCEPTION, not a return value — the status that decides
    class D lives on the requests.HTTPError's `.response`. Every caller that
    has to tell "you are not invited" (401/402/403/407/429, or a redirect that
    landed on a sign-in page) from "the page is broken" (404, 5xx, timeout,
    DNS) needs the same two facts off the same object, so the recovery lives
    here once: the ingest loop and the class B walker both read it, and a
    second copy would be a second definition of what counts as a wall.

    Returns (None, None) for a transport failure that never produced a
    response — the honest answer, and demote_on_response leaves the declared
    class intact for it (a broken page is not a wall).
    """
    response = getattr(exc, "response", None)
    return (getattr(response, "status_code", None),
            getattr(response, "url", None))


#: Substrings that mark a URL (or an error string) as a sign-in surface. Matched
#: case-insensitively. Deliberately short and specific: a false positive here
#: costs coverage, so we only claim "login wall" on unambiguous markers.
_LOGIN_MARKERS = ("/login", "/signin", "/sign-in", "/sign_in", "/auth/", "/accounts/login",
                  "oauth/authorize", "captcha", "are you a robot")


def _looks_like_login(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _LOGIN_MARKERS)


def looks_like_login_url(value: str) -> bool:
    """Public name for the sign-in-surface test above.

    The claim intake (worker/claim/intake.py) has to answer the SAME question
    about a URL a venue pastes in — "is this a feed, or a login screen?" — and
    two copies of the marker list would drift apart in exactly the direction
    that costs us: one surface would start accepting a sign-in URL the other
    refuses. One authority, two callers.
    """
    return _looks_like_login(value or "")


def classify_catalog(catalog: list) -> Dict[str, ClassVerdict]:
    """Classify a whole catalog, keyed by entry id.

    An entry with no usable id is keyed by its name so it still appears — a
    source must never vanish from the class report for want of an id field
    (Coverage Law: a dropped row is a defect, and that includes this report).
    """
    out: Dict[str, ClassVerdict] = {}
    for entry in catalog:
        key = str(entry.get("id") or entry.get("name") or f"entry_{len(out)}")
        out[key] = classify_entry(entry)
    return out
