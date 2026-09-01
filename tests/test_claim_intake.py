"""Claim intake — the class-D door that opens inward (Coverage Law E/F).

HERMETIC by construction: worker/claim/intake.py has no DB, no network and no
credentials, so every refusal in the trust surface is provable here. The tests
that matter most are the ones asserting what the path REFUSES: a claim may not
choose its own confidence, may not reach the anchor tier, and may not carry a
login through the door.
"""
import pytest

from worker.claim import intake
from worker.claim.intake import (
    CLAIM_CONFIDENCE,
    ClaimRefused,
    build_claim,
    hold_reason,
    normalize_feed_url,
    parse_listings_csv,
    resolve_forward_address,
)
from worker.confidence import CONFIDENCE_STATES
from worker.gating import ANCHOR_CLASSES, is_first_party, multi_confirm_gate


# --- The class rule is mechanical --------------------------------------------

def test_organizer_is_class_e_and_third_party_is_class_f():
    organizer = build_claim(
        venue_name="Mohawk", submitter_role="organizer",
        intake_mode="ics_url", feed_url="https://mohawkaustin.com/events.ics")
    reporter = build_claim(
        venue_name="Mohawk", submitter_role="third_party",
        intake_mode="ics_url", feed_url="https://mohawkaustin.com/events.ics")
    assert organizer.coverage_class == "E"
    assert reporter.coverage_class == "F"
    assert organizer.pipeline_source_class == "claimed_upload_unverified"
    assert reporter.pipeline_source_class == "human_report"


def test_unknown_role_or_mode_is_refused_not_guessed():
    with pytest.raises(ClaimRefused):
        build_claim(venue_name="X", submitter_role="venue_owner_probably",
                    intake_mode="ics_url", feed_url="https://x.test/e.ics")
    with pytest.raises(ClaimRefused):
        build_claim(venue_name="X", submitter_role="organizer",
                    intake_mode="scrape_it_for_me", feed_url="https://x.test/e.ics")


def test_venue_name_is_required():
    with pytest.raises(ClaimRefused):
        build_claim(venue_name="   ", submitter_role="organizer",
                    intake_mode="email_forward")


# --- Confidence is never an input --------------------------------------------

def test_every_claim_is_recorded_unverified():
    for role in ("organizer", "third_party"):
        for mode, kwargs in (
            ("ics_url", {"feed_url": "https://x.test/e.ics"}),
            ("csv_upload", {"csv_text": "title,start\nA,2026-09-12T21:00:00-05:00\n"}),
            ("email_forward", {"env": {intake.FORWARD_ADDRESS_ENV: "listings@example.test"}}),
        ):
            claim = build_claim(venue_name="X", submitter_role=role,
                                intake_mode=mode, **kwargs)
            assert claim.confidence == "unverified"


def test_confidence_is_not_a_parameter_the_caller_can_supply():
    """A claim must not be able to name the terms on which it is trusted."""
    import inspect

    params = set(inspect.signature(build_claim).parameters)
    assert not params & {"confidence", "coverage_class", "source_class",
                         "pipeline_source_class", "verified"}


def test_claim_confidence_is_a_real_state_in_the_canonical_model():
    assert CLAIM_CONFIDENCE in CONFIDENCE_STATES


# --- The impersonation refusal: a fresh claim never reaches the anchor tier ---

def test_claim_classes_never_reach_the_first_party_tier():
    """The whole point of `unverified`. `claimed_upload` / `email_opt_in` are
    ANCHOR classes that promote on one source because a human established the
    claimant. A self-serve claim has established nothing, so its classes must
    never answer True to "is this the horse's mouth" — otherwise the claim form
    is an impersonation path straight to `confirmed`.

    This asserts the PROPERTY, not the mechanism: whatever set a claim class
    does or does not belong to, `is_first_party()` must say False and the name
    must not be an anchor. That holds while the classes are unknown to
    gating.py (today — they ride its fail-closed unknown branch, founder
    decision 2026-09-01 / R-082) and it would still hold if a later PR records
    them in THIRD_PARTY_CLASSES. A membership assertion would have proven only
    which set was edited."""
    for pipeline_class in intake.PIPELINE_SOURCE_CLASS.values():
        assert is_first_party(pipeline_class) is False, pipeline_class
        assert pipeline_class not in ANCHOR_CLASSES, pipeline_class


def test_a_claimed_listing_alone_does_not_promote():
    for pipeline_class in intake.PIPELINE_SOURCE_CLASS.values():
        verdict = multi_confirm_gate([pipeline_class])
        assert verdict.ok_to_promote is False, pipeline_class


def test_claim_classes_are_distinct_from_the_verified_anchor_names():
    """Guards the rename that would silently re-open the path: if a claim class
    ever equalled `claimed_upload` or `email_opt_in`, it would inherit their
    single-source promotion."""
    assert not set(intake.PIPELINE_SOURCE_CLASS.values()) & {"claimed_upload", "email_opt_in"}


def test_source_config_records_the_claim_as_unverified():
    claim = build_claim(venue_name="Mohawk", submitter_role="organizer",
                        intake_mode="email_forward", contact_email="booking@x.test",
                        env={intake.FORWARD_ADDRESS_ENV: "listings@example.test"})
    config = claim.source_config(received_at="2026-09-01T00:00:00+00:00", recorded_by="ops@x.test")
    assert config["coverage_class"] == "E"
    assert config["confidence"] == "unverified"
    assert config["claim"]["verified"] is False
    assert config["claim"]["recorded_by"] == "ops@x.test"


def test_receipt_says_received_held_not_live_and_claims_no_relationship():
    """The founder's receipt rule (2026-09-01): the ops receipt is internal and
    states received / held / not live. It must never say we have their calendar
    or that they are on 1Live."""
    claim = build_claim(venue_name="X", submitter_role="organizer", intake_mode="email_forward",
                        env={intake.FORWARD_ADDRESS_ENV: "listings@example.test"})
    reason = hold_reason(claim).lower()
    for state in intake.RECEIPT_STATES:
        assert state in reason, state
    assert "unverified" in reason
    for forbidden in ("we have your calendar", "you are live", "they are live on 1live",
                      "your calendar is live", "partnered with"):
        assert forbidden not in reason, forbidden


# --- No wall is opened -------------------------------------------------------

def test_feed_url_accepts_a_plain_https_calendar():
    assert normalize_feed_url("  https://example.com/events.ics ") == "https://example.com/events.ics"


def test_feed_url_accepts_a_private_but_unguessable_calendar_address():
    """A secret ICS address the owner CHOSE to give us is a legitimate
    first-party handover, not a bypass — it must not be refused."""
    secret = "https://calendar.google.com/calendar/ical/abc123secret%40group.calendar.google.com/private-9f/basic.ics"
    assert normalize_feed_url(secret) == secret


@pytest.mark.parametrize("bad", [
    "",
    "   ",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "ftp://example.com/events.ics",
    "https:///events.ics",
])
def test_feed_url_refuses_anything_that_is_not_a_web_feed(bad):
    with pytest.raises(ClaimRefused):
        normalize_feed_url(bad)


def test_feed_url_refuses_embedded_credentials():
    """We do not accept, store, or replay someone's login."""
    with pytest.raises(ClaimRefused) as excinfo:
        normalize_feed_url("https://user:hunter2@example.com/private.ics")
    assert "credential" in str(excinfo.value).lower()


@pytest.mark.parametrize("login_url", [
    "https://www.facebook.com/login/?next=/events",
    "https://example.com/signin",
    "https://example.com/accounts/login",
    "https://example.com/oauth/authorize?client_id=1",
])
def test_feed_url_refuses_a_sign_in_page(login_url):
    with pytest.raises(ClaimRefused) as excinfo:
        normalize_feed_url(login_url)
    assert "sign-in" in str(excinfo.value).lower()


def test_intake_module_has_no_network_or_db_imports():
    """The path that touches an organizer's URL must not be able to fetch it."""
    source = (intake.__file__ or "")
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    for forbidden in ("import requests", "urllib.request", "httpx", "psycopg2", "socket"):
        assert forbidden not in text, forbidden


# --- CSV: every row lands, or none does --------------------------------------

def test_csv_parses_required_and_optional_columns():
    rows = parse_listings_csv(
        "title,start,end,venue,city,url\n"
        "Doom Jazz,2026-09-12T21:00:00-05:00,2026-09-13T01:00:00-05:00,Mohawk,Austin,https://x.test/1\n"
        "Quiet Set,2026-09-13T20:00:00-05:00,,Mohawk,Austin,\n"
    )
    assert [r.title for r in rows] == ["Doom Jazz", "Quiet Set"]
    assert rows[0].city == "Austin"
    assert rows[1].end == ""
    assert rows[0].row_number == 2  # the row number the person sees in their sheet


def test_csv_headers_are_case_and_space_insensitive():
    rows = parse_listings_csv(" Title , Start \nA,2026-09-12T21:00:00-05:00\n")
    assert rows[0].title == "A"


def test_csv_keeps_unknown_columns_instead_of_dropping_them():
    rows = parse_listings_csv("title,start,door_price\nA,2026-09-12T21:00,10\n")
    assert rows[0].extra == {"door_price": "10"}


def test_csv_skips_only_wholly_blank_spacer_lines():
    rows = parse_listings_csv("title,start\nA,2026-09-12T21:00\n,\nB,2026-09-13T21:00\n")
    assert [r.title for r in rows] == ["A", "B"]


@pytest.mark.parametrize("bad_csv, needle", [
    ("", "empty"),
    ("title,start\n", "no listings"),
    ("name,when\nA,tomorrow\n", "missing required column"),
    ("title,start\n,2026-09-12T21:00\n", "row 2"),
    ("title,start\nA,\n", "row 2"),
    ("title,title,start\nA,B,2026-09-12T21:00\n", "duplicate"),
])
def test_csv_refuses_loudly_and_names_the_problem(bad_csv, needle):
    with pytest.raises(ClaimRefused) as excinfo:
        parse_listings_csv(bad_csv)
    assert needle in str(excinfo.value).lower()


def test_a_bad_row_refuses_the_whole_file_rather_than_dropping_it():
    """A half-recorded calendar is worse than a rejected one: the venue would
    believe their listings are in."""
    with pytest.raises(ClaimRefused):
        parse_listings_csv(
            "title,start\n"
            "Good One,2026-09-12T21:00\n"
            "Bad One,\n"
            "Also Good,2026-09-14T21:00\n"
        )


def test_oversized_csv_is_refused_whole_never_truncated():
    body = "title,start\n" + "".join(
        f"Show {i},2026-09-12T21:00\n" for i in range(intake.MAX_CSV_ROWS + 1))
    with pytest.raises(ClaimRefused) as excinfo:
        parse_listings_csv(body)
    assert "nothing was recorded" in str(excinfo.value).lower()


def test_csv_at_the_cap_is_accepted():
    body = "title,start\n" + "".join(
        f"Show {i},2026-09-12T21:00\n" for i in range(intake.MAX_CSV_ROWS))
    assert len(parse_listings_csv(body)) == intake.MAX_CSV_ROWS


# --- What each mode hands over ------------------------------------------------

def test_ics_and_email_modes_hand_over_no_listings_yet():
    """We never invent an event from the promise of a calendar."""
    ics = build_claim(venue_name="X", submitter_role="organizer",
                      intake_mode="ics_url", feed_url="https://x.test/e.ics")
    email = build_claim(venue_name="X", submitter_role="organizer",
                        intake_mode="email_forward",
                        env={intake.FORWARD_ADDRESS_ENV: "listings@example.test"})
    assert ics.listing_count == 0 and email.listing_count == 0
    assert ics.feed_url == "https://x.test/e.ics"
    assert email.feed_url == ""


def test_csv_mode_carries_the_listings_at_unverified_confidence():
    claim = build_claim(
        venue_name="Mohawk", submitter_role="organizer", intake_mode="csv_upload",
        csv_text="title,start,city\nDoom Jazz,2026-09-12T21:00:00-05:00,Austin\n")
    assert claim.listing_count == 1
    extracted = claim.listings[0].as_extracted()
    assert extracted["title"] == "Doom Jazz"
    assert extracted["confidence"] == "unverified"
    assert extracted["artist_names"] == []


def test_listing_start_is_kept_verbatim_not_reinterpreted():
    """Guessing a timezone here would fabricate a fact the claimant never stated."""
    rows = parse_listings_csv("title,start\nA,Friday 9pm\n")
    assert rows[0].start == "Friday 9pm"
    assert rows[0].as_extracted()["start_time"] == "Friday 9pm"


def test_ics_mode_requires_a_url_and_csv_mode_requires_rows():
    with pytest.raises(ClaimRefused):
        build_claim(venue_name="X", submitter_role="organizer", intake_mode="ics_url")
    with pytest.raises(ClaimRefused):
        build_claim(venue_name="X", submitter_role="organizer", intake_mode="csv_upload")


# --- The forwarding address ---------------------------------------------------

def test_forward_address_has_no_hard_coded_default():
    """An address nobody verified must not become the operational one just
    because it is in the source (evaluator finding, PR #203). Unconfigured is a
    real state an operator has to see."""
    assert resolve_forward_address({}) == ""
    assert resolve_forward_address(None) == ""
    assert resolve_forward_address({intake.FORWARD_ADDRESS_ENV: "  "}) == ""
    assert resolve_forward_address({intake.FORWARD_ADDRESS_ENV: " listings@example.test "}) \
        == "listings@example.test"
    assert not hasattr(intake, "DEFAULT_FORWARD_ADDRESS")


def test_email_mode_refuses_when_no_mailbox_is_configured():
    """Telling an organizer to email an address nobody configured sends their
    listings nowhere, and they will not write twice."""
    with pytest.raises(ClaimRefused) as excinfo:
        build_claim(venue_name="X", submitter_role="organizer",
                    intake_mode="email_forward", env={})
    assert intake.FORWARD_ADDRESS_ENV in str(excinfo.value)


def test_claim_owned_source_types_are_exactly_the_two_claim_types():
    """api/claims.py fences its `source` upsert on this set, so it must contain
    the claim types and nothing else — a stray member would let a claim
    overwrite a source it does not own."""
    assert intake.CLAIM_OWNED_SOURCE_TYPES == frozenset(
        {"claimed_upload_unverified", "human_report"})


# --- A listing's own URL gets the same scrutiny as the feed URL ---------------

def test_listing_url_is_validated_like_a_feed_url():
    """A stored link becomes a user-facing ticket link the moment a candidate is
    promoted (evaluator finding, PR #203)."""
    rows = parse_listings_csv(
        "title,start,url\nA,2026-09-12T21:00,https://example.com/tickets\n")
    assert rows[0].url == "https://example.com/tickets"
    assert rows[0].as_extracted()["ticket_link"] == "https://example.com/tickets"


def test_listing_url_may_be_empty_because_a_listing_need_not_link():
    rows = parse_listings_csv("title,start,url\nA,2026-09-12T21:00,\n")
    assert rows[0].url == ""
    assert rows[0].as_extracted()["ticket_link"] is None


@pytest.mark.parametrize("bad_url", [
    "javascript:alert(1)",
    "file:///etc/passwd",
    "ftp://example.com/t",
    "https://user:hunter2@example.com/t",
    "https://example.com/login?next=/t",
    "not-a-url",
])
def test_a_bad_listing_url_refuses_the_whole_file_and_names_its_row(bad_url):
    with pytest.raises(ClaimRefused) as excinfo:
        parse_listings_csv(
            "title,start,url\n"
            "Good,2026-09-12T21:00,https://example.com/ok\n"
            f"Bad,2026-09-13T21:00,{bad_url}\n")
    message = str(excinfo.value)
    assert "row 3" in message, message
    assert "nothing was recorded" in message.lower(), message


def test_normalize_listing_url_is_the_same_authority_as_the_feed_check():
    """One function, two callers — the lax path is always the one exercised."""
    with pytest.raises(ClaimRefused):
        intake.normalize_listing_url("https://example.com/signin", row_number=2)
    with pytest.raises(ClaimRefused):
        normalize_feed_url("https://example.com/signin")


def test_email_mode_records_the_address_it_told_the_organizer_to_use():
    claim = build_claim(venue_name="X", submitter_role="organizer",
                        intake_mode="email_forward",
                        env={intake.FORWARD_ADDRESS_ENV: "listings@example.test"})
    assert claim.forward_to == "listings@example.test"
    config = claim.source_config(received_at="t", recorded_by="ops")
    assert config["claim"]["forward_to"] == "listings@example.test"
