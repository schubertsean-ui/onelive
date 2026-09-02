"""R-030 — a listing's time may borrow a date the SAME PAGE states.

Run 33579093995 stored 92 of 198 candidates (46%) with `start_time = NULL`,
every one refused `no-full-date-evidence`, because the extractor was handed a
bare clock ('9:00PM', '6:00PM', '10 am', '19:00:00'). Those rows publish and
are then invisible forever: a NULL can never satisfy `/tonight`'s
`start_time >= <from>` predicate.

The three cases the founder named are `test_a_`, `test_b_` and `test_c_`
below. Everything after them is a guard on the same rule: the date must be
STATED on this page, and a date that contradicts the claim, or a page that
states several dates with no way to tell which listing owns them, is refused
exactly as loudly as before. Nothing here may ever invent a day.
"""
from datetime import date

import pytest

from worker.datetime_normalize import normalize_extracted_datetimes
from worker.same_page_dates import (
    normalize_extracted_datetimes_with_page,
    resolve_same_page_datetime,
    same_page_dates,
)

# A page fetched on this date is the anchor for every weekday-pinned year
# below. Sep 6 falls on a Saturday in 2025 (and on a Sunday in 2026) —
# which is the whole point of pinning by the weekday the page prints.
FETCHED = date(2025, 9, 1)

# (a) the founder's page: one listing, a date and a time side by side.
PAGE_A = (
    "<li class='show'><h3>Sat Sep 6 &bull; 9:00PM</h3>"
    "<p>Trio night at the Elephant Room.</p></li>"
)
# (b) the same listing with the date removed — a clock and nothing else.
PAGE_B = "<li class='show'><h3>9:00PM</h3><p>Trio night.</p></li>"
# (c) a DIFFERENT page that happens to state a date.
PAGE_OTHER = "<li class='show'><h3>Sat Sep 6 &bull; 8:00PM</h3><p>Elsewhere.</p></li>"


# --------------------------------------------------------------------------
# The three named cases
# --------------------------------------------------------------------------

def test_a_date_and_time_on_the_same_page_are_stored():
    """"Sat Sep 6 • 9:00PM" on one page -> dated."""
    iso, refusal, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=PAGE_A, as_of=FETCHED)
    assert iso == "2025-09-06T21:00:00"
    assert refusal is None
    # The stored date is auditable back to the exact words on the page.
    assert evidence == {"date": "2025-09-06", "kind": "visible-weekday",
                        "scope": "page", "raw": "Sat Sep 6", "claim": "9:00PM"}


def test_b_a_clock_with_no_date_on_the_page_is_still_null():
    """"9:00PM" alone -> still NULL. This is the 92's exact shape."""
    iso, refusal, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=PAGE_B, as_of=FETCHED)
    assert iso is None
    assert refusal == {"raw": "9:00PM", "reason": "no-full-date-evidence"}
    assert evidence is None


def test_c_a_date_from_a_different_page_must_not_attach():
    """A date on page OTHER may not date a listing on page B.

    The resolver is a pure function of the text it is handed and keeps no
    state between calls, so the two facts that matter are both asserted:
    the other page's date resolves on its OWN page, and the SAME claim on
    the dateless page stays NULL even when the other page was read first.
    """
    other_iso, _, _ = resolve_same_page_datetime(
        "8:00PM", page_text=PAGE_OTHER, as_of=FETCHED)
    assert other_iso == "2025-09-06T20:00:00"

    iso, refusal, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=PAGE_B, as_of=FETCHED)
    assert iso is None
    assert refusal == {"raw": "9:00PM", "reason": "no-full-date-evidence"}
    assert evidence is None


# --------------------------------------------------------------------------
# Guards — the rule is "read the page's date", never "produce a date"
# --------------------------------------------------------------------------

@pytest.mark.parametrize("carrier,page", [
    ("jsonld", '<script type="application/ld+json">'
               '{"@type":"Event","startDate":"2025-09-06T21:00:00"}</script>'
               "<li>9:00PM Trio night</li>"),
    ("time-tag", '<li><time datetime="2025-09-06T21:00">9:00PM</time> Trio</li>'),
    ("ics", "BEGIN:VEVENT\nDTSTART;TZID=America/Chicago:20250906T210000\n"
            "SUMMARY:Trio night\nEND:VEVENT"),
    ("visible-full-date", "<li>September 6, 2025 — 9:00PM Trio night</li>"),
])
def test_every_named_carrier_supplies_the_date(carrier, page):
    """Visible text, JSON-LD, or ICS on that URL — the founder's list."""
    iso, refusal, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=page, as_of=FETCHED)
    assert (iso, refusal) == ("2025-09-06T21:00:00", None), carrier
    assert evidence["kind"] == carrier.replace("visible-full-date", "visible-date")


def test_the_page_weekday_pins_the_year_and_a_wrong_one_refuses():
    """A year absent from the page comes from the page's OWN weekday or
    not at all: Sep 6 is a Saturday in 2025, so a page fetched a year
    later cannot mean "Sat Sep 6" — and gets NULL, not a shifted day."""
    assert resolve_same_page_datetime(
        "9:00PM", page_text=PAGE_A, as_of=date(2026, 9, 2))[0] is None
    # With no fetch anchor at all, weekday pinning is OFF entirely.
    assert resolve_same_page_datetime("9:00PM", page_text=PAGE_A)[0] is None


def test_a_month_day_without_a_weekday_is_never_completed():
    """Nothing on this page says WHICH Sep 6, so no year may be supplied."""
    iso, refusal, _ = resolve_same_page_datetime(
        "9:00PM", page_text="<li>Sep 6 &bull; 9:00PM Trio</li>", as_of=FETCHED)
    assert iso is None
    assert refusal["reason"] == "no-full-date-evidence"


def test_the_listings_own_block_wins_over_the_page():
    """"Nearby" on a calendar page listing many shows means the event's
    own block; the page's other dates must not reach it."""
    page = ("<ul>"
            '<li><time datetime="2025-09-05T20:00">Fri Sep 5</time> Act one</li>'
            '<li><time datetime="2025-09-06T21:00">Sat Sep 6</time> Act two</li>'
            '<li><time datetime="2025-09-11T20:30">Thu Sep 11</time> Act three</li>'
            "</ul>")
    block = '<li><time datetime="2025-09-06T21:00">Sat Sep 6</time> Act two</li>'
    iso, refusal, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=page, block_text=block, as_of=FETCHED)
    assert (iso, refusal) == ("2025-09-06T21:00:00", None)
    assert evidence["scope"] == "block"


def test_many_page_dates_and_no_block_is_refused_not_guessed():
    """Which of the three shows owns this clock is exactly what we cannot
    know, so the answer is a refusal — never the first date on the page."""
    page = ("<ul>"
            '<li><time datetime="2025-09-05T20:00">Fri Sep 5</time> Act one</li>'
            '<li><time datetime="2025-09-06T21:00">Sat Sep 6</time> Act two</li>'
            "</ul>")
    iso, refusal, _ = resolve_same_page_datetime(
        "9:00PM", page_text=page, as_of=FETCHED)
    assert iso is None
    assert refusal == {"raw": "9:00PM", "reason": "ambiguous-same-page-dates"}


def test_markup_and_prose_that_agree_are_one_date_not_two():
    """The commonest real listing states its date twice. That is not
    ambiguity, and must not be refused as if it were."""
    page = ('<li><time datetime="2025-09-06T21:00">Sat Sep 6, 9:00PM</time></li>')
    iso, refusal, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=page, as_of=FETCHED)
    assert (iso, refusal) == ("2025-09-06T21:00:00", None)
    assert evidence["kind"] == "time-tag"   # strongest carrier is reported


def test_a_page_date_that_contradicts_the_claim_is_refused():
    """The page says Sep 6; the claim says July 22. Storing either would
    assert something neither source said."""
    iso, refusal, _ = resolve_same_page_datetime(
        "July 22, 7pm", page_text=PAGE_A, as_of=FETCHED)
    assert iso is None
    assert refusal == {"raw": "July 22, 7pm",
                       "reason": "same-page-date-contradicts-claim"}


def test_a_weekday_in_the_claim_must_match_the_page_date():
    """"Friday 7pm" cannot be dated to a Saturday."""
    iso, refusal, _ = resolve_same_page_datetime(
        "Friday 7pm", page_text=PAGE_A, as_of=FETCHED)
    assert iso is None
    assert refusal["reason"] == "same-page-date-contradicts-claim"


def test_a_year_missing_from_the_claim_is_supplied_when_the_page_agrees():
    """The complement of the contradiction case: page and claim agree on
    the month and day, so the page's year completes the claim."""
    iso, refusal, evidence = resolve_same_page_datetime(
        "Sep 6, 9:00PM", page_text=PAGE_A, as_of=FETCHED)
    assert (iso, refusal) == ("2025-09-06T21:00:00", None)
    assert evidence["date"] == "2025-09-06"


@pytest.mark.parametrize("claim", ["2026", "7", "TBD", "doors at dusk"])
def test_a_claim_with_no_clock_is_never_completed_by_a_page_date(claim):
    """A page date plus no time would invent the whole timestamp."""
    iso, refusal, _ = resolve_same_page_datetime(
        claim, page_text=PAGE_A, as_of=FETCHED)
    assert iso is None
    assert refusal["raw"] == claim


@pytest.mark.parametrize("claim,reason", [
    ("03/04/2026 8pm", "ambiguous-numeric-date"),
    ("7pm ET", "unrecognized-timezone-abbreviation"),
])
def test_deliberate_refusals_are_not_lifted_by_page_evidence(claim, reason):
    """These two refuse the claim's OWN date/timezone. No page fixes that."""
    iso, refusal, _ = resolve_same_page_datetime(
        claim, page_text=PAGE_A, as_of=FETCHED)
    assert iso is None
    assert refusal["reason"] == reason


def test_two_clocks_in_one_unparseable_claim_are_refused():
    """"Doors 7pm, show 8pm" does not say which one it is claiming."""
    iso, refusal, _ = resolve_same_page_datetime(
        "Doors 7pm, show 8pm", page_text=PAGE_A, as_of=FETCHED)
    assert iso is None
    assert refusal["reason"] == "unparseable"


def test_one_clock_in_an_unparseable_claim_is_read():
    """The founder's listing line, handed over whole: dateutil cannot parse
    it, but it states exactly one clock and the page states the day."""
    iso, refusal, _ = resolve_same_page_datetime(
        "Sat Sep 6 • 9:00PM", page_text=PAGE_A, as_of=FETCHED)
    assert (iso, refusal) == ("2025-09-06T21:00:00", None)


def test_malformed_json_ld_does_not_cost_the_page_its_other_dates():
    page = ('<script type="application/ld+json">{ this is not json </script>'
            '<li><time datetime="2025-09-06T21:00">Sat Sep 6</time> 9:00PM</li>')
    iso, _, evidence = resolve_same_page_datetime(
        "9:00PM", page_text=page, as_of=FETCHED)
    assert iso == "2025-09-06T21:00:00"
    assert evidence["kind"] == "time-tag"


def test_json_ld_dates_are_not_double_counted_as_visible_prose():
    """A script body is not visible text; counting it twice would make a
    single-date page look ambiguous and refuse a resolvable listing."""
    page = ('<script type="application/ld+json">'
            '{"@type":"Event","startDate":"2025-09-06T21:00:00"}</script>'
            "<li>9:00PM Trio night</li>")
    assert [d.date for d in same_page_dates(page)] == [date(2025, 9, 6)]


def test_a_full_date_in_the_claim_is_never_overridden_by_the_page():
    """The claim already evidences its own day; the page does not get a vote."""
    iso, refusal, evidence = resolve_same_page_datetime(
        "2025-07-22T19:00:00", page_text=PAGE_A, as_of=FETCHED)
    assert (iso, refusal, evidence) == ("2025-07-22T19:00:00", None, None)


# --------------------------------------------------------------------------
# The batch helper stays backward-compatible
# --------------------------------------------------------------------------

def test_the_page_aware_helper_matches_r021_exactly_without_page_text():
    """The wiring PR swaps one call, so the page-aware helper must be a
    true drop-in: with no page text its result is identical, field for
    field, to the R-021 helper the armed cron runs today."""
    claims = {"start_time": "9:00PM", "end_time": "11:00PM"}
    old_shaped, new_shaped = dict(claims), dict(claims)
    old_refused = normalize_extracted_datetimes(old_shaped)
    new_refused = normalize_extracted_datetimes_with_page(new_shaped)
    assert old_shaped == new_shaped == {"start_time": None, "end_time": None}
    assert old_refused == new_refused
    assert new_refused["start_time"]["reason"] == "no-full-date-evidence"


def test_this_engine_is_now_inside_the_armed_crons_runtime_closure():
    """The wiring PR (this one) is the PR #209 named: the moment
    worker/ai_extract.py imports this engine, it joins the armed cron's
    computed runtime closure and the arming-evidence binding rightly
    demands a fresh smoke run.

    #209's version of this test asserted the opposite — that the engine sat
    OUTSIDE the closure — because it was unwired by design. The assertion
    flips with the wiring; the guard does not weaken. It is still computed
    against tools/arming_runtime.py, the same source trust-gate uses, never
    a hand-kept list, so a future change that silently drops the engine out
    of the armed path fails here."""
    from tools.arming_runtime import runtime_files
    runtime = runtime_files()
    assert "worker/datetime_normalize.py" in runtime
    assert "worker/same_page_dates.py" in runtime
    assert "worker/ai_extract.py" in runtime


def test_batch_helper_reports_resolutions_for_provenance():
    shaped = {"start_time": "9:00PM", "end_time": "11:00PM"}
    resolutions = {}
    refused = normalize_extracted_datetimes_with_page(
        shaped, page_text=PAGE_A, as_of=FETCHED, resolutions=resolutions)
    assert refused == {}
    assert shaped["start_time"] == "2025-09-06T21:00:00"
    assert shaped["end_time"] == "2025-09-06T23:00:00"
    assert resolutions["start_time"]["raw"] == "Sat Sep 6"


# --------------------------------------------------------------------------
# The wired extract path (this PR): the rule now runs where the cron runs
# --------------------------------------------------------------------------

class _ClockOnlyProvider:
    """The 92's exact shape: the model returns a title and a bare clock and
    never a date. Any date that reaches the stored row came from the page."""

    def extract_event_json(self, text, schema_json, system_prompt=None, **kw):
        if "9:00PM" not in text:
            return {}
        return {"title": "Trio night", "start_time": "9:00PM"}


@pytest.fixture
def wired(monkeypatch):
    """worker.ai_extract with both DB writes captured instead of executed."""
    import worker.ai_extract as ai_extract
    created = []
    monkeypatch.setattr(ai_extract, "create_candidate",
                        lambda **kw: created.append(kw) or f"c{len(created)}")
    monkeypatch.setattr(ai_extract, "add_evidence", lambda **kw: None)
    monkeypatch.setattr(ai_extract, "record_ai_degradation", lambda p: None)
    return ai_extract, created


def _extract(wired, page):
    ai_extract, created = wired
    ai_extract.extract_candidates(
        ai=_ClockOnlyProvider(), text=page, source_class="B",
        source_name="Elephant Room", source_url="https://example.test/shows",
        as_of=FETCHED)
    return created[0]["extracted"]


def test_wired_a_same_page_date_now_reaches_the_stored_candidate(wired):
    """Case (a) through the REAL extract path, not just the resolver: the
    date the page printed is what the candidate row carries."""
    stored = _extract(wired, PAGE_A)
    assert stored["start_time"] == "2025-09-06T21:00:00"
    assert "unstored_datetime_claims" not in stored["_provenance"]


def test_wired_b_a_clock_with_no_page_date_is_still_stored_null(wired):
    """Case (b) through the real path: the 92's shape on a dateless page
    still stores NULL, with the raw claim preserved exactly as R-021 left it."""
    stored = _extract(wired, PAGE_B)
    assert stored["start_time"] is None
    refused = stored["_provenance"]["unstored_datetime_claims"]["start_time"]
    assert refused == {"raw": "9:00PM", "reason": "no-full-date-evidence"}
    assert "same_page_date_resolutions" not in stored["_provenance"]


def test_wired_the_stored_date_is_auditable_back_to_the_page(wired):
    """A stored date that cannot be traced to the words that published it is
    not evidence. The carrier, scope and exact source string ride the row."""
    stored = _extract(wired, PAGE_A)
    resolution = stored["_provenance"]["same_page_date_resolutions"]["start_time"]
    assert resolution == {"date": "2025-09-06", "kind": "visible-weekday",
                          "scope": "block", "raw": "Sat Sep 6",
                          "claim": "9:00PM"}


def test_wired_a_malformed_provenance_is_repaired_not_destroyed(wired):
    """The refusal path REPLACES a malformed _provenance and keeps the
    original (PR #44 r1). The resolution path must do the same, and it is
    the only path that runs when every claim resolves."""
    ai_extract, created = wired

    class _BadProvProvider(_ClockOnlyProvider):
        def extract_event_json(self, text, schema_json, system_prompt=None, **kw):
            out = super().extract_event_json(text, schema_json, **kw)
            if out:
                out["_provenance"] = "not-a-dict"
            return out

    ai_extract.extract_candidates(
        ai=_BadProvProvider(), text=PAGE_A, source_class="B",
        source_name="Elephant Room", source_url="https://example.test/shows",
        as_of=FETCHED)
    stored = created[0]["extracted"]
    assert stored["start_time"] == "2025-09-06T21:00:00"
    assert stored["_provenance"]["same_page_date_resolutions"]
    assert stored["_provenance_malformed_original"] == "not-a-dict"


def test_wired_every_block_on_a_page_pins_against_one_anchor(wired):
    """The anchor is resolved ONCE per page, not once per block: a page
    extracted across UTC midnight must not date its last listing a day
    differently from its first."""
    import worker.ai_extract as ai_extract
    calls = []
    real = ai_extract._extraction_anchor
    ai_extract._extraction_anchor = lambda: calls.append(1) or real()
    try:
        ai_extract.extract_candidates(
            ai=_ClockOnlyProvider(), text=PAGE_A + PAGE_A + PAGE_A,
            source_class="B", source_name="Elephant Room",
            source_url="https://example.test/shows")
    finally:
        ai_extract._extraction_anchor = real
    assert len(calls) == 1
