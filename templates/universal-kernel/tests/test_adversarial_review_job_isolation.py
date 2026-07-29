"""The job boundary that keeps PR-controlled code away from the API secret.

TEMPLATE-LOCAL BY DESIGN. This kernel ships a secret-bearing evaluator
workflow, so the invariant that protects it has to travel WITH the kernel.
Before this file existed the only isolation test lived in the origin repo's
root suite, which meant that after transport an adopting project's own
`tools/validate` could not catch reintroducing the key-exfiltration hole —
caught by the PR #75 r9 absence-only review seat, class
`missing-template-local-trust-test`.

THE HOLE THIS PREVENTS. `$GITHUB_PATH` and `$GITHUB_ENV` are per-JOB: anything
an earlier STEP writes to them is applied by the runner to every later step in
the same job. So a workflow that installs dependencies, runs the test suite,
and then hands a secret to a "trusted" step lets a malicious PR shadow `git`,
`sha256sum`, `mktemp` or `python` — or set `BASH_ENV` / `<PROVIDER>_BASE_URL` —
and its own code executes, or the API call redirects, with the key present.
Pinning the reviewer FILE by SHA + digest protects WHAT runs, never WHICH
binaries verify and run it, and `python -I` isolates the import path, not which
interpreter `PATH` resolves to.

The fix is a job boundary: a fresh runner is a whitelist by construction, where
enumerating dangerous variables would be a blacklist — fail-open on a
key-exfiltration path. These tests assert what the split DECIDES, not that the
words are present.
"""
import pathlib
import re

import pytest

# Imported, not `importorskip`ed, deliberately: this guards a key-exfiltration
# boundary, and a silently skipped trust test is the failure mode the kernel's
# own charter calls the founding anti-pattern. If PyYAML is absent the suite
# says so loudly. Install it (`pip install PyYAML`) rather than skipping.
try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment defect, not logic
    raise RuntimeError(
        "PyYAML is required to verify the evaluator workflow's job isolation. "
        "This test guards a key-exfiltration boundary and must never be skipped "
        "into silence — install PyYAML."
    ) from exc

_ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = ".github/workflows/adversarial-review.yml"

UNTRUSTED_COMMANDS = (
    r"(?<![\w/.-])pip install\b",
    r"(?<![\w/.-])pytest(?![\w.-])",
    r"(?<![\w.-])tools/validate(?![\w.-])",
    r"(?<![\w/.-])npm (ci|test|run build)\b",
    r"(?<![\w/.-])npx\s",
)
MODEL_API_KEYS = ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")

# ALLOWLIST, never a blacklist (PR #75 r15, openai attacker-smuggle, class
# pr-selected-code-in-secret-job). The first cut of both guards below asserted
# a SHAPE — "the install is pinned", "the action is not workspace-relative" —
# and a shape check cannot say WHICH code runs. A later PR could add
# `attacker_pkg==1.0` to the key-bearing job's install (a wheel may drop a
# `.pth` file that executes on every subsequent `python -I` in that job, so
# --no-deps --only-binary=:all: does not contain it), or `uses:
# attacker/action@v1` (published, therefore "not PR-authored" by the old
# rule, yet still code the subject chose, running before the secret step with
# full $GITHUB_ENV / $GITHUB_PATH access). Both stayed green.
#
# The property that matters is not "pinned" or "not local" — it is that
# EVERY unit of code in the key-bearing job was chosen by the base, not by
# the subject. That is only expressible as an enumeration of what IS allowed,
# so widening it is an edit to this gate file, visible in the same review.
# ADOPTERS: if your evaluator job needs another dependency or action, add it
# HERE, deliberately — do not loosen the check.
# FULL SPECS, not names (PR #75 r16, openai both seats, class
# key-job-code-not-content-bound). r15's allowlists bound `pyyaml` and
# `actions/checkout` — the name and the repo — while the executable code is
# selected by name+VERSION and repo+REF. `PyYAML==7.0.0` and
# `actions/checkout@main` both stayed green, so the guard said "an approved
# NAME runs here" when the property it claims is "approved CODE runs here".
# Comparison is lowercased for the package (pip is case-insensitive on names,
# not on versions) and exact for the action ref.
KEY_JOB_ALLOWED_PACKAGES = frozenset({"pyyaml==6.0.2"})
KEY_JOB_ALLOWED_ACTIONS = frozenset({
    "actions/checkout@v4", "actions/setup-python@v5",
    "actions/download-artifact@v4",
})


# The ONLY install shape a key-bearing job may use: isolated interpreter,
# pinned, no transitive pull-in, wheels only (no setup.py executes).
_PINNED_INSTALL_RE = re.compile(
    r"python -I -m pip install\b(?=.*--no-deps)(?=.*--only-binary=:all:)"
    r"(?!.*\s-r\b)(?!.*\s-e\b)"
)


def _load():
    path = _ROOT / WORKFLOW
    assert path.is_file(), f"{WORKFLOW} is missing — the gate cannot be verified"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _executable_lines(step):
    """Lines a shell would actually RUN — comments and `echo` are prose, and
    shell continuations are joined so a flag-shape check sees whole commands."""
    out, pending = [], ""
    for raw in (step.get("run") or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("echo "):
            pending = ""
            continue
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        out.append((pending + line).strip())
        pending = ""
    if pending:
        out.append(pending.strip())
    return out


def _key_bearing_jobs(wf):
    return {n: j for n, j in wf["jobs"].items()
            if any(k in yaml.dump(j) for k in MODEL_API_KEYS)}


def test_the_workflow_has_a_key_bearing_job_at_all():
    """Guards against a vacuous suite: if the evaluator workflow stops holding
    a key, every test below would pass by examining nothing."""
    assert _key_bearing_jobs(_load()), (
        f"{WORKFLOW} names no model API key — either the mandatory review was "
        f"removed (a gate-threshold relaxation, founder-crucial) or this test "
        f"is now checking nothing")


def test_api_keys_never_share_a_job_with_untrusted_commands():
    """THE invariant. A key and PR-authored code in one job is the bypass."""
    wf = _load()
    for name, job in _key_bearing_jobs(wf).items():
        for step in job.get("steps", []):
            for line in _executable_lines(step):
                if _PINNED_INSTALL_RE.search(line):
                    continue  # exempt shape, asserted below
                for cmd in UNTRUSTED_COMMANDS:
                    assert not re.search(cmd, line), (
                        f"{WORKFLOW}: job {name!r} holds an API key AND executes "
                        f"PR-controlled code ({cmd!r} in {line!r}) — a PR can poison "
                        f"$GITHUB_PATH/$GITHUB_ENV in that step")


def test_a_key_bearing_install_is_pinned_isolated_and_precedes_checkout():
    """`python -m pip` puts the CWD on sys.path, so with the PR checked out
    first a PR-supplied `pip.py` executes inside the trusted job."""
    wf = _load()
    for name, job in _key_bearing_jobs(wf).items():
        steps = job["steps"]
        checkouts = [i for i, s in enumerate(steps)
                     if "actions/checkout" in str(s.get("uses", ""))]
        for i, step in enumerate(steps):
            for line in _executable_lines(step):
                if "pip install" not in line:
                    continue
                assert _PINNED_INSTALL_RE.search(line), (
                    f"{WORKFLOW}: job {name!r} installs without the required "
                    f"`python -I -m pip ... --no-deps --only-binary=:all:` shape "
                    f"(and never `-r`, which is PR-authored): {line!r}")
                pkgs = re.findall(r'"([^"]+==[^"]+)"', line) or re.findall(
                    r"(?<!-)\b([A-Za-z][\w.-]*==[\w.]+)", line)
                assert pkgs, (
                    f"{WORKFLOW}: job {name!r} installs an unpinned package: {line!r}")
                for pkg in pkgs:
                    spec = pkg.strip().lower()
                    assert spec in KEY_JOB_ALLOWED_PACKAGES, (
                        f"{WORKFLOW}: job {name!r} holds a key and installs "
                        f"{pkg!r}, which is not in KEY_JOB_ALLOWED_PACKAGES "
                        f"({sorted(KEY_JOB_ALLOWED_PACKAGES)}). Pinning says "
                        f"WHICH VERSION runs, not WHICH CODE: a wheel can drop "
                        f"a .pth that executes on every later `python -I` in "
                        f"this job.")
                assert not checkouts or i < min(checkouts), (
                    f"{WORKFLOW}: job {name!r} installs at step {i}, AFTER the "
                    f"checkout at {min(checkouts)} — the workspace must be empty")


def test_the_untrusted_work_moved_rather_than_disappeared():
    """The split must MOVE the work; a workflow that stopped running the tests
    would satisfy the invariant above vacuously."""
    wf = _load()
    everything = "\n".join(
        line for job in wf["jobs"].values() for step in job.get("steps", [])
        for line in _executable_lines(step))
    raw = (_ROOT / WORKFLOW).read_text(encoding="utf-8")
    required = [r"(?<![\w/.-])pytest(?![\w.-])",
                r"(?<![\w.-])tools/validate(?![\w.-])"]
    for npm in (r"npm ci", r"npm test", r"npm run build", r"npx "):
        if re.search(npm, raw):
            required.append(re.escape(npm))
    for cmd in required:
        assert re.search(cmd, everything), (
            f"{WORKFLOW}: {cmd!r} no longer runs in ANY job — the evidence the "
            f"review is judged on would be missing")


def test_a_failed_evidence_job_reds_the_gate_instead_of_skipping_it():
    """Without `if: always()` the required check reports "skipped" when its
    dependency fails, and a skipped required check can count as satisfied."""
    wf = _load()
    for name, job in _key_bearing_jobs(wf).items():
        if not job.get("needs"):
            continue
        assert str(job.get("if")).strip() == "always()", (
            f"{WORKFLOW}: job {name!r} gates on `needs` without `if: always()`")
        steps = job["steps"]
        guards = [i for i, s in enumerate(steps)
                  if re.search(r"\.result\s*}}", yaml.dump(s))]
        assert guards, (
            f"{WORKFLOW}: job {name!r} runs with if: always() but never checks the "
            f"dependency's result — always() alone turns a red dependency green")
        keyed = [i for i, s in enumerate(steps)
                 if any(k in yaml.dump(s) for k in MODEL_API_KEYS)]
        assert min(guards) < min(keyed), (
            f"{WORKFLOW}: the evidence guard runs after the first key-bearing step")


def test_the_secret_job_consumes_no_output_of_an_untrusted_job():
    """Step OUTPUTS of an untrusted job are attacker-chosen values; only inert
    artifacts (log files, read as text) may cross the boundary."""
    wf = _load()
    untrusted = {n for n, j in wf["jobs"].items()
                 if any(re.search(c, line)
                        for s in j.get("steps", [])
                        for line in _executable_lines(s)
                        for c in UNTRUSTED_COMMANDS)
                 and not any(k in yaml.dump(j) for k in MODEL_API_KEYS)}
    assert untrusted, f"{WORKFLOW}: no secretless job runs the PR's code"
    for name, job in _key_bearing_jobs(wf).items():
        for u in untrusted:
            assert f"needs.{u}.outputs" not in yaml.dump(job), (
                f"{WORKFLOW}: {name!r} consumes an output of untrusted job {u!r}")


def test_the_reviewer_is_executed_only_from_a_base_owned_copy():
    """The job split protects the COMMANDS; this protects the FILE. Both are
    needed — shipping only the second is what the origin repo's r6 did, and
    the review correctly called the resulting claim overstated."""
    text = (_ROOT / WORKFLOW).read_text(encoding="utf-8")
    assert re.search(r'git show "\$TRUSTED_(BASE|SHA):tools/', text), (
        f"{WORKFLOW}: the reviewer is no longer fetched from a base-owned ref")
    assert "sha256sum" in text, f"{WORKFLOW}: the reviewer's digest is not verified"
    assert "python -I" in text, f"{WORKFLOW}: the reviewer no longer runs under -I"


def test_nothing_is_hidden_from_the_reviewed_diff():
    """PR #75 r13, class hidden-diff-exclusion-without-compensating-gate.

    The kernel ships no supply-chain audit — it cannot assume npm, Node, or
    any ecosystem. So excluding lockfiles from the reviewed diff would let a
    pull request change dependency RESOLUTION with nothing looking at it. An
    exclusion is legitimate only when a second control verifiably examines
    what was removed; here there is none, so there is no exclusion.

    A project that later adds a blocking dependency-audit gate may reintroduce
    an exclusion in the same change — and must then update this test, which is
    the point: the pairing becomes a deliberate, reviewed decision.
    """
    text = (_ROOT / WORKFLOW).read_text(encoding="utf-8")
    diff_cmds = [ln for ln in text.splitlines()
                 if "git diff" in ln and "pr.diff" in ln]
    assert diff_cmds, f"{WORKFLOW}: no diff-producing command found"
    for line in diff_cmds:
        assert ":(exclude)" not in line, (
            f"{WORKFLOW}: the reviewed diff hides paths with no compensating "
            f"gate examining them — the Independent Evaluator would judge an "
            f"incomplete change: {line.strip()!r}")


def test_a_key_bearing_job_invokes_no_pr_authored_local_action():
    """A LOCAL action (`uses: ./...`) is PR-authored code executing in the job,
    with no `run:` line for the other checks here to inspect — so the boundary
    could be reopened through a surface this suite never looked at while every
    test stayed green (PR #75 r14, class untested-local-action-execution).

    Published actions (`owner/repo@ref`) remain allowed: they are not authored
    by the pull request, which is the property this guards.
    """
    wf = _load()
    for name, job in _key_bearing_jobs(wf).items():
        for i, step in enumerate(job.get("steps", [])):
            uses = str(step.get("uses", "")).strip()
            if not uses:
                continue
            assert uses.strip() in KEY_JOB_ALLOWED_ACTIONS, (
                f"{WORKFLOW}: job {name!r} step {i} invokes {uses!r}, which is "
                f"not in KEY_JOB_ALLOWED_ACTIONS "
                f"({sorted(KEY_JOB_ALLOWED_ACTIONS)}). 'Published' is not the "
                f"same as 'not chosen by the subject' — anyone can publish "
                f"attacker/action@v1, and the PR-owned workflow choosing it "
                f"puts subject-selected code in the key-bearing job, able to "
                f"write $GITHUB_ENV / $GITHUB_PATH before the secret step.")
            assert not uses.startswith((".", "/")), (
                f"{WORKFLOW}: job {name!r} step {i} invokes a workspace-relative "
                f"action ({uses!r}) — PR-authored code in the key-bearing job")


# ── MUTATION PROOF. A guard that has never been shown to REJECT anything is a
# green test, not a gate (PR #75 r15). Both allowlists are exercised against
# the real workflow with one smuggled unit of subject-selected code added to
# the key-bearing job.

def _mutated_key_job(extra_step):
    wf = _load()
    for job in _key_bearing_jobs(wf).values():
        job["steps"].insert(0, extra_step)
        return wf
    raise AssertionError(f"{WORKFLOW}: no key-bearing job to mutate")


def test_the_package_allowlist_rejects_a_smuggled_dependency(monkeypatch):
    wf = _mutated_key_job({"run": (
        'python -I -m pip install --no-deps --only-binary=:all: '
        '"attacker_pkg==1.0"')})
    monkeypatch.setitem(globals(), "_load", lambda: wf)
    with pytest.raises(AssertionError, match="KEY_JOB_ALLOWED_PACKAGES"):
        test_a_key_bearing_install_is_pinned_isolated_and_precedes_checkout()


def test_the_action_allowlist_rejects_a_published_third_party_action(monkeypatch):
    wf = _mutated_key_job({"uses": "attacker/action@v1"})
    monkeypatch.setitem(globals(), "_load", lambda: wf)
    with pytest.raises(AssertionError, match="KEY_JOB_ALLOWED_ACTIONS"):
        test_a_key_bearing_job_invokes_no_pr_authored_local_action()


def test_the_package_allowlist_rejects_a_version_swap(monkeypatch):
    """PR #75 r16: binding the NAME left the version — and therefore the
    wheel, and therefore the code — free."""
    wf = _mutated_key_job({"run": (
        'python -I -m pip install --no-deps --only-binary=:all: '
        '"PyYAML==7.0.0"')})
    monkeypatch.setitem(globals(), "_load", lambda: wf)
    with pytest.raises(AssertionError, match="KEY_JOB_ALLOWED_PACKAGES"):
        test_a_key_bearing_install_is_pinned_isolated_and_precedes_checkout()


def test_the_action_allowlist_rejects_a_ref_swap(monkeypatch):
    wf = _mutated_key_job({"uses": "actions/checkout@main"})
    monkeypatch.setitem(globals(), "_load", lambda: wf)
    with pytest.raises(AssertionError, match="KEY_JOB_ALLOWED_ACTIONS"):
        test_a_key_bearing_job_invokes_no_pr_authored_local_action()
