"""Mechanical binding: reviewed head == code the arming smoke run exercised.

PR #43 r16: prose claiming "the evidence commit is docs-only" is not
verification. This test recomputes the claim FROM GIT on every run: every
path changed between the recorded smoke-run commit
(docs/evidence/ARMING_SMOKE_RUN.json) and the code under test must lie in
the non-runtime set — docs/, TODOS.md, STATE.md, tests/, design/ — none
of which execute in the armed workflow (ingest.yml runs run_once.py;
tests never ship into that path; design/ holds founder-facing HTML
proposals nothing in the pipeline imports; TODOS.md/STATE.md are the
work-queue and status rollup governance docs). Any change to workflows, worker/, tools/, ai/, or anything
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
# Directories are prefix-matched; files exactly (r18 nit: a bare
# startswith would have blessed e.g. TODOS.md.bak).
_NON_RUNTIME_DIR_PREFIXES = ("docs/", "tests/", "design/")
_NON_RUNTIME_FILES = ("TODOS.md", "STATE.md")


def _is_non_runtime(path: str) -> bool:
    return path.startswith(_NON_RUNTIME_DIR_PREFIXES) or path in _NON_RUNTIME_FILES


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
    runtime_changes = [p for p in changed if not _is_non_runtime(p)]
    assert not runtime_changes, (
        "runtime code changed since the recorded green smoke run — the "
        f"evidence no longer covers this head: {runtime_changes}. Re-run "
        "the head smoke run and update docs/evidence/ARMING_SMOKE_RUN.json "
        "in the same (docs-only) commit."
    )


def test_recorded_run_is_authentic_via_actions_api():
    """PR #43 r21 blocker: the evidence JSON is self-authored — a
    fabricated run_id/conclusion would pass the git-side binding. This
    half verifies the RUN against the live Actions API: it exists, it
    succeeded, it ran the ingest workflow at exactly the recorded head
    SHA, and the recorded artifact belongs to it (digest compared when
    the API exposes one). REQUIRED (fail closed, no skip) wherever
    ARMING_SMOKE_VERIFY=required — which the trust-gate job sets, making
    the required check the authoritative venue for this half exactly as
    it is for the git half. Environments with no token and no
    requirement flag skip LOUDLY, deferring to trust-gate."""
    import json as _json
    import os
    import urllib.request

    import pytest

    evidence = _json.loads(_EVIDENCE.read_text())
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    required = os.environ.get("ARMING_SMOKE_VERIFY") == "required"
    if not token:
        assert not required, (
            "ARMING_SMOKE_VERIFY=required but no GH_TOKEN/GITHUB_TOKEN — "
            "the run evidence CANNOT be authenticated; failing closed."
        )
        pytest.skip(
            "no Actions API token here — authoritative venue is the "
            "trust-gate required check (ARMING_SMOKE_VERIFY=required)."
        )
    repo = os.environ.get("GITHUB_REPOSITORY", "schubertsean-ui/onelive")

    def _get(url):
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return _json.loads(resp.read().decode("utf-8"))

    try:
        run = _get(f"https://api.github.com/repos/{repo}/actions/runs/"
                   f"{evidence['run_id']}")
    except Exception as exc:  # noqa: BLE001 — tolerated ONLY when not required
        assert not required, (
            f"ARMING_SMOKE_VERIFY=required but the Actions API is "
            f"unreachable ({type(exc).__name__}) — failing closed."
        )
        pytest.skip(
            f"Actions API unreachable here ({type(exc).__name__}; this "
            "sandbox's proxy forbids api.github.com) — authoritative venue "
            "is the trust-gate required check."
        )
    assert run["conclusion"] == "success", run["conclusion"]
    assert run["head_sha"] == evidence["run_head_sha"]
    assert run["path"] == ".github/workflows/ingest.yml"

    arts = _get(f"https://api.github.com/repos/{repo}/actions/runs/"
                f"{evidence['run_id']}/artifacts")["artifacts"]
    match = [a for a in arts if str(a["id"]) == str(evidence["artifact_id"])]
    assert match, (
        f"recorded artifact {evidence['artifact_id']} not found on run "
        f"{evidence['run_id']}"
    )
    art = match[0]
    assert art["name"] == f"replay-log-{evidence['run_id']}"
    digest = art.get("digest")
    if digest:
        assert digest == f"sha256:{evidence['artifact_zip_sha256']}", digest
