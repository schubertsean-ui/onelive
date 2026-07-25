"""Construction Loop Stage 3 gate: blocking retrieval, fail-closed physics.

Covers (#67 r4 — the rule ships WITH its mechanism; r5 — citations bind
to the current change's ADDED LINES, and a missing/unresolvable diff
base fails closed): uncited matched class blocks; cited passes; no-match
prints explicitly; unreadable/empty index fails closed; the STALE-CITATION
hole is pinned red in a real temporary git repo (token present only in
pre-existing base content must NOT pass).
"""
import subprocess

import pytest

from tools.construction_gate import load_index, main, match_classes

INDEX = """# test index
| token | triggers | source |
|---|---|---|
| caller-suppliable-custody-inputs | publish_gate, custody | KAIZEN r3 |
| volatile-safety-store | journal | KAIZEN r14 |
"""


@pytest.fixture()
def index_file(tmp_path):
    path = tmp_path / "RED_CLASSES.md"
    path.write_text(INDEX)
    return str(path)


def _citations(tmp_path, text):
    path = tmp_path / "added_lines.txt"
    path.write_text(text)
    return str(path)


def test_uncited_matched_class_blocks(tmp_path, index_file, capsys):
    rc = main(
        [
            "--index", index_file,
            "--citation-text-file", _citations(tmp_path, "no citations here"),
            "--paths", "social/carousel/publish_gate.py",
        ]
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert "do not cite: caller-suppliable-custody-inputs" in out


def test_cited_matched_class_passes(tmp_path, index_file):
    rc = main(
        [
            "--index", index_file,
            "--citation-text-file", _citations(
                tmp_path, "Stage 3: caller-suppliable-custody-inputs answered."
            ),
            "--paths", "social/carousel/publish_gate.py",
        ]
    )
    assert rc == 0


def test_no_match_is_an_explicit_printed_result(tmp_path, index_file, capsys):
    rc = main(
        [
            "--index", index_file,
            "--citation-text-file", _citations(tmp_path, "anything"),
            "--paths", "web/app/page.tsx",
        ]
    )
    assert rc == 0
    assert "no matched red classes" in capsys.readouterr().out


def test_unreadable_or_empty_index_fails_closed(tmp_path):
    cite = _citations(tmp_path, "anything")
    with pytest.raises(SystemExit, match="unreadable"):
        main(["--index", str(tmp_path / "absent.md"), "--citation-text-file", cite, "--paths", "x"])
    empty = tmp_path / "empty.md"
    empty.write_text("# no table here\n")
    with pytest.raises(SystemExit, match="zero rows"):
        main(["--index", str(empty), "--citation-text-file", cite, "--paths", "x"])


def test_matching_is_path_substring_case_insensitive(index_file):
    index = load_index(index_file)
    assert match_classes(index, ["Worker/Journal_Writer.py"]) == ["volatile-safety-store"]
    assert match_classes(index, ["README.md"]) == []


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_stale_citation_in_base_history_never_passes(tmp_path, index_file, monkeypatch, capsys):
    # #67 r5 blocker pinned red for real: the token exists in PRE-EXISTING
    # base content (cumulative history), the current change touches a
    # trigger path but ADDS no citation — the gate must FAIL. Then adding
    # the citation IN the change passes.
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "STATE.md").write_text(
        "old contract cited caller-suppliable-custody-inputs long ago\n"
    )
    (repo / "publish_gate.py").write_text("original\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "feature")
    (repo / "publish_gate.py").write_text("original\nchanged with no citation\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "change")

    import tools.construction_gate as gate

    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    rc = main(["--index", index_file, "--diff-range", "master...HEAD"])
    assert rc == 1
    assert "ADDED LINES do not cite" in capsys.readouterr().out

    (repo / "STATE.md").write_text(
        "old contract cited caller-suppliable-custody-inputs long ago\n"
        "NEW contract: caller-suppliable-custody-inputs retrieved and answered\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "cite in-change")
    assert main(["--index", index_file, "--diff-range", "master...HEAD"]) == 0


def test_unresolvable_diff_base_fails_closed(tmp_path, index_file, monkeypatch):
    repo = tmp_path / "repo2"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    import tools.construction_gate as gate

    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    with pytest.raises(SystemExit, match="misconfiguration"):
        main(["--index", index_file, "--diff-range", "origin/nonexistent...HEAD"])


def test_real_index_parses_and_covers_the_shipped_classes():
    from tools.construction_gate import DEFAULT_INDEX

    index = load_index(DEFAULT_INDEX)
    for token in (
        "caller-suppliable-custody-inputs",
        "deferred-trust-work",
        "volatile-safety-store",
    ):
        assert token in index
