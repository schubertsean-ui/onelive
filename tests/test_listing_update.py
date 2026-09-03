"""The confirmed-listing-update path — founder Session Contract #55 (2026-09-02).

Must-dos 2, 3 and 4 of the founder's ticket, one section each:

  2. On confirmed same-page evidence only: update time / cancel / postpone /
     title. Write evidence. Do not delete the catalog row.
  3. Unconfirmed (timeout, 429, cap, empty, ambiguous parse): no mutation.
     last_attempt only.
  4. Confirmed gone (clean 404 of defining URL, or clean parse that the event
     is absent from that calendar): mark cancelled/moved with evidence; row
     remains.

Hermetic: the adjudicator is pure, and the writer runs against a fake cursor
that records exactly what SQL it was handed. No DB, no network, no model.
"""
from datetime import datetime, timedelta, timezone

import pytest

from worker.crawl_state import (
    UNVERIFIED,
    UPDATABLE_LISTING_FIELDS,
    VERIFIED_ABSENT,
    VERIFIED_PRESENT,
    TickBudget,
    classify_recheck,
)
from worker.listing_update import (
    MATCH_FAR,
    MATCH_TIME,
    MATCH_TITLE,
    MAX_TITLE_ONLY_RETIME,
    ACTION_MARK_GONE,
    ACTION_NONE,
    ACTION_UPDATE,
    GONE_STATUS,
    ParsedListing,
    PublishedListing,
    adjudicate_page,
    apply_decisions,
    match_kind,
    normalize_title,
    render_decision_table,
    title_still_on_page,
)

DAY = datetime(2026, 9, 15, 1, 0, tzinfo=timezone.utc)   # a published show
EARLIER = DAY - timedelta(days=3)
LATER = DAY + timedelta(days=3)

ALWAYS_PASSES = lambda _cid: True        # noqa: E731 — a one-line test double
NEVER_PASSES = lambda _cid: False        # noqa: E731


def published(**kw):
    base = dict(event_id="e1", title="Copper Kettle Revue", start_time=DAY)
    base.update(kw)
    return PublishedListing(**base)


def parsed(**kw):
    base = dict(candidate_id="c1", title="Copper Kettle Revue", start_time=DAY)
    base.update(kw)
    return ParsedListing(**base)


def bracket():
    """Two other listings on the page, one either side of the published date.

    Present in every absence test on purpose: absence is only evidence when the
    page's own coverage reaches the date, so a fixture without a bracket would
    be testing the guard rather than the rule.
    """
    return [ParsedListing(candidate_id="cA", title="Earlier Show", start_time=EARLIER),
            ParsedListing(candidate_id="cZ", title="Later Show", start_time=LATER)]


#: Raw page text for the absence tests: a page that plainly loaded and lists
#: other things, and does NOT name "Copper Kettle Revue" anywhere. Absence is
#: corroborated against THIS, never against the extractor's silence.
PAGE_WITHOUT_IT = """
    Granite Hall — upcoming shows
    Earlier Show, doors 7pm.  Later Show, doors 8pm.  Box office open daily.
"""

PAGE_THAT_STILL_NAMES_IT = PAGE_WITHOUT_IT + "\n  Copper Kettle Revue, 9pm.\n"


def only(decisions):
    assert len(decisions) == 1, decisions
    return decisions[0]


# --- must-do 2: confirmed same-page evidence may update -----------------------

@pytest.mark.parametrize("field,new_value", [
    ("start_time", DAY + timedelta(hours=2)),
    ("end_time", DAY + timedelta(hours=5)),
    ("title", "Copper Kettle Revue: Farewell Night"),
])
def test_a_confirmed_page_updates_the_field_it_now_states_differently(field, new_value):
    """Founder: "Confirmed check MAY update a published listing (time, cancel,
    postpone, title) only with same-page evidence."

    Each field is matched on the OTHER one — a retimed show still matches by
    title, a retitled show still matches by time — which is why the matcher
    takes title OR time and never both."""
    fresh = {"end_time": DAY + timedelta(hours=3)}
    fresh[field] = new_value
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(end_time=DAY + timedelta(hours=3))],
        parsed=[parsed(**fresh)],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_UPDATE
    assert d.fields == {field: new_value}
    assert d.matched_candidate_id == "c1"


def test_only_the_founders_four_fields_can_ever_be_written():
    """"time, cancel, postpone, title" and nothing else. Anything a future
    extractor learns to read is NOT admitted here by accident."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published()],
        parsed=[parsed(title="A New Name", start_time=DAY + timedelta(hours=1))],
        gate_passes=ALWAYS_PASSES))
    assert set(d.fields) <= set(UPDATABLE_LISTING_FIELDS)


def test_a_page_that_still_says_the_same_thing_changes_nothing():
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()], parsed=[parsed()],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE and not d.fields


def test_a_null_on_the_page_never_blanks_a_published_value():
    """Silence is not evidence. A read that stopped mentioning the end time has
    not said the event lost one."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(end_time=DAY + timedelta(hours=3))],
        parsed=[parsed(title=None, end_time=None)],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE


def test_the_matched_listings_own_gate_verdict_licenses_the_update(caplog):
    """R-091(a), the precondition. The PAGE's gate verdict is the verdict of its
    FIRST candidate; a calendar of forty shows carries one PASS that says
    nothing about the other thirty-nine. So the licence is the MATCHED
    listing's own verdict, and a page-level present is not enough."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published()],
        parsed=[parsed(start_time=DAY + timedelta(hours=2))],
        gate_passes=NEVER_PASSES))
    assert d.action == ACTION_NONE
    assert "did not PASS" in d.why


def test_two_matching_listings_are_ambiguous_and_keep():
    """"Ambiguous parse = keep." Two listings on the page share this row's
    title or time — we cannot tell which one is ours, so neither speaks for it."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published()],
        parsed=[parsed(candidate_id="c1", start_time=DAY + timedelta(hours=1)),
                parsed(candidate_id="c2", start_time=DAY + timedelta(hours=4))],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE and "ambiguous" in d.why


def test_titles_match_across_case_punctuation_and_spacing_but_not_across_words():
    assert normalize_title("Copper Kettle Revue") == normalize_title("copper  kettle — revue!")
    assert normalize_title("Copper Kettle Revue") != normalize_title("Copper Kettle Revue II")
    assert normalize_title(None) is None and normalize_title("  ") is None


def test_two_untitled_listings_are_not_a_match():
    """The extraction prompt makes a null title the COMMON case, so treating
    null == null as a match would marry unrelated listings on nearly every
    page. Here the times differ too, so nothing matches — and an unbracketed
    absence keeps."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(title=None)],
        parsed=[parsed(title=None, start_time=DAY + timedelta(days=40))],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE


# --- must-do 3: unconfirmed changes nothing -----------------------------------

@pytest.mark.parametrize("kind,status,decision", [
    ("missed", None, None),          # timeout / transport failure
    ("missed", 500, None),           # server error
    ("backoff", 429, None),          # rate limited
    ("backoff", 503, None),
    ("wall", 403, None),             # closed door
    ("deferred", None, None),        # budget or politeness cap
    ("offsite", None, None),
    ("changed", None, "sensor_rejected"),   # empty / unreadable page
    ("changed", None, "deferred"),          # model budget spent
    ("changed", None, "held"),              # gate declined
    ("changed", None, "escalated"),         # gate escalated
    ("a_shape_nobody_has_written_yet", None, None),
])
def test_an_unconfirmed_check_mutates_nothing(kind, status, decision):
    """Founder: "Unconfirmed (timeout, 429, cap, empty, ambiguous parse): no
    mutation. last_attempt only." Including the shape nobody has written yet —
    the default has to be the closed one."""
    verdict, reason = classify_recheck(
        door_kind=kind, page_decision=decision, http_status=status)
    assert verdict == UNVERIFIED
    decisions = adjudicate_page(
        verdict=verdict, verdict_reason=reason,
        published=[published()],
        parsed=[parsed(start_time=DAY + timedelta(hours=9))],  # a change we refuse to see
        gate_passes=ALWAYS_PASSES)
    assert all(d.action == ACTION_NONE and not d.fields for d in decisions)
    assert "unconfirmed" in only(decisions).why


def test_a_verified_page_that_produced_no_listings_changes_nothing():
    """A byte-identical page (extraction is skipped by design) and a clean parse
    that named nothing arrive here the same way. "The page listed nothing" is
    also exactly the shape a broken render takes — it cancels no one."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()], parsed=[],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE and "no listings" in d.why


# --- must-do 4: confirmed gone is marked, never deleted -----------------------

def test_a_clean_404_of_the_defining_url_marks_the_row_gone():
    """Founder overrule 2026-09-02: "Confirmed gone (clean 404 of defining URL
    ...): mark cancelled/moved with evidence; row remains."""
    verdict, reason = classify_recheck(door_kind="missed", http_status=404)
    assert verdict == VERIFIED_ABSENT
    d = only(adjudicate_page(verdict=verdict, verdict_reason=reason,
                             published=[published()], parsed=[],
                             gate_passes=NEVER_PASSES))
    assert d.action == ACTION_MARK_GONE
    assert d.fields == {"status": GONE_STATUS}
    assert "404" in d.why


def test_absent_from_a_clean_parse_that_brackets_the_date_marks_the_row_gone():
    """The second confirmed-gone shape, and the one that carries real same-page
    evidence: the page still loads, still lists shows either side of this date,
    and no longer names this one."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()], parsed=bracket(),
        gate_passes=ALWAYS_PASSES, page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_MARK_GONE
    assert d.fields == {"status": GONE_STATUS}


@pytest.mark.parametrize("times,why", [
    ([EARLIER, EARLIER - timedelta(days=1)], "calendar truncated before the date"),
    ([LATER, LATER + timedelta(days=1)], "calendar starts after the date"),
    ([None, None], "listings with no time cannot bracket anything"),
])
def test_an_unbracketed_absence_keeps_the_row(times, why):
    """THE FALSE-ABSENCE GUARD. A calendar showing the next ten shows
    legitimately stops mentioning a show three months out; reading that as
    "cancelled" would take a real event off the live feed on evidence that was
    never about it."""
    page = [ParsedListing(candidate_id=f"c{i}", title=f"Other {i}", start_time=t)
            for i, t in enumerate(times)]
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()], parsed=page,
        gate_passes=ALWAYS_PASSES, page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_NONE, why
    assert "do not reach this date" in d.why


def test_a_marked_row_is_never_deleted_only_restated():
    """Founder: "Do not delete the row from the catalog." Coverage Law says the
    same thing, and the 4-state model says disputed is shown, never hidden."""
    for verdict in (VERIFIED_PRESENT, VERIFIED_ABSENT, UNVERIFIED, "unknown"):
        for d in adjudicate_page(verdict=verdict, published=[published()],
                                 parsed=bracket(), gate_passes=ALWAYS_PASSES,
                                 page_text=PAGE_WITHOUT_IT):
            assert d.action in (ACTION_UPDATE, ACTION_MARK_GONE, ACTION_NONE)
            assert "delete" not in d.action


def test_the_module_contains_no_delete_and_no_insert_into_event():
    """Structural, not behavioural: the writer cannot remove or create a
    published row because no such statement exists in the file, and it imports
    no promote path."""
    import ast
    import pathlib

    import worker.listing_update as lu
    text = pathlib.Path(lu.__file__).read_text()
    tree = ast.parse(text)
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not any((m or "").startswith("worker.promote") for m in modules)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            sql = node.value.lower()
            assert "delete from" not in sql
            assert "insert into event" not in sql


# --- the writer ---------------------------------------------------------------

class FakeCursor:
    """Records the SQL it is handed. rowcount mimics an UPDATE that matched."""

    def __init__(self, rowcount=1):
        self.calls = []
        self.rowcount = rowcount

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))

    def sql_matching(self, needle):
        return [c for c in self.calls if needle in c[0].lower()]


def test_every_mutation_writes_its_evidence_and_its_audit_row():
    """Founder: "Write evidence." / "mark cancelled/moved with evidence"."""
    cur = FakeCursor()
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(start_time=DAY + timedelta(hours=2))],
        gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(
        decisions, source_id="s1", source_name="Granite Hall",
        source_class="venue_calendar", page_url="https://gh.example/calendar",
        run_id="run-1", budget=TickBudget(), cur=cur)
    assert counts == {"updated": 1, "marked_gone": 0, "skipped_budget": 0}
    assert len(cur.sql_matching("update event")) == 1
    assert len(cur.sql_matching("insert into candidate_evidence")) == 1
    assert len(cur.sql_matching("insert into audit_log")) == 1
    audit = cur.sql_matching("insert into audit_log")[0][1]
    assert "https://gh.example/calendar" in audit[1] and "run-1" in audit[1]


def test_a_no_op_decision_writes_nothing_at_all():
    """"last_attempt only" — an unconfirmed check touches no table here. The
    attempt itself is already recorded by the fetch layer's raw_fetch row."""
    cur = FakeCursor()
    decisions = adjudicate_page(
        verdict=UNVERIFIED, verdict_reason="rate-limited (429)",
        published=[published()], parsed=[parsed(start_time=LATER)],
        gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(
        decisions, source_id="s1", source_name="Granite Hall",
        source_class="venue_calendar", page_url="https://gh.example/calendar",
        run_id="run-1", budget=TickBudget(), cur=cur)
    assert cur.calls == []
    assert counts == {"updated": 0, "marked_gone": 0, "skipped_budget": 0}


def test_the_update_re_asserts_the_human_lock_in_its_own_where_clause():
    """A human action landing between the read and the write WINS. The row is
    re-qualified inside the UPDATE, so the race is lost by the loop, not by the
    person."""
    cur = FakeCursor()
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(start_time=DAY + timedelta(hours=2))],
        gate_passes=ALWAYS_PASSES)
    apply_decisions(decisions, source_id="s1", source_name="Granite Hall",
                    source_class="venue_calendar", page_url="u", run_id="r",
                    budget=TickBudget(), cur=cur)
    sql = cur.sql_matching("update event")[0][0].lower()
    assert "override_lock = false" in sql and "status = 'scheduled'" in sql


def test_a_lost_race_is_a_no_op_never_a_retry():
    cur = FakeCursor(rowcount=0)      # somebody moved the row first
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(start_time=DAY + timedelta(hours=2))],
        gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(decisions, source_id="s1", source_name="G",
                             source_class="venue_calendar", page_url="u",
                             run_id="r", budget=TickBudget(), cur=cur)
    assert counts["updated"] == 0
    assert not cur.sql_matching("insert into audit_log")


def test_the_tick_mutation_budget_bounds_the_blast_radius():
    """A cap that turns a bug from a catalog-wide event into a bounded one.
    Past it the tick stops MUTATING and keeps crawling — coverage is never what
    a safety cap costs."""
    cur = FakeCursor()
    budget = TickBudget(max_listing_mutations=1)
    rows = [published(event_id=f"e{i}") for i in range(3)]
    news = [parsed(candidate_id=f"c{i}", start_time=DAY + timedelta(hours=2))
            for i in range(1)]
    decisions = adjudicate_page(verdict=VERIFIED_PRESENT, published=rows,
                                parsed=news, gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(decisions, source_id="s1", source_name="G",
                             source_class="venue_calendar", page_url="u",
                             run_id="r", budget=budget, cur=cur)
    assert counts["updated"] + counts["marked_gone"] == 1
    assert counts["skipped_budget"] == 2
    assert budget.listing_mutations == 1


# --- the founder's table ------------------------------------------------------

def test_the_table_prints_a_row_per_event_with_its_reason():
    """`event | check result | mutated? | why` — the artifact the ticket asks
    for. A no-op is a row: "we looked and changed nothing, here is why" is the
    answer a fail-closed loop most often has."""
    updated = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(start_time=DAY + timedelta(hours=2))],
        gate_passes=ALWAYS_PASSES))
    kept = only(adjudicate_page(
        verdict=UNVERIFIED, verdict_reason="rate-limited (429/503)",
        published=[published(event_id="e2")], parsed=[], gate_passes=ALWAYS_PASSES))
    table = render_decision_table([
        ("Copper Kettle Revue", VERIFIED_PRESENT, updated),
        ("Tin Sparrow", UNVERIFIED, kept),
    ])
    lines = table.splitlines()
    assert lines[0].split(" | ")[0].strip() == "event"
    assert [c.strip() for c in lines[0].split("|")] == [
        "event", "check result", "mutated?", "why"]
    assert "present" in lines[2] and "yes" in lines[2]
    assert "no" in lines[3] and "rate-limited" in lines[3]


# --- the two blocking findings from the PR #214 adversarial panel -------------
#
# Both were real, both were on the published-data path, and both are pinned
# here so neither can come back.

def test_a_recurring_title_never_retimes_the_published_night():
    """FINDING 1 (openai/attacker-smuggle): title-only identity matching can
    retime the wrong event.

    "Open Mic" repeats its exact title every week. When the published night has
    rolled off the calendar and only a LATER occurrence is still listed, a
    title-only match was a single hit and the published row was moved to the
    wrong night — a person reads "the show moved" and turns up to a dark room.

    A title match too far away in time is NOT an identity. It is also NOT an
    absence: something on the page carries our title, which is precisely the
    reason to say nothing rather than cancel."""
    next_week = DAY + timedelta(days=7)
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(title="Open Mic")],
        parsed=[parsed(candidate_id="c9", title="Open Mic", start_time=next_week)],
        gate_passes=ALWAYS_PASSES, page_text="Open Mic every Tuesday, 9pm."))
    assert d.action == ACTION_NONE
    assert not d.fields
    assert "too far off to be the same occurrence" in d.why


@pytest.mark.parametrize("shift,expected", [
    (timedelta(hours=1), MATCH_TITLE),        # doors moved an hour
    (timedelta(hours=6), MATCH_TITLE),        # matinee moved to the evening
    (MAX_TITLE_ONLY_RETIME, MATCH_TITLE),     # the boundary is inclusive
    (timedelta(hours=13), MATCH_FAR),
    (timedelta(days=1), MATCH_FAR),           # a DAILY series' next occurrence
    (timedelta(days=7), MATCH_FAR),           # a weekly series' next occurrence
])
def test_the_retime_window_separates_a_correction_from_another_occurrence(shift, expected):
    """Twelve hours, not twenty-four, and the difference is the point: a daily
    series at a fixed hour puts its next occurrence exactly 24h away."""
    assert match_kind(published(), parsed(start_time=DAY + shift)) == expected


def test_a_matching_start_time_still_licenses_a_rename():
    """The other direction is unaffected: when the start times agree, the DATE
    pins which occurrence this is, so a differing title is safely a rename."""
    assert match_kind(published(), parsed(title="A Whole New Name")) == MATCH_TIME
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(title="A Whole New Name")], gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_UPDATE and d.fields == {"title": "A Whole New Name"}


def test_an_extraction_miss_is_not_a_cancellation():
    """FINDING 2 (openai, both seats): AI extraction omission can mark a real
    event cancelled.

    The absence branch read "the extractor did not return this event" as "the
    page no longer says it". Extraction is the one probabilistic stage in the
    pipeline, and a model that skips a listing produces exactly the same empty
    result as a genuinely removed show. Absence is now corroborated against the
    RAW PAGE TEXT, deterministically and without a model."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()], parsed=bracket(),
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT))
    assert d.action == ACTION_NONE
    assert "extraction miss is not a cancellation" in d.why


@pytest.mark.parametrize("page_text,title", [
    (None, "Copper Kettle Revue"),      # no page text (e.g. another queue)
    ("", "Copper Kettle Revue"),
    (PAGE_WITHOUT_IT, None),            # a published row with no title to look for
])
def test_absence_that_cannot_be_checked_against_the_page_keeps(page_text, title):
    """None means "we could not ask", and that is never absence."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published(title=title)],
        parsed=bracket(), gate_passes=ALWAYS_PASSES, page_text=page_text))
    assert d.action == ACTION_NONE
    assert "absence unconfirmed" in d.why


def test_the_page_text_check_is_deterministic_and_word_boundaried():
    assert title_still_on_page("Copper Kettle Revue", PAGE_THAT_STILL_NAMES_IT) is True
    assert title_still_on_page("Copper Kettle Revue", PAGE_WITHOUT_IT) is False
    # case, punctuation and spacing are noise on both sides, as everywhere else
    assert title_still_on_page("copper  kettle — revue!", PAGE_THAT_STILL_NAMES_IT) is True
    # a longer title is not "present" merely because a prefix of it is
    assert title_still_on_page("Copper Kettle Revue Reunion", PAGE_THAT_STILL_NAMES_IT) is False
    assert title_still_on_page(None, PAGE_WITHOUT_IT) is None
    assert title_still_on_page("Anything", None) is None


def test_a_404_still_marks_gone_without_any_page_text():
    """The corroboration applies to a page that LOADS. A clean 404 has no page
    to quote and is a confirmed-gone shape on the founder's own overrule, so it
    must not be blocked by a check it can never satisfy."""
    verdict, reason = classify_recheck(door_kind="missed", http_status=404)
    d = only(adjudicate_page(verdict=verdict, verdict_reason=reason,
                             published=[published()], parsed=[],
                             gate_passes=NEVER_PASSES, page_text=None))
    assert d.action == ACTION_MARK_GONE


# --- round 2: the bracket that proves absence must itself be gated ------------

def test_an_ungated_bracket_cannot_cancel_a_published_row():
    """PR #214 r2, both openai seats: absence cancellation was licensed by
    ungated AI-extracted bracketing listings.

    The asymmetry pointed the wrong way. An UPDATE already required the matched
    listing's own trust-gate PASS, while a CANCEL — the larger, user-visible
    action that takes a row off the live feed — rested on bracket timestamps
    straight from the extractor. A garbled or hostile extraction that omits the
    real event and emits plausible earlier+later listings around its date would
    manufacture exactly the coverage window the guard demands.

    This is the fixture the panel's nit asked for: the title IS absent from the
    raw page text, the parsed listings DO bracket the date, and the bracketing
    candidates fail the gate."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()], parsed=bracket(),
        gate_passes=NEVER_PASSES, page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_NONE
    assert "gate-passed listings do not reach this date" in d.why


def test_one_gated_side_is_not_a_bracket():
    """Half a coverage window is not a coverage window: if only the EARLIER
    listing passes the gate, the page has not shown it reaches the date."""
    earlier, later = bracket()
    passes_earlier_only = lambda cid: cid == earlier.candidate_id  # noqa: E731
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[earlier, later], gate_passes=passes_earlier_only,
        page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_NONE


def test_the_bracket_scan_only_asks_the_gate_about_listings_that_could_help():
    """The gate re-computes a verdict from stored evidence, so the scan must not
    ask about every listing on a forty-show calendar. It stops as soon as both
    sides are satisfied and skips anything that cannot move the answer."""
    asked = []

    def counting_gate(cid):
        asked.append(cid)
        return True

    noise = [ParsedListing(candidate_id=f"noise{i}", title=f"Other {i}",
                           start_time=EARLIER - timedelta(days=i + 1))
             for i in range(20)]
    earlier, later = bracket()
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[earlier, later] + noise, gate_passes=counting_gate,
        page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_MARK_GONE
    # Both sides are settled by the first two listings; the twenty redundant
    # earlier ones are never asked about.
    assert asked == [earlier.candidate_id, later.candidate_id]


def test_a_listing_exactly_on_the_moment_can_still_supply_the_missing_side():
    """A guard on the short-circuit itself: a listing AT the moment satisfies
    both comparisons, so "skip anything on a side I already have" would drop it
    while the side it could fill was still missing."""
    from worker.listing_update import _brackets
    at_moment = ParsedListing(candidate_id="cX", title="Same Minute", start_time=DAY)
    earlier = ParsedListing(candidate_id="cA", title="Earlier", start_time=EARLIER)
    assert _brackets([earlier, at_moment], DAY, ALWAYS_PASSES) is True


def test_a_404_needs_no_bracket_at_all():
    """The bracket is evidence about a page that LOADS. A clean 404 has no
    listings to gate and must not be blocked by a test it cannot satisfy."""
    verdict, _ = classify_recheck(door_kind="missed", http_status=404)
    d = only(adjudicate_page(verdict=verdict, published=[published()],
                             parsed=[], gate_passes=NEVER_PASSES, page_text=None))
    assert d.action == ACTION_MARK_GONE
