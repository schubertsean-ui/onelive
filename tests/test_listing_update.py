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
    MATCH_COLLISION,
    MATCH_FAR,
    MATCH_TIME,
    MATCH_UNTITLED,
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
    matches,
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

def test_a_confirmed_page_updates_the_field_it_now_states_differently():
    """Founder: "Confirmed check MAY update a published listing (time, cancel,
    postpone, title) only with same-page evidence."

    Rewritten at r8. This test used to run over BOTH time fields, on the premise
    that "each field is matched on the OTHER one — a retimed show still matches
    by title". Both openai seats blocked that premise: a title is not an
    occurrence, so a listing matched only by title writes nothing at all now.
    What a page can still confirm is a listing it agrees with on title AND start
    minute, stating a different end."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(end_time=DAY + timedelta(hours=3))],
        parsed=[parsed(end_time=DAY + timedelta(hours=5))],
        gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_UPDATE
    assert d.fields == {"end_time": DAY + timedelta(hours=5)}
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
        parsed=[parsed(end_time=DAY + timedelta(hours=5))],
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
    """Founder: "Write evidence." / "mark cancelled/moved with evidence".

    The listing carries its own class here, because that is now the ONLY thing
    that can label an evidence row — see
    test_the_writer_cannot_borrow_a_class_from_anywhere."""
    cur = FakeCursor()
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(end_time=DAY + timedelta(hours=5),
                       source_class="venue_calendar")],
        gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(
        decisions, source_id="s1", source_name="Granite Hall", page_url="https://gh.example/calendar",
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
        decisions, source_id="s1", source_name="Granite Hall", page_url="https://gh.example/calendar",
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
        parsed=[parsed(end_time=DAY + timedelta(hours=5))],
        gate_passes=ALWAYS_PASSES)
    apply_decisions(decisions, source_id="s1", source_name="Granite Hall", page_url="u", run_id="r",
                    budget=TickBudget(), cur=cur)
    sql = cur.sql_matching("update event")[0][0].lower()
    assert "override_lock = false" in sql and "status = 'scheduled'" in sql


def test_a_lost_race_is_a_no_op_never_a_retry():
    cur = FakeCursor(rowcount=0)      # somebody moved the row first
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(end_time=DAY + timedelta(hours=5))],
        gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(decisions, source_id="s1", source_name="G", page_url="u",
                             run_id="r", budget=TickBudget(), cur=cur)
    assert counts["updated"] == 0
    assert not cur.sql_matching("insert into audit_log")


def test_the_tick_mutation_budget_bounds_the_blast_radius():
    """A cap that turns a bug from a catalog-wide event into a bounded one.
    Past it the tick stops MUTATING and keeps crawling — coverage is never what
    a safety cap costs."""
    cur = FakeCursor()
    budget = TickBudget(max_listing_mutations=1)
    # Distinct titles AND distinct minutes on purpose: three rows sharing one
    # title and one time are refused by the one-to-one rule, and three sharing
    # one MINUTE are refused by the founder's collision clause (two titles, one
    # minute, no unique id — see _contested_minutes). This test is about the
    # CAP, so the fixture keeps all three cleanly identifiable.
    rows = [published(event_id=f"e{i}", title=f"Show {i}",
                      start_time=DAY + timedelta(hours=i)) for i in range(3)]
    news = [parsed(candidate_id=f"c{i}", title=f"Show {i}",
                   start_time=DAY + timedelta(hours=i),
                   end_time=DAY + timedelta(hours=5 + i))
            for i in range(3)]
    decisions = adjudicate_page(verdict=VERIFIED_PRESENT, published=rows,
                                parsed=news, gate_passes=ALWAYS_PASSES)
    counts = apply_decisions(decisions, source_id="s1", source_name="G", page_url="u",
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
        parsed=[parsed(end_time=DAY + timedelta(hours=5))],
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


def test_a_shared_start_time_with_a_different_title_is_a_collision_not_a_rename():
    """PR #214 r3, both openai seats: a time-only match could rewrite the
    published title from a DIFFERENT event.

    A multi-room venue puts two bands on at 8pm as a matter of course, and a
    replacement booking takes the slot of the show it replaced. The parsed
    listing's gate PASS proves that IT is real; it says nothing about it being
    OURS. Rewriting the row from it would put a different event on the feed
    under the old row's identity."""
    assert match_kind(published(), parsed(title="A Whole New Name")) == MATCH_COLLISION
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(title="A Whole New Name")], gate_passes=ALWAYS_PASSES))
    assert d.action == ACTION_NONE and not d.fields


def test_a_collision_blocks_the_cancel_path_too():
    """A different event holding our start time makes our absence unreadable —
    it is not evidence we are gone. Fail closed both ways: no rewrite AND no
    cancel."""
    other = ParsedListing(candidate_id="cB", title="Another Band", start_time=DAY)
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[other] + bracket(), gate_passes=ALWAYS_PASSES,
        page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_NONE
    assert "different event holds this row's start time" in d.why


def test_a_shared_start_time_identifies_only_when_both_sides_can_name_it():
    """Rewritten at r7. This test used to pin the OPPOSITE rule — that an
    untitled side "cannot be claiming to be a different event", so the time
    match still identified the row. openai/absence-only showed that reasoning is
    backwards: an anonymous listing contradicts nothing AND confirms nothing,
    and the gate PASS on it proves only that it is real, never that it is ours.
    A shared minute identifies the row when both sides name it and agree."""
    assert match_kind(published(), parsed()) == MATCH_TIME
    assert match_kind(published(), parsed(title=None)) == MATCH_UNTITLED
    assert match_kind(published(title=None), parsed()) == MATCH_UNTITLED
    assert match_kind(published(title=None), parsed(title=None)) == MATCH_UNTITLED
    assert not matches(published(), parsed(title=None))


def test_no_title_is_ever_written_from_same_page_evidence():
    """The honest conclusion of the r3 finding, and a narrowing of the founder's
    own enumeration ("time, cancel, postpone, title") recorded as R-095.

    Ask what would license a rewrite: proof this parsed listing IS that
    published row, holding while the title itself changes. Same start time
    cannot supply it, and same title supplies it only by being EQUAL — in which
    case there is nothing to write. No third anchor exists on same-page
    evidence, so a rename and a replacement are indistinguishable."""
    for parsed_listing in (
            parsed(title="Something Else Entirely"),          # collision
            parsed(title="Copper Kettle Revue: Farewell"),    # would-be rename
            parsed(title=None, start_time=DAY + timedelta(hours=1)),
    ):
        for d in adjudicate_page(
                verdict=VERIFIED_PRESENT, published=[published()],
                parsed=[parsed_listing], gate_passes=ALWAYS_PASSES,
                page_text=PAGE_WITHOUT_IT):
            assert "title" not in d.fields


@pytest.mark.parametrize("page,present", [
    ("<b>Rock</b> &amp; Roll tonight", True),      # entity + tags
    ("Rock &#38; Roll tonight", True),             # numeric entity
    ("Rock &amp;amp; Roll", False),                # double-escaped is NOT it
    ("Jazz Night only, no rock here", False),
])
def test_the_absence_check_reads_markup_the_way_a_person_sees_it(page, present):
    """PR #214 r3, openai/attacker-smuggle: the check searched RAW html, so a
    page still saying `Rock &amp; Roll` read as not containing "Rock & Roll" —
    `&amp;` normalizes to the word "amp". Titles with an ampersand are ordinary
    ("Sam & Dave"), which made this the common case, and with a gated bracket
    it cancels a real event off the live feed."""
    assert title_still_on_page("Rock & Roll", page) is present


def test_tags_become_spaces_so_neighbouring_words_never_fuse():
    """A title split across two table cells must not fuse with its neighbour's
    words into a match that was never on the page."""
    assert title_still_on_page("Sam Dave", "<td>Sam</td><td>Dave</td>") is True
    assert title_still_on_page("Samdave", "<td>Sam</td><td>Dave</td>") is False


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


# --- round 4: an evidence row attests, so every column must be real ----------

def _one_update(gate=ALWAYS_PASSES, **parsed_kw):
    return adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(end_time=DAY + timedelta(hours=5), **parsed_kw)],
        gate_passes=gate)


def test_the_evidence_quote_is_never_the_adjudicators_own_sentence():
    """PR #214 r4, openai/attacker-smuggle: `candidate_evidence.quote` was
    populated with "re-check <run>: <why>" — the system's own adjudication
    text, in a column that holds text FROM THE PAGE (worker/ai_extract.py puts
    the listing's own block there). Anything surfacing a quote would show a
    person words the venue never published."""
    cur = FakeCursor()
    apply_decisions(_one_update(source_class="venue_calendar"),
                    source_id="s1", source_name="Granite Hall", page_url="https://gh.example/c",
                    run_id="run-1", budget=TickBudget(), cur=cur)
    quote = cur.sql_matching("insert into candidate_evidence")[0][1][4]
    assert quote == "", "the quote column holds page text or nothing at all"
    # The reason is still recorded — in the audit row, where the founder ruled
    # it belongs (2026-09-03).
    assert "run-1" in cur.sql_matching("insert into audit_log")[0][1][1]


def test_the_evidence_class_is_the_listings_own_never_an_anchor_default():
    """The same seat's second finding: `source_class or "venue_calendar"` wrote
    an ANCHOR class (worker/gating.py) whenever the caller supplied none, so
    unknown provenance was silently upgraded to the strongest tier in the trust
    vocabulary — on a row attached to a published-data mutation."""
    cur = FakeCursor()
    apply_decisions(_one_update(source_class="social"),
                    source_id="s1", source_name="Granite Hall",
                    page_url="u", run_id="r", budget=TickBudget(), cur=cur)
    written_class = cur.sql_matching("insert into candidate_evidence")[0][1][1]
    assert written_class == "social", "the listing's own class wins"


def test_an_unlabelled_listing_gets_no_evidence_row_but_still_an_audit_row():
    """No default, at all. A row asserting provenance it cannot support is
    worse than no row — and the mutation is still recorded."""
    cur = FakeCursor()
    counts = apply_decisions(_one_update(source_class=None),
                             source_id="s1", source_name="Granite Hall", page_url="u", run_id="r",
                             budget=TickBudget(), cur=cur)
    assert cur.sql_matching("insert into candidate_evidence") == []
    assert len(cur.sql_matching("insert into audit_log")) == 1
    assert counts["updated"] == 1


def test_the_writer_cannot_borrow_a_class_from_anywhere(monkeypatch):
    """PR #214 r5, openai/absence-only blocking (and attacker-smuggle's nit on
    the same line): the code and the rule this module states had drifted apart.

    The docstring already claimed "the listing's OWN class, read from the
    candidate row", but the code still fell back to the caller's value when the
    candidate had none — and the caller's value can be an ANCHOR class. That
    near-miss is the whole risk: the evidence row would look correct, cite a
    real source-level class, and still assert provenance the listing never had.

    Checked structurally as well as behaviourally, because the honest fix was
    to DELETE the parameter that carried a caller class into the writer, so no
    future edit can reintroduce the borrow by accident."""
    import inspect
    from worker import listing_update as lu
    for fn in (lu.apply_decisions, lu._write_all):
        assert "source_class" not in inspect.signature(fn).parameters, (
            f"{fn.__name__} still accepts a caller class it could borrow")


def test_an_update_whose_candidate_has_no_class_writes_only_the_audit_row():
    """The regression the panel's nit asked for by name: matched_source_class
    is None while a caller-side class would have been available."""
    cur = FakeCursor()
    counts = apply_decisions(_one_update(source_class=None),
                             source_id="s1", source_name="Granite Hall",
                             page_url="u", run_id="r", budget=TickBudget(), cur=cur)
    assert cur.sql_matching("insert into candidate_evidence") == []
    assert len(cur.sql_matching("insert into audit_log")) == 1
    assert counts["updated"] == 1


# --- round 6: two ways to be confidently wrong about identity ----------------
#
# Both blocking findings on this round were the same shape: a rule that reads
# correctly for one row, one page, one alphabet, and turns into a confident
# wrong answer the moment reality is slightly wider than the fixture.


@pytest.mark.parametrize("published_title, page_title", [
    ("Beyoncé", "Beyonce"),          # the accent is ours, the page's is plain
    ("Beyonce", "Beyoncé"),          # and the other way round
    ("Sigur Rós", "Sigur Ros"),      # accent INSIDE the word, not at the end
    ("Café Tacvba", "Cafe Tacvba"),
    ("Mötley Crüe", "Motley Crue"),
    ("Núria & Són", "Nuria & Son"),
])
def test_an_accent_is_not_an_absence(published_title, page_title):
    """openai/attacker-smuggle, r6. The old reduction DELETED every non-ASCII
    letter, so `Beyoncé` became `beyonc` and a page saying `Beyonce` did not
    contain it. That is the single answer that can license a cancellation, so a
    typographic difference between our row and the venue's CMS could take a
    real, still-listed event off the live feed."""
    assert title_still_on_page(
        published_title, f"<p>Tonight: {page_title} live</p>") is True


def test_a_folded_title_still_has_to_be_the_same_words():
    """Folding accents is not folding meaning: it must not make the guard
    answer True for a title the page does not carry."""
    assert title_still_on_page("Beyoncé", "<p>Tonight: Solange live</p>") is False


def test_a_non_latin_title_keeps_its_letters_instead_of_vanishing():
    """The same defect in its severe form: a title whose letters have no ASCII
    form used to reduce to whatever Latin scraps it carried, so `Кино Night`
    became the needle `night` — a word half the internet contains. Now the
    letters survive, and the question is asked about the actual title."""
    assert normalize_title("Кино Night") == "кино night"
    assert title_still_on_page("Кино Night", "<p>Кино Night, 9pm</p>") is True
    assert title_still_on_page("Кино Night", "<p>Jazz Night, 9pm</p>") is False


def test_the_match_path_does_not_fold_and_refuses_instead():
    """Rewritten at r9, and it now asserts the OPPOSITE of what it did.

    This test used to require the accent fold to reach the match path, on the
    reasoning that both rules should agree about what a title is. They should
    not: the two questions have opposite dangerous answers. A false yes in the
    absence guard keeps a row; a false yes in IDENTITY writes to one. So the
    match path keeps every mark, and a page spelling our title differently at
    our start minute is a contradiction to refuse, not a fold to absorb."""
    assert normalize_title("Beyoncé") != normalize_title("Beyonce")
    assert match_kind(published(title="Café Tacvba"),
                      parsed(title="Cafe Tacvba")) == MATCH_COLLISION


def _two_same_title_nights():
    """Two published occurrences of one recurring night, close enough together
    that either could be read as a retime of the other."""
    early = published(event_id="e_early", title="Open Mic",
                      start_time=DAY.replace(hour=20))
    late = published(event_id="e_late", title="Open Mic",
                     start_time=DAY.replace(hour=23))
    return early, late


def test_one_page_listing_cannot_identify_two_published_rows():
    """openai/absence-only, r6. Cardinality was checked in ONE direction —
    how many listings match this row — never the other. A page returning only
    the later of two same-title occurrences gives BOTH rows exactly one match,
    the same one, so the earlier row reads it as "the page moved me" and is
    retimed onto an event that is not it, while the later row keeps its own
    time. The catalog would then publish a real event at an hour nobody
    announced, which is the exact failure this whole path exists to prevent."""
    early, late = _two_same_title_nights()
    only_the_later = parsed(candidate_id="c_late", title="Open Mic",
                            start_time=DAY.replace(hour=23, minute=30))

    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[early, late],
        parsed=[only_the_later], gate_passes=ALWAYS_PASSES,
        page_text=PAGE_THAT_STILL_NAMES_IT)

    assert [d.action for d in decisions] == [ACTION_NONE, ACTION_NONE]
    for d in decisions:
        assert "one listing cannot be two rows" in d.why


def test_the_contested_listing_is_named_in_the_decision():
    """The refusal says WHICH listing it could not attribute, so the table and
    the audit trail can be read without re-deriving the match."""
    early, late = _two_same_title_nights()
    contested = parsed(candidate_id="c_late", title="Open Mic",
                       start_time=DAY.replace(hour=23, minute=30))
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[early, late], parsed=[contested],
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT)
    assert {d.matched_candidate_id for d in decisions} == {"c_late"}


def test_a_contested_listing_writes_nothing():
    """The decision is a no-op, so it must reach the writer as one: no update,
    no evidence row, no audit row."""
    early, late = _two_same_title_nights()
    contested = parsed(candidate_id="c_late", title="Open Mic",
                       start_time=DAY.replace(hour=23, minute=30))
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[early, late], parsed=[contested],
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT)
    cur = FakeCursor()
    counts = apply_decisions(decisions, source_id="s1", source_name="Granite Hall",
                             page_url="u", run_id="r", budget=TickBudget(), cur=cur)
    assert cur.calls == []
    assert counts == {"updated": 0, "marked_gone": 0, "skipped_budget": 0}


def test_two_rows_matched_by_their_own_listings_still_both_update():
    """The guard is one-to-ONE, not "give up whenever a page has two of
    anything". Two rows the page distinguishes cleanly both get their change.

    (Two occurrences of the SAME title inside the retime window are refused by
    the older `len(hits) > 1` rule before this one is reached — the page offers
    each row two readings of itself. That is the r1 recurring-title finding,
    and it stays refused; this test is about rows a page CAN tell apart.)"""
    supper = published(event_id="e_supper", title="Supper Club",
                       start_time=DAY.replace(hour=20))
    matinee = published(event_id="e_matinee", title="Matinee Reading",
                        start_time=DAY.replace(hour=23))
    p_supper = parsed(candidate_id="c_supper", title="Supper Club",
                      start_time=DAY.replace(hour=20),
                      end_time=DAY.replace(hour=22))
    p_matinee = parsed(candidate_id="c_matinee", title="Matinee Reading",
                       start_time=DAY.replace(hour=23),
                       end_time=DAY.replace(hour=23, minute=59))

    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[supper, matinee],
        parsed=[p_supper, p_matinee], gate_passes=ALWAYS_PASSES,
        page_text=PAGE_THAT_STILL_NAMES_IT)

    assert [d.action for d in decisions] == [ACTION_UPDATE, ACTION_UPDATE]
    assert [d.matched_candidate_id for d in decisions] == ["c_supper", "c_matinee"]


def test_a_contested_listing_cannot_cancel_the_row_it_could_not_identify():
    """A row whose only match is contested keeps its data AND its status: the
    refusal is a no-op, never a fall-through into the absence branch."""
    early, late = _two_same_title_nights()
    contested = parsed(candidate_id="c_late", title="Open Mic",
                       start_time=DAY.replace(hour=23, minute=30))
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[early, late],
        parsed=[contested] + bracket(), gate_passes=ALWAYS_PASSES,
        page_text=PAGE_WITHOUT_IT)
    assert all(d.action == ACTION_NONE for d in decisions)
    assert all(not d.fields for d in decisions)


def test_an_uncontested_page_is_unaffected_by_the_new_check():
    """The ordinary single-row page still updates — the guard fires on
    contested identity, not on every page."""
    decisions = adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(end_time=DAY + timedelta(hours=5))],
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT)
    assert only(decisions).action == ACTION_UPDATE


# --- round 7: what a page STATES, and what it merely fails to contradict -----


def test_a_moved_start_is_refused_whatever_else_the_page_states():
    """Rewritten at r8. These cases used to be the window rule's territory: a
    moved start with no stated end was refused, one with a stated end was
    written. Both openai seats then blocked the identity underneath — a listing
    matched only by title is not shown to be the same occurrence — so a moved
    start is now refused BEFORE the window is ever considered, and `start_time`
    is unwritable by construction."""
    for parsed_kw in [
        {"start_time": DAY + timedelta(hours=3)},                       # no end stated
        {"start_time": DAY + timedelta(hours=3),
         "end_time": DAY + timedelta(hours=5)},                         # whole window stated
    ]:
        d = only(adjudicate_page(
            verdict=VERIFIED_PRESENT,
            published=[published(start_time=DAY, end_time=DAY + timedelta(hours=2))],
            parsed=[parsed(**parsed_kw)],
            gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT))
        assert d.action == ACTION_NONE, parsed_kw
        assert "a repeat cannot be told from a move" in d.why


def test_no_update_decision_writes_a_start_time_without_an_identity():
    """R-099, now stated with the scope it always had: WITHOUT a per-listing
    identifier the only writing match is a shared start minute, and a shared
    minute has no start change — so `start_time` is unwritable by construction.
    Every fixture below carries NO identity on either side, which is what makes
    the claim true; the identity stack lifts exactly this and nothing else
    (tests/test_identity_stack.py holds the paired case where it is written).
    This is what would fail if the title/time rules were ever loosened without
    an identifier to justify it."""
    shifts = [None, DAY - timedelta(hours=6), DAY, DAY + timedelta(hours=3)]
    for new_start in shifts:
        for new_end in shifts:
            for pub_end in (None, DAY + timedelta(hours=2)):
                for gate in (ALWAYS_PASSES, NEVER_PASSES):
                    for d in adjudicate_page(
                            verdict=VERIFIED_PRESENT,
                            published=[published(start_time=DAY, end_time=pub_end)],
                            parsed=[parsed(start_time=new_start, end_time=new_end)],
                            gate_passes=gate,
                            page_text=PAGE_THAT_STILL_NAMES_IT):
                        assert "start_time" not in d.fields, (
                            f"{new_start}/{new_end} on a row ending {pub_end} "
                            f"wrote {d.fields}")


def test_the_window_rules_still_guard_the_writer_they_can_reach():
    """`_incoherent` is unit-tested directly because one of its two rules is
    unreachable through the adjudicator on the NO-IDENTITY path: a diff there
    can no longer carry a moved start, so "start moved, end not stated" cannot
    arise. It is not dead code — an identity match does move a start, and it is
    the rule that stops the `coalesce` hazard from reaching the writer there."""
    from worker import listing_update as lu
    row = published(start_time=DAY, end_time=DAY + timedelta(hours=2))
    silent = parsed(start_time=DAY + timedelta(hours=3))
    assert "states no end" in lu._incoherent(
        row, silent, {"start_time": DAY + timedelta(hours=3)})
    stated = parsed(start_time=DAY + timedelta(hours=3),
                    end_time=DAY + timedelta(hours=5))
    assert lu._incoherent(row, stated, {"start_time": DAY + timedelta(hours=3),
                                        "end_time": DAY + timedelta(hours=5)}) is None
    assert lu._incoherent(row, parsed(), {}) is None


@pytest.mark.parametrize("new_end", [
    DAY - timedelta(hours=1),   # ends before the start we keep
    DAY,                        # zero-length window
])
def test_a_page_whose_own_times_are_not_a_window_is_refused(new_end):
    """openai/attacker-smuggle, r7, still reachable at r8 through the one match
    that writes: the page agrees with us on title and start minute, and states
    an end that is not after it. A gate PASS proves a listing's evidence was
    corroborated, not that its fields are sane."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(start_time=DAY, end_time=DAY + timedelta(hours=2))],
        parsed=[parsed(start_time=DAY, end_time=new_end)],
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT))
    assert d.action == ACTION_NONE
    assert "do not make a window" in d.why


def test_a_new_end_before_the_kept_start_is_refused():
    """The mirror: only the end moves, and it lands before the start we keep."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(start_time=DAY, end_time=DAY + timedelta(hours=2))],
        parsed=[parsed(start_time=DAY, end_time=DAY - timedelta(hours=1))],
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT))
    assert d.action == ACTION_NONE
    assert "do not make a window" in d.why


def test_no_update_decision_can_carry_an_impossible_window():
    """The invariant behind the two rules above, asserted over the decision
    rather than over one fixture: whatever an ACTION_UPDATE writes, the pair the
    row ends up with is a window the page stated."""
    windows = [None, DAY - timedelta(hours=1), DAY, DAY + timedelta(hours=2)]
    for pub_end in windows:
        for new_start in windows:
            for new_end in windows:
                decisions = adjudicate_page(
                    verdict=VERIFIED_PRESENT,
                    published=[published(start_time=DAY, end_time=pub_end)],
                    parsed=[parsed(start_time=new_start, end_time=new_end)],
                    gate_passes=ALWAYS_PASSES,
                    page_text=PAGE_THAT_STILL_NAMES_IT)
                for d in decisions:
                    if d.action != ACTION_UPDATE:
                        continue
                    start = d.fields.get("start_time", DAY)
                    end = d.fields.get("end_time", pub_end)
                    assert end is None or end > start, (
                        f"published end={pub_end} + page {new_start}/{new_end} "
                        f"-> {d.fields}, which is not a window")


def test_an_anonymous_listing_on_our_minute_writes_nothing():
    """openai/absence-only, r7. A parsed listing with no title at the same start
    minute used to be MATCH_TIME — an identity — so `_field_diff` could write
    its end_time onto our row. The same multi-room page that puts two bands on
    at 8pm also produces untitled listings, and an extraction that drops a title
    produces them by the dozen."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published(end_time=None)],
        parsed=[parsed(title=None, end_time=DAY + timedelta(hours=4))],
        gate_passes=ALWAYS_PASSES, page_text=PAGE_THAT_STILL_NAMES_IT))
    assert d.action == ACTION_NONE
    assert not d.fields


def test_an_anonymous_listing_on_our_minute_blocks_the_cancel_too():
    """It identifies nothing, but it is not nothing: something is sitting on
    this row's start time and cannot be told apart from it, which is a reason to
    say nothing rather than a reason to cancel."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT, published=[published()],
        parsed=[parsed(candidate_id="anon", title=None)] + bracket(),
        gate_passes=ALWAYS_PASSES, page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_NONE
    assert "no title to check it against" in d.why


@pytest.mark.parametrize("ours, theirs", [
    ("Beyoncé", "Beyonce"),                     # Latin, Mn
    ("Sigur Rós", "Sigur Ros"),
    ("שָׁלוֹם עֲלֵיכֶם", "שלום עליכם"),                # Hebrew niqqud, Mn
    ("مُحَمَّد Live", "محمد Live"),                # Arabic harakat, Mn
])
def test_optional_marks_never_read_as_an_absence(ours, theirs):
    """openai/absence-only, r7. The r6 fold enumerated the combining RANGES I
    could think of — Latin, Greek, Cyrillic — so Hebrew, Arabic and Indic marks
    still fell through to the punctuation pass and became SPACES, splitting a
    word in two. One side carrying its marks and the other not then read as a
    confident absence, on the path that cancels."""
    assert title_still_on_page(ours, f"<p>tonight: {theirs}</p>") is True
    assert title_still_on_page(theirs, f"<p>tonight: {ours}</p>") is True
    # And the fold stays where it belongs: identity does not absorb it.
    assert normalize_title(ours) != normalize_title(theirs)


def test_a_spacing_vowel_sign_is_part_of_the_word_and_is_kept():
    """The other half of the same rule, and why `unicodedata.combining()` is the
    wrong test: it returns 0 for spacing marks (Mc). A Devanagari or Tamil vowel
    sign is not optional decoration — deleting it would merge words that are
    genuinely different, so Mc is KEPT while Mn and Me are folded away."""
    assert normalize_title("हिंदी Night") != normalize_title("हदी Night")
    assert normalize_title("தமிழ் Night") is not None


def test_the_fold_is_asked_of_unicode_rather_than_enumerated():
    """Structural, because the defect twice over was an enumeration that looked
    complete: no block ranges in the reduction, and the category test present."""
    import inspect
    from worker import listing_update as lu
    src = inspect.getsource(lu._fold_run) + inspect.getsource(lu._reduce)
    assert "unicodedata.category" in src
    assert "\\u03" not in src, "a hand-listed combining range is back"


def test_a_multi_word_title_still_matches_as_one_run():
    """Punctuation collapses to a single space on both sides, or a whole-word
    search for a two-word title stops finding it."""
    assert title_still_on_page("Open  Mic -- Night!", "<p>open mic night</p>") is True


# --- round 9: the fold is a property of the question, not of the text --------


@pytest.mark.parametrize("ours, theirs, what", [
    ("नुक्कड़ Night", "नुक्कड Night", "Devanagari NUKTA (Mn, meaning-bearing)"),
    ("अंक् Live", "अंक Live", "Devanagari VIRAMA (Mn, meaning-bearing)"),
    ("Beyoncé", "Beyonce", "Latin acute"),
])
def test_a_mark_never_merges_two_identities(ours, theirs, what):
    """openai/absence-only, r9. `_fold_run` called every Mn mark "optional", but
    the Devanagari virama and nukta are Mn and carry meaning — `नुक्कड़` and
    `नुक्कड` are different words. Two same-minute listings whose titles differ
    by one of those marks were collapsing to a single identity, which let this
    path write an end_time onto the wrong published event."""
    assert normalize_title(ours) != normalize_title(theirs), what
    assert match_kind(published(title=ours), parsed(title=theirs)) == MATCH_COLLISION


def test_a_mark_difference_at_our_minute_writes_nothing_and_cancels_nothing():
    """The end-to-end consequence: refusing both ways. It cannot rewrite our
    row, and it cannot read our row as absent either — something we cannot
    distinguish from us is holding our start time."""
    d = only(adjudicate_page(
        verdict=VERIFIED_PRESENT,
        published=[published(title="नुक्कड़ Night", end_time=None)],
        parsed=[parsed(title="नुक्कड Night", end_time=DAY + timedelta(hours=4))]
               + bracket(),
        gate_passes=ALWAYS_PASSES, page_text=PAGE_WITHOUT_IT))
    assert d.action == ACTION_NONE
    assert not d.fields


def test_the_two_reductions_disagree_on_purpose():
    """The invariant behind the split, asserted directly: for a pair differing
    only by an optional mark, the absence guard says "still here" while identity
    says "not shown to be the same". Anything that made these agree again would
    reintroduce one of the two defects."""
    from worker import listing_update as lu
    ours, theirs = "Sigur Rós", "Sigur Ros"
    assert lu._reduce(ours, fold_marks=True) == lu._reduce(theirs, fold_marks=True)
    assert lu._reduce(ours, fold_marks=False) != lu._reduce(theirs, fold_marks=False)
    assert lu.title_still_on_page(ours, f"<p>{theirs}</p>") is True
    assert normalize_title(ours) != normalize_title(theirs)
