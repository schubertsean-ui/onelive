"""The R-083 one-way door is enforced in CODE, not only in the Record.

Evaluator finding on the consolidated head: backfill-dates.yml holds
production DB credentials and is dispatchable by hand, while the HARD STOP
that must precede a `real=true` run lived only in docs/RECORD.md. A hard stop
that a human has to remember is not a hard stop.
"""
import pytest

from worker.backfill_datetime_resolution import (
    BackfillPreconditionError,
    assert_safe_to_write,
)


def test_real_writes_are_refused_while_the_gate_bug_stands():
    """R-084(a) is unfixed on this checkout, so the probe must refuse. The
    check is BEHAVIOURAL — it asks the real gate — so it cannot drift from
    the code it describes the way a flag could."""
    with pytest.raises(BackfillPreconditionError) as exc:
        assert_safe_to_write()
    msg = str(exc.value)
    assert "REFUSING --real" in msg
    # The refusal must say WHY and where the ordering is written down.
    assert "R-085" in msg or "R-084" in msg
    assert "PATH_TO_THOUSANDS" in msg


def test_the_probe_asks_the_real_gate_not_a_copy():
    """If someone 'fixes' the precondition by editing a constant while the gate
    still conflicts, this test still fails — which is the point."""
    from worker.trust_gate3 import _has_conflicting_start_time
    assert _has_conflicting_start_time(
        {"start_times": ["2026-08-08T19:30:00+00:00", "2026-08-08T19:30:00"]}
    ), ("the gate no longer treats one instant written two ways as a "
        "conflict — R-084(a) appears fixed, so update this test AND flip the "
        "backfill's remaining precondition deliberately, not incidentally")
