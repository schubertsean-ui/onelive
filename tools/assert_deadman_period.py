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

Optional (purely additive — unset means behavior identical to before):
  REPORT_FLIPS               set to literal "1" to run the R-023 PATH A
                             alarm-verification probe (trigger part 2)
                             AFTER every assertion above has passed
                             unchanged: reads the verified check's flip
                             (status-change) history for the last 24h via
                             the same RO key and prints a plain table with
                             every DOWN event marked. Readability under the
                             RO key was unverified when R-023 was filed and
                             was PROVEN by the first live dispatch (HTTP
                             200, run 29963320514); therefore EVERY flips
                             failure — including 401/403 (a rejected key is
                             a config regression, r7: auth fail-closed),
                             404 (ambiguous), network faults, and malformed
                             bodies — fails LOUD. No probe failure path
                             exits 0.

Exit codes per tools/README.md: 0 asserted / 2 misconfiguration, API
failure, no matching check, or period/grace mismatch — every path closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://healthchecks.io/api/v3/checks/"

# R-023 trigger part 2 asks for "at least the last 24h" of flip history;
# the endpoint's `seconds` filter makes the window explicit rather than
# relying on the server's unfiltered default.
FLIPS_WINDOW_SECONDS = 86400


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


def fetch_flips(api_key: str, check_id: str) -> list:
    """GET the check's status-change (flip) history for the probe window
    (healthchecks API v3: GET /api/v3/checks/<uuid|unique_key>/flips/,
    documented as readable by read-only keys — proven live by the first
    dispatch's HTTP 200, run 29963320514; R-023 part 2 closed on the
    second dispatch's flip table [R-023]). Separated
    for testability like fetch_checks; every failure disposition
    belongs to the caller, and every one fails loud (r7). The response body is a JSON array of
    {"timestamp": <iso8601>, "up": 0|1} objects, either bare (upstream
    repo docs) or wrapped as {"flips": [...]} (the hosted service wraps
    exactly as its checks endpoint wraps in {"checks": [...]} — the
    first live probe run answered 200 with a non-bare body, PR #51);
    the caller normalizes both."""
    url = f"{API_URL}{check_id}/flips/?seconds={FLIPS_WINDOW_SECONDS}"
    req = urllib.request.Request(url, headers={"X-Api-Key": api_key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def report_flips(api_key: str, check: dict) -> int:
    """R-023 PATH A alarm-verification probe (trigger part 2): after the
    period/grace/binding assertions have ALL passed unchanged, print the
    verified check's flips (status changes) for the last 24h, marking
    every DOWN event — the mechanical evidence for whether the dead-man
    alarm actually flipped during the sparse-delivery gaps.

    Dispositions (r7: EVERY failure path is loud — auth fail-closed):
    - 200 + well-formed list: print the table, exit 0.
    - 401/403: key revoked/changed. Readability was live-proven (run
      29963320514 [R-023]), so denial is a config REGRESSION — fail
      loud; a green workflow must never paper over a rejected key.
    - 404: AMBIGUOUS (identifier-not-found vs denial) — fails loud
      (pre-attack nit, PR #51).
    - anything else (network fault, malformed body, no usable check
      identifier): fail LOUD via the standard closed path — a broken
      probe must never masquerade as a completed one.
    No secret material in output: the check is identified by name only,
    never by uuid/unique_key/ping URL."""
    # Prefer unique_key (the identifier read-only list responses carry;
    # a sha1 derivative, so nothing pingable leaks into the request URL);
    # uuid is the fallback for read-write keys, which do expose it.
    check_id = (check.get("unique_key") or check.get("uuid") or "").strip()
    if not check_id:
        return _fail(
            "flips probe: the verified check exposes neither unique_key "
            "nor uuid, so no flips URL can be formed — probe broken, "
            "failing loud (this is not the R-023 inaccessibility answer)."
        )
    try:
        flips = fetch_flips(api_key, check_id)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            # r7 blocker: exit-0 here was auth-fail-open. The "access
            # answer" disposition belonged to the UNTESTED state; flips
            # readability under this key is live-proven (HTTP 200, run
            # 29963320514), so a denial today means the key was revoked
            # or changed — a config regression that must fail LOUD, never
            # a green workflow with a log line.
            return _fail(
                f"flips probe: HTTP {exc.code} — the read-only key was "
                "rejected. Readability was live-proven (run 29963320514), "
                "so denial is a key/config REGRESSION, not an access "
                "answer. Fix the key; founder confirmation (R-023 PATH B) "
                "covers verification meanwhile. Failing loud."
            )
        if exc.code == 404:
            # Pre-attack nit (PR #51): 404 is ambiguous — identifier not
            # found (stale unique_key, endpoint moved) is at least as
            # plausible as access denial, and readability is already
            # live-proven (200, run 29963320514). An ambiguous signal may
            # not masquerade as the access answer: fail loud.
            return _fail(
                "flips probe: HTTP 404 from the flips endpoint — "
                "identifier-not-found is indistinguishable from access "
                "denial here, and readability was already proven live "
                "(HTTP 200). Ambiguous, NOT the access answer; failing "
                "loud."
            )
        return _fail(
            f"flips probe: unexpected HTTP {exc.code} from the flips "
            "endpoint — neither readable history nor the documented "
            "access-denied answer. Probe inconclusive, failing loud."
        )
    except Exception as exc:  # noqa: BLE001 — non-HTTP faults fail loud
        return _fail(
            f"flips probe: could not fetch flip history "
            f"({type(exc).__name__}) — network/parse fault, NOT an "
            "access answer. Probe inconclusive, failing loud."
        )
    # Normalize the two documented shapes: bare array (upstream repo
    # docs) or {"flips": [...]} wrapper (the hosted service, mirroring
    # its {"checks": [...]} wrapper — live-confirmed by the first probe
    # run's 200-with-non-bare-body failure, PR #51).
    if isinstance(flips, dict) and isinstance(flips.get("flips"), list):
        flips = flips["flips"]
    if not isinstance(flips, list) or not all(
        isinstance(f, dict)
        and isinstance(f.get("timestamp"), str)
        and f.get("up") in (0, 1, True, False)  # documented domain is 0|1;
        # JSON booleans are DELIBERATELY accepted as the hosted service's
        # possible serialization variant (r6 nit: documented, not
        # accidental — Python's True==1 makes bool acceptance implicit in
        # any int check, and rejecting bools would break the probe if the
        # service emits true/false; an out-of-domain int (2, -1) remains
        # malformed, never silently UP — r5 nit)
        for f in flips
    ):
        # Diagnose with STRUCTURE ONLY (types and key names, never
        # values) so the next shape variant is one-look fixable without
        # ever logging response content.
        if isinstance(flips, dict):
            shape = f"dict with keys {sorted(flips.keys())}"
        elif isinstance(flips, list) and flips:
            first = flips[0]
            shape = (
                f"list of {type(first).__name__}"
                + (
                    f" with keys {sorted(first.keys())}"
                    if isinstance(first, dict)
                    else ""
                )
            )
        else:
            shape = type(flips).__name__
        return _fail(
            "flips probe: the flips endpoint answered 200 but the body "
            "matches neither documented shape (bare array or {'flips': "
            f"[...]}} wrapper of {{timestamp, up}} objects) — got {shape}. "
            "Malformed response, failing loud."
        )
    name = check.get("name")
    print(
        f"FLIP REPORT (R-023 PATH A, trigger part 2) — check "
        f"name={name!r}, window last {FLIPS_WINDOW_SECONDS}s (24h):"
    )
    if not flips:
        print(
            "  (no flips: the check's status never changed in the "
            "window — no DOWN events recorded)"
        )
        return 0
    down_count = 0
    for flip in flips:
        if flip["up"]:
            print(f"  {flip['timestamp']:<32} UP")
        else:
            down_count += 1
            print(f"  {flip['timestamp']:<32} DOWN   <-- DOWN event")
    print(f"  total: {len(flips)} flip(s), {down_count} DOWN")
    return 0


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
    # R-023 PATH A (trigger part 2): OPTIONAL report mode, additive only —
    # it runs strictly AFTER every assertion above passed unchanged, so
    # with REPORT_FLIPS unset the tool's effect is identical to before.
    report_flips_value = os.environ.get("REPORT_FLIPS", "").strip()
    if report_flips_value == "1":
        return report_flips(api_key, check_after)
    if report_flips_value not in ("", "0"):
        # Pre-attack nit (PR #51): a dispatch typo ("true"/"yes") must not
        # silently skip the probe while reporting overall success.
        return _fail(
            f"REPORT_FLIPS must be unset, '', '0', or '1' — got "
            f"{report_flips_value!r}. Refusing to guess; failing loud."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
