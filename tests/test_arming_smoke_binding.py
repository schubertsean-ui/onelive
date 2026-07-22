"""Mechanical binding: reviewed head == code the arming smoke run exercised.

PR #43 r16: prose claiming "the evidence commit is docs-only" is not
verification. This test recomputes the claim FROM GIT on every run: every
path changed between the recorded smoke-run commit
(docs/evidence/ARMING_SMOKE_RUN.json) and the code under test must lie in
the non-runtime set — docs/, TODOS.md, STATE.md, tests/ — none of which
execute in the armed workflow. This classification is NOT asserted prose:
test_non_runtime_set_is_proven_against_workflow_closure below DERIVES it
from ingest.yml's actual execution closure on every run (PR #47 r1 — an
allowlist entry justified only by assertion is a classifier relaxation).
Any change to workflows, worker/, tools/, ai/, or anything
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
# Every entry here must be justified by the closure-proof test below,
# which derives the armed workflow's execution surface from ingest.yml
# and fails if any allowlisted path is part of it or consumed by it.
_NON_RUNTIME_DIR_PREFIXES = ("docs/", "tests/")
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


def _workflow_entry_scripts() -> list[pathlib.Path]:
    """Repo .py files invoked by non-comment lines of ingest.yml."""
    import re
    text = (_ROOT / ".github" / "workflows" / "ingest.yml").read_text()
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    tokens = re.findall(r"[\w/.-]+\.py\b", "\n".join(lines))
    entries = sorted({t for t in tokens if (_ROOT / t).is_file()})
    return [pathlib.Path(t) for t in entries]


def _import_closure(entries: list[pathlib.Path]) -> set[pathlib.Path]:
    """Transitive intra-repo import closure by static AST parse (no
    execution). Third-party/stdlib imports are ignored; only names that
    resolve to files inside the repo are followed."""
    import ast
    seen: set[pathlib.Path] = set()
    queue = list(entries)
    while queue:
        rel = queue.pop()
        if rel in seen:
            continue
        seen.add(rel)
        tree = ast.parse((_ROOT / rel).read_text())
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    names.append(node.module)
                    names += [f"{node.module}.{a.name}" for a in node.names]
                elif node.level > 0:
                    # PR #47 r2 blocker: package-relative imports must
                    # resolve too. level=1 is the module's own package;
                    # each extra level climbs one package higher.
                    base = rel.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                    prefix = ".".join(base.parts)
                    mod = f"{prefix}.{node.module}" if node.module else prefix
                    if mod:
                        names.append(mod)
                        names += [f"{mod}.{a.name}" for a in node.names]
        for name in names:
            parts = name.split(".")
            for cut in range(len(parts), 0, -1):
                cand = pathlib.Path(*parts[:cut]).with_suffix(".py")
                init = pathlib.Path(*parts[:cut]) / "__init__.py"
                for c in (cand, init):
                    if (_ROOT / c).is_file() and c not in seen:
                        queue.append(c)
    return seen


def _non_docstring_strings(path: pathlib.Path) -> list[str]:
    import ast
    tree = ast.parse((_ROOT / path).read_text())
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(
                    body[0].value, ast.Constant) and isinstance(
                    body[0].value.value, str):
                doc_nodes.add(id(body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in doc_nodes]


_PATH_TOKEN_RE = None  # compiled lazily below


def _allowlisted_path_tokens(text: str) -> list[str]:
    """Tokens in text that name an allowlisted file or a path under an
    allowlisted directory prefix (PR #47 r2 blockers 1+3: files AND
    directory prefixes, in Python literals AND workflow shell)."""
    import re
    global _PATH_TOKEN_RE
    if _PATH_TOKEN_RE is None:
        files = "|".join(re.escape(f) for f in _NON_RUNTIME_FILES)
        dirs = "|".join(re.escape(d) for d in _NON_RUNTIME_DIR_PREFIXES)
        _PATH_TOKEN_RE = re.compile(rf"(?:{files})|(?:{dirs})[\w./-]*")
    return _PATH_TOKEN_RE.findall(text)


def _pin(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# Reviewed PROSE mentions of allowlisted paths in executable contexts —
# each is a doc-pointer inside a human-facing message, not file I/O, and
# each is pinned to the sha256 of its exact containing literal/line: any
# NEW mention, or any EDIT to a pinned one, fails the proof closed until
# a human reclassifies it here (boundary-ignore pattern: enumerated,
# visible in diff, evaluator-reviewed).
_REVIEWED_PROSE_MENTIONS = {
    # ingest.yml preconditions step: "See docs/SPRINT_LIVE_SITE.md Step 5."
    # inside the missing-secrets ::error echo — a doc pointer in a
    # human-facing refusal message; the line performs no file access.
    ("ingest.yml", "docs/SPRINT_LIVE_SITE.md", "21dffb6d5c99"),
    # ai/claude_provider.py extraction-blocked error message cites the
    # Record row and bar ("docs/RECORD.md R-013 ... R-006") — message
    # text; the module performs no docs/ file access.
    ("ai/claude_provider.py", "docs/RECORD.md", "708b66db190e"),
    # tools/model_router.py cites its policy doc in an unknown-stage
    # error and a routing-policy message; STAGE_MODELS is hardcoded in
    # the module — verified: no open()/read_text in the file, the doc
    # is documentation OF the mapping, never parsed as config.
    ("tools/model_router.py", "docs/MODEL_ROUTING.md", "542b03cae0e9"),
    ("tools/model_router.py", "docs/MODEL_ROUTING.md", "8ecdcaeef40d"),
    ("tools/model_router.py", "docs/RECORD.md", "739f350469b9"),
}


def test_non_runtime_set_is_proven_against_workflow_closure():
    """PR #47 r1 blocker (extended at r2): allowlist entries must be
    mechanically proven, not asserted. Three signals, all fail-closed:

    1. WORKFLOW TEXT (r2 blocker 1): every non-comment line of ingest.yml
       is scanned for allowlisted-path tokens — the workflow's own shell
       consuming STATE.md/TODOS.md/docs//tests/ turns this red.
    2. CLOSURE PLACEMENT: no file in the derived execution closure
       (ingest.yml entry scripts + transitive intra-repo imports,
       INCLUDING package-relative imports — r2 blocker 2) may live under
       an allowlisted path.
    3. CLOSURE LITERALS (r2 blocker 3): every non-docstring string
       literal in the closure is scanned for allowlisted-path tokens —
       files AND directory prefixes.

    Existing PROSE mentions (doc pointers inside error messages) are
    enumerated in _REVIEWED_PROSE_MENTIONS, pinned to the sha256 of
    their exact containing text: any new mention or edit re-REDs this
    test for human reclassification. Static analysis is not a sandbox —
    a dynamically assembled path evades any static check — but every
    straightforward consumption shape (a path token reaching executable
    text) turns this red, which is the failure property the classifier
    must have.
    """
    entries = _workflow_entry_scripts()
    assert entries, "no entry scripts derived from ingest.yml — proof impossible, failing closed"
    assert pathlib.Path("worker/run_once.py") in entries, (
        f"ingest.yml no longer invokes worker/run_once.py (got {entries}) — "
        "the workflow contract changed; re-derive this proof before trusting "
        "the non-runtime classification"
    )

    # Signal 1: the workflow's own executable text.
    wf_lines = [ln for ln in
                (_ROOT / ".github" / "workflows" / "ingest.yml")
                .read_text().splitlines()
                if not ln.lstrip().startswith("#")]
    wf_unreviewed = []
    for ln in wf_lines:
        for tok in _allowlisted_path_tokens(ln):
            key = ("ingest.yml", tok, _pin(ln.strip()))
            if key not in _REVIEWED_PROSE_MENTIONS:
                wf_unreviewed.append(key)
    assert not wf_unreviewed, (
        f"ingest.yml's executable lines reference allowlisted paths not "
        f"enumerated as reviewed prose: {wf_unreviewed} — reclassify "
        "before trusting the smoke binding"
    )

    # Signal 2: closure placement.
    closure = _import_closure(entries)
    inside = [str(p) for p in closure if _is_non_runtime(str(p))]
    assert not inside, (
        f"files under allowlisted non-runtime paths are part of the armed "
        f"workflow's execution closure: {inside} — the allowlist is wrong"
    )

    # Signal 3: closure executable literals.
    lit_unreviewed = []
    for rel in sorted(closure):
        for s in _non_docstring_strings(rel):
            for tok in _allowlisted_path_tokens(s):
                key = (str(rel), tok, _pin(s))
                if key not in _REVIEWED_PROSE_MENTIONS:
                    lit_unreviewed.append(key)
    assert not lit_unreviewed, (
        f"executable string literals in the armed closure reference "
        f"allowlisted paths not enumerated as reviewed prose: "
        f"{lit_unreviewed} — reclassify before trusting the smoke binding"
    )
