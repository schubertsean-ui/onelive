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


# --- base-ref freshness proof (#71 r5-r8: false-confidence-gate ×4) -----
# Four offline proofs were proposed and each was shown to be reproducible
# from a STALE base: a fetch's exit code (r5), a repo-wide .git/FETCH_HEAD
# mtime (r6), a recent write to the ref (r7), and a two-parent HEAD whose
# first parent matches the base ref (r8 — obtainable by checking out a
# stale base and merging the feature branch). Staleness is a fact about
# the REMOTE, so the gate now contacts it or fails. These tests pin that
# there is NO offline path, and exercise the SHIPPED probes against real
# git rather than only against a double.


class _Probes:
    """Hermetic stand-in for _GitProbes: evidence as data.

    `fetch` deliberately mutates NOTHING (#71 r7 blocker): a double that
    makes the fetch succeed is a double that cannot fail. Convergence is
    expressed as the sequence of ids the ref reports, and the real
    command's effect is pinned separately against git below.
    """

    def __init__(self, tip=None, oids=()):
        self._tip = tip
        self._oids = list(oids)
        self.fetched = []

    def remote_tip(self, remote, branch):
        return self._tip

    def fetch(self, remote, branch):
        self.fetched.append((remote, branch))

    def local_oid(self, ref):
        if not self._oids:
            return None
        return self._oids.pop(0) if len(self._oids) > 1 else self._oids[0]


def test_matching_oids_are_the_proof_and_need_no_fetch():
    from tools.construction_gate import assert_base_fresh

    probes = _Probes(tip="a" * 40, oids=["a" * 40])
    proof = assert_base_fresh("origin/master", probes=probes)
    assert probes.fetched == []  # already synchronized — nothing to converge
    assert "== remote tip aaaaaaaaaaaa" in proof


def test_a_stale_ref_converges_by_fetch_then_passes():
    from tools.construction_gate import assert_base_fresh

    probes = _Probes(tip="b" * 40, oids=["a" * 40, "b" * 40])
    proof = assert_base_fresh("origin/master", probes=probes)
    assert probes.fetched == [("origin", "master")]
    assert "== remote tip bbbbbbbbbbbb" in proof


def test_a_successful_fetch_that_leaves_the_ref_behind_fails_closed():
    # THE r5 BLOCKER, pinned: the fetch raised no error yet the base ref
    # still does not match the remote. Exit codes are not the property.
    from tools.construction_gate import assert_base_fresh

    probes = _Probes(tip="b" * 40, oids=["a" * 40])
    with pytest.raises(SystemExit, match="a fetch did not converge them"):
        assert_base_fresh("origin/master", probes=probes)
    assert probes.fetched == [("origin", "master")]


def test_an_unreachable_remote_ALWAYS_fails_closed():
    # THE r6/r7/r8 BLOCKERS, pinned as one contract: no local artifact
    # substitutes for the remote. There is no argument, environment, or
    # repository shape that reaches a PASS from here.
    from tools.construction_gate import assert_base_fresh

    with pytest.raises(SystemExit, match="deliberately NO"):
        assert_base_fresh("origin/master", probes=_Probes(tip=None, oids=["c" * 40]))


def test_an_unreachable_remote_fails_closed_even_from_a_merge_checkout(tmp_path,
                                                                      monkeypatch):
    # THE r8 SHAPE, pinned against real git: a stale base checked out and
    # merged with the feature branch produces a two-parent HEAD whose
    # first parent IS origin/master. That was accepted in r7 and is
    # rejected now — the topology proves nothing about the remote.
    import tools.construction_gate as gate

    _, clone = _real_pair(tmp_path, "merge-shape")
    monkeypatch.setattr(gate, "REPO_ROOT", str(clone))
    _git(clone, "config", "user.email", "t@t")
    _git(clone, "config", "user.name", "t")
    _git(clone, "checkout", "-q", "-b", "feature")
    (clone / "g.txt").write_text("feature\n", encoding="utf-8")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-qm", "feature")
    _git(clone, "checkout", "-q", "--detach", "origin/master")
    _git(clone, "merge", "-q", "--no-ff", "-m", "merge", "feature")
    def read(*args):
        return subprocess.run(
            ["git", *args], cwd=clone, check=True, capture_output=True, text=True
        ).stdout.strip()

    # the r7-accepted shape, exactly:
    parents = read("rev-list", "--parents", "-n", "1", "HEAD").split()[1:]
    assert len(parents) == 2
    assert parents[0] == read("rev-parse", "origin/master")
    # ...and with the remote unreachable it must still fail closed.
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "does-not-exist"))
    with pytest.raises(SystemExit, match="deliberately NO"):
        gate.assert_base_fresh("origin/master")


def test_malformed_base_ref_cannot_be_proven():
    from tools.construction_gate import assert_base_fresh

    with pytest.raises(SystemExit, match="not in <remote>/<branch> form"):
        assert_base_fresh("master", probes=_Probes(tip="a" * 40, oids=["a" * 40]))


# --- the SHIPPED probes, against real git (#71 r7 blocker) --------------
# A test double cannot catch a git command that does not do what we
# believe. These use two real repositories and no network.


def _real_pair(tmp_path, name):
    upstream = tmp_path / f"{name}-upstream"
    upstream.mkdir()
    _git(upstream, "init", "-q", "-b", "master")
    _git(upstream, "config", "user.email", "t@t")
    _git(upstream, "config", "user.name", "t")
    (upstream / "f.txt").write_text("one\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-qm", "one")
    clone = tmp_path / f"{name}-clone"
    subprocess.run(["git", "clone", "-q", str(upstream), str(clone)], check=True)
    return upstream, clone


def test_real_fetch_actually_updates_the_remote_tracking_ref(tmp_path, monkeypatch):
    # THE r7 BLOCKER, pinned against real git: after the upstream moves,
    # _GitProbes.fetch must leave refs/remotes/origin/master ON the new
    # tip. The explicit refspec is what guarantees it.
    import tools.construction_gate as gate

    upstream, clone = _real_pair(tmp_path, "converge")
    monkeypatch.setattr(gate, "REPO_ROOT", str(clone))
    before = gate._GitProbes.local_oid("origin/master")

    (upstream / "f.txt").write_text("two\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-qm", "two")
    tip = gate._GitProbes.remote_tip("origin", "master")
    assert tip is not None and tip != before  # the clone is now genuinely stale

    gate._GitProbes.fetch("origin", "master")
    assert gate._GitProbes.local_oid("origin/master") == tip


def test_real_probes_carry_assert_base_fresh_end_to_end(tmp_path, monkeypatch):
    import tools.construction_gate as gate

    upstream, clone = _real_pair(tmp_path, "e2e")
    monkeypatch.setattr(gate, "REPO_ROOT", str(clone))
    (upstream / "f.txt").write_text("three\n", encoding="utf-8")
    _git(upstream, "add", "-A")
    _git(upstream, "commit", "-qm", "three")
    proof = gate.assert_base_fresh("origin/master")
    assert "== remote tip" in proof
    assert gate._GitProbes.local_oid("origin/master") == gate._GitProbes.remote_tip(
        "origin", "master"
    )


def test_real_remote_tip_is_none_when_the_remote_is_unreachable(tmp_path, monkeypatch):
    import tools.construction_gate as gate

    repo = tmp_path / "noremote"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "master")
    monkeypatch.setattr(gate, "REPO_ROOT", str(repo))
    assert gate._GitProbes.remote_tip("origin", "master") is None


def test_fully_supplied_runs_never_touch_the_remote(tmp_path, index_file, monkeypatch,
                                                    capsys):
    # #71 r9, self-caught in CI: a run whose paths, content and citations
    # are all supplied derives nothing from git, so it must not demand
    # remote access. Making freshness eager turned the hermetic tests into
    # network-dependent ones — green on a machine with a reachable remote,
    # red in CI's plain pytest step. Pinned by making the proof EXPLODE:
    # if the gate reaches for it here, this test fails.
    import tools.construction_gate as gate

    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("base freshness demanded on a fully-supplied run")

    monkeypatch.setattr(gate, "assert_base_fresh", _must_not_be_called)
    rc = _run(
        tmp_path, index_file,
        paths=["social/carousel/publish_gate.py"],
        citations="[S3:caller-suppliable-custody-inputs] answered.",
    )
    assert rc == 0
    assert "[S3:…] contract citations — PASS" in capsys.readouterr().out


# ── The gate must not accept evidence that contradicts itself (PR #78 r7,
# class false-confidence-gate). It checked that every matched class HAS an
# answer and never that the answers agree.

def test_two_live_answers_for_one_class_are_rejected():
    from tools.construction_gate import contradictory_citations
    text = ("[S3:scripted-edit-not-reread] no scripted edit was applied.\n"
            "[S3:scripted-edit-not-reread] a scripted edit destroyed the ledger.\n")
    assert contradictory_citations(text) == ["scripted-edit-not-reread"]


def test_a_marked_supersession_is_accepted():
    """Corrections across review rounds are legitimate; SILENT ones are not."""
    from tools.construction_gate import contradictory_citations
    for marker in ("SUPERSEDED", "CORRECTED", "WITHDRAWN"):
        text = (f"[S3:x] {marker} at r7 — this was written at r1 and is stale.\n"
                "[S3:x] the live answer.\n")
        assert contradictory_citations(text) == [], marker


def test_the_check_is_order_independent():
    """A contract is edited in place, so the stale line can sit anywhere —
    'all but the last' was the wrong rule and passed the real contradiction."""
    from tools.construction_gate import contradictory_citations
    assert contradictory_citations(
        "[S3:x] the live answer.\n[S3:x] SUPERSEDED — stale, kept for history.\n") == []


def test_a_single_answer_is_never_flagged():
    from tools.construction_gate import contradictory_citations
    assert contradictory_citations("[S3:x] the only answer.\n") == []


def test_the_current_session_contract_carries_no_contradiction():
    """Scoped to the NEWEST contract block, matching what the gate judges.

    The gate reads only the lines a change ADDS. STATE.md as a whole holds
    every past contract, and the same token legitimately gets a different
    answer in each — asserting over the whole file confused "reused across
    contracts" with "contradictory within one", which is a different thing.
    """
    import os, re
    from tools.construction_gate import contradictory_citations, REPO_ROOT, CONTRACT_RELPATH
    text = open(os.path.join(REPO_ROOT, CONTRACT_RELPATH), encoding="utf-8").read()
    blocks = re.split(r"^## Session Contract ", text, flags=re.MULTILINE)
    assert len(blocks) > 1, "no session contract blocks found — test is vacuous"
    current = blocks[1]
    assert "[S3:" in current, "the newest contract carries no citations — vacuous"
    assert contradictory_citations(current) == []
