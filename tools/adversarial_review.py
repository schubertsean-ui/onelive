#!/usr/bin/env python3
"""Independent (non-Claude) adversarial review gate — Session Contract #1 item 2.

Greppable summary: posts a raw git diff + test logs to the OpenAI API (the
charter's Independent Evaluator, default model gpt-5.5) and demands an
explicit `VERDICT: APPROVE` or `VERDICT: REQUEST-CHANGES` with file:line
issues. Enforces CLAUDE.md §0.2: the generator (Claude) never grades its own
auth/pipeline/SQL/RLS/data-trust/prompt changes. Raw-diff-in, raw-text-out on
purpose (§0.7: grade traces, not self-summaries). Stdlib-only (urllib), no
`openai` package dependency.

Usage:
  python tools/adversarial_review.py --target HEAD          # review one commit
  python tools/adversarial_review.py --range master..HEAD   # review a range
  python tools/adversarial_review.py --diff-file pr.patch --test-log pytest.log
  python tools/adversarial_review.py --target HEAD --require  # CI: key mandatory

Env: OPENAI_API_KEY (unset -> SKIPPED-loud, exit 0 — the charter says flag,
don't block — unless --require, then exit 2); OPENAI_REVIEW_MODEL (default
gpt-5.5); OPENAI_BASE_URL (default https://api.openai.com/v1).

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

SYSTEM_PROMPT = """You are the Independent Evaluator for the OneLive build \
(a non-Claude model, per the repo charter's generator/evaluator separation). \
You are adversarial by mandate: your job is to find what is wrong, not to be \
agreeable. Grade the raw diff and test logs against the repo's bar: no \
swallowed errors, fail loud on misconfig, parameterized SQL only, AI never \
publishes directly, disputed events never hidden, auth fail-closed, tests \
that can actually fail, no stubs or deferred work.

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

    The verdict must be unambiguous: exactly one VERDICT line, and it decides
    the exit code. An evaluator that hedges gets a hard failure, not a pass.
    """
    verdicts = [
        line.split("VERDICT:", 1)[1].strip()
        for line in review_text.splitlines()
        if line.strip().upper().startswith("VERDICT:")
    ]
    if len(verdicts) != 1 or verdicts[0].upper() not in (APPROVE, REQUEST_CHANGES):
        raise ValueError(
            f"ambiguous evaluator verdict (found {verdicts!r}); expected exactly "
            f"one 'VERDICT: {APPROVE}' or 'VERDICT: {REQUEST_CHANGES}' line"
        )
    return verdicts[0].upper()


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
        test_logs = []
        for path in args.test_log:
            with open(path, encoding="utf-8", errors="replace") as f:
                test_logs.append((os.path.basename(path), f.read()))
        review_input = build_review_input(diff, test_logs, args.max_diff_bytes)
        # `or` (not a .get default): CI forwards these vars even when the repo
        # variable is unset, so they arrive present-but-empty — and an empty
        # model string 400s at the API (first live run of this gate).
        model = os.environ.get("OPENAI_REVIEW_MODEL") or DEFAULT_MODEL
        base_url = os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
        review = request_review(review_input, api_key, model, base_url)
        print(review)
        verdict = parse_verdict(review)
    except (RuntimeError, ValueError, OSError, urllib.error.URLError) as exc:
        print(f"adversarial_review: HARD FAIL — {exc}", file=sys.stderr)
        return 2

    if verdict == APPROVE:
        print(f"\nadversarial_review: {APPROVE} (model={model})")
        return 0
    print(f"\nadversarial_review: {REQUEST_CHANGES} (model={model}) — fix the "
          "file:line issues above and re-run; do not merge on red.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
