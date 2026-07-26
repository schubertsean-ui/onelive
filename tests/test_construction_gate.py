"""Construction Loop Stage 3 gate: blocking retrieval, fail-closed physics.

Covers (#67 r4-r6): deliberate [S3:token] contract citations (bare token
mentions are incidental text and never pass); path AND content trigger
matching (semantic classes match on diff text); index self-protection
(deleted tokens / narrowed triggers fail closed; bootstrap prints
explicitly); duplicate tokens fail closed; stale base-history citations
never pass (real temp git repo); unresolvable diff base fails closed.
"""
import subprocess

import pytest

from tools.construction_gate import load_index, main, match_classes, parse_index

INDEX = """# test index
| token | triggers | source |
|---|---|---|
| caller-suppliable-custody-inputs | publish_gate, custody | KAIZEN r3 |
| volatile-safety-store | journal | KAIZEN r14 |
| nonfinite-decimal-accepted | price, decimal | KAIZEN r2 |
"""


@pytest.fixture()
def index_file(tmp_path):
    path = tmp_path / "RED_CLASSES.md"
    path.write_text(INDEX)
    return str(path)


def _file(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


def _run(tmp_path, index_file, *, paths, citations="", content=None, base_index="-"):
    argv = [
        "--index", index_file,
        "--base-index-file", base_index if base_index == "-" else _file(tmp_path, "base.md", base_index),
        "--citation-text-file", _file(tmp_path, "cite.txt", citations),
        "--paths", *paths,
    ]
    if content is not None:
        argv += ["--content-file", _file(tmp_path, "content.txt", content)]
    return main(argv)


def test_bare_token_mention_is_not_a_citation(tmp_path, index_file, capsys):
    # r6 blocker: a changelog line / comment containing the token must NOT
    # pass — only the deliberate [S3:token] tag counts.
    rc = _run(
        tmp_path, index_file,
        paths=["social/carousel/publish_gate.py"],
        citations="changelog: fixed caller-suppliable-custody-inputs today",
    )
    assert rc == 1
    assert "[S3:caller-suppliable-custody-inputs]" in capsys.readouterr().out


def test_tagged_contract_citation_passes(tmp_path, index_file):
    rc = _run(
        tmp_path, index_file,
        paths=["social/carousel/publish_gate.py"],
        citations="[S3:caller-suppliable-custody-inputs] allowlist registry + clock owned by gate.",
    )
    assert rc == 0


def test_content_triggers_match_semantic_classes(tmp_path, index_file, capsys):
    # r6 blocker: a diff touching price/Decimal logic matches the class
    # even when no changed PATH names it.
    rc = _run(
        tmp_path, index_file,
        paths=["social/carousel/generator.py"],
        content="+    value = decimal(str(raw))  # price normalization",
        citations="",
    )
    assert rc == 1
    assert "nonfinite-decimal-accepted" in capsys.readouterr().out


def test_no_match_is_an_explicit_printed_result(tmp_path, index_file, capsys):
    rc = _run(tmp_path, index_file, paths=["web/app/page.tsx"])
    assert rc == 0
    assert "no matched red classes" in capsys.readouterr().out


def test_index_token_deletion_fails_closed(tmp_path, index_file):
    # r6 blocker: the gate is not silently weakenable through its own data.
    with pytest.raises(SystemExit, match="REMOVED"):
        _run(
            tmp_path, index_file,
            paths=["web/app/page.tsx"],
            base_index=INDEX + "| deleted-class | somewhere | old |\n",
        )


def test_index_trigger_narrowing_fails_closed(tmp_path):
    narrowed = INDEX.replace("publish_gate, custody", "publish_gate")
    index_file = _file(tmp_path, "narrowed.md", narrowed)
    with pytest.raises(SystemExit, match="lost triggers"):
        _run(tmp_path, index_file, paths=["web/app/page.tsx"], base_index=INDEX)


def test_bootstrap_absent_base_index_is_explicit(tmp_path, index_file, capsys):
    rc = _run(tmp_path, index_file, paths=["web/app/page.tsx"], base_index="-")
    assert rc == 0
    assert "bootstrap" in capsys.readouterr().out


def test_duplicate_tokens_fail_closed():
    with pytest.raises(SystemExit, match="duplicate red-class token"):
        parse_index(INDEX + "| volatile-safety-store | again | dup |\n", "test")


def test_unreadable_or_empty_index_fails_closed(tmp_path):
    with pytest.raises(SystemExit, match="unreadable"):
        main(["--index", str(tmp_path / "absent.md"), "--paths", "x"])
    empty = _file(tmp_path, "empty.md", "# no table\n")
    with pytest.raises(SystemExit, match="zero rows"):
        main(["--index", empty, "--paths", "x"])


def test_matching_is_case_insensitive_on_both_surfaces(index_file):
    index = load_index(index_file)
    assert match_classes(index, ["Worker/Journal_Writer.py"], "") == ["volatile-safety-store"]
    assert match_classes(index, ["README.md"], "ADDED A PRICE FIELD") == [
        "nonfinite-decimal-accepted"
    ]
    assert match_classes(index, ["README.md"], "") == []


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_stale_citation_in_base_history_never_passes(tmp_path, index_file, monkeypatch, capsys):
    # r5 blocker pinned red for real: a tagged citation in PRE-EXISTING
    # base content must NOT pass; the tag added IN the change passes.
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "STATE.md").write_text("[S3:caller-suppliable-custody-inputs] old contract\n")
    (repo / "publish_gate.py").write_text("original\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "checkout", "-qb", "feature")
    (repo / "publish_gate.py").write_text("original\nchanged with no citation\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "change")

    import tools.construction_gate as gate

    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    rc = main(["--index", index_file, "--base-index-file", "-", "--diff-range", "master...HEAD"])
    assert rc == 1
    assert "added lines lack" in capsys.readouterr().out

    with open(repo / "STATE.md", "a") as fh:
        fh.write("[S3:caller-suppliable-custody-inputs] answered in THIS build\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "cite in-change")
    assert (
        main(["--index", index_file, "--base-index-file", "-", "--diff-range", "master...HEAD"])
        == 0
    )


def test_unresolvable_diff_base_fails_closed(tmp_path, index_file, monkeypatch):
    repo = tmp_path / "repo2"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    import tools.construction_gate as gate

    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    with pytest.raises(SystemExit, match="misconfiguration"):
        main(["--index", index_file, "--base-index-file", "-", "--diff-range", "origin/x...HEAD"])


def test_every_ledger_marker_class_has_an_index_row():
    # #67 r8: hand-picked token sampling could not fail when a newly
    # committed class was missing — coverage is now DERIVED: every
    # "marker: <token>" structural-fix stamp in the Kaizen ledger must
    # have a retrievable row in RED_CLASSES.md (Stage 6: a marked class
    # absent from the index is a prose-only lesson, an open defect).
    import re

    from tools.construction_gate import DEFAULT_INDEX, REPO_ROOT
    import os

    index = load_index(DEFAULT_INDEX)
    ledger = open(
        os.path.join(REPO_ROOT, "docs", "metrics", "KAIZEN_LEDGER.md"), encoding="utf-8"
    ).read()
    marked = set(re.findall(r"marker: ([a-z0-9-]+)", ledger))
    assert marked, "ledger marker convention missing — test would be vacuous"
    missing = sorted(marked - set(index))
    assert not missing, f"ledger-marked classes absent from RED_CLASSES.md: {missing}"


# --- base-ref freshness proof (#71 CI-caught: false-confidence-gate) ---
# The gate's obligation is that origin/master REFLECTS the remote, not
# that this process performed the fetch. Both accepted proofs and the
# fail-closed default are red-tested here; none touches the network.


def test_successful_fetch_here_proves_freshness():
    from tools.construction_gate import assert_base_fresh

    calls = []

    def fetch(remote, branch):
        calls.append((remote, branch))
        return True

    proof = assert_base_fresh("origin/master", fetch=fetch, age=lambda: None)
    assert calls == [("origin", "master")]
    assert "fetched master from origin" in proof


def test_recent_recorded_fetch_proves_freshness_when_fetch_is_impossible():
    # CI's shape: actions/checkout fetches the full history, then drops
    # the credentials (persist-credentials: false), so a fetch from
    # inside the job cannot authenticate while the base is fresher than
    # any fetch this gate could perform.
    from tools.construction_gate import assert_base_fresh

    proof = assert_base_fresh("origin/master", fetch=lambda r, b: False, age=lambda: 120.0)
    assert "last fetched 120s ago" in proof


def test_stale_recorded_fetch_fails_closed():
    from tools.construction_gate import BASE_FRESHNESS_WINDOW_S, assert_base_fresh

    with pytest.raises(SystemExit, match="cannot prove origin/master is fresh"):
        assert_base_fresh(
            "origin/master", fetch=lambda r, b: False, age=lambda: BASE_FRESHNESS_WINDOW_S + 1
        )


def test_no_fetch_record_at_all_fails_closed():
    from tools.construction_gate import assert_base_fresh

    with pytest.raises(SystemExit, match="no fetch record"):
        assert_base_fresh("origin/master", fetch=lambda r, b: False, age=lambda: None)


def test_unresolvable_base_ref_fails_closed_even_inside_the_window(tmp_path, monkeypatch):
    # A recent fetch record does not license a base ref that does not
    # exist — both halves of proof 2 are required.
    import tools.construction_gate as gate

    repo = tmp_path / "repo3"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    with pytest.raises(SystemExit, match="does not resolve"):
        gate.assert_base_fresh("origin/master", fetch=lambda r, b: False, age=lambda: 1.0)


def test_fetch_head_age_is_read_from_the_real_fetch_record(tmp_path, monkeypatch):
    import os

    import tools.construction_gate as gate

    repo = tmp_path / "repo4"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    assert gate._fetch_head_age_s() is None  # no fetch has ever run here
    fetch_head = repo / ".git" / "FETCH_HEAD"
    fetch_head.write_text("recorded\n", encoding="utf-8")
    os.utime(fetch_head, (1000.0, 1000.0))
    assert gate._fetch_head_age_s(now=1300.0) == 300.0
