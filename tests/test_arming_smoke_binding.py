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
    resolve to files inside the repo are followed. Bare imports are
    resolved from the repo root AND from every entry script's own
    directory (PR #47 r3 blocker 1: `python worker/run_once.py` puts
    worker/ on sys.path for the whole process, so any module in the
    closure can import siblings of any entry script by bare name)."""
    import ast
    bases = [pathlib.Path("")] + sorted({e.parent for e in entries})
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
                for base in bases:
                    cand = (base / pathlib.Path(*parts[:cut])).with_suffix(".py")
                    init = base / pathlib.Path(*parts[:cut]) / "__init__.py"
                    for c in (cand, init):
                        if (_ROOT / c).is_file() and c not in seen:
                            queue.append(c)
    return seen


_PATH_TOKEN_RE = None  # compiled lazily below


def _allowlisted_path_tokens(text: str) -> list[str]:
    """Tokens in text that name an allowlisted file or a path under an
    allowlisted directory prefix (r2: files AND directory prefixes),
    plus bare directory-name literals (r3: the atoms of ordinary path
    construction — Path("docs") / "x", os.path.join("docs", ...))."""
    import re
    global _PATH_TOKEN_RE
    if _PATH_TOKEN_RE is None:
        files = "|".join(re.escape(f) for f in _NON_RUNTIME_FILES)
        dirs = "|".join(re.escape(d) for d in _NON_RUNTIME_DIR_PREFIXES)
        _PATH_TOKEN_RE = re.compile(rf"(?:{files})|(?:{dirs})[\w./-]*")
    hits = _PATH_TOKEN_RE.findall(text)
    bare = text.strip().lstrip("./")
    if bare + "/" in _NON_RUNTIME_DIR_PREFIXES:
        hits.append(f"{bare} (bare directory-name literal)")
    return hits


def _shell_word_hits(line: str) -> list[str]:
    """r4: in shell, bare directory operands are the NORMAL consumption
    spelling — `find docs -type f`, `ls tests`, `tar -cf x docs`.
    Tokenize into shell words and flag any word that IS an allowlisted
    directory name (./-prefix tolerated). English prose collisions
    enumerate hash-pinned like every other reviewed mention."""
    import re
    words = re.split(r"""[\s;|&()<>='"`]+""", line)
    return [f"{w} (bare shell word)" for w in words
            if w and w.lstrip("./") + "/" in _NON_RUNTIME_DIR_PREFIXES]


def _strings_with_context(source: str):
    """(value, context) for every non-docstring string literal in source.
    Context = the dotted callee of the nearest enclosing Call, or
    "<no-call>" (PR #47 r5 blocker 2: a prose pin without call-site
    context lets the SAME literal be reused inside open()/Path().read_text()
    unnoticed — the context makes that reuse a different, unreviewed key)."""
    import ast
    tree = ast.parse(source)
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node
    doc_ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if body and isinstance(node, (ast.Module, ast.ClassDef,
                                      ast.FunctionDef, ast.AsyncFunctionDef)):
            if isinstance(body[0], ast.Expr) and isinstance(
                    body[0].value, ast.Constant) and isinstance(
                    body[0].value.value, str):
                doc_ids.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in doc_ids:
            ctx = "<no-call>"
            cur = node
            while cur in parent:
                cur = parent[cur]
                if isinstance(cur, ast.Call):
                    ctx = ast.unparse(cur.func)
                    break
            out.append((node.value, ctx))
    return out


def _non_docstring_strings(path: pathlib.Path):
    return _strings_with_context((_ROOT / path).read_text())


def _pin(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# Reviewed PROSE mentions of allowlisted paths in executable text — each
# is a doc-pointer inside a human-facing message, not file I/O. Python
# entries pin (file, token, sha256(literal), call-site context); workflow
# entries pin (token, sha256(line)). Any NEW mention, any EDIT, or the
# SAME literal reappearing in a DIFFERENT call context (e.g. moved into
# open()) produces an unreviewed key and fails closed until a human
# reclassifies it here (boundary-ignore pattern: enumerated, visible in
# diff, evaluator-reviewed).
_REVIEWED_WORKFLOW_MENTIONS = {
    # preconditions step: "See docs/SPRINT_LIVE_SITE.md Step 5." inside
    # the missing-secrets ::error echo — no file access on the line.
    ("docs/SPRINT_LIVE_SITE.md", "21dffb6d5c99"),
}
_REVIEWED_PROSE_MENTIONS = {
    # ai/claude_provider.py extraction-blocked RuntimeError message cites
    # the Record row and bar — message text, no docs/ access.
    ("ai/claude_provider.py", "docs/RECORD.md", "708b66db190e",
     "ExtractionConfigError"),
    # tools/model_router.py cites its policy doc in its CLI description,
    # an unknown-stage KeyError, and an extraction-blocked RuntimeError;
    # STAGE_MODELS is hardcoded — verified no open()/read_text in file.
    ("tools/model_router.py", "docs/MODEL_ROUTING.md", "542b03cae0e9",
     "argparse.ArgumentParser"),
    ("tools/model_router.py", "docs/MODEL_ROUTING.md", "8ecdcaeef40d",
     "KeyError"),
    ("tools/model_router.py", "docs/RECORD.md", "739f350469b9",
     "ValueError"),
}


def _literal_tokens(s: str) -> list[str]:
    """All allowlisted-path tokens in a Python string literal: prefix
    tokens, bare directory-name literals, AND bare shell-word operands
    (PR #47 r5 blocker 1: subprocess.run("find docs -type f", shell=True)
    carries consumption in a command STRING — shell-word detection must
    apply to Python literals, not only to ingest.yml lines)."""
    return _allowlisted_path_tokens(s) + _shell_word_hits(s)


def test_non_runtime_set_is_proven_against_workflow_closure():
    """PR #47 r1 blocker (extended r2-r5): allowlist entries must be
    mechanically proven, not asserted. Three signals, all fail-closed:

    1. WORKFLOW TEXT: every non-comment line of ingest.yml scanned for
       allowlisted-path tokens AND bare directory shell operands.
    2. CLOSURE PLACEMENT: no file in the derived execution closure
       (ingest.yml entry scripts + transitive intra-repo imports incl.
       package-relative and script-directory resolution) may live under
       an allowlisted path.
    3. CLOSURE LITERALS: every non-docstring string literal in the
       closure scanned with the SAME token+shell-word detection, keyed
       by call-site context so a reviewed prose literal reused inside a
       file-access call becomes an unreviewed key.

    Reviewed prose mentions are enumerated + hash/context-pinned above.
    Static analysis is not a sandbox — a dynamically assembled path can
    evade any static check (dynamic-primitive detection is queued,
    TODOS P3) — but every straightforward consumption spelling turns
    this red, and test_proof_signals_catch_known_evasion_classes pins
    each closed evasion class so it cannot silently regress.
    """
    entries = _workflow_entry_scripts()
    assert entries, "no entry scripts derived from ingest.yml — proof impossible, failing closed"
    assert pathlib.Path("worker/run_once.py") in entries, (
        f"ingest.yml no longer invokes worker/run_once.py (got {entries}) — "
        "the workflow contract changed; re-derive this proof before trusting "
        "the non-runtime classification"
    )

    wf_lines = [ln for ln in
                (_ROOT / ".github" / "workflows" / "ingest.yml")
                .read_text().splitlines()
                if not ln.lstrip().startswith("#")]
    wf_unreviewed = []
    for ln in wf_lines:
        toks = [t for t in _allowlisted_path_tokens(ln)
                if not t.endswith("(bare directory-name literal)")]
        toks += _shell_word_hits(ln)
        for tok in toks:
            if (tok, _pin(ln.strip())) not in _REVIEWED_WORKFLOW_MENTIONS:
                wf_unreviewed.append((tok, _pin(ln.strip())))
    assert not wf_unreviewed, (
        f"ingest.yml's executable lines reference allowlisted paths not "
        f"enumerated as reviewed prose: {wf_unreviewed} — reclassify "
        "before trusting the smoke binding"
    )

    closure = _import_closure(entries)
    inside = [str(p) for p in closure if _is_non_runtime(str(p))]
    assert not inside, (
        f"files under allowlisted non-runtime paths are part of the armed "
        f"workflow's execution closure: {inside} — the allowlist is wrong"
    )

    lit_unreviewed = []
    for rel in sorted(closure):
        for s, ctx in _non_docstring_strings(rel):
            for tok in _literal_tokens(s):
                key = (str(rel), tok, _pin(s), ctx)
                if key not in _REVIEWED_PROSE_MENTIONS:
                    lit_unreviewed.append(key)
    assert not lit_unreviewed, (
        f"executable string literals in the armed closure reference "
        f"allowlisted paths not enumerated as reviewed prose (or a "
        f"reviewed literal moved into a new call context): "
        f"{lit_unreviewed} — reclassify before trusting the smoke binding"
    )


def test_proof_signals_catch_known_evasion_classes():
    """Every evasion class closed in PR #47 r1-r5 is pinned here so it
    cannot silently regress (r5 nit: the analyzer needs self-tests for
    the exact classes it claims to close, not prose comments)."""
    # r1: prefix tokens in one literal
    assert _allowlisted_path_tokens("docs/RECORD.md")
    assert _allowlisted_path_tokens("see tests/conftest.py")
    # r3: bare directory-name literal (path-construction atom)
    assert any("bare" in t for t in _allowlisted_path_tokens("docs"))
    assert any("bare" in t for t in _allowlisted_path_tokens("./tests"))
    assert not _allowlisted_path_tokens("documents")
    # r4: bare directory operands in shell lines
    assert _shell_word_hits("find docs -type f")
    assert _shell_word_hits("ls tests")
    assert _shell_word_hits("tar -cf x.tar ./docs")
    assert not _shell_word_hits("pip install -r worker/requirements.txt")
    assert not _shell_word_hits("documented steps")
    # r5 blocker 1: shell-word detection applies to Python literals
    assert _literal_tokens('find docs -type f')
    # r5 blocker 2: same literal, different call context -> different key
    prose = _strings_with_context(
        'raise ValueError("see docs/MODEL_ROUTING.md")')
    consuming = _strings_with_context(
        'open("see docs/MODEL_ROUTING.md")')
    assert prose[0][0] == consuming[0][0] and prose[0][1] != consuming[0][1]
    # r2: package-relative imports resolve (worker/__init__.py exists ->
    # a synthetic check via the real closure: orchestrator reached)
    closure = _import_closure([pathlib.Path("worker/run_once.py")])
    assert pathlib.Path("worker/orchestrator.py") in closure
    # r3 blocker 1: script-dir sibling resolution is part of closure bases
    assert pathlib.Path("worker/sentinel.py") in closure
