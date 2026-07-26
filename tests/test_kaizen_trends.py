"""Tests for tools/kaizen_trends.py — the mechanical Kaizen trend meter.

The meter's job (founder direction 2026-07-18): trends are COMPUTED, never
asserted. These tests cover the parser, the class-family alarm (the mechanized
repeat-class rule the evaluator enforced by judgment on PR #35 r2), the
addressed-marker logic, escape detection, and a smoke run against the real
ledger.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.kaizen_trends import (
    build_report,
    class_counts,
    family_alarm,
    family_groups,
    family_marker_last_row,
    m1_direction,
    open_escapes,
    parse_pr_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "kaizen_trends.py"
REAL_LEDGER = REPO_ROOT / "docs" / "metrics" / "KAIZEN_LEDGER.md"

FAKE_LEDGER = """
# KAIZEN LEDGER (fixture)

## PR rows

| Date | PR | M1 rounds | M2 catches (gate: class × n) | M4 gate-gaps closed | M5 est. cost | Notes |
|---|---|---|---|---|---|---|
| 2026-07-01 | #1 | 5 | evaluator: empty-env ×1, silent-truncation ×1 | — | ~5 calls | |
| 2026-07-02 | #2 | 4 | CI: empty-env ×1; evaluator: coverage-gap ×2 | coverage floor added | ~4 calls | |
| 2026-07-03 | #3 | 2 | evaluator: fail-open-empty-env ×2 | — | ~2 calls | |
| 2026-07-04 | #4 | 1 | founder(Red): missed-citation ×1 | addressed-thing fixed | ~1 call | |

## Other section (ignored by the parser)

| 2026-07-05 | not-a-pr-row | x | fake ×9 | | | |
"""


def test_parser_reads_only_pr_rows():
    rows = parse_pr_rows(FAKE_LEDGER)
    assert len(rows) == 4
    assert rows[0]["pr"] == "#1"
    assert all("fake" not in r["m2"] for r in rows)


def test_class_counts_sum_across_rows():
    counts = class_counts(parse_pr_rows(FAKE_LEDGER))
    assert counts["empty-env"] == 2
    assert counts["fail-open-empty-env"] == 2
    assert counts["coverage-gap"] == 2


def test_containment_families_group_related_tokens():
    groups = family_groups(["empty-env", "fail-open-empty-env", "coverage-gap"])
    fams = [sorted(g) for g in groups]
    assert ["empty-env", "fail-open-empty-env"] in fams
    assert ["coverage-gap"] in fams


def test_unaddressed_family_over_threshold_raises_finding():
    # empty-env family totals 4 with no M4 marker naming it → alarm.
    _, findings = build_report(FAKE_LEDGER)
    assert any("empty-env" in f and "REPEAT-CLASS ALARM" in f for f in findings)


def test_marker_row_is_located_exactly():
    rows = parse_pr_rows(FAKE_LEDGER)
    assert family_marker_last_row({"addressed-thing"}, rows) == 3
    assert family_marker_last_row({"empty-env", "fail-open-empty-env"}, rows) is None


def test_recurrence_after_marker_alarms_immediately():
    # Evaluator r6: a fix marker covers catches at-or-before its row ONLY.
    # One recurrence after it = "the fix escaped" — alarms at count 1, not 3.
    extra = (
        "| 2026-07-05 | #5 | 1 | evaluator: coverage-gap ×2 | coverage-gap floor v2 | — | fix row |\n"
        "| 2026-07-06 | #6 | 1 | evaluator: coverage-gap ×1 | — | — | recurrence |\n"
    )
    ledger = FAKE_LEDGER.replace(
        "\n## Other section", "\n" + extra + "\n## Other section"
    )
    rows = parse_pr_rows(ledger)
    alarm = family_alarm({"coverage-gap"}, rows, 3)
    assert alarm is not None and "RECURRED" in alarm and "fix escaped" in alarm


def test_marker_covers_prior_catches_without_alarm():
    ledger = FAKE_LEDGER.replace(
        "\n## Other section",
        "\n| 2026-07-05 | #5 | 1 | — | empty-env linter shipped | — | fix row |\n\n## Other section",
    )
    rows = parse_pr_rows(ledger)
    assert family_alarm({"empty-env", "fail-open-empty-env"}, rows, 3) is None


def test_m1_direction_falling_is_improving():
    assert "FALLING" in m1_direction([5, 4, 2, 1])
    assert "RISING" in m1_direction([1, 2, 4, 5])
    assert m1_direction([3]) == "insufficient data"


# --- M3 escape semantics, founder-ratified 2026-07-26 ("option a") -----------
# The blocking condition is "an escape whose gate gap is still OPEN", not "any
# escape ever recorded". The count is permanent and stays visible; a closed gap
# stops blocking. Mirrors what family_alarm already does for repeat classes.

_ESCAPE_TABLE = """
## M3 escapes (absolute-zero goal)

| Date | What escaped | Where found | Root cause | Gate-gap closed |
|---|---|---|---|---|
{rows}

## After
"""


def _ledger_with_escapes(*rows: str) -> str:
    return FAKE_LEDGER.replace(
        "\n## Other section",
        _ESCAPE_TABLE.format(rows="\n".join(rows)) + "\n## Other section")


_OPEN_ROW = ("| 2026-07-06 | M3-ESCAPE prod-bad-fact | prod | nothing tested it "
             "| — |")
# Cites a file that REALLY EXISTS. It used to name `tests/test_thing.py`, which
# does not, and the gate accepted it — the PR #80 blocker
# `CLASS:unvalidated-escape-closure`: closure was satisfied by any non-placeholder
# prose, so `fixed` typed into the column turned the M3 alarm green. Pointing this
# fixture at a real path is what makes the tests below discriminate.
_CLOSED_ROW = ("| 2026-07-06 | M3-ESCAPE prod-bad-fact | prod | nothing tested it "
               "| `tests/test_kaizen_trends.py`, proven red first |")


def test_an_escape_with_an_open_gate_gap_is_a_hard_finding():
    _, findings = build_report(_ledger_with_escapes(_OPEN_ROW))
    assert any("OPEN GATE GAP" in f for f in findings), findings


def test_an_escape_whose_gap_is_closed_no_longer_blocks():
    """The whole point of option (a): permanent history, not permanent red."""
    report, findings = build_report(_ledger_with_escapes(_CLOSED_ROW))
    assert not any("OPEN GATE GAP" in f for f in findings), findings
    # ...and the escape is STILL counted and visible. Never silently forgiven.
    assert "m3_escapes: 1" in report
    assert "m3_escapes_open: 0" in report


def test_a_closed_escape_does_not_excuse_a_later_open_one():
    report, findings = build_report(_ledger_with_escapes(_CLOSED_ROW, _OPEN_ROW))
    assert any("OPEN GATE GAP" in f for f in findings), findings
    assert "m3_escapes: 2" in report
    assert "m3_escapes_open: 1" in report


def test_a_malformed_escape_row_fails_closed():
    """A row that cannot be shown to have a closed gap must count as open."""
    malformed = "| 2026-07-06 | M3-ESCAPE something |"
    _, findings = build_report(_ledger_with_escapes(malformed))
    assert any("OPEN GATE GAP" in f for f in findings), findings


@pytest.mark.parametrize("filler", ["", "-", "—", "none", "TBD", "pending",
                                    "not yet", "n/a"])
def test_placeholder_text_does_not_count_as_a_closed_gap(filler):
    row = f"| 2026-07-06 | M3-ESCAPE x | prod | cause | {filler} |"
    _, findings = build_report(_ledger_with_escapes(row))
    assert any("OPEN GATE GAP" in f for f in findings), (filler, findings)


@pytest.mark.parametrize("prose", [
    "fixed", "done", "closed", "resolved", "we shipped a test for it",
    "the gate now covers this", "handled in review", "asdf",
    # The near-miss that matters most: a citation SHAPED like a path but naming
    # nothing on disk. Accepting it is indistinguishable from accepting prose.
    "`tests/test_definitely_not_a_real_file.py`",
    "see `tools/no_such_tool.py`",
    "R-999 covers it",
])
def test_prose_that_names_no_REAL_mechanism_does_not_close_a_gap(prose):
    """`CLASS:unvalidated-escape-closure` (openai/attacker-smuggle, PR #80).

    The M3 alarm guards an ABSOLUTE-ZERO target, and its pass condition was
    "the cell is not a placeholder" — so the alarm could be silenced by typing.
    A closure must cite a repo path that exists or a RECORD.md row that exists;
    a machine still cannot judge whether the named test is ADEQUATE, but it can
    refuse a citation that points at nothing.
    """
    row = f"| 2026-07-06 | M3-ESCAPE x | prod | cause | {prose} |"
    _, findings = build_report(_ledger_with_escapes(row))
    assert any("OPEN GATE GAP" in f for f in findings), (prose, findings)


@pytest.mark.parametrize("citation", [
    "`tests/test_kaizen_trends.py`",
    "`tools/kaizen_trends.py` — proven red on the old form",
    "closed by tests/test_watchdog_check.py which scans every workflow",
    "`.github/workflows/watchdog.yml` ships the alarm",
    "deferred deliberately, tracked as R-002 with an objective trigger",
])
def test_a_citation_that_resolves_on_disk_does_close_a_gap(citation):
    """The other half — without this the tightening would just be a permanent
    red, which is the ignored-gate failure option (a) was ratified to avoid."""
    row = f"| 2026-07-06 | M3-ESCAPE x | prod | cause | {citation} |"
    report, findings = build_report(_ledger_with_escapes(row))
    assert not any("OPEN GATE GAP" in f for f in findings), (citation, findings)
    assert "m3_escapes: 1" in report and "m3_escapes_open: 0" in report


def test_the_closure_column_is_indexed_from_the_front_not_the_end():
    """`cells[-1]` graded whatever the LAST column happened to be, so appending a
    sixth column to the escapes table would silently move the check onto it
    (reviewer nit, gemini seat, PR #80). Column 5 is the contract."""
    from tools.kaizen_trends import open_escapes
    header = ("## M3 escapes\n\n"
              "| Date | What escaped | Where found | Root cause | Gate-gap closed "
              "| Notes |\n|---|---|---|---|---|---|\n")
    # Column 5 is a real citation; a sixth column of prose must not change the
    # answer in either direction.
    closed = (header + "| 2026-07-06 | M3-ESCAPE x | prod | cause "
              "| `tests/test_kaizen_trends.py` | some later note |\n")
    assert open_escapes(closed) == []
    # ...and prose in column 5 stays OPEN even when column 6 looks like a citation.
    still_open = (header + "| 2026-07-06 | M3-ESCAPE x | prod | cause "
                  "| fixed | `tests/test_kaizen_trends.py` |\n")
    assert len(open_escapes(still_open)) == 1


def test_the_citation_resolver_is_injectable_so_the_rule_is_testable():
    """The default resolves against the working tree; tests must be able to state
    the rule without depending on which files happen to exist today."""
    from tools.kaizen_trends import open_escapes
    header = ("## M3 escapes\n\n| Date | What | Where | Cause | Gate-gap closed |\n"
              "|---|---|---|---|---|\n")
    row = header + "| 2026-07-06 | M3-ESCAPE x | prod | cause | anything at all |\n"
    assert open_escapes(row, cited_mechanisms=lambda cell: ["pretend.py"]) == []
    assert len(open_escapes(row, cited_mechanisms=lambda cell: [])) == 1


def test_the_all_time_count_can_never_be_reduced_by_closing_a_gap():
    open_report, _ = build_report(_ledger_with_escapes(_OPEN_ROW))
    closed_report, _ = build_report(_ledger_with_escapes(_CLOSED_ROW))
    assert "m3_escapes: 1" in open_report
    assert "m3_escapes: 1" in closed_report


def test_report_contains_the_curves():
    report, _ = build_report(FAKE_LEDGER)
    for needle in (
        "m3_escapes: 0",
        "m1_rounds_to_green",
        "founder_red_catches: 1",
        "catches_per_gate",
        "repeat_class_alarms",
    ):
        assert needle in report


def test_cli_missing_ledger_fails_closed():
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--ledger", "docs/NO_SUCH_LEDGER.md"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 2
    assert "cannot read" in proc.stderr


def test_real_ledger_parses_and_has_no_open_escape_gaps():
    """Smoke against the live ledger.

    Renamed from ...has_zero_escapes: under option (a) the live ledger records
    ONE escape permanently (2026-07-26, the cron that could never run) and that
    number must never go down. What must be zero is escapes with an OPEN gate
    gap. If this fails, that is the alarm working — an escape was recorded
    without a shipped mechanism.
    """
    text = REAL_LEDGER.read_text(encoding="utf-8")
    report, findings = build_report(text)
    assert "ledger_rows:" in report
    assert "m3_escapes_open: 0" in report
    assert not any("OPEN GATE GAP" in f for f in findings), findings
    # The recorded escape is still there and still counted — history is permanent.
    assert "m3_escapes: 0 (" not in report, "the recorded escape vanished from the ledger"


def test_short_class_tokens_are_counted():
    # Evaluator r4: a length floor would let `sql ×3`-style trust-critical
    # classes escape the alarm entirely.
    ledger = FAKE_LEDGER.replace(
        "evaluator: empty-env ×1, silent-truncation ×1",
        "evaluator: sql ×3, empty-env ×1",
    )
    counts = class_counts(parse_pr_rows(ledger))
    assert counts["sql"] == 3


def test_m4_credit_requires_exact_token_not_substring():
    # Evaluator r4: "not-empty-env-fixed" in an M4 cell must NOT credit the
    # empty-env family (the r3 loose-binding pattern, meter edition).
    rows = parse_pr_rows(
        FAKE_LEDGER.replace("| — | ~2 calls |", "| not-empty-env-fixed | ~2 calls |", 1)
    )
    assert family_marker_last_row({"empty-env", "fail-open-empty-env"}, rows) is None
    rows2 = parse_pr_rows(
        FAKE_LEDGER.replace("| — | ~2 calls |", "| empty-env linter shipped | ~2 calls |", 1)
    )
    assert family_marker_last_row({"empty-env", "fail-open-empty-env"}, rows2) is not None


def test_generic_single_segment_token_does_not_absorb_compounds():
    # A bare `gap` (from an old prose-style row) must not family with
    # `coverage-gap`; but exact repeats of short tokens still count, and
    # multi-segment containment still groups.
    groups = family_groups(["gap", "coverage-gap", "empty-env", "fail-open-empty-env", "sql"])
    fams = [sorted(g) for g in groups]
    assert ["gap"] in fams
    assert ["coverage-gap"] in fams
    assert ["empty-env", "fail-open-empty-env"] in fams
    assert ["sql"] in fams


def test_code_span_pipes_do_not_shift_columns():
    # Evaluator r16: a row quoting shell like `|| exit` must parse into the
    # SAME 7 columns — class tokens and M4 markers read from the right cells.
    extra = (
        "| 2026-07-07 | #7 | 1 | evaluator: pipe-class ×1 (caught `[ -n ] || exit` form) "
        "| pipe-class fixed via `|| exit` rule | ~1 call | notes |\n"
    )
    ledger = FAKE_LEDGER.replace("\n## Other section", "\n" + extra + "\n## Other section")
    rows = parse_pr_rows(ledger)
    row = next(r for r in rows if r["pr"] == "#7")
    assert "pipe-class" in row["m2"]
    assert "pipe-class" in row["m4"]
    assert row["m5"] == "~1 call"


def test_malformed_row_fails_loud():
    import pytest as _pytest
    extra = "| 2026-07-08 | #8 | 1 | raw | pipe | breaks | cells | badly | notes |\n"
    ledger = FAKE_LEDGER.replace("\n## Other section", "\n" + extra + "\n## Other section")
    with _pytest.raises(ValueError):
        parse_pr_rows(ledger)


def test_a_citation_OUTSIDE_the_repo_does_not_close_a_gap(tmp_path):
    """`CLASS:dataflow-taint-unvalidated-input` (gemini/dataflow-taint, PR #80 r4).

    `(root / candidate).exists()` was not containment: `Path("/repo") / "/tmp/x.py"`
    discards `/repo` and returns `/tmp/x.py`, so a citation naming ANY absolute
    path to an existing host file closed an M3 escape — a bypass of the check
    written one round earlier to stop prose closing that alarm. `..` traversal is
    the same hole with extra steps.
    """
    from tools.kaizen_trends import _cited_mechanisms, _resolves_inside

    outside = tmp_path / "outside.py"
    outside.write_text("# a real file, in the wrong place\n", encoding="utf-8")
    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    inside = root / "tools" / "real.py"
    inside.write_text("# a real file, in the right place\n", encoding="utf-8")

    # Absolute path to a file that EXISTS — rejected because it is not in the repo.
    assert _cited_mechanisms(f"`{outside}`", root) == []
    assert not _resolves_inside(root, str(outside))
    # `..` traversal escaping the root — same answer.
    assert _cited_mechanisms("`tools/../../outside.py`", root) == []
    # A directory is not a mechanism, even inside the root.
    assert not _resolves_inside(root, "tools")
    # ...and the legitimate citation still resolves, or the fix is a permanent red.
    assert _cited_mechanisms("`tools/real.py`", root) == ["tools/real.py"]
    # Traversal that stays INSIDE is fine — the rule is containment, not syntax.
    assert _resolves_inside(root, "tools/../tools/real.py")


def test_the_traversal_bypass_would_have_closed_a_real_escape(tmp_path):
    """The bypass asserted end-to-end through build_report, not just the helper —
    a containment check that the caller does not use is not a control."""
    outside = tmp_path / "elsewhere.py"
    outside.write_text("# not ours\n", encoding="utf-8")
    row = f"| 2026-07-06 | M3-ESCAPE x | prod | cause | `{outside}` |"
    _, findings = build_report(_ledger_with_escapes(row))
    assert any("OPEN GATE GAP" in f for f in findings), findings
