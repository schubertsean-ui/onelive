"""The job boundary that keeps PR-controlled code away from the API secrets.

PR #75 r7, class `runner-env-poisoning`: both OpenAI review seats blocked on a
live key-exfiltration path and they were right. Until r8 the whole workflow was
ONE job — `pip install`, `pytest`, `bash tools/validate` and the npm build, all
PR-controlled, ran in the same job that later held `OPENAI_API_KEY`. r6 had
pinned the reviewer FILE (immutable SHA + sha256), which stops the file being
swapped but says nothing about the COMMANDS that verify and run it: any earlier
step in a job may append to `$GITHUB_PATH`/`$GITHUB_ENV`, and the runner applies
those to every LATER step. A malicious PR could shadow `git`, `sha256sum`,
`mktemp` or `python`, or set `BASH_ENV`/`OPENAI_BASE_URL`, and its own code
would execute — or the API call redirect — with the secret in the environment.
`python -I` isolates the interpreter's import path, not WHICH interpreter
`PATH` resolves to.

The fix is a job boundary, because `$GITHUB_PATH`/`$GITHUB_ENV` are per-job: a
fresh runner is a whitelist by construction, where enumerating dangerous
variables would be a blacklist — fail-open on a key-exfiltration path.

These tests assert what the split DECIDES, not that the words are present
(class `untested-gate-branch`): which job holds which secret, which job runs
untrusted commands, that the guard precedes the first key-bearing step, and
that a failed evidence job reds the required check instead of skipping it.
"""
import pathlib
import re

import pytest

# Imported, NOT `importorskip`ed (PR #75 r11, class
# fail-open-trust-test-dependency). This is a key-exfiltration regression
# suite: `importorskip` let the whole boundary check vanish into a skip when
# the parser was missing, which is the founding anti-pattern — "we could not
# check" looking identical to "there was nothing wrong". The template-local
# copy already hard-failed; these two must not disagree about whether a trust
# invariant may be silently skipped.
try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment defect, not logic
    raise RuntimeError(
        "PyYAML is required to verify the evaluator workflow's job isolation. "
        "This guards a key-exfiltration boundary and must never be skipped into "
        "silence — install PyYAML."
    ) from exc

_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Both the live workflow and the staged kernel template carry this structure;
# a fix that lands in one and not the other ships the hole to every project
# that adopts the kernel, which is how r7's finding reached the template.
WORKFLOWS = [
    ".github/workflows/adversarial-review.yml",
    "templates/universal-kernel/.github/workflows/adversarial-review.yml",
]

# Commands that EXECUTE PR-authored content. Presence of any of these in a
# secret-bearing job is the defect this module exists to prevent.
#
# Matched as invocations, not substrings. A plain `in` check reported the
# trusted job as running pytest because it passes `pr-evidence/pytest.log` as a
# --test-log ARGUMENT (self-caught while writing this file). The lookarounds
# refuse a match that is part of a longer path or filename token, so reading a
# log named after a command is not mistaken for running it.
UNTRUSTED_COMMANDS = (
    r"(?<![\w/.-])pip install\b",
    r"(?<![\w/.-])pytest(?![\w.-])",
    r"(?<![\w.-])tools/validate(?![\w.-])",
    r"(?<![\w/.-])npm (ci|test|run build)\b",
    r"(?<![\w/.-])npx\s",
)

MODEL_API_KEYS = ("OPENAI_API_KEY", "GEMINI_API_KEY")


def _load(rel):
    path = _ROOT / rel
    assert path.is_file(), f"{rel} is missing — the gate cannot be verified"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _executable_lines(step):
    """The lines a shell would actually RUN in this step.

    Comments and `echo` lines are prose — the workflow deliberately prints
    policy text mentioning `npm ci` to the evaluator, and counting that as an
    execution produces a false finding (caught while writing this test).
    """
    out = []
    pending = ""
    for raw in (step.get("run") or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("echo "):
            # A comment or echo cannot continue a command; drop any partial.
            pending = ""
            continue
        # Shell line-continuations make ONE command. Splitting on newlines
        # alone tore `pip install \` from its own flags, so a flag-shape
        # check saw a bare `pip install` (self-caught by this file's own
        # pinned-install test failing on a correctly-pinned command).
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        out.append((pending + line).strip())
        pending = ""
    if pending:
        out.append(pending.strip())
    return out


def _job_holding(workflow, key):
    return {
        name
        for name, job in workflow["jobs"].items()
        if key in yaml.dump(job)
    }


# A key-bearing job may install a dependency ONLY in this exact shape: a
# pinned NAME==VERSION literal, --no-deps (nothing else comes along), and
# --only-binary=:all: (no package's setup.py executes). The trusted job needs
# PyYAML because the base-owned co-gate helper parses a workflow file, and
# the job split deliberately removed its `pip install -r`.
#
# This is a NARROWING with conditions, not a loophole: `-r <file>` stays
# banned because requirements files are PR-authored, and an unpinned or
# path/editable install stays banned because it re-opens the same input.
# test_a_key_bearing_pip_install_is_pinned_and_closed below asserts the shape
# itself, so the exemption cannot be widened by writing a looser command.
_PINNED_INSTALL_RE = re.compile(
    r"python -I -m pip install\b(?=.*--no-deps)(?=.*--only-binary=:all:)"
    r"(?!.*\s-r\b)(?!.*\s-e\b)"
)


def _is_pinned_literal_install(line):
    return bool(_PINNED_INSTALL_RE.search(line))


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_a_key_bearing_pip_install_is_pinned_and_closed(rel):
    """Every install in a key-bearing job takes the exempt shape AND names
    only pinned `NAME==VERSION` packages. An unpinned name would let the
    resolver pick tomorrow's release into the job that holds the secret."""
    wf = _load(rel)
    for name, job in wf["jobs"].items():
        if not any(k in yaml.dump(job) for k in MODEL_API_KEYS):
            continue
        for step in job.get("steps", []):
            for line in _executable_lines(step):
                if "pip install" not in line:
                    continue
                assert _is_pinned_literal_install(line), (
                    f"{rel}: job {name!r} holds a key and installs without the "
                    f"required --no-deps --only-binary=:all: shape: {line!r}")
                pkgs = re.findall(r'"([^"]+)"', line) or re.findall(
                    r"(?<!-)\b([A-Za-z][\w.-]*==[\w.]+)", line)
                assert pkgs, f"{rel}: install names no pinned package: {line!r}"
                for pkg in pkgs:
                    assert "==" in pkg, (
                        f"{rel}: job {name!r} installs {pkg!r} unpinned into a "
                        f"key-bearing job")


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_model_api_keys_never_share_a_job_with_untrusted_commands(rel):
    """THE invariant. A key and PR-authored code in one job is the bypass."""
    wf = _load(rel)
    for name, job in wf["jobs"].items():
        dumped = yaml.dump(job)
        holds_key = any(k in dumped for k in MODEL_API_KEYS)
        if not holds_key:
            continue
        for step in job.get("steps", []):
            for line in _executable_lines(step):
                if _is_pinned_literal_install(line):
                    continue  # exempt shape, asserted by the test above
                for cmd in UNTRUSTED_COMMANDS:
                    assert not re.search(cmd, line), (
                        f"{rel}: job {name!r} holds a model API key AND executes "
                        f"PR-controlled code ({cmd!r} in {line!r}). A PR can poison "
                        f"$GITHUB_PATH/$GITHUB_ENV in that step and shadow the "
                        f"commands the trusted step relies on."
                    )


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_the_untrusted_commands_still_run_somewhere(rel):
    """The split must MOVE the work, never quietly drop it — a workflow that
    stopped running the tests would satisfy the invariant above vacuously."""
    wf = _load(rel)
    everything = "\n".join(
        line
        for job in wf["jobs"].values()
        for step in job.get("steps", [])
        for line in _executable_lines(step)
    )
    # Every danger-listed command that the workflow ACTUALLY runs must still
    # run somewhere. The first version checked only pip/pytest/validate, so a
    # future edit could silently drop the npm build and web-SCA gate while
    # this test stayed green (PR #75 r9, absence-only seat, class
    # untested-gate-branch). The npm commands are conditional on web/ files
    # being touched, so they are required only where the workflow has them.
    required = [r"(?<![\w/.-])pip install\b", r"(?<![\w/.-])pytest(?![\w.-])",
                r"(?<![\w.-])tools/validate(?![\w.-])"]
    raw = (_ROOT / rel).read_text(encoding="utf-8")
    for npm in (r"npm ci", r"npm test", r"npm run build", r"npx "):
        if re.search(npm, raw):
            required.append(re.escape(npm))
    for cmd in required:
        assert re.search(cmd, everything), (
            f"{rel}: {cmd!r} no longer runs in ANY job — the evidence the review "
            f"is judged on would be missing"
        )


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_secret_bearing_job_does_not_depend_on_untrusted_job_outputs(rel):
    """Step OUTPUTS of an untrusted job are attacker-chosen values. Only inert
    artifacts (log files, read as text) may cross the boundary."""
    wf = _load(rel)
    untrusted = {
        name
        for name, job in wf["jobs"].items()
        if any(
            re.search(cmd, line)
            for step in job.get("steps", [])
            for line in _executable_lines(step)
            for cmd in UNTRUSTED_COMMANDS
        )
    }
    assert untrusted, f"{rel}: no job runs the PR's code — test is not exercising anything"
    for name, job in wf["jobs"].items():
        if not any(k in yaml.dump(job) for k in MODEL_API_KEYS):
            continue
        for u in untrusted:
            assert f"needs.{u}.outputs" not in yaml.dump(job), (
                f"{rel}: the secret-bearing job {name!r} consumes an output of the "
                f"untrusted job {u!r} — outputs are attacker-chosen; pass evidence "
                f"as artifacts instead"
            )


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_a_failed_evidence_job_reds_the_gate_instead_of_skipping_it(rel):
    """Fail-open guard. Without `if: always()` the required check reports
    "skipped" when its dependency fails, and GitHub can treat a skipped
    required check as satisfied — on exactly the runs most likely broken."""
    wf = _load(rel)
    for name, job in wf["jobs"].items():
        if not any(k in yaml.dump(job) for k in MODEL_API_KEYS):
            continue
        if not job.get("needs"):
            continue
        assert str(job.get("if")).strip() == "always()", (
            f"{rel}: job {name!r} gates on `needs` without `if: always()` — a failed "
            f"dependency makes the required check SKIP rather than fail"
        )
        steps = job["steps"]
        guards = [
            i for i, s in enumerate(steps)
            if re.search(r"\.result\s*}}", yaml.dump(s))
        ]
        assert guards, (
            f"{rel}: job {name!r} runs with if: always() but never checks the "
            f"dependency's result — always() alone turns a red dependency into a "
            f"green gate"
        )
        keyed = [
            i for i, s in enumerate(steps)
            if any(k in yaml.dump(s) for k in MODEL_API_KEYS)
        ]
        assert keyed, f"{rel}: job {name!r} was selected as key-bearing but has no keyed step"
        assert min(guards) < min(keyed), (
            f"{rel}: the evidence guard (step {min(guards)}) runs AFTER the first "
            f"key-bearing step ({min(keyed)}) — the secret enters the job before the "
            f"refusal can fire"
        )


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_the_reviewer_is_executed_only_from_a_base_owned_copy(rel):
    """Unchanged from r6 and re-asserted here: the job split protects the
    COMMANDS; this protects the FILE. Both are needed — r6 shipped only the
    second and the seats correctly called the claim overstated."""
    wf = _load(rel)
    text = (_ROOT / rel).read_text(encoding="utf-8")
    assert re.search(r'git show "\$TRUSTED_(BASE|SHA):tools/', text), (
        f"{rel}: the reviewer is no longer fetched from a base-owned ref"
    )
    assert "sha256sum" in text, f"{rel}: the reviewer's content digest is no longer verified"
    assert "python -I" in text, f"{rel}: the reviewer no longer runs under python -I"


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_a_key_bearing_install_runs_before_any_checkout(rel):
    """PR #75 r10, class runner-env-poisoning — r9's own fix reopened r8's hole.

    `python -m pip` puts the CWD on sys.path. With the PR checked out first, a
    malicious PR shipping `pip.py` / `pip/__main__.py` at the repo root gets its
    OWN code executed inside the trusted job, before the key-bearing steps and
    free to poison $GITHUB_ENV / $GITHUB_PATH / OPENAI_BASE_URL. Pinning the
    PACKAGE said nothing about which pip MODULE was imported.

    Two independent guards, and this asserts BOTH: the install runs before any
    checkout (empty workspace — nothing to import), and under `python -I`
    (implies -P, so the cwd is never prepended to sys.path). Either alone
    closes it; requiring both means a reorder cannot silently re-open it.
    """
    wf = _load(rel)
    for name, job in wf["jobs"].items():
        if not any(k in yaml.dump(job) for k in MODEL_API_KEYS):
            continue
        steps = job["steps"]
        checkouts = [i for i, s in enumerate(steps)
                     if "actions/checkout" in str(s.get("uses", ""))]
        installs = [i for i, s in enumerate(steps)
                    for line in _executable_lines(s) if "pip install" in line]
        for idx in installs:
            assert not checkouts or idx < min(checkouts), (
                f"{rel}: job {name!r} installs at step {idx}, AFTER the checkout at "
                f"step {min(checkouts)} — `python -m pip` resolves modules from the "
                f"PR workspace, so a PR-supplied pip.py would execute in the "
                f"secret-bearing job")
            line = next(l for l in _executable_lines(steps[idx]) if "pip install" in l)
            assert "python -I -m pip" in line, (
                f"{rel}: job {name!r} installs without `python -I` (which implies "
                f"-P, keeping the cwd off sys.path): {line!r}")


@pytest.mark.parametrize("rel", WORKFLOWS)
def test_a_key_bearing_job_invokes_no_pr_authored_local_action(rel):
    """PR #75 r14, class untested-local-action-execution.

    Every check above inspects shell `run:` lines. A LOCAL action —
    `uses: ./.github/actions/whatever` — is PR-authored code checked out into
    the workspace and executed in the job, with full ability to write
    $GITHUB_ENV / $GITHUB_PATH before the key-bearing step. It carries no
    `run:` line at all, so the entire boundary could be reopened through a
    surface the compensating tests never looked at, and they would stay green.

    Workspace-relative `uses:` is therefore banned outright in a key-bearing
    job. Published actions (`owner/repo@ref`) stay allowed: they are not
    authored by the pull request, which is the property that matters here.
    """
    wf = _load(rel)
    for name, job in wf["jobs"].items():
        if not any(k in yaml.dump(job) for k in MODEL_API_KEYS):
            continue
        for i, step in enumerate(job.get("steps", [])):
            uses = str(step.get("uses", "")).strip()
            if not uses:
                continue
            assert not uses.startswith((".", "/")), (
                f"{rel}: job {name!r} step {i} invokes a workspace-relative "
                f"action ({uses!r}) — that is PR-authored code executing in the "
                f"job that holds the API key, able to poison $GITHUB_ENV / "
                f"$GITHUB_PATH before the secret step. Published actions only.")
