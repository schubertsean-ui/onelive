"""Structural contract tests for .github/workflows/import_structured.yml.

The couplings that must never drift apart silently (mirroring the ingest.yml
contract, adapted to a DAILY cron rather than every-N-minutes):

1. CADENCE ↔ DECLARED PERIOD: the workflow declares EXPECTED_PERIOD_SECONDS for
   the dead-man assertion. It must equal the period implied by the cron — a daily
   cron ⇒ 86400s. Editing one without the other fails here, in the same PR.
2. DEAD-MAN ASSERTION PRESENT + gated to schedule: the assert_deadman_period.py
   step exists with its four env inputs and only runs on schedule events —
   removing the watchdog is a loud diff, not a quiet edit.
3. SUCCESS/FAIL PINGS present and success-gated: a fresh success ping resets the
   alarm; its absence raises it. So the success ping must be conditioned on
   success(), never unconditional.
"""
import pathlib
import re

_WF = (pathlib.Path(__file__).resolve().parent.parent
       / ".github" / "workflows" / "import_structured.yml").read_text()


def _crons() -> list:
    return re.findall(r'-\s*cron:\s*"([^"]+)"', _WF)


def _fire_hours() -> list:
    """The sorted list of hours the cron fires at, asserting a fixed-minute,
    every-day shape (minute int; day/month/dow '*'; hours a comma list)."""
    crons = _crons()
    assert len(crons) == 1, f"expected exactly one cron, found {len(crons)}: {crons}"
    fields = crons[0].split()
    assert len(fields) == 5, f"malformed cron: {crons[0]!r}"
    minute, hour, dom, month, dow = fields
    assert dom == "*" and month == "*" and dow == "*", (
        f"contract assumes an every-day cron (day/month/dow '*'); got {crons[0]!r} — "
        "a different cadence must update EXPECTED_PERIOD_SECONDS and this test together")
    assert minute.isdigit(), f"cron needs a fixed minute: {crons[0]!r}"
    hours = sorted(int(h) for h in hour.split(","))
    assert all(0 <= h <= 23 for h in hours), f"bad hours in cron: {crons[0]!r}"
    return hours


def test_fires_are_evenly_spaced_within_the_day():
    hours = _fire_hours()
    assert len(hours) >= 1
    # Evenly-spaced fires so a single dead-man period can represent the cadence
    # (the ingest contract enforces the same for its minute-spaced cron).
    spacings = {(b - a) % 24 for a, b in zip(hours, hours[1:])}
    spacings.add((hours[0] + 24 - hours[-1]) % 24)
    assert len(spacings) == 1, (
        f"cron fire-hours {hours} are unevenly spaced — a single dead-man period "
        "cannot represent a variable cadence")


def test_declared_period_matches_the_cron_cadence():
    m = re.search(r'EXPECTED_PERIOD_SECONDS:\s*"(\d+)"', _WF)
    assert m, "EXPECTED_PERIOD_SECONDS must be declared for the dead-man assertion"
    declared = int(m.group(1))
    # Period is derived from the fire count: N evenly-spaced fires/day ⇒ 86400/N.
    # (1 fire ⇒ 86400 daily; 2 fires ⇒ 43200 twice-daily.) Bound mechanically so
    # the cron and the alarm period cannot drift apart silently.
    expected = 86400 // len(_fire_hours())
    assert declared == expected, (
        f"EXPECTED_PERIOD_SECONDS={declared} does not match the cron's "
        f"{len(_fire_hours())} fires/day (expected {expected}s). "
        "Change the cron and this declaration together.")


def test_deadman_assertion_step_present_with_all_env_and_schedule_gated():
    # The four env inputs the assert step needs.
    for key in ("ORCHESTRATOR_PING_URL", "HEALTHCHECKS_API_KEY_RO",
                "DEADMAN_CHECK_SLUG", "EXPECTED_PERIOD_SECONDS", "MAX_GRACE_SECONDS"):
        assert key in _WF, f"dead-man assert step missing env {key}"
    assert "tools/assert_deadman_period.py" in _WF, "assert_deadman_period step removed"
    assert 'DEADMAN_CHECK_SLUG: "onelive-structured-import"' in _WF, (
        "the dead-man check must be DECLARED by its slug next to the cron")
    # The assertion must be gated to schedule events (manual dispatch is human-watched).
    assert re.search(
        r"Assert dead-man period[\s\S]{0,800}?if:\s*github\.event_name == 'schedule'",
        _WF), "the dead-man assertion must be gated to schedule events"


def test_success_ping_is_conditioned_on_success():
    # The load-bearing ping must only fire on success — an unconditional success
    # ping would reset the alarm even when the run failed (defeating the watchdog).
    assert re.search(
        r"Dead-man SUCCESS ping[\s\S]{0,300}?if:\s*\$\{\{\s*github\.event_name == 'schedule' && success\(\)",
        _WF), "the SUCCESS ping must be conditioned on schedule && success()"


def test_import_step_still_bounded_and_no_ai():
    # The dead-man wiring must not have disturbed the deterministic import: the
    # bound is still required and the runner is the structured (no-AI) importer.
    assert "run_structured_import --limit" in _WF
    # The AI ingest loop must never be INVOKED here (the header comment may name
    # run_once.py to say it does NOT run it — so check the run: invocation, not
    # the mere presence of the string).
    assert not re.search(r"python[0-9 ]*\S*\brun_once\.py\b", _WF), (
        "import-structured must NOT invoke the AI ingest loop (run_once.py)")


def test_every_limit_binding_supplies_a_value_on_a_schedule_event():
    """The scheduled-import fetch-bound bug, and this is the test that was
    missing rather than the guard.

    The workflow declares a twice-daily schedule, and each step that needs the
    fetch bound also fails CLOSED when it is empty. Both halves were correct;
    the WIRING between them was not. A `schedule` event carries no `inputs`
    context at all, so `${{ github.event.inputs.limit }}` expands to the empty
    string, the `:?` guard fires, and the scheduled import could never run — it
    never once did. The pre-existing tests all passed throughout, because they
    asserted the guard EXISTED (what the workflow contains) and never that the
    schedule branch DECIDES a value (what the branch does) — the
    `untested-gate-branch` class exactly.

    So this asserts the decision, per binding, not the presence of a default
    anywhere: every env binding of LIMIT must key on `github.event_name` and
    offer a non-empty literal on the schedule side. A future step that reads
    inputs.limit raw fails here rather than silently killing the cron again.
    """
    bindings = re.findall(r"^\s*LIMIT:\s*(.+)$", _WF, re.MULTILINE)
    assert bindings, "no LIMIT env binding found — the fetch bound must be wired"
    for b in bindings:
        assert "github.event_name" in b, (
            f"LIMIT binding {b!r} does not key on github.event_name — on a "
            "schedule event `inputs` does not exist, so this expands to empty "
            "and the fail-closed guard kills every scheduled run")
        literal = re.search(r"github\.event_name\s*==\s*'schedule'\s*&&\s*'(\d+)'", b)
        assert literal, (
            f"LIMIT binding {b!r} has no quoted integer literal on the "
            "schedule side of the ternary")
        assert int(literal.group(1)) >= 1, (
            f"LIMIT binding {b!r} offers {literal.group(1)!r} on the schedule "
            "side; the guard rejects 0, so that is still a dead cron")


def test_scheduled_fetch_bound_matches_the_declared_dispatch_default():
    """The scheduled bound and the dispatch input's own default must agree, so a
    scheduled run and a hand-run run fetch the same breadth. Drifting them would
    make the cron's real coverage differ from the documented one with nothing
    saying so."""
    declared = re.search(r"limit:\s*\n\s*description:[^\n]*\n\s*required:\s*true\s*\n\s*default:\s*\"(\d+)\"", _WF)
    assert declared, "the dispatch `limit` input must declare a quoted integer default"
    scheduled = set(re.findall(r"github\.event_name\s*==\s*'schedule'\s*&&\s*'(\d+)'", _WF))
    assert scheduled == {declared.group(1)}, (
        f"scheduled bound(s) {sorted(scheduled)} disagree with the dispatch "
        f"default {declared.group(1)!r} — change both together")
