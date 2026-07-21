#!/usr/bin/env python3
"""Assert the dead-man check's period/grace matches the armed cron cadence.

Greppable summary: R-020's mechanical closure (PR #43 r11 — the evaluator
correctly refused to arm a recurring cron whose Sentinel alarm config was
founder-confirmed prose). This runs as a BLOCKING precondition step in
ingest.yml: it reads the healthchecks.io check's live configuration through
a READ-ONLY API key and fails CLOSED unless the check's period equals the
cadence the workflow declares next to its cron line, with grace inside the
declared bound. A paused/mispointed/stale-period check can no longer hide:
the run refuses to proceed, which is itself a loud red on every scheduled
slot.

The enforced contract (r17 — two halves, both required, both fail-closed):
1. CONFIG: the check DECLARED by the workflow (DEADMAN_CHECK_SLUG, with
   uuid-hash/ping_url as secondary match paths) must exist, be unpaused,
   and carry the declared period/grace.
2. BINDING: a /log probe POSTed to ORCHESTRATOR_PING_URL must move THAT
   check's ping counter within this run — proving the worker's ping URL
   and the config-verified check are the same object, every run, immune
   to silent Actions-secret drift. /log records an event without
   signalling success or resetting the schedule, so the probe can never
   mask a dead loop.
If healthchecks changes any of these API shapes, the assertion misses and
FAILS CLOSED — the cron refuses to run rather than running unwatched. No
secret material (API key, full ping UUID) ever appears in output;
identifiers are elided to their last 4 characters.

Env contract (all required, fail closed):
  ORCHESTRATOR_PING_URL      the check's ping URL (existing secret)
  HEALTHCHECKS_API_KEY_RO    READ-ONLY healthchecks.io API key (founder-
                             minted; read-only so a leak cannot modify or
                             delete checks)
  EXPECTED_PERIOD_SECONDS    declared next to the cron line in ingest.yml;
                             tests/test_ingest_workflow_contract.py derives
                             the same number from the cron expression, so
                             cadence and this declaration cannot drift apart
  MAX_GRACE_SECONDS          upper bound for the check's grace

Exit codes per tools/README.md: 0 asserted / 2 misconfiguration, API
failure, no matching check, or period/grace mismatch — every path closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request

API_URL = "https://healthchecks.io/api/v3/checks/"


def _fail(msg: str) -> int:
    print(f"assert_deadman_period: FAIL — {msg}", file=sys.stderr)
    return 2


def _elide(value: str) -> str:
    return f"…{value[-4:]}" if len(value) >= 4 else "…"


def fetch_checks(api_key: str) -> list:
    """GET the account's checks. Separated for testability; any exception
    is the caller's fail-closed path."""
    req = urllib.request.Request(API_URL, headers={"X-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8")).get("checks", [])


def send_binding_probe(ping_url: str) -> None:
    """POST a /log event to the worker's ping URL (PR #43 r17).

    /log records a ping WITHOUT signalling success or resetting the
    dead-man schedule — so probing here can never mask a dead loop. The
    caller then re-reads the verified check and requires its ping counter
    to have moved: a standing, every-run proof that ORCHESTRATOR_PING_URL
    and the config-verified check are the SAME object, immune to silent
    secret drift. Any delivery failure is the caller's fail-closed path."""
    req = urllib.request.Request(
        ping_url.rstrip("/") + "/log",
        data=b"assert_deadman_period: ping-url binding probe",
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"probe returned HTTP {resp.status}")


def match_check(checks: list, ping_id: str, declared_slug: str) -> dict | None:
    """Find the dead-man check. PRIMARY path: the workflow DECLARES the
    check by slug/name (DEADMAN_CHECK_SLUG env, reviewed next to the cron
    line) and we match that declaration — no inference. This replaced
    hash-guessing after it failed live twice (PR #43: read-only keys
    identify checks by unique_key, whose derivation from the UUID is an
    undocumented implementation detail; both dashed and undashed sha1
    forms missed against the real API). The uuid-hash and ping_url paths
    remain as secondary matches for configurations where they do work; a
    miss on every path still fails closed at the caller.

    The declared-slug path identifies the check; it does NOT prove the
    ping URL targets it — that proof is main()'s /log binding probe
    (r17), which must move this check's counter within the run or the
    run is refused. This function only selects; the probe binds."""
    ping_id = ping_id.strip().lower()
    candidates = {
        hashlib.sha1(form.encode("utf-8")).hexdigest()
        for form in (ping_id, ping_id.replace("-", ""))
    }
    for check in checks:
        slug = (check.get("slug") or "").lower()
        name = (check.get("name") or "").lower()
        if declared_slug and declared_slug in (slug, name):
            return check
        ping_url = (check.get("ping_url") or "").rstrip("/").lower()
        if ping_url.endswith("/" + ping_id):
            return check
        if (check.get("unique_key") or "").lower() in candidates:
            return check
        if slug and slug == ping_id:
            return check
    return None


def main() -> int:
    ping_url = os.environ.get("ORCHESTRATOR_PING_URL", "").strip()
    api_key = os.environ.get("HEALTHCHECKS_API_KEY_RO", "").strip()
    try:
        expected_period = int(os.environ["EXPECTED_PERIOD_SECONDS"])
        max_grace = int(os.environ["MAX_GRACE_SECONDS"])
    except (KeyError, ValueError):
        expected_period = max_grace = -1
    if expected_period <= 0 or max_grace <= 0:
        return _fail(
            "EXPECTED_PERIOD_SECONDS / MAX_GRACE_SECONDS must be set "
            "POSITIVE integers — they are declared next to the cron line "
            "in ingest.yml so cadence and alarm period move together "
            "(r12: non-positive bounds would make the assertion "
            "unsatisfiable or meaningless, fail closed)."
        )
    if not ping_url:
        return _fail("ORCHESTRATOR_PING_URL is not set — failing closed.")
    if not api_key:
        return _fail(
            "HEALTHCHECKS_API_KEY_RO is not set. Mint a READ-ONLY API key "
            "(healthchecks.io → Settings → API access) and store it as an "
            "Actions secret — R-020's mechanical closure requires it. "
            "Failing closed: the cron must not run unwatched."
        )
    declared_slug = os.environ.get("DEADMAN_CHECK_SLUG", "").strip().lower()
    if not declared_slug:
        return _fail(
            "DEADMAN_CHECK_SLUG is not set — the workflow must DECLARE "
            "which check is the dead-man (reviewed next to the cron line). "
            "Failing closed."
        )
    ping_uuid = ping_url.rstrip("/").rsplit("/", 1)[-1]
    try:
        checks = fetch_checks(api_key)
    except Exception as exc:  # noqa: BLE001 — any API failure fails closed
        return _fail(
            f"could not read check configuration from healthchecks.io "
            f"({type(exc).__name__}) — refusing to run unwatched."
        )
    check = match_check(checks, ping_uuid, declared_slug)
    if check is None:
        if not checks:
            return _fail(
                "the API key sees ZERO checks — healthchecks API keys are "
                "per-PROJECT, so this read-only key was almost certainly "
                "created in a different project than the check. Create the "
                "read-only key in the project that contains the dead-man "
                "check. Refusing to run unwatched."
            )
        visible = ", ".join(
            f"name={c.get('name')!r} slug={c.get('slug')!r}"
            for c in checks[:10]
        )
        return _fail(
            f"the API key sees {len(checks)} check(s) [{visible}], but "
            f"none match the DECLARED slug {declared_slug!r} or the ping "
            f"URL (id {_elide(ping_uuid)}). Either rename the check (or "
            "fix DEADMAN_CHECK_SLUG through review) so declaration and "
            "reality agree, or the key is from another project. Refusing "
            "to run unwatched."
        )
    if check.get("status") == "paused":
        return _fail(
            "the dead-man check is PAUSED — a paused check alarms on "
            "nothing. Resume it before any run."
        )
    if "timeout" not in check:
        return _fail(
            "the dead-man check is schedule-based (no simple period). Use "
            "a simple check whose Period matches the cron cadence."
        )
    period = check["timeout"]
    grace = check.get("grace")
    if period != expected_period:
        return _fail(
            f"period mismatch on check name={check.get('name')!r} "
            f"slug={check.get('slug')!r}: it has {period}s, the armed "
            f"cadence needs {expected_period}s — a stale period hides "
            "missed slots. Update the check's Period, or change both "
            "cadence and declaration together through review."
        )
    if not isinstance(grace, int) or isinstance(grace, bool) \
            or not 0 <= grace <= max_grace:
        return _fail(
            f"grace {grace!r}s is outside [0, {max_grace}]s — alarms must "
            "fire within period+grace of a dead cron (r12: negative or "
            "mistyped grace fails closed too)."
        )

    # PING-URL BINDING PROOF (r17 blocker: name-matching alone would go
    # green for check A while the worker pings check B or a dead URL —
    # secrets drift without review). A /log probe to ORCHESTRATOR_PING_URL
    # must move THIS check's ping counter, every run, or we refuse to run.
    n_before = check.get("n_pings")
    if not isinstance(n_before, int) or isinstance(n_before, bool):
        return _fail(
            "the API did not expose an integer n_pings for the verified "
            "check — the ping-URL binding cannot be proven. Refusing to "
            "run unwatched."
        )
    try:
        send_binding_probe(ping_url)
    except Exception as exc:  # noqa: BLE001 — any probe failure is closed
        return _fail(
            f"binding probe to ORCHESTRATOR_PING_URL failed "
            f"({type(exc).__name__}) — the worker's ping URL is not "
            "deliverable, so the loop would run unwatched. Refusing."
        )
    try:
        checks_after = fetch_checks(api_key)
    except Exception as exc:  # noqa: BLE001
        return _fail(
            f"could not re-read the check after the binding probe "
            f"({type(exc).__name__}) — binding unproven, refusing."
        )
    check_after = match_check(checks_after, ping_uuid, declared_slug)
    n_after = (check_after or {}).get("n_pings")
    if not isinstance(n_after, int) or isinstance(n_after, bool) \
            or n_after <= n_before:
        return _fail(
            f"the verified check {check.get('name')!r} did NOT receive the "
            f"probe (n_pings {n_before} -> {n_after!r}) — "
            "ORCHESTRATOR_PING_URL targets a DIFFERENT check or a stale "
            "URL, i.e. the alarm is misbound. Fix the secret to the "
            "verified check's ping URL. Refusing to run unwatched."
        )
    print(
        f"assert_deadman_period: OK — check name={check.get('name')!r} "
        f"period {period}s, grace {grace}s: matches the armed cadence. "
        f"Ping-URL binding PROVEN this run: /log probe moved n_pings "
        f"{n_before} -> {n_after} on the verified check (a /log event "
        "never signals success, so this cannot mask a dead loop)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
