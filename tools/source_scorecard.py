#!/usr/bin/env python3
"""Per-source ingestion scorecard — tried, working, remediation, volume, trend.

Founder directive, 2026-07-26: "a scorecard for all ingestion sources that
includes if it's been tried, if it's working, if no to the first two then what
is the remediation/fix to make it work, a count metric score in number of venues
and such flowing through the source, a count of improvements over time for every
measure... This should be an ongoing performance measure."

DESIGN RULE, learned expensively on this project: status is DERIVED from
evidence, never hand-maintained. A hand-kept "working: yes" column is a claim
that rots the first time a feed changes shape, and the whole point of this file
is to stop sources being described as healthy because nobody re-checked. So:

  tried    <- a fetch attempt exists for the source (raw_fetch rows)
  working  <- rows from that source are actually in the store (licensed_event)
  volume   <- counted from the store, per source
  trend    <- diffed against the previous snapshot in the history file

Where evidence is ABSENT the answer is UNKNOWN, printed as UNKNOWN, and never
silently rendered as "no". "We have not measured this" and "this is broken" are
different facts and the remediation for them is different.

The two counts are kept apart on purpose: EVENTS is throughput, VENUES is reach.
A source can pour thousands of events from six rooms; another contributes four
venues nobody else has. Ranking on events alone would retire exactly the sources
the long-tail strategy depends on, so UNIQUE VENUES — venues no other source
supplies — is tracked as its own measure.

Inputs are files so this runs anywhere, including the network-less dev sandbox:
  --registry  the source registry (tools/build_source_registry.py)
  --rows      JSON dump of ingested rows: source_name, venue_name, venue_city
  --attempts  JSON dump of fetch attempts: source_name, ok, at
Without --rows/--attempts the tool still runs and reports UNKNOWN honestly.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.sources.taxonomy import SOURCE_CLASSES  # noqa: E402

HISTORY = REPO / "docs" / "metrics" / "SOURCE_SCORECARD_HISTORY.jsonl"

# Status is a small closed set so it can be counted and trended. Ordered worst
# to best for reporting.
STATUS_NEVER_TRIED = "NEVER_TRIED"
STATUS_BLOCKED_CREDENTIAL = "BLOCKED_CREDENTIAL"
STATUS_TRIED_FAILING = "TRIED_FAILING"
STATUS_TRIED_EMPTY = "TRIED_EMPTY"
STATUS_WORKING = "WORKING"
STATUS_UNKNOWN = "UNKNOWN_NO_EVIDENCE"

STATUS_ORDER = [STATUS_UNKNOWN, STATUS_NEVER_TRIED, STATUS_BLOCKED_CREDENTIAL,
                STATUS_TRIED_FAILING, STATUS_TRIED_EMPTY, STATUS_WORKING]

# The remediation each status implies. Generic by status; a source may override
# with its own `remediation` field when the specific fix is known (e.g. "SSL
# chain broken at austintrailoflights.org"). Every non-working status MUST
# produce a next action — a scorecard row that says "broken" and stops is a
# complaint, not a work item.
REMEDIATION_BY_STATUS = {
    STATUS_NEVER_TRIED: "Wire it into a runner and attempt one fetch; until "
                        "then its yield is unknown, not zero.",
    STATUS_BLOCKED_CREDENTIAL: "Founder mints the credential (agents never mint "
                               "keys); then one dry-run verifies payload shape "
                               "before the feed is trusted.",
    STATUS_TRIED_FAILING: "Read the recorded failure class and fix it: denial "
                          "(UA/robots/ToS), TLS chain, JS-rendered calendar, "
                          "feed at an unguessed path, or payload-shape drift.",
    STATUS_TRIED_EMPTY: "Served but yielded nothing. Confirm whether the "
                        "calendar is genuinely empty or the reader is losing "
                        "rows — those are different defects.",
    STATUS_UNKNOWN: "No evidence available. Connect the store/attempt log and "
                    "re-run before drawing any conclusion.",
    STATUS_WORKING: "",
}


def _index_rows(rows: list, known: set | None = None) -> tuple:
    """(events per source, venue set per source, venue -> sources).

    Evidence that names no source, or names one the registry does not hold, is
    a MISCONFIGURATION and is refused. Skipping it silently excluded real
    delivered rows from a source's score, so a typo or a stale name made a
    working source read as NEVER_TRIED — the scorecard reporting the exact
    false status it exists to prevent. Evaluator finding, PR #86 r1.
    """
    unbound = sorted({(r.get("source_name") or "") for r in rows
                      if not r.get("source_name")
                      or (known is not None and r.get("source_name") not in known)})
    if unbound:
        raise SystemExit(
            f"source_scorecard: FAIL — {len(unbound)} evidence row group(s) "
            f"name no registry source: {unbound[:10]}. Unbound evidence is a "
            f"misconfiguration, not an absence — silently dropping it makes a "
            f"delivering source look never-tried.")
    events: dict = {}
    venues: dict = {}
    venue_owners: dict = {}
    for r in rows:
        src = r.get("source_name")
        events[src] = events.get(src, 0) + 1
        name = (r.get("venue_name") or "").strip().lower()
        if name:
            venues.setdefault(src, set()).add(name)
            venue_owners.setdefault(name, set()).add(src)
    return events, venues, venue_owners


def _index_attempts(attempts: list, known: set | None = None) -> dict:
    """source -> {'n': int, 'ok': int, 'last': iso}

    Same binding rule as _index_rows, and it matters more here: attempts are
    the evidence that distinguishes never-tried from tried-and-failing, so a
    silently dropped attempt turns a source we KNOW is broken into one we
    appear never to have touched."""
    unbound = sorted({(a.get("source_name") or "") for a in attempts
                      if not a.get("source_name")
                      or (known is not None and a.get("source_name") not in known)})
    if unbound:
        raise SystemExit(
            f"source_scorecard: FAIL — {len(unbound)} attempt row group(s) "
            f"name no registry source: {unbound[:10]}. An unbound attempt "
            f"makes a source we know is broken look never-tried.")
    out: dict = {}
    for a in attempts:
        src = a.get("source_name")
        rec = out.setdefault(src, {"n": 0, "ok": 0, "last": None})
        rec["n"] += 1
        if a.get("ok"):
            rec["ok"] += 1
        at = a.get("at")
        if at and (rec["last"] is None or at > rec["last"]):
            rec["last"] = at
    return out


def score_source(entry: dict, events: dict, venues: dict, venue_owners: dict,
                 attempts: dict, have_evidence: bool) -> dict:
    sid = entry.get("id")
    cls = entry.get("source_class")
    meta = SOURCE_CLASSES.get(cls, {})

    n_events = events.get(sid, 0)
    v = venues.get(sid, set())
    n_venues = len(v)
    # Reach that exists ONLY because of this source. This is what makes a
    # four-venue first-party feed worth more than a thousand duplicate rows.
    n_unique = sum(1 for name in v if len(venue_owners.get(name, ())) == 1)
    att = attempts.get(sid, {})

    # ORDER IS THE WHOLE CORRECTNESS ARGUMENT. Evidence outranks assumption.
    #
    # This previously tested the credential FIRST, and `credential_present` is
    # initialised to None for every source because nothing populates it. `not
    # None` is true, so every credentialed source — Ticketmaster included, with
    # real rows in the store — scored BLOCKED_CREDENTIAL and was handed a "mint
    # the key" remediation for a key that is already working. A measure that
    # reports live feeds as blocked is worse than no measure.
    #
    # So: delivered rows are a FACT and settle it. Attempts are a fact and
    # settle it next. Only when there is no attempt at all does the credential
    # matter, and only when it is KNOWN absent — an unknown credential state is
    # not evidence of a missing key, and calling it one is the same fabrication
    # in the other direction.
    if not have_evidence:
        status = STATUS_UNKNOWN
    elif n_events > 0:
        status = STATUS_WORKING
    elif att.get("n"):
        status = (STATUS_TRIED_FAILING if att.get("ok", 0) == 0
                  else STATUS_TRIED_EMPTY)
    elif entry.get("needs_credential") and entry.get("credential_present") is False:
        status = STATUS_BLOCKED_CREDENTIAL
    else:
        status = STATUS_NEVER_TRIED

    return {
        "id": sid,
        "name": entry.get("name"),
        "source_class": cls,
        "provides": meta.get("provides", "?"),
        "trust": meta.get("trust", "?"),
        "status": status,
        "tried": bool(att.get("n")) if have_evidence else None,
        "working": (n_events > 0) if have_evidence else None,
        "events": n_events,
        "venues": n_venues,
        "unique_venues": n_unique,
        "attempts": att.get("n", 0),
        "attempts_ok": att.get("ok", 0),
        # Health: does an attempt actually pay? A source attempted 40 times for
        # 3 events is costing more than it returns.
        "yield_per_attempt": (round(n_events / att["n"], 2)
                              if att.get("n") else None),
        "last_attempt": att.get("last"),
        "remediation": (entry.get("remediation")
                        or REMEDIATION_BY_STATUS.get(status, "")),
        "known_failure_modes": meta.get("known_failure_modes", []),
        "cost": meta.get("cost", "?"),
    }


MEASURES = ("events", "venues", "unique_venues", "attempts_ok",
            "yield_per_attempt")


def diff_against(previous: dict, current: list) -> dict:
    """Per-source deltas plus, for every measure, how many sources IMPROVED.

    The founder asked for "a count of improvements over time for every measure".
    Improvement is counted per measure per snapshot so the direction of travel is
    visible even while absolute numbers stay small — which is the state this
    project is actually in, and a trend that only moves when totals move would
    show nothing for weeks.
    """
    prev_by_id = {r["id"]: r for r in previous.get("sources", [])} if previous else {}
    improved = {m: 0 for m in MEASURES}
    regressed = {m: 0 for m in MEASURES}
    deltas: dict = {}
    for row in current:
        was = prev_by_id.get(row["id"])
        if not was:
            continue
        d: dict = {}
        for m in MEASURES:
            a, b = was.get(m), row.get(m)
            if a is None or b is None:
                continue
            if b > a:
                improved[m] += 1
                d[m] = f"+{round(b - a, 2)}"
            elif b < a:
                regressed[m] += 1
                d[m] = str(round(b - a, 2))
        if d:
            deltas[row["id"]] = d
    # Status moves BOTH ways. Only status_improved existed, while the contract
    # says decay must be visible — so a source sliding from WORKING to
    # TRIED_FAILING moved the trend by zero and read as "nothing happened".
    # A one-directional trend is the flattering direction by construction.
    # Evaluator finding, PR #86 r1.
    status_up = status_down = 0
    for row in current:
        was = prev_by_id.get(row["id"])
        if not was:
            continue
        now_i = STATUS_ORDER.index(row["status"])
        was_i = STATUS_ORDER.index(was["status"])
        if now_i > was_i:
            status_up += 1
        elif now_i < was_i:
            status_down += 1
    return {"improved": improved, "regressed": regressed,
            "status_improved": status_up, "status_regressed": status_down,
            "per_source": deltas}


def load_json(path: str | None, default):
    if not path:
        return default
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def last_snapshot() -> dict | None:
    if not HISTORY.exists():
        return None
    lines = [ln for ln in HISTORY.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return json.loads(lines[-1]) if lines else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=str(REPO / "sources" / "source_registry.json"))
    ap.add_argument("--rows", help="JSON dump of ingested rows")
    ap.add_argument("--attempts", help="JSON dump of fetch attempts")
    ap.add_argument("--record", action="store_true",
                    help="append this snapshot to the history file (the ongoing measure)")
    ap.add_argument("--stamp", help="ISO timestamp for the snapshot (CI supplies it)")
    args = ap.parse_args(argv)

    reg = json.loads(pathlib.Path(args.registry).read_text(encoding="utf-8"))
    # `reg.get(...)` resolves the method on `reg` BEFORE the default
    # expression is evaluated, so a top-level JSON array crashed here
    # rather than being read. Evaluator nit, PR #86 r1.
    entries = reg if isinstance(reg, list) else reg.get("sources", [])

    rows = load_json(args.rows, [])
    attempts_raw = load_json(args.attempts, [])
    # "We measured, and nothing happened" is a RESULT. "We did not measure" is
    # not. Deriving this from the file CONTENTS collapsed the two: a successful
    # database read returning zero rows scored every source UNKNOWN, exactly as
    # if the dump had never run — so the scorecard could never report a genuinely
    # empty pipeline, which is the state it most needs to be able to report.
    # Supplied-ness is the honest signal, so it is read from the ARGUMENTS.
    have_evidence = args.rows is not None or args.attempts is not None

    # The registry's own ids AND names are the namespace evidence must bind to.
    known = {e.get("id") for e in entries} | {e.get("name") for e in entries}
    known.discard(None)
    events, venues, venue_owners = _index_rows(rows, known)
    attempts = _index_attempts(attempts_raw, known)
    scored = [score_source(e, events, venues, venue_owners, attempts, have_evidence)
              for e in entries]
    scored.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), -r["events"]))

    prev = last_snapshot()
    trend = diff_against(prev, scored)

    by_status: dict = {}
    for r in scored:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    print("=" * 72)
    print(f" SOURCE SCORECARD — {len(scored)} source(s)")
    print("=" * 72)
    if not have_evidence:
        print(" NO EVIDENCE SUPPLIED — every status is UNKNOWN, which is NOT the")
        print(" same as 'not working'. Pass --rows/--attempts to measure.")
    elif not rows and not attempts_raw:
        print(" EVIDENCE SUPPLIED AND EMPTY — this IS a measurement: nothing has")
        print(" been fetched and nothing has been stored. Not the same as unmeasured.")
    print()
    for status in STATUS_ORDER:
        if by_status.get(status):
            print(f"  {status:<22} {by_status[status]}")
    print()
    print(f"  {'SOURCE':<30} {'CLASS':<20} {'STATUS':<20} {'EV':>6} {'VEN':>5} {'UNIQ':>5}")
    print(f"  {'-'*30} {'-'*20} {'-'*20} {'-'*6} {'-'*5} {'-'*5}")
    for r in scored[:60]:
        print(f"  {str(r['name'])[:30]:<30} {str(r['source_class'])[:20]:<20} "
              f"{r['status']:<20} {r['events']:>6} {r['venues']:>5} "
              f"{r['unique_venues']:>5}")
    if len(scored) > 60:
        print(f"  … {len(scored) - 60} more (full detail in the JSON snapshot)")

    print()
    print("-- NEEDS ACTION --------------------------------------------------")
    acted = [r for r in scored if r["status"] != STATUS_WORKING and r["remediation"]]
    for r in acted[:25]:
        print(f"  [{r['status']}] {r['name']}")
        print(f"      -> {r['remediation']}")
    if len(acted) > 25:
        print(f"  … {len(acted) - 25} more")

    print()
    print("-- TREND vs previous snapshot ------------------------------------")
    if prev is None:
        print("  FIRST SNAPSHOT — no trend yet. Re-run with --record to build one.")
    else:
        print(f"  previous snapshot: {prev.get('stamp')}")
        for m in MEASURES:
            print(f"    {m:<20} improved {trend['improved'][m]:>3} · "
                  f"regressed {trend['regressed'][m]:>3}")
        print(f"    {'status':<20} improved {trend['status_improved']:>3}   "
              f"REGRESSED {trend['status_regressed']:>3}")

    snapshot = {"stamp": args.stamp or "unstamped",
                "source_count": len(scored),
                "have_evidence": have_evidence,
                "by_status": by_status,
                "totals": {m: sum(r[m] or 0 for r in scored)
                           for m in ("events", "venues", "unique_venues")},
                "trend": {k: v for k, v in trend.items() if k != "per_source"},
                "sources": scored}
    if args.record:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(snapshot) + "\n")
        print(f"\n  recorded -> {HISTORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
