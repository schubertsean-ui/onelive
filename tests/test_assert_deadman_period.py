"""tools/assert_deadman_period.py — R-020's mechanical closure (PR #43 r11).

The rule under test: the ingestion cron must refuse to run unless the
healthchecks.io check's live period/grace provably match the cadence the
workflow declares. Every failure path exits 2 (closed): missing config,
API failure, no matching check, paused check, cron-type check, period
mismatch, grace over bound. Matching: the DECLARED slug/name
(DEADMAN_CHECK_SLUG) is the PRIMARY contract — the uuid-hash forms
tested here are legacy SECONDARY paths kept for configurations where
they happen to work (the sha1 derivation failed against the live API,
which is exactly why declaration replaced inference — r16 wording fix).
The r17 binding contract is pinned: a /log probe to the ping URL must move the verified check's counter, so a misbound/stale secret fails closed even when the named check's config is perfect. No secret material in output.

Also pinned: the R-023 PATH A alarm-verification probe (trigger part 2,
REPORT_FLIPS=1) — additive-only (unset/''/'0' mean fetch_flips is NEVER
called; any OTHER value fails loud rather than silently skipping), flip
table printed with DOWN marked on success, 401/403 answered by the
FLIPS-UNREADABLE line at exit 0 (access revocation reported IS probe
success), 404 failed loud as ambiguous (identifier-not-found vs denial,
readability already live-proven), and every other flips fault (network,
malformed body, out-of-domain 'up') loud nonzero.

Hermetic: fetch_checks/fetch_flips are monkeypatched; no network.
"""
import hashlib
import urllib.error

import pytest

import tools.assert_deadman_period as adp

_UUID = "3f2a9c1e-0000-4444-8888-abcdefabcdef"
_PING = f"https://hc-ping.com/{_UUID}"


def _check(**over):
    base = {
        "name": "onelive-ingest",  # matches the declared slug fixture
        "unique_key": hashlib.sha1(_UUID.encode()).hexdigest(),
        "status": "up",
        "timeout": 1200,
        "grace": 600,
        "n_pings": 8,
    }
    base.update(over)
    return base


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PING_URL", _PING)
    monkeypatch.setenv("HEALTHCHECKS_API_KEY_RO", "ro-key")
    monkeypatch.setenv("DEADMAN_CHECK_SLUG", "onelive-ingest")
    monkeypatch.setenv("EXPECTED_PERIOD_SECONDS", "1200")
    monkeypatch.setenv("MAX_GRACE_SECONDS", "600")
    # Hermeticity (pre-attack nit): an ambient REPORT_FLIPS on the host
    # must never reach the real network path in unrelated tests.
    monkeypatch.delenv("REPORT_FLIPS", raising=False)
    return monkeypatch


def _run(monkeypatch, checks, bound=True):
    """Drive main() with a fake API and a fake /log probe.

    bound=True simulates ORCHESTRATOR_PING_URL actually delivering to the
    matched check (its n_pings rises after the probe); bound=False
    simulates a misbound/stale URL (no counter moves) — r17's blocker
    demands the latter FAIL, never pass."""
    monkeypatch.setattr(adp, "fetch_checks", lambda key: checks)

    def _probe(url):
        if bound:
            for c in checks:
                c["n_pings"] = c.get("n_pings", 0) + 1
    monkeypatch.setattr(adp, "send_binding_probe", _probe)
    return adp.main()


def test_readonly_key_unique_key_match_passes(env, capsys):
    assert _run(env, [_check()]) == 0
    out = capsys.readouterr().out
    assert "OK" in out and _UUID not in out  # uuid elided, never printed


def test_readonly_key_undashed_hex_hash_matches(env):
    """The live PR #43 failure mode: healthchecks hashes the UUID's
    undashed hex form. Both dash conventions must match."""
    undashed = hashlib.sha1(_UUID.replace("-", "").encode()).hexdigest()
    assert _run(env, [_check(unique_key=undashed)]) == 0


def test_uppercase_ping_url_still_matches(env):
    env.setenv("ORCHESTRATOR_PING_URL", _PING.upper().replace("HTTPS", "https"))
    assert _run(env, [_check()]) == 0


def test_readwrite_key_ping_url_match_passes(env):
    checks = [_check(unique_key="not-the-hash", ping_url=_PING)]
    assert _run(env, checks) == 0


@pytest.mark.parametrize("missing", [
    "ORCHESTRATOR_PING_URL", "HEALTHCHECKS_API_KEY_RO",
    "EXPECTED_PERIOD_SECONDS", "MAX_GRACE_SECONDS",
])
def test_missing_config_fails_closed(env, missing):
    env.delenv(missing)
    assert _run(env, [_check()]) == 2


def test_api_failure_fails_closed(env, capsys):
    def boom(key):
        raise OSError("connection reset")
    env.setattr(adp, "fetch_checks", boom)
    assert adp.main() == 2
    assert "unwatched" in capsys.readouterr().err


def test_no_matching_check_fails_closed(env, capsys):
    assert _run(env, [_check(unique_key="other", name="unrelated")]) == 2
    err = capsys.readouterr().err
    assert "none match" in err and _UUID not in err


def test_zero_checks_names_the_wrong_project_cause(env, capsys):
    """r13 field failure: an empty list means the key is from another
    healthchecks PROJECT — the error must say so, actionably."""
    assert _run(env, []) == 2
    assert "different project" in capsys.readouterr().err


def test_slug_style_ping_url_matches_by_slug(env):
    """Slug-based ping URLs (hc-ping.com/<ping-key>/<slug>) carry the slug
    as the last segment; matching must work without uuid or ping_url."""
    env.setenv("ORCHESTRATOR_PING_URL", "https://hc-ping.com/pk_abc/onelive-ingest")
    checks = [_check(unique_key="not-a-uuid-hash", slug="onelive-ingest")]
    assert _run(env, checks) == 0


def test_paused_check_fails_closed(env):
    assert _run(env, [_check(status="paused")]) == 2


def test_cron_type_check_fails_closed(env):
    c = _check()
    del c["timeout"]
    c["schedule"] = "*/20 * * * *"
    assert _run(env, [c]) == 2


def test_period_mismatch_fails_closed(env, capsys):
    assert _run(env, [_check(timeout=3600)]) == 2
    assert "period mismatch" in capsys.readouterr().err


@pytest.mark.parametrize("bad_grace", [601, 86400, None, "600", -1, True])
def test_grace_out_of_bounds_or_mistyped_fails_closed(env, bad_grace):
    """r12: 0 <= grace <= max_grace, int only — negative and bool fail too."""
    assert _run(env, [_check(grace=bad_grace)]) == 2


@pytest.mark.parametrize("var,bad", [
    ("EXPECTED_PERIOD_SECONDS", "0"), ("EXPECTED_PERIOD_SECONDS", "-1200"),
    ("MAX_GRACE_SECONDS", "0"), ("MAX_GRACE_SECONDS", "-600"),
    ("EXPECTED_PERIOD_SECONDS", "twenty"),
])
def test_nonpositive_or_garbage_bounds_fail_closed(env, var, bad):
    """r12: non-positive declared bounds are misconfig, never satisfiable."""
    env.setenv(var, bad)
    assert _run(env, [_check()]) == 2


def test_secret_material_never_in_failure_output(env, capsys):
    _run(env, [_check(timeout=999)])
    err = capsys.readouterr().err
    assert "ro-key" not in err and _UUID not in err


def test_declared_slug_is_required(env):
    env.delenv("DEADMAN_CHECK_SLUG")
    assert _run(env, [_check()]) == 2


def test_declared_slug_matches_when_ping_url_is_bound(env):
    env.setenv("DEADMAN_CHECK_SLUG", "Named-Check")
    checks = [{"name": "named-check", "slug": "x", "status": "up",
               "timeout": 1200, "grace": 600, "unique_key": "zzz",
               "n_pings": 3}]
    assert _run(env, checks, bound=True) == 0


def test_misbound_ping_url_fails_even_with_matching_name(env, capsys):
    """r17 BLOCKER inverted into the contract: a check whose name matches
    the declaration but whose ping counter does not move after the probe
    means ORCHESTRATOR_PING_URL feeds some other check — fail closed."""
    env.setenv("DEADMAN_CHECK_SLUG", "Named-Check")
    checks = [{"name": "named-check", "slug": "x", "status": "up",
               "timeout": 1200, "grace": 600, "unique_key": "zzz",
               "n_pings": 3}]
    assert _run(env, checks, bound=False) == 2
    assert "misbound" in capsys.readouterr().err


def test_probe_delivery_failure_fails_closed(env):
    def boom(url):
        raise OSError("connection refused")
    env.setattr(adp, "send_binding_probe", boom)
    env.setattr(adp, "fetch_checks", lambda key: [_check()])
    assert adp.main() == 2


def test_missing_n_pings_fails_closed(env):
    c = _check()
    del c["n_pings"]
    assert _run(env, [c]) == 2


def test_wrong_declaration_and_no_other_match_fails_closed(env, capsys):
    env.setenv("DEADMAN_CHECK_SLUG", "some-other-check")
    checks = [{"name": "unrelated", "slug": "unrelated", "status": "up",
               "timeout": 1200, "grace": 600, "unique_key": "zzz"}]
    assert _run(env, checks) == 2
    assert "DECLARED slug" in capsys.readouterr().err


# --- R-023 PATH A alarm-verification probe (trigger part 2) -----------------
# The rule under test: REPORT_FLIPS=1 adds a flip report strictly AFTER the
# existing assertions pass; unset, the flips endpoint is never touched (the
# mode is purely additive). 401/403/404 = the probe's answer (exit 0 with the
# FLIPS-UNREADABLE line naming PATH B); any other flips fault = loud nonzero.

_FLIPS = [
    {"timestamp": "2026-07-22T14:17:02+00:00", "up": 1},
    {"timestamp": "2026-07-22T12:47:02+00:00", "up": 0},
]


def test_report_flips_prints_table_and_marks_down(env, capsys):
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", lambda key, cid: list(_FLIPS))
    assert _run(env, [_check()]) == 0
    out = capsys.readouterr().out
    assert "OK" in out  # the existing assertion output is unchanged
    assert "FLIP REPORT" in out and "R-023" in out
    assert "2026-07-22T14:17:02+00:00" in out
    assert "2026-07-22T12:47:02+00:00" in out
    assert "DOWN event" in out and "1 DOWN" in out


def test_report_flips_empty_history_reports_no_down_events(env, capsys):
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", lambda key, cid: [])
    assert _run(env, [_check()]) == 0
    assert "no DOWN events" in capsys.readouterr().out


def test_report_flips_uses_unique_key_and_never_prints_it(env, capsys):
    """The RO list response identifies checks by unique_key — the flips URL
    must be formed from it, and it must never reach output."""
    seen = {}

    def _spy(key, cid):
        seen["cid"] = cid
        return []
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", _spy)
    checks = [_check()]
    assert _run(env, checks) == 0
    assert seen["cid"] == checks[0]["unique_key"]
    out = capsys.readouterr().out
    assert seen["cid"] not in out and _UUID not in out


@pytest.mark.parametrize("code", [401, 403])
def test_report_flips_access_denied_is_the_answer_exit_zero(env, capsys, code):
    """401/403 = the RO key's access was revoked — the probe's access
    answer; it reports and succeeds (exit 0). 404 is NOT in this group
    (see the dedicated ambiguity test)."""
    def _denied(key, cid):
        raise urllib.error.HTTPError("url", code, "denied", None, None)
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", _denied)
    assert _run(env, [_check()]) == 0
    out = capsys.readouterr().out
    assert f"FLIPS-UNREADABLE: read-only key cannot access flip history " \
           f"(HTTP {code})" in out
    assert "PATH B" in out


def test_report_flips_404_is_ambiguous_and_fails_loud(env, capsys):
    """Pre-attack nit (PR #51): 404 can mean identifier-not-found at least
    as plausibly as denial — and readability is already live-proven — so
    it must never masquerade as the access answer."""
    def _notfound(key, cid):
        raise urllib.error.HTTPError("url", 404, "not found", None, None)
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", _notfound)
    assert _run(env, [_check()]) == 2
    err = capsys.readouterr().err
    assert "404" in err and "Ambiguous" in err


def test_report_flips_network_error_fails_loud(env, capsys):
    def _boom(key, cid):
        raise OSError("connection reset")
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", _boom)
    assert _run(env, [_check()]) == 2
    assert "failing loud" in capsys.readouterr().err


def test_report_flips_unexpected_http_code_fails_loud(env):
    """5xx is neither history nor an access answer — inconclusive, loud."""
    def _boom(key, cid):
        raise urllib.error.HTTPError("url", 500, "server error", None, None)
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", _boom)
    assert _run(env, [_check()]) == 2


def test_report_flips_wrapped_body_is_normalized(env, capsys):
    """The hosted service wraps the array as {"flips": [...]} — mirroring
    its {"checks": [...]} wrapper — while the upstream repo docs show a
    bare array. The FIRST live probe run answered 200 with the wrapped
    shape and the strict parser failed loud (PR #51, run 29963320514);
    both shapes must now parse identically."""
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", lambda key, cid: {"flips": list(_FLIPS)})
    assert _run(env, [_check()]) == 0
    out = capsys.readouterr().out
    assert "FLIP REPORT" in out and "1 DOWN" in out


@pytest.mark.parametrize("bad_body", [
    {"other": []},                                   # dict without a flips list
    {"flips": "nope"},                               # wrapper, wrong payload
    [{"timestamp": "2026-07-22T14:17:02+00:00"}],    # entry missing "up"
    [{"up": 1}],                                     # entry missing timestamp
    # out-of-domain "up": documented domain is 0|1 — 2/-1 must be malformed,
    # never silently read as UP (evaluator r5 nit)
    [{"timestamp": "2026-07-22T14:17:02+00:00", "up": 2}],
    [{"timestamp": "2026-07-22T14:17:02+00:00", "up": -1}],
    "nonsense",
])
def test_report_flips_malformed_response_fails_loud(env, bad_body):
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips", lambda key, cid: bad_body)
    assert _run(env, [_check()]) == 2


def test_report_flips_malformed_failure_diagnoses_structure_only(env, capsys):
    """An unrecognized 200 body must fail with type/key-name structure in
    the message (one-look fixable next time) and NEVER response values."""
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(
        adp, "fetch_flips",
        lambda key, cid: {"surprise": ["secret-value-never-logged"]},
    )
    assert _run(env, [_check()]) == 2
    err = capsys.readouterr().err
    assert "dict with keys ['surprise']" in err
    assert "secret-value-never-logged" not in err


@pytest.mark.parametrize("value", [None, "0", ""])
def test_report_flips_off_never_touches_the_flips_endpoint(env, value):
    """Purely-additive guarantee: anything but the literal '1' (including
    unset) must leave the flips endpoint completely uncontacted."""
    calls = []
    if value is None:
        env.delenv("REPORT_FLIPS", raising=False)
    else:
        env.setenv("REPORT_FLIPS", value)
    env.setattr(adp, "fetch_flips",
                lambda key, cid: calls.append(cid) or [])
    assert _run(env, [_check()]) == 0
    assert calls == []


@pytest.mark.parametrize("value", ["true", "yes", "2", " on "])
def test_report_flips_out_of_domain_value_fails_loud(env, capsys, value):
    """Pre-attack nit (PR #51): a dispatch typo ('true'/'yes') must not
    silently skip the probe while the run reports overall success."""
    calls = []
    env.setenv("REPORT_FLIPS", value)
    env.setattr(adp, "fetch_flips",
                lambda key, cid: calls.append(cid) or [])
    assert _run(env, [_check()]) == 2
    assert calls == []
    assert "REPORT_FLIPS must be unset" in capsys.readouterr().err


def test_report_flips_skipped_when_assertions_fail(env):
    """The probe runs only AFTER the existing assertions pass — a failing
    tree must exit 2 without ever consulting the flips endpoint."""
    calls = []
    env.setenv("REPORT_FLIPS", "1")
    env.setattr(adp, "fetch_flips",
                lambda key, cid: calls.append(cid) or [])
    assert _run(env, [_check(timeout=3600)]) == 2  # period mismatch
    assert calls == []
