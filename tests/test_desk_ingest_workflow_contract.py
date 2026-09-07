"""Structural contract test for .github/workflows/desk-ingest.yml.

ONE coupling, pinned mechanically: the write job's wall clock must be
large enough to cover the walk it is configured to do AND the write that
follows it.

WHY THIS TEST EXISTS — the run that proved 30 was too small:

  Dispatch 34079785167 (master, write=true, default doors) validated the
  DSN, walked both desks, and printed its ~1584-row plan at 03:39Z. It
  was still writing 20 minutes later when GitHub cancelled the job at
  03:59Z on `timeout-minutes: 30` (run_duration 1822s = 30.4 min).
  Python was alive at the kill, mid-write, so a partial wave in the
  catalog is possible — the one failure the ingest key cannot see, since
  a half-written run leaves keys the NEXT run reads as already-written.

  A cancelled writer is not a failed writer, and 30 minutes cancels this
  one every time: the walk alone spends most of that budget before the
  first row is written.

HONEST LIMIT, stated so nobody reads this test as a proof it is not: 60
is derived from the walk floor below plus the observed fact that 20
minutes of writing was not enough. Nobody has yet MEASURED a completed
1584-row write, so 60 is a ceiling this run fits under, not a measured
duration. If a dispatch is cancelled again at 60, that is new evidence
and a new ticket — not a cue to shrink the walk by raising politeness or
cutting the follow cap.

The number 60 is also `ingest.yml`'s, the repo's other job that writes to
the catalog — this brings the desks in line with it rather than inventing
a budget.
"""
import pathlib
import re
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WF = (_ROOT / ".github" / "workflows" / "desk-ingest.yml").read_text()

# The minutes the walk must leave behind for the write. Every input to
# the arithmetic is READ from the tree (below), never retyped: the page
# ceiling the workflow dispatches with, the founder follow cap, the
# politeness delay between live fetches, and HOW MANY DOORS A DEFAULT
# DISPATCH WALKS. That last one was the literal `2` until 2026-09-07,
# when the default became every public door in the locale pack: the LIST
# phase can now spend `doors * max_pages` fetches before a single event
# page is followed, so a test still multiplying by two would compute a
# floor for a walk this workflow no longer does — and would keep passing
# while the job it guards was cancelled mid-write.
#
# 20 is deliberately a KNOWN-INSUFFICIENT floor — run 34079785167 spent
# 20 minutes writing and did not finish. So this constant is a drift
# ALARM (the walk must not grow into the write's budget), never a proof
# that the remaining time is enough. Measuring what a completed
# 1584-row write actually costs is what the next green write gives us.
_WALK_FLOOR_MINUTES_MUST_LEAVE_FOR_THE_WRITE = 20


def _yaml_scalar(key: str) -> str:
    """The one value `key:` is given in the workflow, or fail loudly."""
    hits = re.findall(rf'^\s*{re.escape(key)}:\s*"?([^"\n#]+?)"?\s*$',
                      _WF, re.MULTILINE)
    assert len(hits) == 1, (
        f"desk-ingest.yml must give {key!r} exactly one value, found {hits!r}")
    return hits[0]


def _job_timeout_minutes() -> int:
    return int(_yaml_scalar("timeout-minutes"))


def _dispatched_max_pages() -> int:
    """The `max_pages` default a founder dispatch actually runs with."""
    block = re.search(r'^\s+max_pages:\s*$\n(?:\s+.*\n)+?\s+default:\s*"(\d+)"',
                      _WF, re.MULTILINE)
    assert block, "desk-ingest.yml no longer declares a max_pages default"
    return int(block.group(1))


def _default_doors_walked() -> int:
    """How many doors a dispatch with an EMPTY `doors` input walks.

    Read from the tool and the pack, never counted by hand: the workflow
    passes no `--door` in that case, and `desk_ingest.default_doors`
    derives the list from `sources/locale_packs/<locale>.json`.
    """
    sys.path.insert(0, str(_ROOT))
    from tools.desk_ingest import default_doors  # noqa: PLC0415

    src = (_ROOT / "tools" / "desk_ingest.py").read_text()
    locale = re.search(r'"--locale",\s*default="([^"]+)"', src)
    assert locale, "tools/desk_ingest.py no longer defaults --locale"
    doors = default_doors(locale.group(1))
    assert doors, f"the {locale.group(1)!r} pack offers no public door to walk"
    return len(doors)


def _walk_constants() -> tuple:
    """Follow cap + politeness delay, read from desk_ingest.py itself."""
    src = (_ROOT / "tools" / "desk_ingest.py").read_text()
    cap = re.search(r"^DEFAULT_FOLLOW_PAGES\s*=\s*(\d+)", src, re.MULTILINE)
    assert cap, "tools/desk_ingest.py no longer defines DEFAULT_FOLLOW_PAGES"
    interval = re.search(
        r'"--min-interval",\s*type=float,\s*default=([\d.]+)', src)
    assert interval, "tools/desk_ingest.py no longer defaults --min-interval"
    return int(cap.group(1)), float(interval.group(1))


def test_the_write_job_gets_at_least_an_hour():
    """30 cancelled the 1584-row write of 34079785167. 60 is the floor now."""
    assert _job_timeout_minutes() >= 60, (
        "desk-ingest.yml writes the catalog; run 34079785167 was cancelled "
        "mid-write at the 30-minute wall (see this module's docstring). "
        "Lowering the ceiling below 60 re-arms that cancellation — and a "
        "cancelled writer leaves a partial wave, not a clean failure.")


def test_the_ceiling_still_covers_the_walk_with_the_write_left_over():
    """The walk may not grow into the time the write needs.

    This is the leg that catches the OTHER direction of drift: raising
    the follow cap or the page ceiling silently spends the write's
    budget, and the symptom is identical to the one this PR fixed — a
    job cancelled with rows half-written.
    """
    follow_cap, interval = _walk_constants()
    max_pages = _dispatched_max_pages()
    doors = _default_doors_walked()
    # Politeness sleeps are the walk's floor: fetch time is on top of them.
    walk_floor_minutes = (doors * max_pages + follow_cap) * interval / 60.0
    headroom = _job_timeout_minutes() - walk_floor_minutes
    assert headroom >= _WALK_FLOOR_MINUTES_MUST_LEAVE_FOR_THE_WRITE, (
        f"the walk's politeness floor is {walk_floor_minutes:.1f} min "
        f"({doors} door(s) x {max_pages} = {doors * max_pages} list + "
        f"{follow_cap} event fetches at {interval}s), "
        f"leaving only {headroom:.1f} min of the "
        f"{_job_timeout_minutes()}-minute job for the write itself — "
        f"under the {_WALK_FLOOR_MINUTES_MUST_LEAVE_FOR_THE_WRITE} min that "
        f"run 34079785167 spent writing WITHOUT finishing. Raise "
        f"timeout-minutes in the same PR as the cap, or leave the cap alone.")
