"""Coverage Law locks on the INGEST path (ONE-LIVE-COVERAGE-LAW.md, 2026-09-01).

Coverage Law splits one decision into two: what the catalog KEEPS (greedy — "if
we legally saw it, it may exist") and what a view SHOWS (picky — /tonight may
filter to CAPCOG and to tonight). These tests pin the greedy half, because that
is the half whose failures are invisible: a row dropped at ingest leaves no
trace to audit later, while a row hidden by a view is still on disk.

Two properties, each of which was a repealed rule:

  1. Locale is never a delete. A San Antonio row survives parse -> normalize
     exactly like an Austin one. CAPCOG stays a view filter and a coverage
     score, never an ingest reject.
  2. Multi-confirm LABELS, it does not delete. A single-source event is written
     and retained; corroboration decides PROMOTION (whether the default view
     shows it), never existence.

These are regression locks on behavior that already holds — an audit of the
write path found no region-based row drop at ingest, normalize, candidate
write, promote, or in any DB constraint. They exist so a later change cannot
quietly introduce one.
"""
import pytest

from worker.gating import multi_confirm_gate
from worker.importers.structured_feed import (
    PROVIDER_ICS, PROVIDER_JSONLD, _normalize_all, parse_ics, parse_jsonld,
)


# --------------------------------------------------------------------------
# 1. Locale is never a delete
# --------------------------------------------------------------------------

def _jsonld_page(city: str) -> str:
    return (
        '<html><head><script type="application/ld+json">'
        '{"@type":"Event","name":"Locale Test Show",'
        '"startDate":"2026-09-12T20:00:00-05:00",'
        '"url":"https://example-venue.test/e/locale",'
        '"location":{"@type":"Place","name":"Example Hall",'
        '"address":{"@type":"PostalAddress","addressLocality":"' + city + '",'
        '"addressRegion":"TX"}}}'
        "</script></head><body></body></html>"
    )


@pytest.mark.parametrize("city", [
    "Austin",       # inside CAPCOG
    "San Antonio",  # the named repeal: Bexar county, explicitly OUT of CAPCOG
    "Lockhart",     # Caldwell county, inside CAPCOG but not Austin
    "Houston",      # far outside the launch market entirely
    "Reykjavik",    # not even the right country — locale is not a border
])
def test_any_locale_survives_ingest(city):
    """Coverage Law: "Do not require a launch decision to keep a non-CAPCOG row."

    The parse -> normalize path must be locale-blind. If this test ever fails
    for one city and passes for another, a region filter has been reintroduced
    on the write path.
    """
    raws = parse_jsonld(_jsonld_page(city))
    assert len(raws) == 1, "the page publishes exactly one Event node"

    normalized = _normalize_all(
        raws, provider=PROVIDER_JSONLD, source_name="locale_test",
        cultural_domain=None,
    )
    assert len(normalized) == 1, (
        f"a {city} row was dropped at normalize — CAPCOG is a VIEW filter and a "
        "coverage-score region, never an ingest reject (Coverage Law, 'Repealed "
        "as catalog law')."
    )
    assert normalized[0]["venue_city"] == city, "the city is kept verbatim, not rewritten"


def test_ics_row_without_start_is_skipped_not_fabricated():
    """The ONLY legitimate ingest drop: a row with no usable start time.

    Coverage Law keeps every row we legally saw, but it also forbids inventing
    one. A VEVENT with no DTSTART carries no event time to keep, so it is
    skipped — never given a made-up date to make it storable.
    """
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\nUID:has-start@test\r\nSUMMARY:Real Show\r\n"
        "DTSTART:20260915T180000Z\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:no-start@test\r\nSUMMARY:Undated Show\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    normalized = _normalize_all(
        parse_ics(ics), provider=PROVIDER_ICS, source_name="ics_test",
        cultural_domain=None,
    )
    titles = [n["title"] for n in normalized]
    assert "Real Show" in titles
    assert "Undated Show" not in titles


# --------------------------------------------------------------------------
# 2. Multi-confirm labels; it never deletes
# --------------------------------------------------------------------------

def test_single_third_party_source_is_labelled_not_deleted():
    """Coverage Law: "Multi-confirm required to exist" is REPEALED.

    The gate may withhold PROMOTION from an uncorroborated third-party row —
    that is a view decision, and this test deliberately does NOT challenge the
    threshold. What it pins is that the outcome is a LABEL: a status and a
    stated next step, with no delete, no exception, and no instruction to
    discard the row.
    """
    result = multi_confirm_gate(["social"])

    assert result.ok_to_promote is False
    assert result.status == "needs_more_confirmation", (
        "a single-source row must be LABELLED as awaiting corroboration; "
        "'needs_more_confirmation' means 'not in the default view', never 'deleted'."
    )
    assert result.required_next, "the label must say what would resolve it"

    text = f"{result.status} {result.reason} {result.required_next}".lower()
    for verb in ("delete", "discard", "drop", "purge", "remove"):
        assert verb not in text, (
            f"the gate's verdict mentions {verb!r} — the gate classifies rows, "
            "it does not remove them."
        )


def test_gate_returns_a_verdict_and_never_raises():
    """The gate is a pure classifier: no input makes it destroy anything.

    A raise here would let a caller mistake "uncorroborated" for "invalid" and
    unwind a transaction that should simply have stored a labelled row.
    """
    for classes in ([], ["social"], ["blog", "directory"], ["ticketing"], [""]):
        verdict = multi_confirm_gate(classes)
        assert verdict.status, f"{classes!r} produced no status"
        assert isinstance(verdict.ok_to_promote, bool)


def test_single_anchor_source_promotes_alone():
    """Single-source EXISTENCE is not merely tolerated — a first-party anchor
    publishes on its own. Pinned so 'multi-confirm' is never read as 'always
    two sources'."""
    assert multi_confirm_gate(["venue_calendar"]).ok_to_promote is True
