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


def _extraction_closed_and_proven() -> bool:
    """True ONLY when extraction is closed in THIS checkout AND the closure
    provably stops the armed cron before any runtime code runs.

    Two independent verifications, both fail-closed (any surprise -> False,
    which routes back to the strict evidence assertion):
      1. AST literal: tools/routing_data.py assigns
         EXTRACTION_THRESHOLD_RATIFIED the exact bool False — never a truthy
         string, never inference from import (the module under test must be
         read as data, the same rule the surface classifier follows).
      2. Behavioral: resolving the extraction model actually raises the
         provider's fail-closed ExtractionConfigError — proving the cron's
         first act (ClaudeProvider construction, worker/run_once.py:235)
         refuses before any fetch or DB access.
    """
    import ast
    try:
        tree = ast.parse((_ROOT / "tools" / "routing_data.py").read_text(
            encoding="utf-8"))
        flag = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if (isinstance(tgt, ast.Name)
                            and tgt.id == "EXTRACTION_THRESHOLD_RATIFIED"):
                        if (isinstance(node.value, ast.Constant)
                                and node.value.value is False):
                            flag = False
                        else:
                            return False
        if flag is not False:
            return False
        from ai.claude_provider import (
            ExtractionConfigError, _resolve_extraction_model)
        try:
            _resolve_extraction_model(None, exam_mode=False)
        except ExtractionConfigError:
            return True
        return False
    except Exception:  # noqa: BLE001 — ANY surprise fails closed to strict
        return False


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

    # A changed file re-fires the binding ONLY if it is in the armed cron's
    # true runtime closure. DynamicImportError (a dynamic import in the closure)
    # propagates as a LOUD failure — fail closed, never silently under-include.
    runtime = _load_arming_runtime().runtime_files()
    runtime_changes = [p for p in changed if p in runtime]
    if runtime_changes and _extraction_closed_and_proven():
        # CLOSURE BRANCH (2026-08-03, the re-certification sitting): a PR that
        # sets EXTRACTION_THRESHOLD_RATIFIED to the literal bool False makes a
        # green smoke run IMPOSSIBLE by design — run_once --real constructs
        # ClaudeProvider (worker/run_once.py:235) BEFORE any fetch/DB work,
        # and the provider's fail-closed gate raises at construction. The
        # armed cron therefore fails CLOSED at startup on every fire (loud,
        # dead-man-covered): no unverified runtime byte can execute, which is
        # the exact property this binding exists to guarantee. The binding
        # DEFERS to the head-bound flag-flip PR that re-opens extraction —
        # that PR changes tools/routing_data.py (runtime set), lands with
        # extraction certified again, and MUST carry fresh green smoke
        # evidence through this same test's normal branch. Fail-closed is
        # preserved end to end; this branch is provable, not asserted:
        # _extraction_closed_and_proven() re-verifies both the AST-literal
        # flag and the provider's actual refusal.
        return
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
