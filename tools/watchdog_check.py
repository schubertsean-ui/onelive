#!/usr/bin/env python3
"""Dead-man watchdog for this repo's scheduled jobs, using GitHub's own API.

**Founder-approved 2026-07-26** ("build the watchdog") as an alternative to a
healthchecks.io account, chosen because it needs no third-party signup and no
secret — the `GITHUB_TOKEN` every workflow already gets is enough. The charter
amendment that permits it, and the weakness the founder accepted, are recorded in
`docs/memory/decisions/2026-07-26_github-native-watchdog.md`.

**What it does.** For each watched workflow it asks the Actions API when that
workflow last completed *successfully*, and reports STALE if that is longer ago
than the workflow's own cadence plus a grace period. A stale row exits 1, which
turns the scheduled run red — and GitHub emails the repository owner on a failed
scheduled run. That email is the dead-man ping.

**The weakness, stated because a dead-man switch that hides its own failure mode
is worse than none.** This watchdog lives inside GitHub Actions, so it is down
whenever Actions is down — which happened on 2026-07-26 (R-060) — and GitHub
disables scheduled workflows in repositories with no activity for 60 days. An
external service does not share those failure modes. This is a deliberate trade of
alarm independence for zero founder setup, made by the founder, not assumed.

**Two lists, deliberately.** `WATCHED` is jobs that must be scheduled AND fresh;
stale or never-run is an alarm. `EXPECTED_SOON` is jobs that *should* be scheduled
and are not yet — each cites its OPEN `docs/RECORD.md` row, and is reported as
PENDING rather than alarmed on, because re-screaming a known, registered gap on
every run is noise that trains people to ignore the alarm. A test enforces that
every `EXPECTED_SOON` entry names a real row.

Exit codes (`tools/README.md`): 0 = every watched job is fresh; 1 = at least one is
stale/never-run; 2 = tool error (including "could not ask the API" — an
unanswerable question is never a pass).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW_DIR = _REPO_ROOT / ".github" / "workflows"
DEFAULT_REPO = "schubertsean-ui/onelive"
API_ROOT = "https://api.github.com"
TIMEOUT = 30

# workflow file -> (cadence hours, grace hours). Max age = cadence + grace.
WATCHED: dict[str, tuple[int, int]] = {
    # Runs 08:17 and 20:17 UTC — 12 h apart. Grace mirrors the healthchecks spec
    # the charter asked for (period 12 h, grace 2 h).
    #
    # THIS WILL REPORT STALE ON ITS FIRST RUN, AND CORRECTLY SO. Measured against
    # the live Actions API on 2026-07-26T18:08Z: 4 successful runs ever, ALL of
    # them manual `workflow_dispatch`, none from a schedule, most recent 22.8 h
    # ago. Cause: the D1 cron fix (a literal on the schedule path) is on the
    # unmerged PR #76 branch, while `origin/master` still reads the bare
    # `github.event.inputs.limit` and so still dies in its own fail-closed guard.
    # This is a REAL current condition, not the permanent-red trap of a gate that
    # can never be satisfied — it clears the moment the fix merges and one
    # scheduled run completes (R-054's own resolution trigger).
    "import_structured.yml": (12, 2),
    # Scheduled 2026-07-26 by founder direction ("do 2", ask 1) at 02:23/14:23 UTC
    # — 12 h apart. Moved here from EXPECTED_SOON in the same change that gave it a
    # schedule, so the watchdog IS its dead-man alarm from the first run rather
    # than a promise to add one later.
    "import_licensed.yml": (12, 2),
}

# workflow file -> the OPEN Record row that tracks why it is not scheduled yet.
# Empty as of 2026-07-26: import_licensed.yml graduated to WATCHED when it was
# given a schedule. Kept as a mechanism, not deleted — the next importer that is
# specified before it is scheduled belongs here with its OPEN Record row, rather
# than being silently absent from the watchdog's attention.
EXPECTED_SOON: dict[str, str] = {}

# Deliberately NOT watched, with the reason, because a silent omission from a
# watchdog is indistinguishable from a job nobody thought about.
EXCLUDED: dict[str, str] = {
    "ingest.yml": "AI extraction is capped off at the provider (founder ask 2), so "
                  "every run fails for a known, recorded reason. Alarming every 20 "
                  "minutes on that would be pure noise. Trigger to include: the "
                  "Anthropic cap is raised.",
    "dependency-hygiene.yml": "hygiene reporting, not a data path — its silence "
                              "does not make the site stale.",
    "source-backfill.yml": "one-off style backfill, not a freshness dependency.",
    "watchdog.yml": "watching itself proves nothing — if it is not running it "
                    "cannot report that it is not running. This is the accepted "
                    "weakness named in the module docstring.",
    "site_health.yml": "on-demand deployment check, not scheduled.",
}

_SCHEDULE_KEY = re.compile(r"^\s+schedule:\s*$", re.MULTILINE)


class WatchdogError(Exception):
    """The watchdog could not take a measurement — never reported as fresh."""


def _api(path: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "onelive-watchdog"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise WatchdogError(
            f"GitHub API {exc.code} for {path} — "
            f"{'set GITHUB_TOKEN (a private repo needs auth)' if exc.code in (401, 403, 404) else 'unexpected'}"
        ) from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise WatchdogError(f"could not reach the GitHub API for {path}: {exc}") from exc


def workflow_has_schedule(name: str) -> bool:
    path = WORKFLOW_DIR / name
    if not path.is_file():
        raise WatchdogError(f"{name} does not exist in {WORKFLOW_DIR}")
    return bool(_SCHEDULE_KEY.search(path.read_text(encoding="utf-8")))


def last_success(repo: str, name: str, event: str = "schedule") -> _dt.datetime | None:
    """When this workflow last succeeded ON THE SCHEDULE CLOCK, or None if never.

    **`event=schedule` is the whole point, and omitting it was a real defect
    caught by the independent reviewer (openai / absence-only, PR #76).** The
    first version asked only for `status=success`, so a human clicking *Run
    workflow* would refresh the timestamp and turn the watchdog green **while the
    cron path stayed dead.** That is not a hypothetical: it is exactly R-054, the
    project's first escaped defect — `import_structured.yml` had four successful
    runs, every one a manual dispatch, and never once ran on its schedule. A
    dead-man alarm that a manual click can silence is not an alarm.

    Pass a different `event` only to ask a different question (e.g. auditing
    manual history); the watched path is always `schedule`.
    """
    data = _api(f"/repos/{repo}/actions/workflows/{name}/runs"
                f"?status=success&event={event}&per_page=1")
    runs = data.get("workflow_runs") or []
    if not runs:
        return None
    stamp = runs[0].get("updated_at") or runs[0].get("created_at")
    if not stamp:
        raise WatchdogError(f"{name}: a successful run carried no timestamp")
    # A corrupt or unexpectedly-typed timestamp must arrive as a WatchdogError
    # (exit 2, "could not measure"), never as an unhandled traceback. `.replace`
    # raises AttributeError on a non-string and `fromisoformat` raises ValueError on
    # a malformed one — either would crash the alarm runner instead of failing
    # through its own tool-error path (`CLASS:swallowed-corrupt-data`, PR #76). An
    # alarm that dies untidily is an alarm nobody can tell apart from one that is
    # simply not running.
    if not isinstance(stamp, str):
        raise WatchdogError(
            f"{name}: run timestamp is {type(stamp).__name__}, not a string "
            f"({stamp!r}) — the Actions API contract changed; refusing to compute "
            f"freshness from a value this tool cannot parse")
    try:
        return _dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WatchdogError(
            f"{name}: could not parse the run timestamp {stamp!r} ({exc}) — "
            f"refusing to report freshness from an unreadable date") from exc


def evaluate(name: str, cadence_h: int, grace_h: int,
             now: _dt.datetime, seen: _dt.datetime | None,
             scheduled: bool) -> tuple[str, str]:
    """Classify one watched workflow. Returns (status, detail)."""
    max_age_h = cadence_h + grace_h
    if not scheduled:
        return "STALE", (f"has NO schedule, so it can never refresh unattended — "
                         f"a watched job must be scheduled")
    if seen is None:
        return "STALE", ("has NEVER completed successfully ON ITS SCHEDULE "
                         "(manual `workflow_dispatch` successes are deliberately "
                         "not counted) — this is the R-054 failure mode exactly: "
                         "a workflow whose cron is dead while hand-runs look fine")
    age_h = (now - seen).total_seconds() / 3600.0
    if age_h > max_age_h:
        return "STALE", (f"last success {age_h:.1f} h ago, limit {max_age_h} h "
                         f"(cadence {cadence_h} h + grace {grace_h} h)")
    return "FRESH", f"last success {age_h:.1f} h ago, limit {max_age_h} h"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repo = argv[0] if argv else os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO)
    if not WATCHED:
        print("watchdog_check: ERROR — the WATCHED table is empty; a watchdog that "
              "watches nothing must never report OK", file=sys.stderr)
        return 2

    now = _dt.datetime.now(_dt.timezone.utc)
    stale: list[str] = []
    try:
        for name, (cadence_h, grace_h) in sorted(WATCHED.items()):
            scheduled = workflow_has_schedule(name)
            seen = last_success(repo, name) if scheduled else None
            status, detail = evaluate(name, cadence_h, grace_h, now, seen, scheduled)
            print(f"{status:6} {name}  ({detail})")
            if status == "STALE":
                stale.append(name)
    except WatchdogError as exc:
        # An unanswerable question is exit 2, never a quiet pass.
        print(f"watchdog_check: ERROR — {exc}", file=sys.stderr)
        return 2

    for name, row in sorted(EXPECTED_SOON.items()):
        print(f"PENDING {name}  (not scheduled yet; tracked as {row} — reported, "
              f"not alarmed on, because the gap is already registered)")
    for name, why in sorted(EXCLUDED.items()):
        print(f"EXCL   {name}  ({why.split('.')[0]}.)")

    print()
    if stale:
        print(f"watchdog_check: {len(stale)} watched job(s) STALE — {', '.join(stale)}. "
              f"A scheduled job that stopped is exactly what this exists to catch; "
              f"do not silence it, find out why it stopped.")
        return 1
    print(f"watchdog_check: OK — {len(WATCHED)} watched job(s) fresh, "
          f"{len(EXPECTED_SOON)} pending, {len(EXCLUDED)} excluded with reasons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
