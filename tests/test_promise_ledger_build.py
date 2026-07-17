"""Build-phase-1 tests (Session Contract #17, renumbered from #8): point-in-time ledger store v0
and the deterministic due-date parser."""

import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ventures.promise_ledger.extract.due_dates import parse_due_dates
from ventures.promise_ledger.schema.claim import (
    Claim, ClaimKind, EntityRef, FulfillmentConfidence, LifecycleEvent,
    LifecycleState, Provenance,
)
from ventures.promise_ledger.store.ledger import Ledger, LedgerIntegrityError

UTC = datetime.timezone.utc


def _prov(retrieved_day):
    return Provenance(
        source_url="https://www.sec.gov/Archives/edgar/data/320193/ex991.htm",
        source_kind="8-K/EX-99.1",
        published_at=datetime.datetime(2026, 7, retrieved_day - 1 or 1, tzinfo=UTC),
        retrieved_at=datetime.datetime(2026, 7, retrieved_day, tzinfo=UTC),
    )


def _claim(claim_id="c-001", retrieved_day=2, **overrides):
    base = dict(
        claim_id=claim_id,
        entity=EntityRef(name="ExampleCorp", cik="0000320193"),
        kind=ClaimKind.NUMERIC_GUIDANCE,
        statement="FY2027 revenue guidance of $1.2B-$1.4B (re-expressed)",
        provenance=_prov(retrieved_day),
        metric="revenue_fy2027", target_low=1200.0, target_high=1400.0,
        unit="USD_millions",
    )
    base.update(overrides)
    return Claim(**base)


# ------------------------------------------------------------------ store

def test_invalid_claim_never_enters_the_ledger():
    led = Ledger()
    bad = _claim(claim_id="   ")
    with pytest.raises(LedgerIntegrityError, match="invalid claim"):
        led.record_claim(bad)
    assert led.events_as_of(datetime.datetime(2030, 1, 1, tzinfo=UTC)) == []


def test_as_of_reads_respect_the_knowledge_horizon():
    led = Ledger()
    led.record_claim(_claim(retrieved_day=2))
    led.record_lifecycle(LifecycleEvent(
        claim_id="c-001", state=LifecycleState.REITERATED,
        confidence=FulfillmentConfidence.LIKELY,
        observed_at=datetime.datetime(2026, 7, 10, tzinfo=UTC),
        recorded_at=datetime.datetime(2026, 7, 10, tzinfo=UTC),
        evidence=(_prov(10),)))
    # As of July 5, only the original claim is knowable.
    before = led.events_as_of(datetime.datetime(2026, 7, 5, tzinfo=UTC))
    assert [e["event_type"] for e in before] == ["claim_recorded"]
    after = led.events_as_of(datetime.datetime(2026, 7, 11, tzinfo=UTC))
    assert [e["event_type"] for e in after] == ["claim_recorded", "lifecycle_event"]


def test_late_discovered_outcome_is_invisible_before_its_discovery():
    """Evaluator r22 — the core point-in-time defect: an outcome OBSERVED in
    the past but DISCOVERED later must not be readable at times between the
    two, or backtests time-travel. The knowledge horizon is recorded_at."""
    led = Ledger()
    led.record_claim(_claim(retrieved_day=2))
    led.record_lifecycle(LifecycleEvent(
        claim_id="c-001", state=LifecycleState.BROKEN,
        confidence=FulfillmentConfidence.LIKELY,
        observed_at=datetime.datetime(2026, 7, 4, tzinfo=UTC),   # happened July 4
        recorded_at=datetime.datetime(2026, 7, 20, tzinfo=UTC),  # learned July 20
        evidence=(_prov(20),)))
    # Between occurrence and discovery: the system could NOT have known.
    mid = led.events_as_of(datetime.datetime(2026, 7, 10, tzinfo=UTC))
    assert [e["event_type"] for e in mid] == ["claim_recorded"]
    assert led.current_state("c-001",
                             datetime.datetime(2026, 7, 10, tzinfo=UTC))["state"] == "made"
    # After discovery it is knowable.
    late = led.events_as_of(datetime.datetime(2026, 7, 21, tzinfo=UTC))
    assert [e["event_type"] for e in late] == ["claim_recorded", "lifecycle_event"]


def test_source_retrieval_is_recordable_and_validated_at_the_door():
    """Evaluator r22: source_retrieved needs a public writer with a payload
    contract — raw-source custody is the third record type, not a stub."""
    led = Ledger()
    seq = led.record_source_retrieval(
        source_url="https://www.sec.gov/Archives/edgar/data/19617/x/ex991.htm",
        sha256="c" * 64, size_bytes=207499,
        retrieved_at=datetime.datetime(2026, 7, 15, 19, 6, tzinfo=UTC),
        entity_key="CIK:0000019617", note="first live run")
    events = led.events_as_of(datetime.datetime(2026, 7, 16, tzinfo=UTC))
    assert [e["event_type"] for e in events] == ["source_retrieved"]
    assert events[0]["payload"]["sha256"] == "c" * 64
    assert events[0]["seq"] == seq
    # Knowledge horizon applies to custody records too.
    assert led.events_as_of(datetime.datetime(2026, 7, 15, tzinfo=UTC)) == []


def test_source_retrieval_rejects_unverifiable_records():
    led = Ledger()
    with pytest.raises(LedgerIntegrityError, match="64 lowercase hex"):
        led.record_source_retrieval(
            source_url="https://www.sec.gov/x.htm", sha256="NOT-A-HASH",
            size_bytes=1, retrieved_at=datetime.datetime(2026, 7, 15, tzinfo=UTC))
    with pytest.raises(LedgerIntegrityError, match="https"):
        led.record_source_retrieval(
            source_url="http://insecure.example/x.htm", sha256="c" * 64,
            size_bytes=1, retrieved_at=datetime.datetime(2026, 7, 15, tzinfo=UTC))
    with pytest.raises(LedgerIntegrityError, match="positive"):
        led.record_source_retrieval(
            source_url="https://www.sec.gov/x.htm", sha256="c" * 64,
            size_bytes=0, retrieved_at=datetime.datetime(2026, 7, 15, tzinfo=UTC))


def test_lifecycle_cannot_be_knowable_before_its_claim():
    """Evaluator r23: a verdict recorded 'earlier' than the claim it judges
    would surface in events_as_of() before the claim exists — state='broken'
    with claim=None. The door rejects it."""
    led = Ledger()
    led.record_claim(_claim(retrieved_day=10))
    ev = LifecycleEvent(claim_id="c-001", state=LifecycleState.REITERATED,
                        confidence=FulfillmentConfidence.LIKELY,
                        observed_at=datetime.datetime(2026, 7, 5, tzinfo=UTC),
                        recorded_at=datetime.datetime(2026, 7, 5, tzinfo=UTC),
                        evidence=(_prov(5),))
    with pytest.raises(LedgerIntegrityError, match="before the claim it judges"):
        led.record_lifecycle(ev)


def test_corrections_stay_within_type_claim_and_time():
    """Evaluator r23: supersedes must target the same event type, the same
    claim, and a record knowable no later than its correction."""
    led = Ledger()
    seq_a = led.record_claim(_claim(retrieved_day=5))
    led.record_claim(_claim(claim_id="c-002", retrieved_day=5))
    # cross-claim correction refused
    with pytest.raises(LedgerIntegrityError, match="within one claim"):
        led.record_claim(_claim(claim_id="c-002", retrieved_day=6), supersedes_seq=seq_a)
    # cross-type correction refused
    ev = LifecycleEvent(claim_id="c-001", state=LifecycleState.REITERATED,
                        confidence=FulfillmentConfidence.LIKELY,
                        observed_at=datetime.datetime(2026, 7, 6, tzinfo=UTC),
                        recorded_at=datetime.datetime(2026, 7, 6, tzinfo=UTC),
                        evidence=(_prov(6),))
    with pytest.raises(LedgerIntegrityError, match="within one event type"):
        led.record_lifecycle(ev, supersedes_seq=seq_a)
    # backdated correction refused: correcting with an EARLIER horizon than
    # the record it corrects claims knowledge we did not have
    with pytest.raises(LedgerIntegrityError, match="cannot be\\s+knowable before"):
        led.record_claim(_claim(retrieved_day=3), supersedes_seq=seq_a)
    # legitimate same-claim, same-type, later-horizon correction still works
    seq_b = led.record_claim(_claim(retrieved_day=7), supersedes_seq=seq_a)
    assert seq_b > seq_a


def test_lifecycle_for_unknown_claim_rejected():
    led = Ledger()
    ev = LifecycleEvent(claim_id="ghost", state=LifecycleState.REITERATED,
                        confidence=FulfillmentConfidence.LIKELY,
                        observed_at=datetime.datetime(2026, 7, 10, tzinfo=UTC),
                        recorded_at=datetime.datetime(2026, 7, 10, tzinfo=UTC),
                        evidence=(_prov(10),))
    with pytest.raises(LedgerIntegrityError, match="unknown claim_id"):
        led.record_lifecycle(ev)


def test_corrections_supersede_but_never_hide():
    led = Ledger()
    seq1 = led.record_claim(_claim(retrieved_day=2, target_high=1300.0))
    led.record_claim(_claim(retrieved_day=3), supersedes_seq=seq1)
    as_of = datetime.datetime(2026, 7, 4, tzinfo=UTC)
    events = led.events_as_of(as_of, claim_id="c-001")
    # BOTH records remain visible in the event listing (shown, never hidden)…
    assert len(events) == 2
    assert events[1]["supersedes_seq"] == seq1
    # …while the projection reports the corrected record as operative.
    state = led.current_state("c-001", as_of)
    assert state["claim"]["target_high"] == 1400.0
    assert state["superseded_events"] == 1


def test_correction_must_reference_an_existing_record():
    led = Ledger()
    with pytest.raises(LedgerIntegrityError, match="does not exist"):
        led.record_claim(_claim(), supersedes_seq=999)


def test_current_state_projection_tracks_lifecycle_and_confidence():
    led = Ledger()
    led.record_claim(_claim(retrieved_day=2))
    led.record_lifecycle(LifecycleEvent(
        claim_id="c-001", state=LifecycleState.BROKEN,
        confidence=FulfillmentConfidence.LIKELY,
        observed_at=datetime.datetime(2027, 10, 1, tzinfo=UTC),
        recorded_at=datetime.datetime(2027, 10, 1, tzinfo=UTC),
        evidence=(_prov(2),)))
    state_before = led.current_state("c-001", datetime.datetime(2026, 8, 1, tzinfo=UTC))
    assert (state_before["state"], state_before["confidence"]) == ("made", "unverified")
    state_after = led.current_state("c-001", datetime.datetime(2027, 11, 1, tzinfo=UTC))
    assert (state_after["state"], state_after["confidence"]) == ("broken", "likely")


def test_store_module_contains_no_update_or_delete_statements():
    """Append-only enforced at review level too: the module must not contain
    UPDATE or DELETE SQL at all."""
    src = (Path(__file__).resolve().parent.parent /
           "ventures/promise_ledger/store/ledger.py").read_text(encoding="utf-8")
    sql = [ln for ln in src.splitlines() if "UPDATE " in ln.upper() or "DELETE " in ln.upper()]
    allowed = [ln for ln in sql if "no UPDATE" in ln or "no DELETE" in ln]
    assert sql == allowed, f"mutating SQL found in append-only store: {sql}"


def test_naive_timestamps_rejected():
    led = Ledger()
    led.record_claim(_claim())
    with pytest.raises(LedgerIntegrityError, match="timezone-aware"):
        led.events_as_of(datetime.datetime(2026, 8, 1))


# ------------------------------------------------------------------ parser

def test_quarter_forms():
    [p2] = parse_due_dates("guidance reaffirmed for Q3 2027 delivery")
    assert p2.due_date == datetime.date(2027, 9, 30)
    assert p2.fiscal is False


def test_fiscal_periods_are_never_resolved_to_calendar_dates():
    """Evaluator r22: issuers' fiscal calendars differ — a guessed calendar
    date for 'fiscal 2027' feeds a false overdue alert (the product's stated
    high-blast-radius failure mode). Fiscal phrases parse to due_date=None
    with the phrase preserved; the claim stays due_date_text-only."""
    [p] = parse_due_dates("expected to launch in the third quarter of fiscal 2027")
    assert p.due_date is None
    assert p.fiscal is True
    assert "third quarter of fiscal 2027" in p.original_text
    [q] = parse_due_dates("targets completion in Q4 FY2028")
    assert q.due_date is None and q.fiscal is True
    [y] = parse_due_dates("to be finished by the end of fiscal 2027")
    assert y.due_date is None and y.fiscal is True


def test_by_month_forms():
    [p] = parse_due_dates("the facility will be operational by March 2028")
    assert p.due_date == datetime.date(2028, 3, 31)
    [p2] = parse_due_dates("submission expected no later than Jul 10, 2027")
    assert p2.due_date == datetime.date(2027, 7, 10)


def test_year_end_form_and_fiscal_flag():
    [p] = parse_due_dates("targeting profitability by the end of fiscal 2028")
    assert p.due_date is None            # fiscal periods are never guessed (r22)
    assert p.fiscal is True
    [c] = parse_due_dates("targeting profitability by the end of 2028")
    assert c.due_date == datetime.date(2028, 12, 31)
    assert c.fiscal is False


def test_half_year_form():
    [p] = parse_due_dates("rollout completing in H1 2028")
    assert p.due_date == datetime.date(2028, 6, 30)


def test_ambiguous_phrases_do_not_parse():
    assert parse_due_dates("we expect meaningful progress soon") == []
    assert parse_due_dates("growth next year") == []          # no year anchor
    assert parse_due_dates("during the quarter") == []        # no year anchor


def test_multiple_deadlines_sorted():
    ps = parse_due_dates("phase one by June 2027 and full rollout in Q4 2028")
    assert [p.due_date for p in ps] == [datetime.date(2027, 6, 30),
                                        datetime.date(2028, 12, 31)]


def test_original_text_always_kept_nonempty():
    for p in parse_due_dates("by January 5, 2027; in Q2 2027; by year-end 2027"):
        assert p.original_text.strip()
