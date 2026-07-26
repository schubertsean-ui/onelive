"""Change-set discipline gate — docs/skills/change_set_discipline.md.

This exists because the lesson was written twice as prose and executed zero
times. The tests therefore check the one property prose cannot have: that
something FAILS.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import subprocess  # noqa: E402
import tools.change_set_gate as gate  # noqa: E402



def _repo(tmp_path) -> pathlib.Path:
    repo = tmp_path / "r"
    repo.mkdir()
    for cmd in (["init", "-q"], ["config", "user.email", "t@t"],
                ["config", "user.name", "t"]):
        subprocess.run(["git", *cmd], cwd=repo, check=True)
    return repo


def _commit(repo: pathlib.Path, name: str, body: str) -> str:
    (repo / name).write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", name], cwd=repo, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True,
                          check=True).stdout.strip()


def _measure(files: int, lines: int) -> dict:
    return {"base": "b", "head": "h", "reviewable_files": files,
            "reviewable_lines": lines, "largest": []}


def test_a_change_past_the_review_ceiling_FAILS(monkeypatch, capsys):
    """Beyond the measured collapse point a change is skimmed, not reviewed."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(5, gate.HARD_LINES + 1))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 1
    assert "SPLIT IT" in capsys.readouterr().err


def test_too_many_files_FAILS(monkeypatch, capsys):
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(gate.HARD_FILES + 1, 100))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 1
    assert "files exceeds" in capsys.readouterr().err


def test_a_change_within_limits_PASSES(monkeypatch):
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD": _measure(4, 120))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 0


def test_the_soft_limit_WARNS_but_does_not_block(monkeypatch, capsys):
    """400 lines is where detection degrades, not where review is impossible.
    Failing there would make the gate unusable and it would be turned off."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(5, gate.SOFT_LINES + 10))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 0
    assert "degrade" in capsys.readouterr().out


def test_SCOPE_GROWTH_UNDER_REVIEW_fails(monkeypatch, capsys):
    """THE rule. A review whose subject expands between rounds cannot converge:
    each round judges a bigger change than the last, and fixes from one round
    become the blockers of the next. #68 (22 rounds) and #74 (11) both died
    here."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(10, 1000))
    monkeypatch.setattr(gate, "load_freeze", lambda: {
        "branch": "feature", "reviewable_files": 8,
        "reviewable_lines": 1000 - gate.MAX_GROWTH_LINES - 1})
    monkeypatch.setattr(gate, "_git", lambda *a: "feature")
    assert gate.main([]) == 1
    err = capsys.readouterr().err
    assert "SCOPE GREW UNDER REVIEW" in err
    assert "new branch" in err.lower(), "must name the remedy, not just the sin"


def test_adopting_a_blocker_is_allowed_growth(monkeypatch):
    """The tolerance is not zero on purpose: fixing what a reviewer found
    legitimately adds lines. Zero tolerance would make the gate absurd and it
    would be disabled, which is the failure mode this whole file guards."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(8, 1000))
    monkeypatch.setattr(gate, "load_freeze", lambda: {
        "branch": "feature", "reviewable_files": 8,
        "reviewable_lines": 1000 - (gate.MAX_GROWTH_LINES // 2)})
    monkeypatch.setattr(gate, "_git", lambda *a: "feature")
    assert gate.main([]) == 0


def test_a_freeze_TRAVELS_WITH_the_change_regardless_of_branch_name(monkeypatch):
    """This test previously asserted the OPPOSITE — that a freeze recorded under
    a different branch name is ignored. That is precisely the bug: every CI
    runner checks out detached, where the name is the literal "HEAD", so the
    growth check was skipped in the one place it has to run. The freeze is a
    COMMITTED file; it travels with the change, and its presence is the whole
    condition. The branch is recorded for the operator, never consulted."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(10, 900))
    monkeypatch.setattr(gate, "load_freeze", lambda: {
        "branch": "some-other-branch", "reviewable_files": 1,
        "reviewable_lines": 1})
    monkeypatch.setattr(gate, "_git", lambda *a: "HEAD")
    assert gate.main([]) == 1, "growth past tolerance must fail whatever the ref"


def test_a_corrupt_freeze_record_REFUSES_rather_than_reading_as_absent(tmp_path,
                                                                      monkeypatch):
    """An unreadable scope record silently disabling the scope rule is the
    failure-reads-as-empty class applied to the gate itself."""
    bad = tmp_path / "SCOPE_FREEZE.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(gate, "FREEZE", bad)
    with pytest.raises(SystemExit, match="could not be read as JSON"):
        gate.load_freeze()


def test_generated_artifacts_do_not_count_against_the_reviewer(monkeypatch):
    """A reviewer does not read a generated target list line by line. Counting
    it like logic would make the gate fire on noise and get it switched off."""
    numstat = ("10\t0\ttools/real_code.py\n"
               "9000\t0\tsources/capcog_venue_targets.json\n")
    monkeypatch.setattr(gate, "_git",
                        lambda *a: numstat if a[0] == "diff" else "sha")
    m = gate.measure("base")
    assert m["reviewable_lines"] == 10
    assert m["reviewable_files"] == 1


def test_the_gate_is_wired_into_validate():
    """A gate that no pipeline runs is the prose it replaced."""
    v = (REPO / "tools" / "validate").read_text(encoding="utf-8")
    assert "change_set_gate" in v, "gate exists but nothing executes it"


def test_the_canon_document_exists_and_cites_its_evidence():
    doc = (REPO / "docs" / "skills" / "change_set_discipline.md"
           ).read_text(encoding="utf-8")
    for anchor in ("24 lines", "400", "dora.dev", "SCOPE FREEZE",
                   "one reversible decision"):
        assert anchor.lower() in doc.lower(), anchor


def test_deleting_a_file_is_ONE_decision_not_N_lines(monkeypatch):
    """Found by using the gate: splitting PR #74 removed ~2,500 lines and the
    measured size went UP, so the tool punished the remedy it exists to demand.
    Reviewing "should this be gone?" is one judgement."""
    numstat = ("0\t900\ttools/removed_module.py\n"
               "10\t2\ttools/edited.py\n")
    # The status letter is the fact, not the zero-addition count — a large CUT
    # to a surviving file also adds nothing, and that IS lines of reading.
    names = "D\ttools/removed_module.py\nM\ttools/edited.py\n"

    def fake_git(*a):
        if a[0] != "diff":
            return "sha"
        return names if "--name-status" in a else numstat

    monkeypatch.setattr(gate, "_git", fake_git)
    m = gate.measure("base")
    assert m["reviewable_lines"] == gate.DELETED_FILE_COST + 12, m


# ---- r1 evaluator findings: the gate was fail-open in four ways --------------

def test_a_git_failure_STOPS_rather_than_measuring_zero(tmp_path, monkeypatch):
    """The worst kind of bug in a size gate: `_git` returned "" on a non-zero
    exit, so a missing base ref produced an empty diff, measured 0 files and
    0 lines, and PASSED. "I could not look" is not "there is nothing to see"."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(gate, "REPO", tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    with pytest.raises(SystemExit) as exc:
        gate._git("rev-parse", "definitely-not-a-ref")
    assert "could not be measured" in str(exc.value)
    assert "FAIL" in str(exc.value)


def test_a_lockfile_is_excluded_WHEREVER_it_sits():
    """Matching lockfiles as path prefixes never fired: our only lockfile is
    web/package-lock.json, which neither equals nor starts with
    "package-lock.json" — so lockfiles were counted while the canon said they
    were not."""
    assert gate._is_low_review_cost("web/package-lock.json")
    assert gate._is_low_review_cost("package-lock.json")
    assert gate._is_low_review_cost("apps/site/pnpm-lock.yaml")
    assert gate._is_low_review_cost("sources/discovered/anything.json")
    # and a normal file is still counted
    assert not gate._is_low_review_cost("web/lib/region.ts")
    assert not gate._is_low_review_cost("tools/package-lock-helper.py")


def test_the_freeze_is_enforced_on_a_DETACHED_head(tmp_path, monkeypatch):
    """Every CI runner checks out detached, where `rev-parse --abbrev-ref HEAD`
    is the literal "HEAD". Gating the growth check on a branch-name match
    therefore skipped it in the one place it has to run."""
    repo = _repo(tmp_path)
    base = _commit(repo, "a.py", "x\n")
    monkeypatch.setattr(gate, "REPO", repo)
    monkeypatch.setattr(gate, "FREEZE", repo / "freeze.json")
    gate.FREEZE.write_text(json.dumps({
        "branch": "some-branch-that-is-not-checked-out",
        "reviewable_files": 1, "reviewable_lines": 1,
        "frozen_at_head": base,
    }), encoding="utf-8")
    _commit(repo, "b.py", "y\n" * (gate.MAX_GROWTH_LINES + 50))
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=repo, check=True)
    assert gate._git("rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    code = gate.main(["--base", base])
    assert code != 0, "scope growth must fail on a detached HEAD"


def test_a_big_CUT_is_not_priced_as_a_file_deletion(tmp_path, monkeypatch):
    """`added == 0 and removed > 0` is not a deletion test: cutting 500 lines
    out of a file that survives adds no lines either, and that IS 500 lines of
    reading. Only git's own status letter distinguishes them."""
    repo = _repo(tmp_path)
    base = _commit(repo, "big.py", "keep\n" + "line\n" * 500)
    monkeypatch.setattr(gate, "REPO", repo)
    _commit(repo, "big.py", "keep\n")          # modified, 500 lines removed
    m = gate.measure(base)
    assert m["reviewable_lines"] == 500, m
    # an actual deletion still costs the flat rate
    base2 = gate._git("rev-parse", "HEAD")
    (repo / "gone.py").write_text("z\n" * 300, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "add"], cwd=repo, check=True)
    base3 = gate._git("rev-parse", "HEAD")
    (repo / "gone.py").unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "rm"], cwd=repo, check=True)
    assert gate.measure(base3)["reviewable_lines"] == gate.DELETED_FILE_COST


def test_an_UNREADABLE_freeze_is_not_an_absent_one(tmp_path, monkeypatch):
    """A directory where the freeze file should be raises OSError, not
    ValueError — and reading that as "no freeze recorded" would silently
    disable the rule that matters most."""
    monkeypatch.setattr(gate, "FREEZE", tmp_path / "freeze.json")
    gate.FREEZE.mkdir()
    with pytest.raises(SystemExit) as exc:
        gate.load_freeze()
    assert "not an absent one" in str(exc.value)
