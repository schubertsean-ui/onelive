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


def test_exactly_one_daily_cron():
    crons = _crons()
    assert len(crons) == 1, f"expected exactly one cron, found {len(crons)}: {crons}"
    fields = crons[0].split()
    assert len(fields) == 5, f"malformed cron: {crons[0]!r}"
    minute, hour, dom, month, dow = fields
    # A DAILY cron: a fixed minute and hour, every day/month/day-of-week.
    assert dom == "*" and month == "*" and dow == "*", (
        f"contract assumes a daily cron (day/month/dow '*'); got {crons[0]!r} — "
        "a different cadence must update EXPECTED_PERIOD_SECONDS and this test together")
    assert minute.isdigit() and hour.isdigit(), f"daily cron needs fixed minute+hour: {crons[0]!r}"


def test_declared_period_matches_the_daily_cron():
    m = re.search(r'EXPECTED_PERIOD_SECONDS:\s*"(\d+)"', _WF)
    assert m, "EXPECTED_PERIOD_SECONDS must be declared for the dead-man assertion"
    declared = int(m.group(1))
    # Daily cadence ⇒ 86400 seconds. Bound mechanically so cron and alarm period
    # cannot drift apart silently.
    assert declared == 86400, (
        f"EXPECTED_PERIOD_SECONDS={declared} does not match a daily cron (86400s). "
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
