"""tools/assert_deadman_period.py — R-020's mechanical closure (PR #43 r11).

The rule under test: the ingestion cron must refuse to run unless the
healthchecks.io check's live period/grace provably match the cadence the
workflow declares. Every failure path exits 2 (closed): missing config,
API failure, no matching check, paused check, cron-type check, period
mismatch, grace over bound. Matching works for both key types (ping_url
for read-write, unique_key == sha1(uuid) for read-only). No secret
material in output.

Hermetic: fetch_checks is monkeypatched; no network.
"""
import hashlib

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
    return monkeypatch


def _run(monkeypatch, checks):
    monkeypatch.setattr(adp, "fetch_checks", lambda key: checks)
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


def test_declared_slug_matches_by_name_or_slug(env):
    env.setenv("DEADMAN_CHECK_SLUG", "Named-Check")
    checks = [{"name": "named-check", "slug": "x", "status": "up",
               "timeout": 1200, "grace": 600, "unique_key": "zzz"}]
    assert _run(env, checks) == 0


def test_wrong_declaration_and_no_other_match_fails_closed(env, capsys):
    env.setenv("DEADMAN_CHECK_SLUG", "some-other-check")
    checks = [{"name": "unrelated", "slug": "unrelated", "status": "up",
               "timeout": 1200, "grace": 600, "unique_key": "zzz"}]
    assert _run(env, checks) == 2
    assert "DECLARED slug" in capsys.readouterr().err
