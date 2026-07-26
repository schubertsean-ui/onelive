"""Tests for tools/watchdog_check.py — the GitHub-native dead-man alarm.

Founder-approved 2026-07-26 ("build the watchdog") in place of a healthchecks.io
account. Decision record:
docs/memory/decisions/2026-07-26_github-native-watchdog.md

An alarm that cannot fire proves nothing (`docs/HOW_WE_WORK.md` §10), so the
first thing these tests do is make it fire: a stale job, a never-run job and an
unscheduled job each turn it red. They also pin the properties that make it
honest — an unanswerable API call is exit 2 and never a pass, an empty watch
table is an error, and every excluded or pending workflow is named with a reason
rather than silently dropped.

No network: the API call is stubbed. Real reachability is exercised by
`.github/workflows/watchdog.yml`, which is where the token exists.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "watchdog_check", _REPO_ROOT / "tools" / "watchdog_check.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


WD = _load()
NOW = dt.datetime(2026, 7, 26, 18, 0, tzinfo=dt.timezone.utc)


def _hours_ago(h: float) -> dt.datetime:
    return NOW - dt.timedelta(hours=h)


# ------------------------------------------------------- the alarm must fire
def test_a_stale_job_is_an_alarm():
    status, detail = WD.evaluate("x.yml", 12, 2, NOW, _hours_ago(15), True)
    assert status == "STALE"
    assert "15.0 h ago" in detail and "limit 14 h" in detail


def test_a_job_that_never_succeeded_is_an_alarm():
    status, detail = WD.evaluate("x.yml", 12, 2, NOW, None, True)
    assert status == "STALE" and "NEVER" in detail
    assert "R-054" in detail   # names the precedent so the reader knows the shape


def test_an_unscheduled_watched_job_is_an_alarm():
    status, detail = WD.evaluate("x.yml", 12, 2, NOW, None, False)
    assert status == "STALE" and "NO schedule" in detail


def test_a_fresh_job_passes():
    status, detail = WD.evaluate("x.yml", 12, 2, NOW, _hours_ago(3), True)
    assert status == "FRESH" and "3.0 h ago" in detail


def test_the_boundary_is_inclusive_of_the_grace_window():
    # Exactly at the limit is still fresh; a minute past it is not.
    assert WD.evaluate("x.yml", 12, 2, NOW, _hours_ago(14), True)[0] == "FRESH"
    assert WD.evaluate("x.yml", 12, 2, NOW, _hours_ago(14.02), True)[0] == "STALE"


# ------------------------------------------------------------- config sanity
def test_every_watched_workflow_exists_and_is_scheduled():
    for name in WD.WATCHED:
        assert (WD.WORKFLOW_DIR / name).is_file(), f"{name} does not exist"
        assert WD.workflow_has_schedule(name), \
            f"{name} is WATCHED but has no schedule — the watchdog would alarm forever"


def test_every_expected_soon_workflow_exists_and_cites_an_open_record_row():
    """EXPECTED_SOON may be EMPTY — that is the healthy state, and is exactly
    what happened on 2026-07-26 when import_licensed.yml was given a schedule and
    graduated to WATCHED. What must never happen is an entry that rests on a
    closed Record row, because that is a permanent silent exemption.
    """
    record = (_REPO_ROOT / "docs" / "RECORD.md").read_text(encoding="utf-8")
    for name, row in WD.EXPECTED_SOON.items():
        assert (WD.WORKFLOW_DIR / name).is_file(), f"{name} does not exist"
        assert f"| {row} |" in record, f"{name} cites {row}, which is not in RECORD.md"
        # The row must be OPEN — a pending exemption resting on a closed row is a
        # permanent silent exemption.
        line = next(ln for ln in record.splitlines() if ln.startswith(f"| {row} |"))
        assert line.rstrip().endswith("| OPEN |"), \
            f"{row} is not OPEN, so {name} must move to WATCHED or be excluded"


def test_every_scheduled_workflow_is_watched_pending_or_excluded_with_a_reason():
    """No scheduled job may be silently absent from the watchdog's attention.

    BOTH extensions. GitHub accepts `.yml` AND `.yaml`, and the first version of
    this test globbed only `*.yml` — so a scheduled `.yaml` workflow could bypass
    the watchdog registry entirely. Caught by the independent reviewer (openai /
    absence-only, PR #76), which correctly named it a repeat of the same
    platform-surface class `tests/test_scheduled_inputs_contract.py` already
    handles with `_WORKFLOW_GLOBS`.
    """
    known = set(WD.WATCHED) | set(WD.EXPECTED_SOON) | set(WD.EXCLUDED)
    workflows = sorted(p for ext in ("*.yml", "*.yaml")
                       for p in WD.WORKFLOW_DIR.glob(ext))
    assert workflows, "no workflow files found — the glob is wrong"
    for path in workflows:
        if not WD.workflow_has_schedule(path.name):
            continue
        assert path.name in known, (
            f"{path.name} is SCHEDULED but appears in none of WATCHED / "
            f"EXPECTED_SOON / EXCLUDED — a scheduled job the watchdog does not "
            f"know about is exactly the silence it exists to prevent")


def test_every_exclusion_carries_a_substantive_reason():
    for name, why in WD.EXCLUDED.items():
        assert len(why) > 40, f"{name}'s exclusion reason is too thin: {why!r}"


def test_the_watchdog_does_not_claim_to_watch_itself():
    assert "watchdog.yml" in WD.EXCLUDED
    assert "cannot report" in WD.EXCLUDED["watchdog.yml"]


# ------------------------------------------------- honesty under failure
def test_an_unanswerable_api_call_is_exit_2_not_a_pass(monkeypatch, capsys):
    def boom(path):
        raise WD.WatchdogError("API 403")
    monkeypatch.setattr(WD, "_api", boom)
    assert WD.main(["owner/repo"]) == 2
    assert "OK" not in capsys.readouterr().out


def test_an_empty_watch_table_is_an_error(monkeypatch):
    monkeypatch.setattr(WD, "WATCHED", {})
    assert WD.main(["owner/repo"]) == 2


def test_main_exits_1_when_a_watched_job_is_stale(monkeypatch, capsys):
    monkeypatch.setattr(WD, "workflow_has_schedule", lambda name: True)
    monkeypatch.setattr(WD, "last_success", lambda repo, name: _hours_ago(99))
    assert WD.main(["owner/repo"]) == 1
    out = capsys.readouterr().out
    assert "STALE" in out and "do not silence it" in out


def test_main_exits_0_and_names_pending_and_excluded(monkeypatch, capsys):
    monkeypatch.setattr(WD, "workflow_has_schedule", lambda name: True)
    monkeypatch.setattr(WD, "last_success", lambda repo, name: _hours_ago(1))
    assert WD.main(["owner/repo"]) == 0
    out = capsys.readouterr().out
    assert "FRESH" in out
    for name in WD.EXPECTED_SOON:
        assert name in out            # pending is reported, never hidden
    for name in WD.EXCLUDED:
        assert name in out            # exclusions are visible too


def test_a_pending_entry_is_reported_when_one_exists(monkeypatch, capsys):
    """The PENDING path still works even though the live table is empty today —
    otherwise the mechanism would rot unnoticed until it was next needed."""
    monkeypatch.setattr(WD, "EXPECTED_SOON", {"future_import.yml": "R-999"})
    monkeypatch.setattr(WD, "workflow_has_schedule", lambda name: True)
    monkeypatch.setattr(WD, "last_success", lambda repo, name: _hours_ago(1))
    assert WD.main(["owner/repo"]) == 0
    out = capsys.readouterr().out
    assert "PENDING future_import.yml" in out and "R-999" in out


def test_both_data_importers_are_watched():
    """The two deterministic feeds are the freshness of the product. Neither may
    drop out of the watch list without this failing."""
    assert "import_structured.yml" in WD.WATCHED
    assert "import_licensed.yml" in WD.WATCHED


def test_last_success_returns_none_when_there_are_no_successful_runs(monkeypatch):
    monkeypatch.setattr(WD, "_api", lambda path: {"workflow_runs": []})
    assert WD.last_success("owner/repo", "x.yml") is None


def test_last_success_asks_only_for_SCHEDULE_runs(monkeypatch):
    """A manual click must never be able to silence the dead-man alarm.

    The blocker the independent reviewer raised (openai / absence-only, PR #76):
    the first version queried `status=success` with no event filter, so a human
    running the workflow by hand would refresh the timestamp and turn the watchdog
    green while the cron path stayed dead. That is R-054 exactly —
    import_structured.yml had four successful runs, all manual, and never once ran
    on its schedule.
    """
    asked: list[str] = []

    def spy(path):
        asked.append(path)
        return {"workflow_runs": [{"updated_at": "2026-07-26T12:00:00Z"}]}

    monkeypatch.setattr(WD, "_api", spy)
    WD.last_success("owner/repo", "x.yml")
    assert len(asked) == 1
    assert "event=schedule" in asked[0], asked[0]
    assert "status=success" in asked[0]


def test_a_workflow_with_only_manual_successes_reads_as_never_run(monkeypatch):
    """End-to-end shape of the same defect: the API returns nothing for
    event=schedule even though manual successes exist, so the watchdog alarms."""
    def only_manual(path):
        # Mirrors GitHub: filtering to event=schedule returns an empty list when
        # every success came from workflow_dispatch.
        return {"workflow_runs": []} if "event=schedule" in path else {
            "workflow_runs": [{"updated_at": "2026-07-26T17:00:00Z"}]}

    monkeypatch.setattr(WD, "_api", only_manual)
    assert WD.last_success("owner/repo", "x.yml") is None
    status, detail = WD.evaluate("x.yml", 12, 2, NOW, None, True)
    assert status == "STALE"
    assert "ON ITS SCHEDULE" in detail and "workflow_dispatch" in detail


def test_last_success_parses_the_api_timestamp(monkeypatch):
    monkeypatch.setattr(WD, "_api", lambda path: {
        "workflow_runs": [{"updated_at": "2026-07-26T12:00:00Z"}]})
    seen = WD.last_success("owner/repo", "x.yml")
    assert seen == dt.datetime(2026, 7, 26, 12, 0, tzinfo=dt.timezone.utc)


def test_a_successful_run_with_no_timestamp_raises(monkeypatch):
    monkeypatch.setattr(WD, "_api", lambda path: {"workflow_runs": [{}]})
    with pytest.raises(WD.WatchdogError):
        WD.last_success("owner/repo", "x.yml")


def test_a_missing_workflow_file_raises(monkeypatch):
    with pytest.raises(WD.WatchdogError):
        WD.workflow_has_schedule("no_such_workflow.yml")


def test_schedule_detection_sees_valid_yaml_a_line_regex_cannot(tmp_path,
                                                                monkeypatch):
    """`CLASS:incomplete-workflow-surface-scan`, PR #80.

    The registry test above only holds if `workflow_has_schedule` recognises every
    way GitHub accepts a cron. It used to match an unquoted `schedule:` on its own
    line, so a scheduled job written as `"schedule":` or inline
    `on: {schedule: [...]}` was silently OUTSIDE the "every scheduled workflow is
    watched" invariant — the enumeration was incomplete, not wrong, which is
    harder to see and just as unwatched.
    """
    monkeypatch.setattr(WD, "WORKFLOW_DIR", tmp_path)
    cases = {
        "plain.yml": 'on:\n  schedule:\n    - cron: "0 * * * *"\n',
        "double_quoted.yml": 'on:\n  "schedule":\n    - cron: "0 * * * *"\n',
        "single_quoted.yml": "on:\n  'schedule':\n    - cron: '0 * * * *'\n",
        "inline.yml": 'on: {schedule: [{cron: "0 * * * *"}]}\n',
        "inline_quoted.yml":
            'on: {"push": null, "schedule": [{"cron": "0 * * * *"}]}\n',
        "deep_indent.yml": 'on:\n      schedule:\n        - cron: "0 * * * *"\n',
    }
    for name, text in cases.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
        assert WD.workflow_has_schedule(name), \
            f"{name} is scheduled but escaped detection:\n{text}"

    # ...and an UNSCHEDULED workflow must still answer False, or every workflow
    # is dragged into WATCHED/EXCLUDED and the registry stops meaning anything.
    for name, text in {
        "dispatch_only.yml": "on:\n  workflow_dispatch:\n",
        "pr_only.yml": "on: {pull_request: null}\n",
        # A job STEP that merely mentions the word must not count.
        "mentions.yml": ('on:\n  workflow_dispatch:\n'
                         'jobs:\n  j:\n    steps:\n'
                         '      - run: echo "no schedule here"\n'),
    }.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
        assert not WD.workflow_has_schedule(name), \
            f"{name} is not scheduled but was pulled into scope:\n{text}"


def test_an_unparseable_workflow_is_treated_as_in_scope(tmp_path, monkeypatch):
    """Fail CLOSED. A file the parser rejects must land INSIDE the registry
    check, because a watchdog that quietly drops what it could not read is a
    watchdog with a hole exactly the size of one malformed file."""
    monkeypatch.setattr(WD, "WORKFLOW_DIR", tmp_path)
    (tmp_path / "broken.yml").write_text("on: [::: not yaml\n  - {{{\n",
                                         encoding="utf-8")
    assert WD.workflow_has_schedule("broken.yml")


def test_detection_still_works_with_no_yaml_parser_available(tmp_path,
                                                             monkeypatch):
    """The parse is an addition, not a replacement: on a runner without PyYAML
    the regex path must still put a scheduled workflow in scope."""
    monkeypatch.setattr(WD, "WORKFLOW_DIR", tmp_path)
    monkeypatch.setattr(WD, "_yaml", None)
    (tmp_path / "plain.yml").write_text('on:\n  schedule:\n    - cron: "0 * * * *"\n',
                                        encoding="utf-8")
    assert WD.workflow_has_schedule("plain.yml")
    # With no parser, "in scope" is the safe answer for everything else too —
    # asserted so the fallback's over-inclusiveness is a stated property rather
    # than a surprise the next reader has to rediscover.
    (tmp_path / "dispatch_only.yml").write_text("on:\n  workflow_dispatch:\n",
                                                encoding="utf-8")
    assert WD.workflow_has_schedule("dispatch_only.yml")


def test_the_repo_argument_must_be_a_plain_owner_name_slug():
    """`CLASS:dataflow-taint-unvalidated-input` (gemini/dataflow-taint, PR #80).

    `repo` comes from argv or `$GITHUB_REPOSITORY` and is interpolated straight
    into `/repos/{repo}/actions/...`. Unvalidated, a value carrying `../` or a
    query string sends the request somewhere else — so the alarm could report
    freshness for a repository nobody asked about, which is the worst possible
    failure for a dead-man switch: confidently green about the wrong thing.
    """
    assert WD.validate_repo("schubertsean-ui/onelive") == "schubertsean-ui/onelive"
    assert WD.validate_repo("owner.with-dots_and-dashes/repo.name-1") is not None
    for bad in ("../../etc/passwd",
                "owner/repo/../../other",
                "owner/repo?per_page=1",
                "owner/repo#frag",
                "owner",
                "owner/",
                "/repo",
                "owner//repo",
                "owner repo",
                "owner/repo/extra",
                "",
                "https://evil.example/owner/repo"):
        with pytest.raises(WD.WatchdogError):
            WD.validate_repo(bad)


def test_main_refuses_a_malformed_repo_rather_than_calling_the_api(monkeypatch, capsys):
    """Exit 2 (tool error), never 0. And it must not reach the network first."""
    def must_not_run(*a, **k):
        raise AssertionError("the API was called with an unvalidated repo")
    monkeypatch.setattr(WD, "last_success", must_not_run)
    assert WD.main(["../../evil"]) == 2
    assert "owner/name slug" in capsys.readouterr().err
