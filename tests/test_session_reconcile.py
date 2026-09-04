"""Tests for the session-start reconciler's drift classification.

Guards the continuity safeguard itself against silent rot: the whole point is to
hard-stop on a material contradiction (the failure mode where a prior session left
STATE.md claiming a PR merged that's actually open, or a table empty that's
populated). These tests lock that behavior in without git/gh/DB access.
"""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "session_reconcile",
    os.path.join(os.path.dirname(__file__), "..", "tools", "session_reconcile.py"))
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)


def _live(prs=None, migs=None, counts=None, prs_ok=True, db_ok=True):
    return {
        "git": {"verified": True, "branch": "x", "head": "abc"},
        "prs": {"verified": prs_ok, "prs": prs or [], "error": None},
        "db": {"verified": db_ok, "migrations": migs or [],
               "row_counts": counts or {}, "reason": "no dsn"},
    }


def test_pr_merged_vs_open_is_material():
    prev = {"prs": {"4": "merged"}}
    live = _live(prs=[{"number": 4, "state": "OPEN", "title": "x"}])
    material, benign, unverified = sr.classify(prev, live)
    assert any("PR #4" in m for m in material)


def test_pr_matching_state_is_clean():
    prev = {"prs": {"5": "merged"}}
    live = _live(prs=[{"number": 5, "state": "MERGED", "title": "x"}])
    material, benign, unverified = sr.classify(prev, live)
    assert not material


def test_zero_to_nonzero_rowcount_is_material():
    prev = {"row_counts": {"source": 0}}
    live = _live(counts={"source": 43})
    material, _, _ = sr.classify(prev, live)
    assert any("source" in m for m in material)


def test_nonzero_count_change_is_benign_not_material():
    prev = {"row_counts": {"event": 10}}
    live = _live(counts={"event": 12})
    material, benign, _ = sr.classify(prev, live)
    assert not material
    assert any("event" in b for b in benign)


def test_claimed_applied_migration_missing_is_material():
    prev = {"applied_migrations": ["0008"]}
    live = _live(migs=["0001", "0007"])
    material, _, _ = sr.classify(prev, live)
    assert any("0008" in m for m in material)


def test_unverified_db_is_flagged_loud():
    prev = {"row_counts": {"source": 43}}
    live = _live(db_ok=False)
    _, _, unverified = sr.classify(prev, live)
    assert any("DB" in u for u in unverified)


def test_heal_preserves_staleness_marker_and_unverified_facts():
    # Regression (caught 2026-08-03): --heal rebuilt the block from live data
    # only, dropping reconciled_through_commit — which staleness_check fails
    # closed on — and discarding the last verified PR/DB facts whenever those
    # legs were UNVERIFIED (no gh / no DSN). The heal must never destroy what
    # it cannot re-derive.
    prev = {
        "reconciled_through_commit": "c" * 40,
        "reconciled_by": "session X",
        "prs_note": "narrative",
        "prs": {"4": "merged"},
        "applied_migrations": ["0001"],
        "row_counts": {"source": 43},
    }
    snap = sr.build_snapshot(_live(prs_ok=False, db_ok=False), prev)
    assert snap["reconciled_through_commit"] == "c" * 40
    assert snap["reconciled_by"] == "session X"
    assert snap["prs_note"] == "narrative"
    assert snap["prs"] == {"4": "merged"}
    assert snap["applied_migrations"] == ["0001"]
    assert snap["row_counts"] == {"source": 43}


def test_heal_verified_legs_overwrite_preserved_facts():
    prev = {"reconciled_through_commit": "c" * 40,
            "prs": {"4": "open"}, "row_counts": {"source": 1}}
    live = _live(prs=[{"number": 4, "state": "MERGED", "title": "x"}],
                 migs=["0001"], counts={"source": 43})
    snap = sr.build_snapshot(live, prev)
    assert snap["prs"] == {"4": "merged"}          # live wins when verified
    assert snap["row_counts"] == {"source": 43}
    assert snap["reconciled_through_commit"] == "c" * 40  # marker still carried


def test_state_block_roundtrip():
    text = "# STATE\n\nsome prose\n"
    snap = {"prs": {"1": "merged"}, "row_counts": {"source": 43}}
    written = sr.write_state_block(text, snap)
    assert sr.read_state_block(written) == snap
    # Rewriting replaces, does not duplicate.
    snap2 = {"prs": {"1": "merged", "2": "open"}}
    rewritten = sr.write_state_block(written, snap2)
    assert rewritten.count(sr.BEGIN) == 1
    assert sr.read_state_block(rewritten) == snap2


def test_a_snapshot_carrying_ordinary_prose_does_not_crash_the_heal():
    r"""An em-dash in the narrative must not blow up the session bookend.

    `json.dumps` writes non-ASCII as `\uXXXX`, and `re.sub` reads backslash
    sequences in a REPLACEMENT STRING as escapes — so a single em-dash anywhere
    in the snapshot raised `re.error: bad escape \u` and took the whole `--heal`
    ritual with it. Every session's STATE narrative has one.
    """
    text = "# STATE\n\n" + sr.BEGIN + "\n```json\n{}\n```\n" + sr.END + "\n"
    snap = {"note": "closed — merged, evaluator APPROVE", "ref": r"C:\path\to"}
    rewritten = sr.write_state_block(text, snap)
    assert sr.read_state_block(rewritten) == snap
    assert rewritten.count(sr.BEGIN) == 1
