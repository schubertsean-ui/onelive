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

Matching: the check is identified from ORCHESTRATOR_PING_URL's UUID —
directly against `ping_url` when the API key exposes it, or against
`unique_key` (the SHA1 of the UUID) which is what healthchecks returns for
read-only keys. No secret material (API key, full ping UUID) ever appears
in output; identifiers are elided to their last 4 characters.

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


def match_check(checks: list, ping_id: str) -> dict | None:
    """Find the check for the ping URL's last path segment: by ping_url
    when present (read-write key), by unique_key == sha1(uuid) (read-only
    key, the documented stable hash), or by slug (slug-style ping URLs,
    hc-ping.com/<ping-key>/<slug>)."""
    id_sha1 = hashlib.sha1(ping_id.encode("utf-8")).hexdigest()
    for check in checks:
        ping_url = (check.get("ping_url") or "").rstrip("/")
        if ping_url.endswith("/" + ping_id):
            return check
        if check.get("unique_key") == id_sha1:
            return check
        if check.get("slug") and check["slug"] == ping_id:
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
    ping_uuid = ping_url.rstrip("/").rsplit("/", 1)[-1]
    try:
        checks = fetch_checks(api_key)
    except Exception as exc:  # noqa: BLE001 — any API failure fails closed
        return _fail(
            f"could not read check configuration from healthchecks.io "
            f"({type(exc).__name__}) — refusing to run unwatched."
        )
    check = match_check(checks, ping_uuid)
    if check is None:
        if not checks:
            return _fail(
                "the API key sees ZERO checks — healthchecks API keys are "
                "per-PROJECT, so this read-only key was almost certainly "
                "created in a different project than the check. Create the "
                "read-only key in the project that contains the dead-man "
                "check. Refusing to run unwatched."
            )
        return _fail(
            f"the API key sees {len(checks)} check(s), but none match the "
            f"ping URL (id {_elide(ping_uuid)}) by ping_url, unique_key "
            "(sha1 of uuid), or slug — the dead-man URL points at a check "
            "in another project, or a deleted one. Refusing to run "
            "unwatched."
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
            f"period mismatch: check has {period}s, armed cadence needs "
            f"{expected_period}s — a stale period hides missed slots. "
            "Update the check's Period, or change both cadence and "
            "declaration together through review."
        )
    if not isinstance(grace, int) or isinstance(grace, bool) \
            or not 0 <= grace <= max_grace:
        return _fail(
            f"grace {grace!r}s is outside [0, {max_grace}]s — alarms must "
            "fire within period+grace of a dead cron (r12: negative or "
            "mistyped grace fails closed too)."
        )
    print(
        f"assert_deadman_period: OK — check {_elide(ping_uuid)} period "
        f"{period}s, grace {grace}s: matches the armed cadence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
