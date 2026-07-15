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


def test_json_schema_carries_the_validator_invariants():
    """The exported interchange schema must not be fail-open relative to the
    Python validator (evaluator r17): each trust invariant the validator
    enforces must appear as a schema construct, and the one invariant JSON
    Schema cannot express must be declared, not silent."""
    schema = to_json_schema()
    # entity requires at least one stable identifier
    entity_anyof = schema["properties"]["entity"]["anyOf"]
    assert {"lei"} in [set(alt.get("required", [])) for alt in entity_anyof]
    assert {"cik"} in [set(alt.get("required", [])) for alt in entity_anyof]
    # conditional requirements mirror Claim.validate
    conds = schema["allOf"]
    ng = next(c for c in conds
              if c.get("if", {}).get("properties", {}).get("kind", {}).get("const") == "numeric_guidance")
    assert "metric" in ng["then"]["required"]
    assert any("target_low" in alt.get("required", []) or "target_high" in alt.get("required", [])
               for alt in ng["then"]["anyOf"])
    de = next(c for c in conds
              if c.get("if", {}).get("properties", {}).get("kind", {}).get("const") == "dated_event")
    assert any("due_date" in alt.get("required", []) or "due_date_text" in alt.get("required", [])
               for alt in de["then"]["anyOf"])
    dd = next(c for c in conds if c.get("if", {}).get("required") == ["due_date"])
    assert dd["then"]["required"] == ["due_date_text"]
    # the inexpressible invariant is declared loudly for consumers
    assert any("published_at" in inv and "retrieved_at" in inv for inv in schema["x-invariants"])
    assert "published_at <= provenance.retrieved_at" in schema["description"] or \
           "published_at <= " in schema["description"]
    # stable namespace, not a placeholder domain
    assert ".example/" not in schema["$id"]


# ---------------------------------------------------- schema parity (r21)
# A minimal internal JSON Schema checker (subset: type/required/properties/
# additionalProperties/pattern/minLength/enum/const/anyOf/allOf-if-then/
# items/minItems) so parity is proven against the EXPORTED SCHEMA ITSELF,
# not against its structure — without adding a dependency. Format keywords
# are ignored (annotation-only in JSON Schema 2020-12 by default).

def _check(instance, schema) -> bool:
    import re as _re
    if "const" in schema:
        return instance == schema["const"]
    if "enum" in schema:
        return instance in schema["enum"]
    types = schema.get("type")
    if types is not None:
        tl = types if isinstance(types, list) else [types]
        ok = any(
            (t == "null" and instance is None) or
            (t == "string" and isinstance(instance, str)) or
            (t == "number" and isinstance(instance, (int, float)) and not isinstance(instance, bool)) or
            (t == "object" and isinstance(instance, dict)) or
            (t == "array" and isinstance(instance, list))
            for t in tl)
        if not ok:
            return False
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            return False
        if "pattern" in schema and not _re.search(schema["pattern"], instance):
            return False
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                return False
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            if set(instance) - set(props):
                return False
        for k, sub in props.items():
            if k in instance and not _check(instance[k], sub):
                return False
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            return False
        if "items" in schema and not all(_check(i, schema["items"]) for i in instance):
            return False
    for branchset in schema.get("anyOf", []) and [schema["anyOf"]] or []:
        if not any(_check(instance, alt) for alt in branchset):
            return False
    for cond in schema.get("allOf", []):
        if "if" in cond:
            if _check(instance, cond["if"]) and not _check(instance, cond.get("then", {})):
                return False
        elif not _check(instance, cond):
            return False
    return True


def _valid_claim_dict():
    return {
        "claim_id": "c-001",
        "entity": {"name": "ExampleCorp", "cik": "0000000000"},
        "kind": "numeric_guidance",
        "statement": "FY2027 revenue guidance of $1.2B-$1.4B (re-expressed)",
        "provenance": {"source_url": "https://www.sec.gov/x.htm", "source_kind": "8-K/EX-99.1",
                       "published_at": "2026-07-01T00:00:00Z", "retrieved_at": "2026-07-02T00:00:00Z"},
        "metric": "revenue_fy2027", "target_low": 1200.0, "target_high": 1400.0,
        "unit": "USD_millions",
    }


def test_mini_checker_accepts_the_valid_document():
    assert _check(_valid_claim_dict(), to_json_schema())


@pytest.mark.parametrize("mutate,desc", [
    (lambda d: d["entity"].pop("cik"), "no stable identifier at all"),
    (lambda d: d["entity"].update(cik=None), "present-but-NULL cik must not satisfy anyOf"),
    (lambda d: d["entity"].update(cik=None, lei=None), "both identifiers null"),
    (lambda d: d.update(claim_id="   "), "whitespace-only claim_id"),
    (lambda d: d["entity"].update(name="  "), "whitespace-only entity name"),
    (lambda d: d.update(statement=" "), "whitespace-only statement"),
    (lambda d: d["provenance"].update(source_kind="  "), "whitespace-only source_kind"),
    (lambda d: d.update(metric="   "), "whitespace-only metric for numeric_guidance"),
    (lambda d: d.update(unit="  "), "whitespace-only unit for numeric_guidance"),
    (lambda d: d.update(unit=None), "missing unit for numeric_guidance"),
], ids=lambda x: x if isinstance(x, str) else "")
def test_exported_schema_rejects_what_the_validator_rejects(mutate, desc):
    """Evaluator r21 blockers, proven against the exported schema itself:
    nullable identifiers, whitespace-only required strings, unit parity."""
    doc = _valid_claim_dict()
    mutate(doc)
    assert not _check(doc, to_json_schema()), desc


def test_exported_schema_rejects_dateless_dated_event():
    doc = _valid_claim_dict()
    doc.update(kind="dated_event", metric=None, target_low=None, target_high=None, unit=None)
    doc["due_date_text"] = ""
    assert not _check(doc, to_json_schema()), "empty due_date_text passed the dated_event conditional"
    doc["due_date_text"] = "   "
    assert not _check(doc, to_json_schema()), "whitespace due_date_text passed"
    doc["due_date_text"] = "by Q3 2027"
    assert _check(doc, to_json_schema()), "legitimate dated_event rejected"


def test_exported_lifecycle_schema_rejects_empty_object_evidence():
    doc = {"claim_id": "c-001", "state": "broken", "confidence": "likely",
           "observed_at": "2027-10-01T00:00:00Z", "evidence": [{}]}
    assert not _check(doc, claim_schema.to_lifecycle_event_json_schema())
    doc["evidence"] = [{"source_url": "https://x.gov/a.htm", "source_kind": "8-K",
                        "published_at": "2027-09-30T00:00:00Z",
                        "retrieved_at": "2027-10-01T00:00:00Z"}]
    assert _check(doc, claim_schema.to_lifecycle_event_json_schema())


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
    def realize(label):
        pred = {"kind": label["kind"]}
        for k, v in label["match_keys"].items():
            if k == "statement_substring":
                pred["statement"] = f"...{v}..."
            else:
                pred[k] = v
        return pred
    perfect = {ex["example_id"]: [realize(l) for l in ex["labels"]] for ex in examples}
    report = golden.score(examples, perfect)
    assert report["precision"] == 1.0 and report["recall"] == 1.0
    ok, text = golden.verdict(report)
    assert not ok and "SYNTHETIC-ONLY" in text and "FAIL" in text


def test_vacuous_kind_only_predictions_do_not_match():
    """Evaluator r17: a prediction that names only the kind (no discriminative
    content) must not count as a match."""
    examples = golden.load_examples()
    vacuous = {ex["example_id"]: [{"kind": l["kind"]} for l in ex["labels"]]
               for ex in examples}
    report = golden.score(examples, vacuous)
    assert report["recall"] == 0.0, "kind-only predictions matched labels — vacuous-match hole"


def test_all_null_match_keys_refused_at_load(tmp_path):
    bad = {"example_id": "x", "synthetic": True, "source_text": "SYNTHETIC: t",
           "labels": [{"kind": "qualitative_commitment", "match_keys": {"metric": None}}]}
    import json as _json
    (tmp_path / "bad.json").write_text(_json.dumps(bad), encoding="utf-8")
    with pytest.raises(golden.GoldenSetError, match="discriminative"):
        golden.load_examples(tmp_path)


def test_statement_substring_matching_is_case_insensitive_and_required():
    examples = [{"example_id": "e", "synthetic": True, "source_text": "SYNTHETIC: t",
                 "labels": [{"kind": "capability_assertion",
                             "match_keys": {"statement_substring": "Fully Autonomous"}}]}]
    hit = {"e": [{"kind": "capability_assertion", "statement": "claims product is fully autonomous AI"}]}
    miss = {"e": [{"kind": "capability_assertion", "statement": "claims something else"}]}
    assert golden.score(examples, hit)["recall"] == 1.0
    assert golden.score(examples, miss)["recall"] == 0.0


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


def test_stage1_lists_8k_filings_not_press_releases():
    # Synthetic fixture mirroring the DOCUMENTED data.sec.gov submissions shape
    # (real fetch blocked from this sandbox — R-014). Note: primaryDocument is
    # the 8-K itself, NOT the press-release exhibit — stage 1 must not claim
    # otherwise (evaluator r17).
    fixture = {
        "filings": {"recent": {
            "form": ["8-K", "10-Q", "8-K"],
            "accessionNumber": ["0000000000-26-000001", "0000000000-26-000002", "0000000000-26-000003"],
            "filingDate": ["2026-07-01", "2026-06-15", "2026-05-01"],
            "primaryDocument": ["form8k.htm", "q.htm", "form8k2.htm"],
            "items": ["2.02,9.01", "", "5.02"],
        }}
    }
    docs = edgar.list_recent_8k_filings(fixture)
    assert [d["accession"] for d in docs] == ["0000000000-26-000001", "0000000000-26-000003"]
    assert docs[0]["items"] == "2.02,9.01"


def test_stage2_filing_index_url_shape():
    assert edgar.filing_index_url("0000320193", "0000320193-26-000001") == \
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/index.json"
    with pytest.raises(ValueError, match="zero-padded"):
        edgar.filing_index_url("320193", "0000320193-26-000001")


def test_stage2_finds_ex99_exhibits_with_honest_confidence():
    # index.json directory shape per SEC Archives; exhibit typing is NOT in
    # index.json, so confidence is capped at "likely" and requires a
    # press-release item code on the parent filing.
    index_json = {"directory": {"item": [
        {"name": "form8k.htm"},
        {"name": "ex991.htm"},
        {"name": "ex99-2.txt"},
        {"name": "graphic.jpg"},
    ]}}
    with_pr_item = {"items": "2.02,9.01"}
    without_pr_item = {"items": "5.02"}
    hits = edgar.find_press_release_exhibit_candidates(index_json, with_pr_item)
    assert [h["document"] for h in hits] == ["ex991.htm", "ex99-2.txt"]
    assert all(h["confidence"] == "likely" for h in hits)
    assert all(h["confidence"] != "confirmed" for h in hits), "confidence must cap below confirmed"
    hits2 = edgar.find_press_release_exhibit_candidates(index_json, without_pr_item)
    assert all(h["confidence"] == "unverified" for h in hits2)


def test_stage2_finds_filing_agent_generated_names():
    """Evaluator r18: EDGAR archives commonly use filing-agent generated names
    like d123456dex991.htm with no separator before 'ex99' — those are real
    press-release exhibits and must not be silently dropped."""
    index_json = {"directory": {"item": [
        {"name": "d123456dex991.htm"},
        {"name": "d99022dex992.txt"},
        {"name": "d123456d8k.htm"},
    ]}}
    hits = edgar.find_press_release_exhibit_candidates(index_json, {"items": "2.02"})
    assert [h["document"] for h in hits] == ["d123456dex991.htm", "d99022dex992.txt"]


def test_lifecycle_event_json_schema_requires_evidence_for_all_events():
    """Evaluator r20: EVERY lifecycle event is a sourced assertion — evidence
    is a required, non-empty field for all states, not only verdicts."""
    schema = claim_schema.to_lifecycle_event_json_schema()
    assert set(schema["properties"]["state"]["enum"]) == {m.value for m in LifecycleState}
    assert "evidence" in schema["required"]
    assert schema["properties"]["evidence"]["minItems"] == 1
    assert ".example/" not in schema["$id"]


def test_lifecycle_evidence_items_are_full_provenance_not_empty_objects():
    """Evaluator r19: [{}] must not validate as evidence — evidence items are
    Provenance records with required source/timestamps."""
    schema = claim_schema.to_lifecycle_event_json_schema()
    items = schema["properties"]["evidence"]["items"]
    assert set(items["required"]) >= {"source_url", "source_kind",
                                      "published_at", "retrieved_at"}
    assert items["additionalProperties"] is False
    assert any("published_at" in inv for inv in schema["x-invariants"])


def test_non_verdict_lifecycle_events_also_require_evidence():
    """Evaluator r20: a withdrawal/modification without source evidence is an
    unsupported mutation of an append-only trust ledger."""
    for state in (LifecycleState.WITHDRAWN, LifecycleState.MODIFIED,
                  LifecycleState.REITERATED, LifecycleState.EXPIRED_UNRESOLVED):
        ev = LifecycleEvent(claim_id="c-001", state=state,
                            confidence=FulfillmentConfidence.LIKELY,
                            observed_at=datetime.datetime(2027, 10, 1, tzinfo=UTC))
        assert any("requires evidence" in e for e in validate(ev)), state
        with_ev = LifecycleEvent(claim_id="c-001", state=state,
                                 confidence=FulfillmentConfidence.LIKELY,
                                 observed_at=datetime.datetime(2027, 10, 1, tzinfo=UTC),
                                 evidence=(_provenance(),))
        assert validate(with_ev) == [], state


def test_dated_event_rejects_empty_due_date_text():
    """Evaluator r20: a dated event whose only date is an empty string is a
    false trust record."""
    c = _claim(kind=ClaimKind.DATED_EVENT, metric=None, target_low=None, target_high=None,
               unit=None, due_date=None, due_date_text="")
    assert any("non-empty due_date_text" in e for e in validate(c))
    c2 = _claim(kind=ClaimKind.DATED_EVENT, metric=None, target_low=None, target_high=None,
                unit=None, due_date=datetime.date(2027, 9, 30), due_date_text="   ")
    assert any("non-empty due_date_text" in e for e in validate(c2))


def test_numeric_guidance_requires_unit():
    errs = validate(_claim(unit=None))
    assert any("requires a unit" in e for e in errs)
    schema = to_json_schema()
    ng = next(c for c in schema["allOf"]
              if c.get("if", {}).get("properties", {}).get("kind", {}).get("const") == "numeric_guidance")
    assert "unit" in ng["then"]["required"]


def test_pdf_exhibits_are_candidates():
    """Evaluator r20: EX-99 press releases are also filed as PDFs — dropping
    them is silent recall loss."""
    index_json = {"directory": {"item": [{"name": "ex991.pdf"}, {"name": "logo.jpg"}]}}
    hits = edgar.find_press_release_exhibit_candidates(index_json, {"items": "2.02"})
    assert [h["document"] for h in hits] == ["ex991.pdf"]


def test_claim_schema_declares_target_bounds_invariant():
    """Evaluator r19: target_low <= target_high is cross-field and
    inexpressible in JSON Schema — it must be DECLARED, not silent."""
    schema = to_json_schema()
    assert any("target_low <= target_high" in inv for inv in schema["x-invariants"])


def test_numeric_guidance_rejects_whitespace_metric():
    errs = validate(_claim(metric="   "))
    assert any("numeric_guidance requires" in e for e in errs)


def test_duplicate_example_ids_refused(tmp_path):
    import json as _json
    ex = {"example_id": "dup", "synthetic": True, "source_text": "SYNTHETIC: t",
          "labels": [{"kind": "capability_assertion",
                      "match_keys": {"statement_substring": "x"}}]}
    (tmp_path / "a.json").write_text(_json.dumps(ex), encoding="utf-8")
    (tmp_path / "b.json").write_text(_json.dumps(ex), encoding="utf-8")
    with pytest.raises(golden.GoldenSetError, match="duplicate example_id"):
        golden.load_examples(tmp_path)


def test_email_shape_requires_domain_dot():
    with pytest.raises(ValueError, match="fair-access"):
        edgar.EdgarClient(operator_name="OneLive Research", admin_email="x@y")


def test_empty_statement_substring_refused_at_load(tmp_path):
    import json as _json
    bad = {"example_id": "x", "synthetic": True, "source_text": "SYNTHETIC: t",
           "labels": [{"kind": "capability_assertion",
                       "match_keys": {"statement_substring": ""}}]}
    (tmp_path / "bad.json").write_text(_json.dumps(bad), encoding="utf-8")
    with pytest.raises(golden.GoldenSetError):
        golden.load_examples(tmp_path)


def test_stage2_ignores_non_document_files_and_non_ex99_names():
    index_json = {"directory": {"item": [{"name": "pressrelease.htm"}, {"name": "ex101.htm"}]}}
    assert edgar.find_press_release_exhibit_candidates(index_json, {"items": "2.02"}) == []
