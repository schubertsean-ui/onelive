"""Claim intake — the PURE half of the class-D → class-E/F door.

Coverage Law (ONE-LIVE-COVERAGE-LAW.md, "Source classes") calls class D a
closed door — login, paywall, or bot wall — and states the only lawful
response: **do not fetch; open a claim/submit path instead.** A venue whose
listings live behind a login is not out of scope; it is out of REACH, and the
reach it is missing is an invitation. This module turns that invitation into a
catalog row.

Three ways in, all of them the organizer handing us the data rather than us
taking it:

    ics_url        they paste the address of their own calendar feed
    csv_upload     they paste (or upload) a spreadsheet of their listings
    email_forward  they forward their listings to the intake mailbox

WHO hands it over decides the class, mechanically, with no judgement call:

    organizer    -> class E (first party — the venue/promoter's own listings)
    third_party  -> class F (human report — someone telling us about an event)

TWO REFUSALS ARE STRUCTURAL, not policy:

1. **Confidence is never an input.** Every claim is recorded at `unverified`
   and the caller cannot ask for anything else — `CLAIM_CONFIDENCE` is a
   constant, not a parameter. A self-serve claim is an ASSERTION of ownership,
   not proof of it, and `claimed_upload` / `email_opt_in` are ANCHOR classes in
   worker/gating.py that promote on one source. If a claim could name its own
   class or confidence, anyone with the form could impersonate a venue straight
   into `confirmed`. So claims carry the two UNVERIFIED classes below, which
   worker/gating.py names third-party: the listings HOLD at the existing gate
   until a human verifies the claimant, exactly as an uncorroborated stranger's
   would. Fail-closed in the direction that costs a queue row, never in the
   direction that asserts authority we cannot back.

2. **No wall is opened.** A pasted URL is checked here and fetched NOWHERE —
   this module has no network. A sign-in URL is refused outright (it is not a
   feed), and so is a URL carrying embedded `user:password@` credentials: we do
   not accept, store, or replay someone's login. A private-but-unguessable feed
   address (a Google Calendar secret ICS, say) IS legitimate — the owner chose
   to hand it to us — and passes.

Nothing here writes, fetches, or promotes. It normalizes and REFUSES; the DB
half is api/claims.py. Pure + stdlib-only, so the whole refusal surface is
unit-testable with no DB, no network, and no credentials.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from worker.confidence import CONFIDENCE_STATES
from worker.sourcing.source_class import (
    CLASS_E_FIRST_PARTY,
    CLASS_F_HUMAN_REPORT,
    looks_like_login_url,
)

# --- The vocabulary a submitter may use ---------------------------------------

#: How the listings reach us. Named for the human act, not the transport.
INTAKE_MODES: Tuple[str, ...] = ("ics_url", "csv_upload", "email_forward")

#: Who is handing them over. This — and ONLY this — decides E vs F.
SUBMITTER_ROLES: Tuple[str, ...] = ("organizer", "third_party")

#: The mechanical role -> Coverage Law class map. One line, no judgement.
COVERAGE_CLASS_BY_ROLE: Dict[str, str] = {
    "organizer": CLASS_E_FIRST_PARTY,
    "third_party": CLASS_F_HUMAN_REPORT,
}

#: The pipeline `source_class` strings a claim writes onto `source` rows and
#: `event_candidate` rows. Deliberately NOT the existing `claimed_upload` /
#: `email_opt_in` / `social` names: those are ANCHOR classes that promote on one
#: source, and an UNVERIFIED claim has not earned that. Both names below are
#: registered in worker/gating.py's THIRD_PARTY_CLASSES, so `is_first_party()`
#: is False for them and the gate holds the listings until a human verifies the
#: claimant and re-classes the source. Renaming either of these without moving
#: the matching entry in gating.py would silently re-open the impersonation
#: path — tests/test_claim_intake.py asserts the pairing.
PIPELINE_SOURCE_CLASS: Dict[str, str] = {
    CLASS_E_FIRST_PARTY: "claimed_upload_unverified",
    CLASS_F_HUMAN_REPORT: "human_report",
}

#: The `source.source_type` a claim registers under, per class. Same reasoning.
SOURCE_TYPE_BY_CLASS: Dict[str, str] = dict(PIPELINE_SOURCE_CLASS)

#: Every claim, always. NOT a parameter — see refusal 1 in the module docstring.
CLAIM_CONFIDENCE = "unverified"
assert CLAIM_CONFIDENCE in CONFIDENCE_STATES  # one authority for the state names

#: Where an organizer forwards listings when they have neither a feed nor a
#: spreadsheet. Recorded as existing in docs/ops/SESSION_KICKOFF_2026-08-05.md
#: ("events@1live.co exists"); overridable per-environment so no code change is
#: needed if the founder points the intake elsewhere. This module never sends
#: mail — the address is DISPLAYED to the organizer and recorded on the claim.
DEFAULT_FORWARD_ADDRESS = "events@1live.co"
FORWARD_ADDRESS_ENV = "ONELIVE_LISTINGS_INTAKE_EMAIL"

#: A runaway backstop, never a silent truncation: a CSV above this many rows is
#: REFUSED whole and named, so nobody's listings are half-ingested in silence.
MAX_CSV_ROWS = 500

#: CSV columns. `title` and `start` are required; the rest are optional and any
#: unknown column is kept verbatim in `extra` rather than dropped.
CSV_REQUIRED_COLUMNS: Tuple[str, ...] = ("title", "start")
CSV_KNOWN_COLUMNS: Tuple[str, ...] = (
    "title", "start", "end", "venue", "city", "url", "notes",
)


class ClaimRefused(ValueError):
    """A claim we will not record, with the reason a human can act on.

    Every refusal names WHAT was wrong and WHICH input caused it, because the
    submitter is a venue owner who gets one chance to understand the answer.
    """


# --- Value objects ------------------------------------------------------------

@dataclass(frozen=True)
class ClaimedListing:
    """One event the claimant handed over. Fields are as GIVEN, never invented.

    `start` stays the submitter's own string: normalizing a timestamp is the
    pipeline's job (worker/datetime_normalize.py) and guessing a timezone here
    would fabricate a fact the claimant did not state.
    """

    title: str
    start: str
    end: str = ""
    venue: str = ""
    city: str = ""
    url: str = ""
    notes: str = ""
    extra: Dict[str, str] = field(default_factory=dict)
    row_number: int = 0

    def as_extracted(self) -> Dict[str, Any]:
        """The `event_candidate.extracted` payload for this listing.

        Carries `confidence` explicitly so the claim's trust state is visible in
        the row itself, not only inferable from the source class.
        """
        return {
            "title": self.title,
            "start_time": self.start,
            "end_time": self.end or None,
            "venue_name": self.venue or None,
            "city": self.city or None,
            "artist_names": [],
            "ticket_link": self.url or None,
            "confidence": CLAIM_CONFIDENCE,
            "claim_row_number": self.row_number,
            "claim_notes": self.notes or None,
            "claim_extra_columns": dict(self.extra) or None,
        }


@dataclass(frozen=True)
class ClaimIntake:
    """A validated claim, ready for the DB layer to write. Nothing has been
    written or fetched yet."""

    venue_name: str
    submitter_role: str
    coverage_class: str          # "E" | "F" (Coverage Law)
    pipeline_source_class: str   # what the gate reads
    source_type: str             # what the `source` row records
    confidence: str              # always CLAIM_CONFIDENCE
    intake_mode: str
    contact_email: str = ""
    contact_name: str = ""
    feed_url: str = ""
    forward_to: str = ""
    notes: str = ""
    listings: Tuple[ClaimedListing, ...] = ()

    @property
    def listing_count(self) -> int:
        return len(self.listings)

    def source_config(self, *, received_at: str, recorded_by: str) -> Dict[str, Any]:
        """The `source.config` jsonb payload — the claim's own record.

        `verified` is hard-coded False: a claim cannot arrive verified, and the
        only thing that flips it is a human checking that this person speaks for
        this venue.
        """
        return {
            "coverage_class": self.coverage_class,
            "confidence": self.confidence,
            "claim": {
                "intake_mode": self.intake_mode,
                "submitted_by": self.submitter_role,
                "venue_name": self.venue_name,
                "contact_name": self.contact_name,
                "contact_email": self.contact_email,
                "feed_url": self.feed_url,
                "forward_to": self.forward_to,
                "notes": self.notes,
                "listing_count": self.listing_count,
                "received_at": received_at,
                "recorded_by": recorded_by,
                "verified": False,
            },
        }


# --- Normalizers / refusals ---------------------------------------------------

def resolve_forward_address(env: Optional[Mapping[str, str]] = None) -> str:
    """The intake mailbox to show an organizer, environment-overridable.

    Takes the environment as an ARGUMENT rather than reading os.environ, so the
    module stays pure and the override is testable without monkeypatching.
    """
    if env:
        override = (env.get(FORWARD_ADDRESS_ENV) or "").strip()
        if override:
            return override
    return DEFAULT_FORWARD_ADDRESS


def normalize_feed_url(raw: str) -> str:
    """Validate a pasted calendar/feed URL. Never fetches it.

    Refuses, in order: an empty value, a non-http(s) scheme (a `file:` or
    `javascript:` paste is not a feed), a URL with no host, a URL carrying
    embedded credentials, and a sign-in page. The credential and sign-in
    refusals are the charter's "no login/paywall/bot-protection bypass" applied
    at the one place a login could enter the system by invitation.
    """
    value = (raw or "").strip()
    if not value:
        raise ClaimRefused("a calendar/feed URL is required for the 'ics_url' intake mode")

    parsed = urlparse(value)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ClaimRefused(
            f"feed URL must be http(s); got scheme {parsed.scheme or '(none)'!r}. "
            "Paste the web address of the calendar feed."
        )
    if not parsed.hostname:
        raise ClaimRefused(f"feed URL has no host: {value!r}")
    if parsed.username or parsed.password:
        raise ClaimRefused(
            "feed URL carries embedded credentials (user:password@). We do not "
            "accept or store logins — send a feed address that needs none, or "
            "use the CSV or email option instead."
        )
    if looks_like_login_url(value):
        raise ClaimRefused(
            "that address is a sign-in page, not a calendar feed. We never log "
            "in on your behalf — send the feed's own address, a CSV, or forward "
            "the listings by email."
        )
    return value


def _clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def parse_listings_csv(text: str, *, max_rows: int = MAX_CSV_ROWS) -> Tuple[ClaimedListing, ...]:
    """Parse a claimant's CSV into listings, refusing LOUDLY on anything odd.

    Discipline (red class `swallowed-corrupt-data`): a row we cannot read is
    never skipped. Either every row parses or the whole submission is refused
    naming the offending row — a half-ingested calendar is worse than a rejected
    one, because the venue believes their listings are in.

    Header handling is case/space-insensitive; unknown columns are preserved in
    `extra` rather than dropped, so a claimant's extra field is never lost.
    """
    body = (text or "").strip()
    if not body:
        raise ClaimRefused("CSV is empty — paste at least a header row and one listing")

    reader = csv.DictReader(io.StringIO(body))
    if not reader.fieldnames:
        raise ClaimRefused("CSV has no header row")

    headers = [(_clean(h) or "").lower() for h in reader.fieldnames]
    if len(set(headers)) != len(headers):
        raise ClaimRefused(f"CSV has duplicate column names: {headers}")
    missing = [c for c in CSV_REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise ClaimRefused(
            f"CSV is missing required column(s) {missing}. Required: "
            f"{list(CSV_REQUIRED_COLUMNS)}; optional: "
            f"{[c for c in CSV_KNOWN_COLUMNS if c not in CSV_REQUIRED_COLUMNS]}."
        )

    listings: list = []
    # Row 1 is the header, so data rows start at 2 — the number a person sees
    # in their spreadsheet, which is the number a refusal must name.
    for offset, raw_row in enumerate(reader, start=2):
        row = {(_clean(k) or "").lower(): _clean(v) for k, v in raw_row.items() if k is not None}
        if not any(row.values()):
            continue  # a wholly blank spacer line carries no listing to lose
        if None in raw_row:
            raise ClaimRefused(
                f"CSV row {offset} has more fields than the header — fix the row "
                "or quote the commas inside it."
            )
        for column in CSV_REQUIRED_COLUMNS:
            if not row.get(column):
                raise ClaimRefused(
                    f"CSV row {offset} is missing {column!r}. Every listing needs "
                    f"{list(CSV_REQUIRED_COLUMNS)}; nothing was recorded."
                )
        if len(listings) >= max_rows:
            raise ClaimRefused(
                f"CSV carries more than {max_rows} listings. Nothing was recorded "
                "— send it in smaller files, or send a calendar feed URL instead, "
                "so no part of your calendar is silently left out."
            )
        listings.append(ClaimedListing(
            title=row["title"],
            start=row["start"],
            end=row.get("end", ""),
            venue=row.get("venue", ""),
            city=row.get("city", ""),
            url=row.get("url", ""),
            notes=row.get("notes", ""),
            extra={k: v for k, v in row.items() if k and k not in CSV_KNOWN_COLUMNS and v},
            row_number=offset,
        ))

    if not listings:
        raise ClaimRefused("CSV has a header but no listings")
    return tuple(listings)


def build_claim(
    *,
    venue_name: str,
    submitter_role: str,
    intake_mode: str,
    contact_email: str = "",
    contact_name: str = "",
    feed_url: str = "",
    csv_text: str = "",
    notes: str = "",
    env: Optional[Mapping[str, str]] = None,
) -> ClaimIntake:
    """Validate one submission into a ClaimIntake. The only entry point.

    Note what is absent from the signature: `confidence`, `source_class`, and
    `verified`. A claim never chooses the terms on which it is trusted (red
    class `caller-suppliable-custody-inputs`) — the role picks the class, and
    the confidence is a constant.
    """
    venue = _clean(venue_name)
    if not venue:
        raise ClaimRefused("venue/organizer name is required — it is what the listings attach to")

    role = _clean(submitter_role).lower()
    if role not in SUBMITTER_ROLES:
        raise ClaimRefused(
            f"submitter_role must be one of {list(SUBMITTER_ROLES)}; got {submitter_role!r}"
        )

    mode = _clean(intake_mode).lower()
    if mode not in INTAKE_MODES:
        raise ClaimRefused(f"intake_mode must be one of {list(INTAKE_MODES)}; got {intake_mode!r}")

    coverage_class = COVERAGE_CLASS_BY_ROLE[role]

    url = ""
    listings: Tuple[ClaimedListing, ...] = ()
    forward_to = ""
    if mode == "ics_url":
        url = normalize_feed_url(feed_url)
    elif mode == "csv_upload":
        listings = parse_listings_csv(csv_text)
    else:  # email_forward
        forward_to = resolve_forward_address(env)

    return ClaimIntake(
        venue_name=venue,
        submitter_role=role,
        coverage_class=coverage_class,
        pipeline_source_class=PIPELINE_SOURCE_CLASS[coverage_class],
        source_type=SOURCE_TYPE_BY_CLASS[coverage_class],
        confidence=CLAIM_CONFIDENCE,
        intake_mode=mode,
        contact_email=_clean(contact_email),
        contact_name=_clean(contact_name),
        feed_url=url,
        forward_to=forward_to,
        notes=_clean(notes),
        listings=listings,
    )


def hold_reason(claim: ClaimIntake) -> str:
    """The one-sentence truth to show the claimant and the operator.

    Says what WILL happen, not what we wish happened: an unverified claim is
    recorded and held, and a human is the thing that moves it.
    """
    return (
        f"Recorded as class {claim.coverage_class} at confidence "
        f"{claim.confidence}. Nothing publishes from this claim: the source is "
        "registered disabled and any listings hold at the gate until a person "
        "verifies that this contact speaks for this venue."
    )
