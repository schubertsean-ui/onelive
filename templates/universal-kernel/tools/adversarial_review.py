#!/usr/bin/env python3
"""Independent (non-Claude) adversarial review gate.

Greppable summary: posts a raw git diff + test logs to the OpenAI API (the
charter's Independent Evaluator, default model gpt-5.5) and demands an
explicit `VERDICT: APPROVE` or `VERDICT: REQUEST-CHANGES` with file:line
issues. Enforces the charter's generator/evaluator separation (CLAUDE.md):
the generator (Claude) never grades its own auth/pipeline/SQL/data-trust/
prompt changes. Raw-diff-in, raw-text-out on purpose (grade traces, not
self-summaries). Stdlib-only (urllib), no
`openai` package dependency.

Usage:
  python tools/adversarial_review.py --target HEAD          # review one commit
  python tools/adversarial_review.py --range master..HEAD   # review a range
  python tools/adversarial_review.py --diff-file pr.patch --test-log pytest.log
  python tools/adversarial_review.py --target HEAD --require  # CI: key mandatory

Env: OPENAI_API_KEY (unset -> SKIPPED-loud, exit 0 — the charter says flag,
don't block — unless --require, then exit 2); OPENAI_REVIEW_MODEL (unset ->
gpt-5.5; set-but-empty or a Claude/Anthropic id -> HARD FAIL exit 2, the
fail-closed + write/grade-separation rules); OPENAI_BASE_URL (unset ->
https://api.openai.com/v1; set-but-empty -> HARD FAIL exit 2).

Exit codes (tools/README.md convention): 0 = APPROVE (or explicit no-key skip
without --require); 1 = REQUEST-CHANGES (blocking findings); 2 = hard failure
(API/network error, ambiguous verdict, bad git ref, or --require without key).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

DEFAULT_MODEL = "gpt-5.5"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MAX_DIFF_BYTES = 300_000
_TRUNCATION_MARKER = "\n\n[DIFF TRUNCATED at byte limit — review what is shown; flag the truncation in your verdict]\n"

APPROVE = "APPROVE"
REQUEST_CHANGES = "REQUEST-CHANGES"

SYSTEM_PROMPT = """You are the Independent Evaluator for this project \
(a non-Claude model, per the repo charter's generator/evaluator separation). \
You are adversarial by mandate: your job is to find what is wrong, not to be \
agreeable. Grade the raw diff and test logs against the project's own bar, \
which is written in its CLAUDE.md and OVERLAY.md: those files define this \
project's trust invariants, and any change that weakens, bypasses, or \
silently reinterprets one of them is BLOCKING. Blocking regardless of what \
those files say: swallowed errors, misconfiguration that fails open instead \
of loud, string-interpolated SQL, auth that is not fail-closed, tests that \
cannot actually fail, stubs, and deferred work that is not recorded.

Report every blocking issue as `file:line — issue — why it blocks`. \
Non-blocking suggestions go in a separate NITS section. Then end your reply \
with exactly one line, nothing after it:
VERDICT: APPROVE
or
VERDICT: REQUEST-CHANGES"""


def _git_diff(range_spec: str) -> str:
    proc = subprocess.run(
        ["git", "diff", range_spec],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff {range_spec!r} failed: {proc.stderr.strip()}")
    return proc.stdout


def build_review_input(diff: str, test_logs: list[tuple[str, str]],
                       max_diff_bytes: int = DEFAULT_MAX_DIFF_BYTES) -> str:
    """Assemble the evaluator's user message from a diff + labeled test logs."""
    if len(diff.encode("utf-8", errors="replace")) > max_diff_bytes:
        diff = diff.encode("utf-8", errors="replace")[:max_diff_bytes].decode(
            "utf-8", errors="replace") + _TRUNCATION_MARKER
    parts = ["## RAW DIFF\n```diff\n" + diff + "\n```"]
    if test_logs:
        for label, body in test_logs:
            parts.append(f"## TEST LOG: {label}\n```\n{body}\n```")
    else:
        parts.append("## TEST LOG\n(none provided — weigh accordingly; "
                     "unverified code is a claim, not a fact)")
    return "\n\n".join(parts)


def parse_verdict(review_text: str) -> str:
    """Extract the final APPROVE/REQUEST-CHANGES verdict. Ambiguous -> error.

    The verdict must be unambiguous: exactly one VERDICT line, it must be the
    LAST non-empty line (the prompt demands "nothing after it" — trailing text
    could contradict or launder the verdict), and it decides the exit code. An
    evaluator that hedges gets a hard failure, not a pass.
    """
    lines = [line.strip() for line in review_text.splitlines() if line.strip()]
    verdict_lines = [l for l in lines if l.upper().startswith("VERDICT:")]
    if (
        len(verdict_lines) != 1
        or not lines
        or lines[-1] != verdict_lines[0]
        or verdict_lines[0].split(":", 1)[1].strip().upper()
        not in (APPROVE, REQUEST_CHANGES)
    ):
        raise ValueError(
            f"ambiguous evaluator verdict (found {verdict_lines!r}); expected "
            f"exactly one 'VERDICT: {APPROVE}' or 'VERDICT: {REQUEST_CHANGES}' "
            "line, as the final line of the review"
        )
    return verdict_lines[0].split(":", 1)[1].strip().upper()


def _post_json(url: str, payload: dict, api_key: str, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Surface the API's error body — "HTTP Error 400" alone is undiagnosable
        # from CI logs (proven by the first live run of this gate).
        body = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"OpenAI API HTTP {exc.code}: {body}") from exc


def request_review(review_input: str, api_key: str, model: str, base_url: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": review_input},
        ],
    }
    data = _post_json(f"{base_url.rstrip('/')}/chat/completions", payload, api_key)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected OpenAI response shape: {data!r:.500}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Non-Claude adversarial review of a diff + test logs "
                    "(exit 0 APPROVE / 1 REQUEST-CHANGES / 2 hard failure)."
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--target", default="HEAD",
                     help="commit to review as <target>^1..<target> (default HEAD; "
                          "works for merge commits via first parent)")
    src.add_argument("--range", dest="range_spec",
                     help="explicit git diff range, e.g. master..HEAD")
    src.add_argument("--diff-file", help="read the diff from a file instead of git")
    parser.add_argument("--test-log", action="append", default=[],
                        help="path to a test-output file to include (repeatable)")
    parser.add_argument("--max-diff-bytes", type=int, default=DEFAULT_MAX_DIFF_BYTES,
                        help=f"truncate the diff beyond this size (default {DEFAULT_MAX_DIFF_BYTES})")
    parser.add_argument("--require", action="store_true",
                        help="exit 2 (not skip) when OPENAI_API_KEY is unset — use in "
                             "CI for trust-critical PRs where this review is MANDATORY")
    args = parser.parse_args(argv)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        if args.require:
            print("adversarial_review: HARD FAIL — OPENAI_API_KEY is unset and "
                  "--require was given. This change class MUST have a non-Claude "
                  "review before merge.", file=sys.stderr)
            return 2
        print("adversarial_review: SKIPPED-loud — OPENAI_API_KEY is unset. This is "
              "NOT an approval: the non-Claude evaluator has not seen this diff. "
              "Mint the key (founder-crucial) and re-run; use --require in CI.",
              file=sys.stderr)
        return 0

    try:
        if args.diff_file:
            with open(args.diff_file, encoding="utf-8", errors="replace") as f:
                diff = f.read()
        else:
            diff = _git_diff(args.range_spec or f"{args.target}^1..{args.target}")
        if not diff.strip():
            print("adversarial_review: HARD FAIL — empty diff (nothing to review "
                  "is a wiring error, not an approval).", file=sys.stderr)
            return 2
        if (args.require
                and len(diff.encode("utf-8", errors="replace")) > args.max_diff_bytes):
            # Evaluator finding (PR #11 round 1): a truncated diff can hide
            # whole files from the reviewer — a partial diff is not a review.
            # Local/advisory runs may truncate; a MANDATORY gate may not.
            print(f"adversarial_review: HARD FAIL — diff exceeds --max-diff-bytes "
                  f"({args.max_diff_bytes}) and --require forbids reviewing a "
                  "truncated diff. Exclude generated files from the diff, split "
                  "the PR, or raise the limit deliberately.", file=sys.stderr)
            return 2
        test_logs = []
        for path in args.test_log:
            with open(path, encoding="utf-8", errors="replace") as f:
                test_logs.append((os.path.basename(path), f.read()))
        review_input = build_review_input(diff, test_logs, args.max_diff_bytes)
        # Fail-closed env rule: UNSET means the default; PRESENT-BUT-EMPTY is
        # a misconfiguration and hard-fails — an explicit-but-blank value must
        # never silently mean "default" on the trust-critical review path.
        # (The workflow exports OPENAI_REVIEW_MODEL only when the repo
        # variable is genuinely non-empty, so "unset" is expressible in CI.)
        model = os.environ.get("OPENAI_REVIEW_MODEL")
        if model is not None and model.strip() == "":
            print("adversarial_review: HARD FAIL — OPENAI_REVIEW_MODEL is set "
                  "but empty/whitespace; set a model id or unset it entirely "
                  "(empty must never silently mean 'default').", file=sys.stderr)
            return 2
        model = (model or DEFAULT_MODEL).strip()
        # Write/grade separation (the charter, CLAUDE.md) enforced at THIS entry point,
        # not just in tools/model_router.py: the reviewer must never be the
        # generator's model family, or the gate grades its own homework. The
        # check is deliberately DUPLICATED from model_router rather than
        # imported — in CI this script runs as a trusted copy from the base
        # ref (`python -I /tmp/trusted/...`) and must not import
        # PR-controlled repo modules.
        if any(m in model.lower() for m in ("claude", "anthropic")):
            print(f"adversarial_review: HARD FAIL — the review model resolves "
                  f"to {model!r}, a generator-family (Claude/Anthropic) model; "
                  "the evaluator must be non-Claude (write/grade separation, "
                  "the charter, CLAUDE.md). Fix OPENAI_REVIEW_MODEL.", file=sys.stderr)
            return 2
        # Same fail-closed rule for the endpoint override.
        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is not None and base_url.strip() == "":
            print("adversarial_review: HARD FAIL — OPENAI_BASE_URL is set but "
                  "empty/whitespace; set a URL or unset it entirely.",
                  file=sys.stderr)
            return 2
        base_url = (base_url or DEFAULT_BASE_URL).strip()
        review = request_review(review_input, api_key, model, base_url)
        verdict = parse_verdict(review)
        # Wrapper status precedes the review so the output ends with the
        # evaluator's own final VERDICT line, never our commentary (evaluator
        # finding, PR #11 round 2).
        if verdict == APPROVE:
            print(f"adversarial_review: {APPROVE} (model={model})\n")
        else:
            print(f"adversarial_review: {REQUEST_CHANGES} (model={model}) — fix "
                  "the file:line issues below and re-run; do not merge on red.\n",
                  file=sys.stderr)
        print(review)
    except (RuntimeError, ValueError, OSError, urllib.error.URLError) as exc:
        print(f"adversarial_review: HARD FAIL — {exc}", file=sys.stderr)
        return 2
    return 0 if verdict == APPROVE else 1


if __name__ == "__main__":
    raise SystemExit(main())
