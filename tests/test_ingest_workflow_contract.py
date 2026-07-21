"""Structural contract tests for .github/workflows/ingest.yml (PR #43).

Three mechanical couplings that must never drift apart silently:

1. CADENCE ↔ DECLARED PERIOD: EXPECTED_PERIOD_SECONDS (fed to the
   dead-man assertion step) is recomputed HERE from the cron expression's
   minute list — evenly spaced minutes, spacing * 60 == declared period.
   Editing the cron without the declaration (or vice versa) fails this
   suite in the same PR (r9/r11 — alarm config must be mechanical).

2. BUDGET EXPRESSION: the schedule-only ceiling fallback
   (`github.event_name == 'schedule' && '10' || ...max_sources`) appears
   EXACTLY twice — the validation step and the run step — and the bare
   fail-open form (`inputs.max_sources || '10'`) appears nowhere. Pins
   the r1 finding (empty manual dispatch must fail loud) structurally.

3. DEAD-MAN ASSERTION PRESENT: the assert_deadman_period.py step exists
   with all four env inputs — removing the watchdog gate is a reviewable
   loud diff here, not a quiet workflow edit.
"""
import pathlib
import re

_WF = (pathlib.Path(__file__).resolve().parent.parent
       / ".github" / "workflows" / "ingest.yml").read_text()

_SCHEDULE_EXPR = ("${{ github.event_name == 'schedule' && '10' || "
                  "github.event.inputs.max_sources }}")


def _cron_minutes() -> list:
    crons = re.findall(r'-\s*cron:\s*"([^"]+)"', _WF)
    assert len(crons) == 1, (
        f"ingest.yml must declare exactly one quoted cron expression, "
        f"found {len(crons)} (r16 nit: counted, not just first-matched)")
    fields = crons[0].split()
    assert len(fields) == 5, f"malformed cron: {m.group(1)!r}"
    assert fields[1:] == ["*", "*", "*", "*"], (
        "contract assumes an every-N-minutes cron (hour/day fields '*'); "
        "a different shape needs this test updated in the same PR")
    return sorted(int(x) for x in fields[0].split(","))


def test_cron_minutes_evenly_spaced_within_the_hour():
    minutes = _cron_minutes()
    assert len(minutes) >= 1
    spacings = {(b - a) % 60 for a, b in zip(minutes, minutes[1:])}
    spacings.add((minutes[0] + 60 - minutes[-1]) % 60)
    assert len(spacings) == 1, (
        f"cron minutes {minutes} are unevenly spaced — the dead-man period "
        "cannot represent a variable cadence")


def test_declared_period_equals_cron_spacing():
    minutes = _cron_minutes()
    spacing = (minutes[1] - minutes[0]) if len(minutes) > 1 else 60
    declared = re.search(r'EXPECTED_PERIOD_SECONDS:\s*"(\d+)"', _WF)
    assert declared, "EXPECTED_PERIOD_SECONDS must be declared in ingest.yml"
    assert int(declared.group(1)) == spacing * 60, (
        f"cron runs every {spacing} min but EXPECTED_PERIOD_SECONDS is "
        f"{declared.group(1)}s — cadence and alarm period must move together")


def test_schedule_only_ceiling_expression_in_both_steps_and_no_fail_open_form():
    assert _WF.count(_SCHEDULE_EXPR) == 2, (
        "the schedule-only MAX_SOURCES expression must appear exactly twice "
        "(validation step and run step) — validated value == executed value")
    assert "inputs.max_sources || '10'" not in _WF.replace(
        "== 'schedule' && '10' || github.event.inputs.max_sources", ""), (
        "bare `|| '10'` fallback found — empty manual dispatch input would "
        "silently get a default instead of failing loud (PR #43 r1)")


def test_deadman_assertion_step_present_with_full_env():
    assert "tools/assert_deadman_period.py" in _WF
    for var in ("ORCHESTRATOR_PING_URL", "HEALTHCHECKS_API_KEY_RO",
                "EXPECTED_PERIOD_SECONDS", "MAX_GRACE_SECONDS"):
        assert var in _WF, f"dead-man assertion env {var} missing"
    # The assertion must run BEFORE the loop step spends anything.
    assert _WF.index("assert_deadman_period.py") < _WF.index(
        "run_once.py --real")
