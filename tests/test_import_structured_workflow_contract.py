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
