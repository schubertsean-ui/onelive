"""Mechanical binding: reviewed head == code the arming smoke run exercised.

PR #43 r16: prose claiming "the evidence commit is docs-only" is not
verification. This test recomputes the claim FROM GIT on every run: every path
changed between the recorded smoke-run commit
(docs/evidence/ARMING_SMOKE_RUN.json) and the code under test that lies in the
ARMED CRON's runtime set re-REDs this test until a fresh green head run updates
the evidence file.

The runtime set is computed PRECISELY (Session Contract #20, 2026-07-24) by
tools/arming_runtime.py: the transitive first-party import closure of the
scripts .github/workflows/ingest.yml runs (run_once.py + assemble_dsn.py +
assert_deadman_period.py) plus ingest.yml itself. It REPLACES the original coarse
denylist (everything except docs/tests/design was "runtime"), which
mis-classified code the cron never runs — the consumer web app (web/), SQL
migrations (supabase/), and the deterministic licensed-feed importer
(worker/importers/) — as cron runtime and demanded a paid re-smoke for changes
that cannot affect the armed cron. The closure is NOT fail-open: anything the
cron begins to import is included automatically, ingest.yml itself is always in
the set (so any change to how it invokes scripts re-fires), and dynamic imports
in the closure fail LOUD rather than silently under-including (fail closed).

What "the code under test" means, precisely (#73 r21): locally it is the branch
tip AND the working tree, so an UNCOMMITTED runtime edit reds this test rather
than passing validate and failing CI on the push — which is exactly how the r21
segment.py fix got through. On CI's synthetic merge checkout the subject is a
commit and the tree is clean, so that half adds nothing there.

Where it binds: this test runs in tools/validate locally AND in the trust-gate
CI job, which checks out FULL history (fetch-depth 0, stage-6 r2) and is a
required check on the PR — so the binding is enforced by a blocking check, not
narrative. In an environment whose clone lacks the recorded commit (shallow
checkout), it fails LOUD as unprovable rather than passing silently — fail
closed, with the trust-gate job as the authoritative venue.
"""
import importlib.util
import json
import pathlib
import subprocess

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_EVIDENCE = _ROOT / "docs" / "evidence" / "ARMING_SMOKE_RUN.json"


def _load_arming_runtime():
    """Load tools/arming_runtime.py (tools/ is not a package) — the single
    source of truth for the armed cron's runtime file set."""
    spec = importlib.util.spec_from_file_location(
        "arming_runtime", _ROOT / "tools" / "arming_runtime.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    changed = {p for p in diff.stdout.splitlines() if p.strip()}

    # #73 r21 self-caught, and it is the `pushed-on-red` class in a new
    # disguise: the committed range above cannot see an UNCOMMITTED runtime
    # edit, so running validate before committing one gives a green binding for
    # a tree that will red in CI the moment it is committed. That is exactly
    # what happened — the r21 segment.py log fix was still in the working tree
    # when validate ran, validate said PASS, and trust-gate failed on the push.
    # So when the subject is the local branch tip, compare the recorded run
    # against the WORKING TREE too (a commit-vs-worktree diff covers staged and
    # unstaged alike). Strictly a superset: on CI's synthetic merge checkout the
    # subject is a commit and the tree is clean, so this adds nothing there and
    # the authoritative venue is unchanged.
    if head == "HEAD":
        worktree = _git("diff", "--name-only", run_sha)
        assert worktree.returncode == 0, worktree.stderr
        changed |= {p for p in worktree.stdout.splitlines() if p.strip()}

    changed = sorted(changed)

    # A changed file re-fires the binding ONLY if it is in the armed cron's
    # true runtime closure. DynamicImportError (a dynamic import in the closure)
    # propagates as a LOUD failure — fail closed, never silently under-include.
    runtime = _load_arming_runtime().runtime_files()
    runtime_changes = [p for p in changed if p in runtime]
    assert not runtime_changes, (
        "armed-cron runtime code changed since the recorded green smoke run — "
        f"the evidence no longer covers this head: {runtime_changes}. Re-run "
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
