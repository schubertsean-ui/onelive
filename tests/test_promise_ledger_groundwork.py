"""Promise-ledger groundwork tests (Session Contract #7).

Covers the three pre-build artifacts: Claim Schema v0 (validation + JSON
Schema lockstep), the fail-closed golden-set harness (including the rule that
a synthetic-only golden set can never PASS — R-014), and the EDGAR client's
contract enforcement (declared identity, budget, CIK padding) — all without
network access, which this sandbox does not have to sec.gov.
"""

import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ventures.promise_ledger.eval import golden
from ventures.promise_ledger.ingest import edgar
from ventures.promise_ledger.schema import claim as claim_schema
from ventures.promise_ledger.schema.claim import (
    Claim, ClaimKind, EntityRef, FulfillmentConfidence, LifecycleEvent,
    LifecycleState, Provenance, to_json_schema, validate,
)

UTC = datetime.timezone.utc


def _provenance(published=None, retrieved=None):
    return Provenance(
        source_url="https://www.sec.gov/Archives/edgar/data/0000000000/ex991.htm",
        source_kind="8-K/EX-99.1",
        published_at=published or datetime.datetime(2026, 7, 1, tzinfo=UTC),
        retrieved_at=retrieved or datetime.datetime(2026, 7, 2, tzinfo=UTC),
    )


def _claim(**overrides):
    base = dict(
        claim_id="c-001",
        entity=EntityRef(name="ExampleCorp", cik="0000000000"),
        kind=ClaimKind.NUMERIC_GUIDANCE,
        statement="FY2027 revenue guidance of $1.2B-$1.4B (re-expressed)",
        provenance=_provenance(),
        metric="revenue_fy2027",
        target_low=1200.0,
        target_high=1400.0,
        unit="USD_millions",
    )
    base.update(overrides)
    return Claim(**base)


# ------------------------------------------------------------ schema

def test_valid_claim_passes():
    assert validate(_claim()) == []


def test_entity_requires_stable_identifier():
    errs = validate(_claim(entity=EntityRef(name="ExampleCorp")))
    assert any("stable identifier" in e for e in errs)


def test_lei_and_cik_formats_enforced():
    assert any("LEI" in e for e in validate(_claim(entity=EntityRef(name="X", lei="short"))))
    assert any("zero-padded" in e for e in validate(_claim(entity=EntityRef(name="X", cik="320193"))))


def test_time_incoherent_provenance_rejected():
    p = _provenance(published=datetime.datetime(2026, 7, 3, tzinfo=UTC),
                    retrieved=datetime.datetime(2026, 7, 2, tzinfo=UTC))
    assert any("time-incoherent" in e for e in validate(_claim(provenance=p)))


def test_numeric_guidance_requires_metric_and_bounds():
    errs = validate(_claim(metric=None, target_low=None, target_high=None))
    assert any("numeric_guidance requires" in e for e in errs)


def test_inverted_target_bounds_rejected():
    errs = validate(_claim(target_low=1400.0, target_high=1200.0))
    assert any("target_low exceeds target_high" in e for e in errs)


def test_parsed_due_date_must_keep_original_text():
    c = _claim(kind=ClaimKind.DATED_EVENT, metric=None, target_low=None, target_high=None,
               due_date=datetime.date(2027, 9, 30), due_date_text=None)
    assert any("due_date_text" in e for e in validate(c))


def test_verdict_without_evidence_rejected():
    ev = LifecycleEvent(claim_id="c-001", state=LifecycleState.BROKEN,
                        confidence=FulfillmentConfidence.LIKELY,
                        observed_at=datetime.datetime(2027, 10, 1, tzinfo=UTC))
    errs = validate(ev)
    assert any("requires evidence" in e for e in errs)


def test_verdict_with_evidence_passes():
    ev = LifecycleEvent(claim_id="c-001", state=LifecycleState.BROKEN,
                        confidence=FulfillmentConfidence.LIKELY,
                        observed_at=datetime.datetime(2027, 10, 1, tzinfo=UTC),
                        evidence=(_provenance(),))
    assert validate(ev) == []


def test_silently_dropped_is_a_first_class_state():
    assert LifecycleState.SILENTLY_DROPPED.value == "silently_dropped"


def test_fulfillment_confidence_is_the_4_state_model():
    assert {m.value for m in FulfillmentConfidence} == {"unverified", "likely", "confirmed", "disputed"}


def test_json_schema_lockstep_with_dataclass():
    schema = to_json_schema()
    schema_props = set(schema["properties"])
    dc_fields = claim_schema.dataclass_field_names(Claim)
    assert schema_props == dc_fields, (
        f"JSON Schema and Claim dataclass drifted: only-in-schema={schema_props - dc_fields}, "
        f"only-in-dataclass={dc_fields - schema_props}")
    assert set(schema["$defs"]["lifecycle_state"]["enum"]) == {m.value for m in LifecycleState}


# ------------------------------------------------------------ golden harness

def test_golden_set_loads_and_synthetic_flags_are_explicit():
    examples = golden.load_examples()
    assert examples, "committed golden set must not be empty"
    assert all(isinstance(ex["synthetic"], bool) for ex in examples)


def test_empty_golden_set_fails_closed(tmp_path):
    with pytest.raises(golden.GoldenSetError, match="EMPTY"):
        golden.load_examples(tmp_path)


def test_perfect_predictions_on_synthetic_set_still_cannot_pass():
    """R-014 mechanically enforced: synthetic-only golden sets exercise the
    harness but can never bless an extractor."""
    examples = golden.load_examples()
    perfect = {ex["example_id"]: [dict(kind=l["kind"], **l["match_keys"]) for l in ex["labels"]]
               for ex in examples}
    report = golden.score(examples, perfect)
    assert report["precision"] == 1.0 and report["recall"] == 1.0
    ok, text = golden.verdict(report)
    assert not ok and "SYNTHETIC-ONLY" in text and "FAIL" in text


def test_wrong_predictions_score_below_bar():
    examples = golden.load_examples()
    wrong = {ex["example_id"]: [{"kind": "numeric_guidance", "metric": "nonsense"}]
             for ex in examples}
    report = golden.score(examples, wrong)
    assert report["precision"] < golden.PRECISION_BAR
    ok, _ = golden.verdict(report)
    assert not ok


# ------------------------------------------------------------ EDGAR client

def test_undeclared_client_refused():
    with pytest.raises(ValueError, match="fair-access"):
        edgar.EdgarClient(operator_name="", admin_email="not-an-email")


def test_cik_padding_enforced():
    c = edgar.EdgarClient(operator_name="OneLive Research", admin_email="admin@example.com")
    with pytest.raises(ValueError, match="zero-padded"):
        c.submissions_url("320193")
    assert c.submissions_url("0000320193").endswith("CIK0000320193.json")


def test_local_budget_stays_under_sec_cap():
    c = edgar.EdgarClient(operator_name="OneLive Research", admin_email="admin@example.com")
    # Simulate a burst within one second at a fixed clock: the first
    # LOCAL_MAX_REQUESTS_PER_SECOND calls need no delay; the next must wait.
    t0 = 1000.0
    delays = [c._respect_budget(now=t0 + i * 0.01) for i in range(edgar.LOCAL_MAX_REQUESTS_PER_SECOND + 1)]
    assert all(d == 0.0 for d in delays[:-1])
    assert delays[-1] > 0.0
    assert edgar.LOCAL_MAX_REQUESTS_PER_SECOND < 10, "local budget must stay under the SEC cap"


def test_extract_8k_docs_from_documented_shape():
    # Synthetic fixture mirroring the DOCUMENTED data.sec.gov submissions shape
    # (real fetch blocked from this sandbox — R-014).
    fixture = {
        "filings": {"recent": {
            "form": ["8-K", "10-Q", "8-K"],
            "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002", "0000000000-26-000003"],
            "filingDate": ["2026-07-01", "2026-06-15", "2026-05-01"],
            "primaryDocument": ["ex991.htm", "q.htm", "er.htm"],
            "items": ["2.02,9.01", "", "7.01"],
        }}
    }
    docs = edgar.extract_8k_press_release_docs(fixture)
    assert [d["accession"] for d in docs] == ["0000000000-26-000001", "0000000000-26-000003"]
    assert docs[0]["items"] == "2.02,9.01"
