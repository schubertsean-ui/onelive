"""Mechanical binding: reviewed head == code the arming smoke run exercised.

PR #43 r16: prose claiming "the evidence commit is docs-only" is not
verification. This test recomputes the claim FROM GIT on every run: every
path changed between the recorded smoke-run commit
(docs/evidence/ARMING_SMOKE_RUN.json) and the code under test must lie in
the non-runtime set — docs/, TODOS.md, tests/ — none of which execute in
the armed workflow (ingest.yml runs run_once.py; tests never ship into
that path). Any change to workflows, worker/, tools/, ai/, or anything
else runtime re-REDs this test until a fresh green head run updates the
evidence file.

Where it binds: this test runs in tools/validate locally AND in the
trust-gate CI job, which checks out FULL history (fetch-depth 0, stage-6
r2) and is a required check on the PR — so the binding is enforced by a
blocking check, not narrative. In an environment whose clone lacks the
recorded commit (shallow checkout), it fails LOUD as unprovable rather
than passing silently — fail closed, with the trust-gate job as the
authoritative venue.
"""
import json
import pathlib
import subprocess

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_EVIDENCE = _ROOT / "docs" / "evidence" / "ARMING_SMOKE_RUN.json"

# Paths that never execute inside the armed workflow. Everything else is
# runtime surface and must be byte-identical to the run's commit.
_NON_RUNTIME_PREFIXES = ("docs/", "tests/", "TODOS.md")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(_ROOT), *args],
        capture_output=True, text=True, check=False,
    )


def test_reviewed_head_is_runtime_code_identical_to_the_smoke_run():
    evidence = json.loads(_EVIDENCE.read_text())
    run_sha = evidence["run_head_sha"]
    assert len(run_sha) == 40 and all(c in "0123456789abcdef" for c in run_sha)

    have = _git("cat-file", "-e", f"{run_sha}^{{commit}}")
    assert have.returncode == 0, (
        f"the recorded smoke-run commit {run_sha[:9]} is not present in this "
        "clone (shallow checkout?) — the binding CANNOT be proven here, so "
        "this fails closed. The authoritative venue is the trust-gate CI "
        "job (full-history checkout, required check) and local validate."
    )

    # On CI's synthetic merge checkout, the PR head is the second parent;
    # locally, HEAD is the branch tip itself.
    head = "HEAD"
    parents = _git("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
    if len(parents) == 3:  # merge commit: self + 2 parents
        second_parent = parents[2]
        if _git("merge-base", "--is-ancestor", run_sha,
                second_parent).returncode == 0:
            head = second_parent

    diff = _git("diff", "--name-only", f"{run_sha}..{head}")
    assert diff.returncode == 0, diff.stderr
    changed = [p for p in diff.stdout.splitlines() if p.strip()]
    runtime_changes = [
        p for p in changed if not p.startswith(_NON_RUNTIME_PREFIXES)
    ]
    assert not runtime_changes, (
        "runtime code changed since the recorded green smoke run — the "
        f"evidence no longer covers this head: {runtime_changes}. Re-run "
        "the head smoke run and update docs/evidence/ARMING_SMOKE_RUN.json "
        "in the same (docs-only) commit."
    )
