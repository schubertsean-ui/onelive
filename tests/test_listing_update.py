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
    ACTION_MARK_GONE,
    ACTION_NONE,
    ACTION_UPDATE,
    GONE_STATUS,
    ParsedListing,
    PublishedListing,
    adjudicate_page,
    apply_decisions,
    normalize_title,
    render_decision_table,
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
        gate_passes=ALWAYS_PASSES))
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
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE, why
    assert "do not reach this date" in d.why


def test_a_marked_row_is_never_deleted_only_restated():
    """Founder: "Do not delete the row from the catalog." Coverage Law says the
    same thing, and the 4-state model says disputed is shown, never hidden."""
    for verdict in (VERIFIED_PRESENT, VERIFIED_ABSENT, UNVERIFIED, "unknown"):
        for d in adjudicate_page(verdict=verdict, published=[published()],
                                 parsed=bracket(), gate_passes=ALWAYS_PASSES):
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
