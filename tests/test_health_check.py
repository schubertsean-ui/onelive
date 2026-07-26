"""Tests for tools/health_check.py — the whole-system checkup.

Greppable summary: the health check's job is to be TRUSTWORTHY, so these tests
target the two ways a measurement tool betrays you: reporting a number it did not
compute (a silent zero where the truth is "could not measure"), and reporting a
comparison that is not like-for-like. Both failure modes were live in the first
draft of this tool and are pinned here.

The dead-module detector gets the most attention because it is the only part that
makes a judgement rather than a count, and a detector that cries wolf is one
nobody reads — so its three entrypoint exemptions are asserted against the real
shapes in this repo that motivated them.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    """tools/ is not a package — load the module by path (same idiom as
    tests/test_arming_smoke_binding.py).

    The sys.modules registration is REQUIRED, not tidiness: the module defines a
    @dataclass, and dataclasses resolves field types via
    sys.modules[cls.__module__], which raises AttributeError for a module loaded
    by path and never registered. Omitting it fails at collection time.
    """
    spec = importlib.util.spec_from_file_location(
        "health_check", _ROOT / "tools" / "health_check.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


hc = _load()


# --- the founding anti-pattern: an unmeasurable metric must not read as zero ---

def test_unmeasurable_metric_is_reported_unverified_never_zero():
    rep = hc.Report()
    rep.note_unverified("live event count", "network egress blocked (403)")
    assert rep.unverified, "the reason must be retained, not swallowed"
    metric, before, after, _ = rep.rows[0]
    assert before == "UNVERIFIED" and after == "UNVERIFIED", (
        "an unmeasurable metric must render as UNVERIFIED in BOTH columns — a 0 "
        "here would make 'we could not measure' look identical to 'the number is "
        "fine', which is the project's founding anti-pattern"
    )
    assert "403" in rep.unverified[0], "the reason must survive to the reader"


def test_render_states_plainly_when_nothing_is_unverified():
    rep = hc.Report()
    rep.add("something", 1, 2, "F5")
    out = hc.render(rep, "abc123", "def456")
    assert "All metrics computed; nothing unverified." in out, (
        "silence about verification is not the same as verified; the report must "
        "say which it is"
    )


def test_render_surfaces_the_unverified_section():
    rep = hc.Report()
    rep.note_unverified("open PRs", "no GitHub credential in this environment")
    out = hc.render(rep, None, "def456")
    assert "UNVERIFIED — measured nothing, and says so" in out
    assert "no GitHub credential" in out


# --- like-for-like comparison: the flaw the first draft shipped with ---

def test_read_before_code_picks_the_binding_set_for_the_ref():
    """At HEAD the modern CANON set exists, so it must be the one measured."""
    words, found, which = hc.read_before_code(None)
    assert found == len(hc.READ_BEFORE_CODE), "every CANON doc should be present at HEAD"
    assert which.startswith("CANON"), which
    assert words > 0


def test_read_before_code_falls_back_to_the_legacy_set_on_an_old_ref():
    """On a ref predating the restructure, measuring today's four files would
    report a surface that GREW from one document to four — the opposite of what
    happened. The legacy set must be measured instead, and named."""
    words, found, which = hc.read_before_code("f907a51")
    assert which.startswith("legacy"), (
        f"expected the legacy set on a pre-restructure ref, got {which!r} — an "
        f"apples-to-oranges comparison presented as a trend is worse than none"
    )
    assert found >= 6, f"most of the legacy set should exist at that ref, found {found}"
    assert words > 0


def test_the_two_binding_sets_are_disjoint_enough_to_tell_apart():
    """If the sets were identical the fallback could never be detected, and the
    like-for-like guarantee would be vacuous."""
    assert set(hc.READ_BEFORE_CODE) != set(hc.LEGACY_READ_BEFORE_CODE)


# --- the detector's judgement calls, pinned to the real shapes that motivated them ---

@pytest.mark.parametrize(
    "label,source,path,workflows",
    [
        ("__main__ guard (ordinary CLI)", "if __name__ == '__main__':\n    main()\n", "tools/x.py", ""),
        ("ASGI app (api/main.py shape)", "from fastapi import FastAPI\napp = FastAPI()\n", "api/main.py", ""),
        ("workflow-invoked script", "print('hi')\n", "tools/sample_feed.py",
         "run: python3 tools/sample_feed.py\n"),
    ],
)
def test_entrypoints_are_not_reported_as_dead_code(label, source, path, workflows):
    assert hc._is_entrypoint(path, source, workflows), (
        f"{label} is REACHED rather than imported — reporting it as unwired would "
        f"be a false positive, and a detector that cries wolf gets ignored"
    )


def test_an_ordinary_importable_module_is_not_treated_as_an_entrypoint():
    assert not hc._is_entrypoint(
        "worker/helper.py", "def f():\n    return 1\n", ""
    ), "the exemptions must be narrow, or real dead code hides behind them"


def test_a_reexport_shim_with_no_callers_is_still_detected():
    """A re-export shim is the subtlest dead-code shape: it looks like
    infrastructure and imports something real, so it reads as load-bearing.

    This is not hypothetical — `worker/multiconfirm.py` was exactly this (a shim
    whose own docstring said "keep this file import-only") and was DELETED on
    2026-07-26 once this detector showed nothing imported it. The shape is pinned
    here so narrowing the entrypoint exemptions can never accidentally exempt the
    next one."""
    assert not hc._is_entrypoint(
        "worker/some_shim.py",
        '"""Thin re-export shim."""\nfrom worker.gating import multi_confirm_gate\n',
        "",
    )


def test_unwired_modules_returns_paths_that_exist_and_finds_known_instances():
    found = hc.unwired_modules(None)
    assert isinstance(found, list)
    for path in found:
        assert (_ROOT / path).is_file(), f"reported a path that is not in the tree: {path}"
    # Two instances the 2026-07-26 audit found BY HAND. If the detector cannot
    # see them, it is not doing the job the audit needed a mechanism for.
    assert "worker/publish_policy.py" in found, (
        "the founder-ratified auto-publish policy is imported by nothing but its "
        "own test (audit D3 / R-056) — the detector must independently find it"
    )
    assert "worker/source_reliability.py" in found, (
        "safeguard 1 of the auto-publish ratification is not live (R-056) — the "
        "detector must independently find that too"
    )


def test_escape_count_reads_the_documented_convention():
    """docs/KAIZEN.md requires an M3 escape row to carry the literal token. The
    health check must count the same way the Kaizen gate does, or the two
    disagree about whether the project has escaped a defect."""
    assert hc.escape_count(None) >= 1, (
        "the first recorded escape must be visible to the health check"
    )
    assert hc.escape_count("f907a51") == 0, "no escape was recorded at that baseline"


def test_bar_status_counts_rows_and_purpose_rows():
    counts = hc.bar_status(None)
    assert counts["rows"] > 0
    assert counts["purpose_rows"] > 0, "section P must be counted separately"
    assert counts["rows"] >= counts["purpose_rows"]
    graded = counts["MET"] + counts["NOT MET"] + counts["UNMEASURED"] + counts["NOT BUILT"]
    assert graded > 0, "statuses must parse; an ungraded bar is an unmeasured bar"


def test_gate_metric_counts_gate_files_not_the_whole_tools_directory():
    """The strongest claim the 2026-07-26 work makes is 'no gate was weakened',
    and this is its mechanical form — so what it counts has to be exactly right.

    The first version counted every file under `tools/`, which broke the moment a
    NEW NON-GATING tool (health_check.py itself) landed there: tools/ changed,
    no threshold moved, and the metric reported a gate change that had not
    happened. The enumeration is the fix, and it is asserted here so nobody
    widens it back to a directory glob."""
    assert "tools/validate" in hc.GATE_FILES
    assert "tools/trust_gate.py" in hc.GATE_FILES
    assert "ai/exam_thresholds.py" in hc.GATE_FILES, (
        "threshold constants are gate-defining even though they live outside tools/"
    )
    assert "tools/health_check.py" not in hc.GATE_FILES, (
        "the health check is a thermometer, not a gate — listing it here would "
        "make every change to it look like a gate change"
    )
    # The DECLARED change set. `tools/validate` gained one `run_advisory` line on
    # 2026-07-26 to wire the health check into the ongoing process; that is
    # additive and non-blocking. Any OTHER gate file appearing here means a
    # threshold or a check moved, which needs saying out loud — so this asserts
    # the exact set rather than a count, and the correct response to a failure is
    # to state the change, never to widen the expectation.
    #
    # THE DECLARED SET GREW ON 2026-07-26, AND HERE IS EVERY REASON. This test
    # failed when it grew, which is the test working; the fix is this paragraph,
    # not a looser assertion.
    #
    #  1. `tools/validate` — ADDITIVE ONLY. Gained `health_check` (advisory),
    #     `decision_codified` and `founder_ask_structure` (both new checks that
    #     can only ADD ways to fail). No existing check was removed, reordered
    #     into irrelevance, or made non-blocking. Exit-code discipline untouched.
    #
    #  2. `tools/kaizen_trends.py` — A REAL GATE CHANGE, FOUNDER-RATIFIED, and the
    #     only one in this set. The M3 escape alarm's blocking condition moved from
    #     "any escape ever recorded" to "any escape whose `Gate-gap closed` column
    #     names no shipped mechanism" (founder: "option a", 2026-07-26; record at
    #     docs/memory/decisions/2026-07-26_escape-alarm-semantics.md). The M3
    #     TARGET is untouched — still 0, absolute — the all-time count still prints
    #     and can never decrease, and an escape with no mechanism still blocks
    #     forever. An agent may not make this change; the founder did.
    #
    # `tools/kpi_report.py` is NOT in this list even though it changed, because
    # `gate_files_changed` compares content and its escaped-defects KPI now calls
    # the same `open_escapes` helper — the identical ratified semantics, not a
    # second decision.
    assert hc.gate_files_changed("f907a51") == [
        "tools/kaizen_trends.py", "tools/validate",
    ], (
        "the expected gate-file changes since the baseline are the additive check "
        "rows in tools/validate and the founder-ratified M3 escape semantics in "
        "kaizen_trends.py; anything else means an UNDECLARED gate moved — state "
        "it here with its authority, never widen this expectation to hide it"
    )
