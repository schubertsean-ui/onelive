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

# The v2 discipline is PANEL-ONLY (#71 r3 blocker): appended to lens
# prompts, never to the single-lens path — so `--panel`-absent runs stay
# byte-identical to v1, which is exactly what the bootstrap/fallback
# story claims ("v1 base = unchanged single-lens physics").
V2_DISCIPLINE = """REVIEW DISCIPLINE (v2 — founder-ratified 2026-07-25):
1. EXHAUSTIVE FIRST PASS WITH SIBLING ENUMERATION: when you find a defect, \
name its CLASS as a kebab-case token and enumerate EVERY sibling instance \
of that class visible in the diff NOW, in this same round — one class \
surfaced across many rounds is the failure mode this discipline exists to \
kill. Format every blocker as:
`CLASS:<kebab-token> file:line — issue — why it blocks`
2. USE THE ROUND HISTORY, DO NOT REDISCOVER: the diff's changelog entries \
for this PR (the `rN` lines) are the review history, and `[S3:...]` lines \
in the diff are the builder's mandatory pre-design retrieval evidence. \
VERIFY that claimed fixes and citations are real (a false claim is itself \
a blocker, CLASS:false-confidence-gate); do not re-open what the history \
shows resolved unless the resolution is defective.
3. THE ESCAPE HATCH IS AN OBLIGATION, ROUND-SCOPED DISCRETION IS \
STRUCTURED: a trust-invariant violation, gate-custody weakening, or \
auth/custody fail-open MUST block, in any round, no discretion. For any \
OTHER class first raised after round 1, your finding must also state in \
one sentence why it was not findable in round 1 (new code since round 1, \
new evidence, or your own earlier miss — which the scorecard counts).
4. SCOPE: judge against the session contract's done-criteria visible in \
the diff. A real quality gap OUTSIDE that scope and NOT invariant-class \
belongs in a `RECOMMEND-RECORD` section (for a RECORD row with an \
objective trigger), not in blockers."""

# --- Forced method lenses (v2): each lens is a PROCEDURE constraint that
# redirects the model's search; findings/format/verdict rules are the
# SYSTEM_PROMPT's, unchanged. Per seat: one method lens + one po-seeded
# lens (stimuli never facts). Panel verdict physics live in main(): ANY
# lens REQUEST-CHANGES = red; any unparseable output = hard fail.
LENSES = {
    "attacker-smuggle": (
        "FORCED LENS — ATTACKER SIMULATION: assume this diff was written by "
        "a malicious insider whose goal is to smuggle a defect or backdoor "
        "past review while looking helpful. Search ONLY for the smuggle "
        "path: what does this change make possible that was impossible "
        "before, and how would the author abuse it? Report only what you "
        "can evidence at file:line."
    ),
    "absence-only": (
        "FORCED LENS — ABSENCE-ONLY REVIEW: you may ONLY report what is "
        "MISSING — absent checks, absent tests, absent invariants, absent "
        "error paths, absent registry bindings. You are forbidden from "
        "commenting on code that exists except to note what it fails to "
        "cover. Negative space only."
    ),
    "dataflow-taint": (
        "FORCED LENS — DATAFLOW TAINT: trace every externally-influenced "
        "value (caller args, env, file/network reads, git-derived data) "
        "from source to every sink where a decision is made. Report every "
        "path that reaches a decision without validation, at file:line."
    ),
    "spec-vs-contract": (
        "FORCED LENS — SPEC-VS-CONTRACT: compare the diff ONLY against the "
        "stated contract/done-criteria and canon documents visible in the "
        "diff. Report every divergence between what is claimed and what is "
        "implemented; claims without mechanism are CLASS:rule-stronger-"
        "than-mechanism blockers."
    ),
}

# Seat -> ordered lens pair (method lens, then the po-carrying lens).
SEAT_LENSES = {
    "openai": ("attacker-smuggle", "absence-only"),
    "gemini": ("dataflow-taint", "spec-vs-contract"),
}

_PO_OPERATORS = (
    ("escape", "po: {anchor} does not exist at all"),
    ("reversal", "po: {anchor} is written by the attacker, not the defender"),
    ("exaggeration", "po: {anchor} runs one million times a day"),
    ("distortion", "po: {anchor} runs AFTER the thing it guards, not before"),
    ("wishful", "po: {anchor} is perfect and needs no review"),
)

_PO_ANCHORS = (
    "the gate", "the test suite", "the caller", "the config", "the registry",
    "the clock", "the key", "the journal", "the retry path", "the merge",
)


def po_provocations(seed: str, count: int = 3) -> list[str]:
    """Deterministic po battery preamble (founder-directed 2026-07-25):
    provocations derived from the seed (CI passes the PR HEAD SHA — never
    a chosen parameter), rotating per run. STIMULI, NEVER FACTS: the
    consuming lens must verify any movement in the diff and explicitly
    discard what does not verify."""
    import hashlib as _hl

    digest = _hl.sha256(seed.encode("utf-8")).digest()
    out = []
    for i in range(count):
        op_name, template = _PO_OPERATORS[digest[2 * i] % len(_PO_OPERATORS)]
        anchor = _PO_ANCHORS[digest[2 * i + 1] % len(_PO_ANCHORS)]
        out.append(f"[{op_name}] {template.format(anchor=anchor)}")
    return out


def po_preamble(seed: str) -> str:
    lines = "\n".join(po_provocations(seed))
    return (
        "PO PREAMBLE (de Bono provocation battery — rotating seed, printed "
        f"for audit: {seed}). Use each provocation for MOVEMENT: hypothesize "
        "the failure mode it suggests, then VERIFY it in the diff. A "
        "hypothesis becomes a finding ONLY with file:line evidence; state "
        "'no movement' explicitly for any provocation that does not verify. "
        "Provocations are stimuli, never facts, and can only ADD candidate "
        "findings — never argue for approval.\n" + lines
    )


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


# The second-family seat's model. FLASH, not pro, for a mechanical reason
# found on the panel's first live run (#72): gemini-2.5-pro has NO free-tier
# quota — the API answers 429 with `limit: 0`, not a retryable rate limit —
# so a founder-minted key on the free tier can never call it, and the seat
# hard-failed the whole gate instead of reviewing anything. Flash has free-
# tier quota and reviews; a working weaker second family is strictly more
# review than a second family that cannot run. gemini-2.5-flash then answered
# 404 'no longer available to new users' (#72 r3) — two guesses from error
# strings, which is why the workflow now runs a preflight that lists the
# ADVERTISED models and then PROVES callability with a live generateContent
# probe of this exact id. Listing alone shows existence and is blind to
# quota; only the probe settles it.
#
# HONEST LIMIT — this id is a FLOATING ALIAS, not an immutable pin (#72 r6,
# class: mutable-model-alias). `*-latest` resolves provider-side, so the
# reviewer's actual model can change without any commit here, which is real
# gate-custody drift: review strength is partly provider-controlled. It is
# used anyway because it is the only id known to work — the two concrete ids
# tried are refused by this key's tier — and because the preflight prints
# the advertised list on every run, which is what makes a concrete id
# choosable. Recorded with an objective trigger, NOT left as a silent
# compromise: docs/RECORD.md R-052 (first CI run whose preflight prints the
# list -> replace this alias with a concrete id from it, same-PR test
# binding preserved). Changing this constant is a gate-custody change and
# lands exactly like this one: a PR judged by the BASE-owned reviewer copy.
# If the founder enables billing on the Gemini project, moving to a concrete
# pro id is a one-line PR through the same path.
GEMINI_DEFAULT_MODEL = "gemini-flash-latest"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def request_review_gemini(review_input: str, system_prompt: str, api_key: str,
                          model: str) -> str:
    """Second-family seat (founder-approved 2026-07-25). Same REST-only
    discipline as the OpenAI path; same fail-closed response parsing."""
    # Key in the HEADER, never the query string (#71 r7 nit): Google
    # accepts both, but a URL carries into proxy logs, traces, and
    # exception text far more readily than a header does.
    url = f"{GEMINI_BASE_URL}/models/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": review_input}]}],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {body}") from exc
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected Gemini response shape: {data!r:.500}") from exc


def run_panel(review_input: str, po_seed: str, openai_key: str, model: str,
              base_url: str, gemini_key: str | None,
              request_openai=None, request_gemini=None) -> tuple[str, list[str]]:
    """The v2 lens panel. Per seat: one forced method lens + one po-seeded
    lens (rotating provocations from the head SHA). Verdict physics — a
    strict TIGHTENING of v1: every lens must APPROVE for the panel to
    approve; ANY lens REQUEST-CHANGES is red; any unparseable lens output
    is a hard failure (raised), never a quiet skip. An absent Gemini key
    leaves that seat EXPLICITLY EMPTY (printed — founder mints keys, the
    panel never fails a PR for a credential that does not exist yet).
    request_openai/request_gemini are injectable for hermetic tests only;
    production passes None and uses the real clients."""
    request_openai = request_openai or (
        lambda ri, sp: request_review_openai_lens(ri, sp, openai_key, model, base_url))
    request_gemini = request_gemini or (
        lambda ri, sp: request_review_gemini(
            ri, sp, gemini_key,
            _resolve_env_model("GEMINI_REVIEW_MODEL", GEMINI_DEFAULT_MODEL,
                              GEMINI_ALLOWED_MODELS)))
    # The seed is printed BY THE TOOL (#71 r10 nit): the CLI contract says
    # the po seed is auditable, and a claim that depends on the caller's
    # workflow echoing it is not the tool keeping its own promise.
    outputs: list[str] = [
        f"### PO SEED: {po_seed} — provocations derived deterministically: "
        + " | ".join(po_provocations(po_seed))
    ]
    # Build the work list first, THEN run it. The lenses are independent by
    # construction — each gets the same input and its own system prompt, and
    # none reads another's output (that isolation is the point: the hats rule
    # forbids lenses seeing each other). The verdict merge is ANY-red = red,
    # which is order-independent. So running them one after another bought
    # nothing and cost four times the latency. MEASURED (§4 of the timing
    # evidence file in docs/session_arcs/evidence/): the
    # 'Independent evaluator' step took 207s with the lenses serial, on
    # both job 89754035048 and job 89821493804. What it becomes when they
    # overlap is UNVERIFIED and stays that way until a merged run reports
    # it, because CI executes this file from the BASE ref — this change
    # cannot speed up the PR that introduces it.
    jobs: list[tuple[str, str, object, str]] = []
    for seat, seat_key, requester in (
        ("openai", openai_key, request_openai),
        ("gemini", gemini_key, request_gemini),
    ):
        if not seat_key:
            outputs.append(
                f"### SEAT {seat}: EMPTY — no API key minted; the panel runs "
                "single-family until the founder mints it (explicit, never silent)"
            )
            continue
        method_lens, po_lens = SEAT_LENSES[seat]
        for lens_name, extra in (
            (method_lens, LENSES[method_lens]),
            (po_lens, LENSES[po_lens] + "\n\n" + po_preamble(po_seed)),
        ):
            system_prompt = SYSTEM_PROMPT + "\n\n" + V2_DISCIPLINE + "\n\n" + extra
            jobs.append((seat, lens_name, requester, system_prompt))

    # Results are collected BY INDEX and emitted in the original order, so
    # the report reads identically to the serial version and a rerun cannot
    # reorder it — concurrency changes when calls happen, never what the
    # panel says. A lens that raises (transport failure, unparseable
    # verdict) still propagates: the first exception is re-raised here and
    # the gate hard-fails exactly as before, never degrading to a partial
    # panel, which would be a silent narrowing.
    # FAIL FAST — WITH ITS REAL BOUND STATED (#73 r7, corrected at r9 after
    # the OpenAI attacker-smuggle seat refuted the earlier wording, which
    # claimed more than the code delivers).
    #
    # WHAT IS TRUE: the first error — transport failure OR unparseable
    # verdict — raises out of this function immediately, so the VERDICT is
    # decided without waiting on any sibling. That is what the tests pin.
    #
    # WHAT IS NOT TRUE, and was claimed here before: that the PROCESS exits
    # immediately. It does not. ThreadPoolExecutor workers are non-daemon and
    # are joined by concurrent.futures' own atexit hook, so `shutdown(
    # wait=False)` returns at once while the interpreter still blocks on any
    # in-flight request at exit. Measured directly, not reasoned about: a
    # worker sleeping 6s returned from the raise at t=0.00s while the process
    # took the full ~6s to exit (preserved run: `real 0m6.042s`). Evidence + the probe script:
    # the timing evidence file in docs/session_arcs/evidence/, §5.
    #
    # SO THE HONEST GUARANTEE IS: verdict immediate, process exit bounded by
    # the per-request timeout in _post_json (300s). A hung lens cannot make
    # the job hang forever, and cannot change the verdict, but it CAN hold
    # the runner until its own request times out. Lowering that timeout is
    # the only lever that tightens the bound; it is left at 300s deliberately
    # because a legitimately slow model call must not be cut off by a gate
    # tuning change, and it is recorded rather than silently adjusted.
    #
    # The cancel() loop stops only futures that have not STARTED. Since
    # max_workers == len(jobs) nothing is ever queued, so today it is
    # defensive rather than load-bearing; it is kept because it becomes real
    # the moment the pool is narrower than the job list, and because parse
    # failures must reach the same path as transport failures.
    #
    # The verdict is unchanged by all of this — an erroring lens hard-fails
    # the whole panel and never degrades it to a partial one, which would be
    # a silent narrowing.
    results: list[tuple[str, str] | None] = [None] * len(jobs)
    if jobs:
        import concurrent.futures as _cf

        pool = _cf.ThreadPoolExecutor(max_workers=len(jobs))
        try:
            futures = {
                pool.submit(requester, review_input, system_prompt): i
                for i, (_seat, _lens, requester, system_prompt) in enumerate(jobs)
            }
            for future in _cf.as_completed(futures):
                i = futures[future]
                try:
                    # parse_verdict MUST be inside this try (#73 r8, Gemini
                    # seat): an unparseable verdict is a lens failure exactly
                    # like a transport error, and parsing outside would raise
                    # past the handler, skipping cancellation and reinstating
                    # the loud-but-late path this block exists to remove.
                    text = future.result()
                    results[i] = (parse_verdict(text), text)
                except BaseException:  # noqa: BLE001 — cancel siblings, then raise
                    for pending in futures:
                        pending.cancel()
                    raise
        finally:
            pool.shutdown(wait=False)

    verdicts: list[str] = []
    for (seat, lens_name, _requester, _prompt), result in zip(jobs, results):
        verdict, text = result  # type: ignore[misc]
        verdicts.append(verdict)
        outputs.append(f"### SEAT {seat} / LENS {lens_name}: {verdict}\n{text}")
    if not verdicts:
        raise RuntimeError("panel produced zero lens verdicts — wiring error, "
                           "never an approval")
    final = APPROVE if all(v == APPROVE for v in verdicts) else REQUEST_CHANGES
    return final, outputs


def request_review_openai_lens(review_input: str, system_prompt: str,
                                      api_key: str, model: str, base_url: str) -> str:
    """OpenAI call with a per-lens system prompt (the v1 request_review
    hardcodes SYSTEM_PROMPT; lenses need their own)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": review_input},
        ],
    }
    data = _post_json(f"{base_url.rstrip('/')}/chat/completions", payload, api_key)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected OpenAI response shape: {data!r:.500}") from exc


# BASE-OWNED ALLOWLIST for the second seat (#72 r8, class:
# self-weakenable-review-model). The workflow that sets
# GEMINI_REVIEW_MODEL is PR-owned, so without this an environment
# override lets the diff under review choose the model that reviews it —
# an attacker picks the weakest callable Gemini id, sails through a
# preflight that only proves callability, and self-certifies. This
# constant lives in the BASE-owned reviewer copy, so an override can only
# SELECT from models the base branch already blessed; introducing a new
# one requires changing this list on master, which is itself a
# gate-custody PR judged by the old copy. Same physics as the panel
# bootstrap: it constrains every PR after the one that lands it.
# Exactly the id in use. A second entry "for later" is unreviewed
# surface, and adding one is the intended flow: a base-branch change,
# reviewed. Every floating `*-latest` member must carry an OPEN
# docs/RECORD.md row naming it — enforced by test, so the compromise
# cannot outlive its trigger (#72 r8, class: mutable-model-alias).
GEMINI_ALLOWED_MODELS = frozenset({"gemini-flash-latest"})


def _resolve_env_model(env_name: str, default: str,
                       allowed: frozenset[str] | None = None) -> str:
    """Fail-closed env rule shared by both seats: unset = default;
    present-but-empty = misconfiguration; Claude/Anthropic ids refused
    (write/grade separation); and, where an `allowed` set is supplied, the
    resolved id must be a member — a caller-suppliable override that can
    name ANY model is a self-weakenable gate, not a configuration knob."""
    value = os.environ.get(env_name)
    if value is not None and value.strip() == "":
        raise RuntimeError(
            f"{env_name} is set but empty/whitespace; set a model id or unset "
            "it entirely (empty must never silently mean 'default')")
    value = (value or default).strip()
    if any(m in value.lower() for m in ("claude", "anthropic")):
        raise RuntimeError(
            f"{env_name} resolves to {value!r}, a generator-family model; the "
            "evaluator must be non-Claude (write/grade separation)")
    if allowed is not None and value not in allowed:
        raise RuntimeError(
            f"{env_name} resolves to {value!r}, which is NOT in the "
            f"base-owned allowlist {sorted(allowed)}. The review model is "
            "gate custody: an override may only SELECT an already-blessed "
            "model, never introduce one. Add it to GEMINI_ALLOWED_MODELS on "
            "the base branch first — that change is itself reviewed.")
    return value


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
    parser.add_argument("--panel", action="store_true",
                        help="v2 lens panel: forced method lenses + po-seeded lens per "
                             "seat (OpenAI always; Gemini when GEMINI_API_KEY exists); "
                             "ANY lens red = red (strict tightening of single-lens v1)")
    parser.add_argument("--po-seed", default=None,
                        help="deterministic po-battery seed; CI passes the PR HEAD SHA "
                             "(required with --panel — a panel without a printed seed "
                             "is a misconfiguration)")
    args = parser.parse_args(argv)

    if args.panel and not (args.po_seed or "").strip():
        print("adversarial_review: HARD FAIL — --panel requires --po-seed "
              "(CI passes the PR head SHA; the rotating seed must be real and "
              "printed, never defaulted).", file=sys.stderr)
        return 2

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
        # Write/grade separation (charter §0.2) enforced at THIS entry point,
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
                  "charter §0.2). Fix OPENAI_REVIEW_MODEL.", file=sys.stderr)
            return 2
        # Same fail-closed rule for the endpoint override.
        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is not None and base_url.strip() == "":
            print("adversarial_review: HARD FAIL — OPENAI_BASE_URL is set but "
                  "empty/whitespace; set a URL or unset it entirely.",
                  file=sys.stderr)
            return 2
        base_url = (base_url or DEFAULT_BASE_URL).strip()
        if args.panel:
            gemini_key = os.environ.get("GEMINI_API_KEY") or None
            verdict, outputs = run_panel(
                review_input, args.po_seed.strip(), api_key, model, base_url,
                gemini_key)
            review = "\n\n".join(outputs) + f"\nVERDICT: {verdict}"
        else:
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
