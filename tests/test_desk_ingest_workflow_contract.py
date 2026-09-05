"""Structural contract tests for .github/workflows/desk-ingest.yml.

This workflow WRITES TO THE LIVE CATALOG on a schedule nobody watches. Every
coupling below is one that, if it drifted quietly, would leave a writer running
unwatched, running blind, or reporting a desk it never opened as a desk with
nothing on. Each is checked mechanically here rather than trusted to review.

1. CADENCE <-> DECLARED PERIOD. EXPECTED_PERIOD_SECONDS, fed to the dead-man
   assertion, is recomputed HERE from the cron's own hour step. Editing one
   without the other fails this suite in the same PR.
2. THE SCHEDULE ACTUALLY WRITES. The founder armed this to publish; a schedule
   that resolved to a dry run would look green forever and change nothing.
3. THE SCHEDULE IS WATCHED. The dead-man assertion runs on `schedule`, with all
   four of its env inputs. Removing the watchdog is a loud diff here.
4. MANUAL DISPATCH STAYS DRY BY DEFAULT, and stays master-only.
5. `pipefail` IS SET on the walk. Without it `tee` swallows the tool's exit 3
   and an unreadable desk reports green — the exact defect this ticket fixed.
"""
import pathlib
import re

import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PATH = _ROOT / ".github" / "workflows" / "desk-ingest.yml"
_TEXT = _PATH.read_text()
# PyYAML reads the `on:` key as the boolean True (YAML 1.1 "on"), which is why
# every lookup below says True rather than "on".
_WF = yaml.safe_load(_TEXT)
_JOB = _WF["jobs"]["ingest"]
_STEPS = _JOB["steps"]


def _step(fragment):
    for step in _STEPS:
        if fragment.lower() in (step.get("name") or "").lower():
            return step
    raise AssertionError(f"no step named like {fragment!r}")


# 1. cadence <-> declared period ------------------------------------------

def test_the_cron_is_an_even_hour_step():
    crons = [entry["cron"] for entry in _WF[True]["schedule"]]
    assert len(crons) == 1, f"one cadence, not {crons}"
    minute, hour = crons[0].split()[0], crons[0].split()[1]
    assert minute.isdigit() and minute != "0", (
        "minute 0 sits in the congestion window where GitHub drops runs")
    assert re.fullmatch(r"\*/\d+", hour), hour


def test_the_declared_deadman_period_equals_the_cron_spacing():
    """The alarm must expect exactly the cadence the cron actually runs."""
    hour = [e["cron"] for e in _WF[True]["schedule"]][0].split()[1]
    every_n_hours = int(hour.split("/")[1])
    step = _step("dead-man")
    assert int(step["env"]["EXPECTED_PERIOD_SECONDS"]) == every_n_hours * 3600


def test_the_founders_cadence_is_six_hours():
    hour = [e["cron"] for e in _WF[True]["schedule"]][0].split()[1]
    assert hour == "*/6", "founder: every 6 hours is enough until we measure"


# 2. the schedule writes ---------------------------------------------------

def test_the_schedule_resolves_to_a_write_and_dispatch_obeys_its_input():
    """A `schedule` event carries NO `inputs`, so keying the write off
    `inputs.write` would have made every scheduled run a silent dry run."""
    assert _JOB["env"]["WRITE_MODE"] == (
        "${{ github.event_name == 'schedule' && 'true' || inputs.write }}")


def test_no_step_decides_the_write_from_the_raw_dispatch_input():
    """Every write-gated step must read the resolved WRITE_MODE. A step still
    reading `inputs.write` would skip itself on schedule — which is how the DSN
    validation would have been skipped on the runs that actually write."""
    for step in _STEPS:
        cond = str(step.get("if") or "")
        assert "inputs.write" not in cond, step.get("name")


def test_the_walk_runs_real_and_uses_the_only_write_seam():
    body = _step("Walk the desks")["run"]
    assert "tools/desk_ingest.py" in body
    assert "--real" in body and "--write" in body
    # One publisher. A second write path would not go through the gate.
    assert not re.search(r"promote|create_candidate", body)


# 3. the schedule is watched ----------------------------------------------

def test_the_deadman_assertion_runs_on_the_schedule_with_its_full_env():
    step = _step("dead-man")
    assert step["if"] == "github.event_name == 'schedule'"
    for key in ("ORCHESTRATOR_PING_URL", "HEALTHCHECKS_API_KEY_RO",
                "DEADMAN_CHECK_SLUG", "EXPECTED_PERIOD_SECONDS",
                "MAX_GRACE_SECONDS"):
        assert key in step["env"], key
    assert "assert_deadman_period.py" in step["run"]


def test_the_desk_loop_has_its_own_alarm_not_the_ingestion_loops():
    """Sharing `onelive-ingestion` would let the 20-minute loop's pings satisfy
    this 6-hourly one, so the desk writer could stop dead and nothing would fire."""
    step = _step("dead-man")
    assert step["env"]["DEADMAN_CHECK_SLUG"] == "onelive-desk-ingest"
    assert step["env"]["ORCHESTRATOR_PING_URL"] == "${{ secrets.DESK_INGEST_PING_URL }}"


def test_the_scheduled_run_pings_the_alarm_it_asserts():
    """Asserting the alarm's config and never pinging it would leave a check
    that alarms on a healthy loop; pinging on dispatch would tell the alarm the
    SCHEDULE is alive when only a person pressed a button."""
    body = _step("Walk the desks")["run"]
    assert "--deadman" in body
    assert "schedule" in body, "the ping must be gated on the schedule event"


# 4. dispatch stays dry, and master-only ----------------------------------

def test_manual_dispatch_still_defaults_to_not_writing():
    assert _WF[True]["workflow_dispatch"]["inputs"]["write"]["default"] is False


def test_the_job_is_master_only():
    assert _JOB["if"] == "github.ref == 'refs/heads/master'"


def test_the_page_ceiling_is_fixed_on_schedule_and_never_fails_open():
    assert _JOB["env"]["IN_MAX_PAGES"] == (
        "${{ github.event_name == 'schedule' && '40' || inputs.max_pages }}")
    assert "inputs.max_pages || " not in _TEXT, "the fail-open fallback form"


# 5. an unreadable desk cannot report green -------------------------------

def test_pipefail_is_set_where_the_tool_is_piped_into_tee():
    body = _step("Walk the desks")["run"]
    assert "| tee" in body
    assert "set -euo pipefail" in body, (
        "without pipefail, tee reports success and the tool's exit 3 is lost — "
        "an unreadable desk would report green, which is the defect this "
        "workflow was armed to stop")


def test_the_report_and_the_failure_annotation_survive_a_failed_walk():
    assert _step("Put the report")["if"] == "always()"
    assert _step("Upload the report")["if"] == "always()"
    assert _step("Say what failed")["if"] == "failure()"


def test_the_run_is_bounded_and_single_writer():
    assert _WF["concurrency"]["group"] == "desk-ingest"
    assert _WF["concurrency"]["cancel-in-progress"] is False
    hour = [e["cron"] for e in _WF[True]["schedule"]][0].split()[1]
    every_n_hours = int(hour.split("/")[1])
    assert _JOB["timeout-minutes"] < every_n_hours * 60, (
        "a run must finish well inside its own cadence or runs queue up")
