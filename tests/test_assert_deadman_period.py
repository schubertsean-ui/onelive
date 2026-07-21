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
        "name": "onelive-ingest",
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
    assert "no check matches" in err and _UUID not in err


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


@pytest.mark.parametrize("bad_grace", [601, 86400, None, "600"])
def test_grace_over_bound_or_mistyped_fails_closed(env, bad_grace):
    assert _run(env, [_check(grace=bad_grace)]) == 2


def test_secret_material_never_in_failure_output(env, capsys):
    _run(env, [_check(timeout=999)])
    err = capsys.readouterr().err
    assert "ro-key" not in err and _UUID not in err
