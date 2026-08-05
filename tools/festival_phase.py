#!/usr/bin/env python3
"""Festival-window PHASE resolver — the definition of "inside an active window".

Founder question (2026-08-05, verbatim): "festivals usually start promoting
lineups and activities months and weeks in advance - they firm up as the
event gets closer and even days before and day of updates, new things,
cancellations, etc.. so we need to capture the right amount of content for
the appropriate amount of time 'inside an active festival window'" —
decision record docs/memory/decisions/2026-08-05_festival-window-phases.md.

The answer, as data-driven phases computed from each window's committed
dates (never scraped, never inferred):

  announce   months out .. rampup      covered by the STANDING WEEKLY full
                                       sweep — a festival page that surfaces
                                       in search is found within a week, at
                                       zero extra cost. No daily machinery.
  rampup     starts-28d .. starts-1d   lineups firm up: DAILY festival-
                                       KEYWORD sweep (this window's
                                       keyword_pack x its geo — a handful of
                                       queries a day, near-zero cost).
  live       starts .. ends            the ratified daily-FULL-sweep band
                                       ("automatic daily inside festival
                                       windows", 2026-08-05) PLUS the keyword
                                       sweep — day-of pop-ups announce with
                                       festival terms the domain pack never
                                       queries.
  winddown   ends+1d                   one more keyword sweep: day-after
                                       additions, cancellations, recap pages
                                       that name the pop-ups we missed.
  off        everything else           honest no-op (printed, never silent).

Per-window overrides: "rampup_days" (default 28) and "winddown_days"
(default 1) in sources/festival_windows.json. Widening a band raises spend:
the budget ledger docs/ops/SEARCH_QUOTA_BUDGET.md governs, and >$40/month
returns to the founder (standing rule).

Cancellations/updates for events ALREADY INGESTED are the re-ingest cron's
job (catalog sources re-fetch every cycle); this resolver only governs the
DISCOVERY scanner's cadence.

CLI: prints the resolved JSON; when GITHUB_ENV is set, also writes
SWEEP_MODE (full|keyword|no) and FESTIVAL_SLUGS (comma-joined keyword-sweep
targets) for the source-scan workflow's step conditions.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import zoneinfo

WINDOWS_DEFAULT = "sources/festival_windows.json"
RAMPUP_DAYS_DEFAULT = 28
WINDDOWN_DAYS_DEFAULT = 1


def phase_for(window: dict, today: datetime.date) -> str:
    """One window's phase on one date: live | rampup | winddown | off."""
    starts = datetime.date.fromisoformat(window["starts"])
    ends = datetime.date.fromisoformat(window["ends"])
    rampup = datetime.timedelta(days=int(window.get("rampup_days", RAMPUP_DAYS_DEFAULT)))
    winddown = datetime.timedelta(days=int(window.get("winddown_days", WINDDOWN_DAYS_DEFAULT)))
    if starts <= today <= ends:
        return "live"
    if starts - rampup <= today < starts:
        return "rampup"
    if ends < today <= ends + winddown:
        return "winddown"
    return "off"


def resolve(windows: list[dict], today: datetime.date) -> dict:
    """Today's sweep plan across all windows.

    mode: 'full' when ANY window is live (full sweep + keyword sweeps),
    'keyword' when only rampup/winddown windows are active, else 'no'.
    Live windows appear in BOTH lists: the full sweep's domain pack never
    queries festival terms, so the keyword sweep runs alongside it.
    """
    live = [w["slug"] for w in windows if phase_for(w, today) == "live"]
    shoulder = [w["slug"] for w in windows
                if phase_for(w, today) in ("rampup", "winddown")]
    keyword = live + shoulder
    mode = "full" if live else ("keyword" if keyword else "no")
    return {"date": today.isoformat(), "mode": mode,
            "full": live, "keyword": keyword}


def main(argv=None) -> int:
    """Resolve today's phase (America/Chicago) and export it for the workflow."""
    path = argv[0] if argv else WINDOWS_DEFAULT
    today = datetime.datetime.now(zoneinfo.ZoneInfo("America/Chicago")).date()
    with open(path, encoding="utf-8") as fh:
        windows = json.load(fh)["windows"]
    plan = resolve(windows, today)
    json.dump(plan, sys.stdout, indent=2)
    print()
    if plan["mode"] == "no":
        print(f"no festival window in any active phase on {plan['date']} — "
              "daily sweep not owed; the weekly cadence stands (honest no-op, "
              "printed not silent)", file=sys.stderr)
    else:
        print(f"phase plan {plan['date']}: mode={plan['mode']} "
              f"full={plan['full']} keyword={plan['keyword']}", file=sys.stderr)
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as fh:
            fh.write(f"SWEEP_MODE={plan['mode']}\n")
            fh.write(f"FESTIVAL_SLUGS={','.join(plan['keyword'])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
