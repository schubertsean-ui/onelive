"""Sentinel minimum: Sentry init + healthchecks.io dead-man ping (Session Contract #1).

Greppable summary: `init_sentry(surface)` initialises the Sentry SDK behind
SENTRY_DSN (unset -> documented no-op; set but sentry-sdk missing -> loud
SentinelConfigError, per the fail-loud-on-misconfig convention). `ping_deadman
(event)` GETs the healthchecks.io URL in ORCHESTRATOR_PING_URL (unset -> no-op;
network fault -> logged warning, never crashes the job it monitors — the
monitor must not be able to kill the monitored). `deadman()` is a context
manager pinging start/success/fail around a scheduled run. Charter rule
(CLAUDE.md Sentinel): no scheduled loop ships without both signals wired.
"""
from __future__ import annotations

import logging
import os
import urllib.error
import urllib.request
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_PING_TIMEOUT_SECONDS = 10


class SentinelConfigError(RuntimeError):
    """SENTRY_DSN is set but the sentry-sdk package is not importable.

    Raised loudly instead of degrading: a configured-but-broken error monitor
    is worse than none, because every surface would silently believe it is
    covered (the same misconfig-vs-transient split as ExtractionConfigError
    in ai/claude_provider.py).
    """


def init_sentry(surface: str) -> bool:
    """Initialise Sentry for one surface ("api" | "worker"). Returns True if live.

    SENTRY_DSN unset -> no-op (returns False): pre-launch environments and
    tests must run cleanly with zero Sentinel configuration.
    """
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        logger.debug("SENTRY_DSN not set — Sentry disabled for surface %r.", surface)
        return False
    try:
        import sentry_sdk
    except ImportError as exc:
        raise SentinelConfigError(
            "SENTRY_DSN is set but the sentry-sdk package is not installed "
            "(pip install sentry-sdk). Refusing to run half-monitored: either "
            "install the SDK or unset SENTRY_DSN."
        ) from exc
    sentry_sdk.init(
        dsn=dsn,
        environment=os.environ.get("ONELIVE_ENV", "development"),
        # Error monitoring only for now; performance tracing is a later,
        # deliberate (and billable-volume) decision.
        traces_sample_rate=0.0,
    )
    sentry_sdk.set_tag("surface", surface)
    logger.info("Sentry initialised for surface %r.", surface)
    return True


def ping_deadman(event: str = "") -> bool:
    """GET the healthchecks.io dead-man URL. event: "" (success)|"start"|"fail".

    ORCHESTRATOR_PING_URL unset -> no-op (returns False). A ping that cannot
    be delivered is logged as a warning and swallowed BY DESIGN: healthchecks'
    whole model is that a missing success ping raises the alarm, so failing
    the monitored job because its monitor was unreachable would invert the
    safety relationship.
    """
    base = os.environ.get("ORCHESTRATOR_PING_URL")
    if not base:
        logger.debug("ORCHESTRATOR_PING_URL not set — dead-man ping skipped.")
        return False
    if event not in ("", "start", "fail"):
        raise ValueError(f"unknown dead-man event {event!r} (want ''|'start'|'fail')")
    url = base.rstrip("/") + (f"/{event}" if event else "")
    try:
        with urllib.request.urlopen(url, timeout=_PING_TIMEOUT_SECONDS) as resp:
            ok = 200 <= resp.status < 300
        if not ok:
            logger.warning("dead-man ping %s returned HTTP %s.", url, resp.status)
        return ok
    except (urllib.error.URLError, OSError) as exc:
        logger.warning(
            "dead-man ping failed (job continues): url=%s event=%s error=%s",
            url, event or "success", exc,
        )
        return False


@contextmanager
def deadman():
    """Wrap a scheduled run in start/success/fail dead-man pings.

    No-op end to end when ORCHESTRATOR_PING_URL is unset. Exceptions from the
    wrapped block are re-raised untouched after the fail ping.
    """
    ping_deadman("start")
    try:
        yield
    except BaseException:
        ping_deadman("fail")
        raise
    ping_deadman()
