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

yaml = pytest.importorskip("yaml")

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
    for raw in (step.get("run") or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("echo "):
            continue
        out.append(line)
    return out


def _job_holding(workflow, key):
    return {
        name
        for name, job in workflow["jobs"].items()
        if key in yaml.dump(job)
    }


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
    for cmd in (r"(?<![\w/.-])pip install\b", r"(?<![\w/.-])pytest(?![\w.-])",
                r"(?<![\w.-])tools/validate(?![\w.-])"):
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
