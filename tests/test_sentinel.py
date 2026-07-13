"""Tests for worker/sentinel.py — Sentry init + healthchecks dead-man ping.

Hermetic: no network (urlopen monkeypatched), no Sentry account. Proves the
no-op-when-unset contract on both signals, the fail-loud SentinelConfigError
when SENTRY_DSN is set but the SDK is missing, that a failed ping never
crashes the monitored job, and that deadman() pings fail-then-reraises on
exceptions (the monitor must never mask the failure it is reporting).
"""
import builtins
import io
import urllib.error

import pytest

from worker import sentinel


class _FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_init_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    assert sentinel.init_sentry("api") is False


def test_init_sentry_fails_loud_when_sdk_missing(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://key@example.ingest.sentry.io/1")
    real_import = builtins.__import__

    def _no_sentry(name, *args, **kwargs):
        if name == "sentry_sdk":
            raise ImportError("No module named 'sentry_sdk'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_sentry)
    with pytest.raises(sentinel.SentinelConfigError):
        sentinel.init_sentry("api")


def test_ping_noop_without_url(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_PING_URL", raising=False)
    assert sentinel.ping_deadman() is False


def test_ping_hits_suffixed_urls(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PING_URL", "https://hc-ping.example/uuid")
    seen = []

    def _fake_urlopen(url, timeout):
        seen.append(url)
        return _FakeResponse(200)

    monkeypatch.setattr(sentinel.urllib.request, "urlopen", _fake_urlopen)
    assert sentinel.ping_deadman("start") is True
    assert sentinel.ping_deadman() is True
    assert sentinel.ping_deadman("fail") is True
    assert seen == [
        "https://hc-ping.example/uuid/start",
        "https://hc-ping.example/uuid",
        "https://hc-ping.example/uuid/fail",
    ]
    with pytest.raises(ValueError):
        sentinel.ping_deadman("bogus")


def test_ping_failure_never_crashes_the_job(monkeypatch, caplog):
    monkeypatch.setenv("ORCHESTRATOR_PING_URL", "https://hc-ping.example/uuid")

    def _boom(url, timeout):
        raise urllib.error.URLError(io.BlockingIOError("down"))

    monkeypatch.setattr(sentinel.urllib.request, "urlopen", _boom)
    with caplog.at_level("WARNING"):
        assert sentinel.ping_deadman() is False
    assert any("dead-man ping" in r.message for r in caplog.records)


def test_deadman_pings_success_and_fail_paths(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PING_URL", "https://hc-ping.example/uuid")
    events = []
    monkeypatch.setattr(
        sentinel, "ping_deadman", lambda event="": events.append(event or "success")
    )

    with sentinel.deadman():
        pass
    assert events == ["start", "success"]

    events.clear()
    with pytest.raises(RuntimeError, match="boom"):
        with sentinel.deadman():
            raise RuntimeError("boom")
    assert events == ["start", "fail"]
