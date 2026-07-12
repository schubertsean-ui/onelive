"""Finding 4: promotion re-checks the FULL three-way trust gate, not just the
2-way source-count gate. worker.promote.assert_promotable is the shared guard
promote_candidate runs immediately before inserting into the canonical `event`
table; these hermetic tests prove it refuses anything that is not a real PASS,
so no database is required to verify the publish-time invariant.
"""
import pytest

from worker.promote import assert_promotable


def _call(**kw):
    base = dict(source_classes=["ticketing"], sxsw_mode=False, extracted={},
               evidence_signals={"start_times": [], "dedupe_ambiguous": False})
    base.update(kw)
    return assert_promotable(**base)


def test_clean_anchor_passes():
    verdict = _call()
    assert verdict.decision.value == "pass"


def test_two_non_anchor_sources_pass():
    verdict = _call(source_classes=["social", "local_media"])
    assert verdict.decision.value == "pass"


def test_insufficient_corroboration_is_refused_as_hold():
    with pytest.raises(ValueError) as exc:
        _call(source_classes=["social"])
    assert "did not PASS" in str(exc.value)
    assert "hold" in str(exc.value).lower()


def test_private_rsvp_is_refused_even_with_anchor():
    with pytest.raises(ValueError) as exc:
        _call(extracted={"is_private_rsvp": True})
    assert "escalate" in str(exc.value).lower()
    assert "private" in str(exc.value).lower()


def test_validation_error_provenance_is_refused():
    with pytest.raises(ValueError) as exc:
        _call(extracted={"_provenance": {"validation_error": True}})
    assert "validation_error" in str(exc.value)


def test_conflicting_start_times_are_refused():
    with pytest.raises(ValueError) as exc:
        _call(evidence_signals={"start_times": ["2026-07-11T20:00:00", "2026-07-11T21:30:00"]})
    assert "conflicting start_time" in str(exc.value)


def test_dedupe_ambiguity_is_refused():
    with pytest.raises(ValueError) as exc:
        _call(evidence_signals={"start_times": [], "dedupe_ambiguous": True})
    assert "dedupe" in str(exc.value).lower()


def test_promote_candidate_uses_the_guard():
    # Structural: promote_candidate must call assert_promotable so the publish
    # path cannot regress to a bare 2-way count check.
    import ast

    import worker.promote as promote

    tree = ast.parse(open(promote.__file__).read())
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "assert_promotable" in calls
