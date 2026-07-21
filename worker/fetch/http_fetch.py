"""HTTP fetch adapter with content-hash dedupe and raw_fetch audit trail.
No login/paywall/bot-protection bypass — policy-safe by construction (see CLAUDE.md).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/fetch/http_fetch.py)
"""
from typing import Optional, Dict, Any
import hashlib
import json
import logging
import os
import time

import psycopg2
import requests

from worker.db_config import resolve_dsn

RAW_DIR = os.getenv("ONELIVE_RAW_DIR", "var/raw")


def db():
    return psycopg2.connect(resolve_dsn())


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# raw_fetch.content_hash for ATTEMPT rows (failed / not-modified fetches):
# successful fetches store the sha256 hex of the fetched bytes; attempt rows
# store "attempt:<outcome>" instead, with the detail in headers jsonb. Why
# attempts are recorded at all (PR #43 r2 nit, real coverage bug): the
# capped scheduled loop rotates on max(raw_fetch.fetched_at) per source
# (worker/run_once.py) — if only SUCCESSES left rows, a permanently-failing
# or perpetually-304 source would look never/least-fetched forever, lead
# every rotation window, and monopolize the per-run budget while healthy
# sources starve. Recording the attempt makes the rotation sweep on "last
# tried", which is the semantics a budget window needs, and gives the audit
# trail the failures it was missing.
ATTEMPT_HASH_PREFIX = "attempt:"


def record_fetch_attempt(
    source_id, url: str, outcome: str, detail: str = "", *, strict: bool,
) -> Optional[Exception]:
    """raw_fetch ATTEMPT row (outcome: 'failed'/'not_modified').

    Two deliberate modes (PR #43 r3/r8 — one blanket mode was wrong in
    each direction, and a quiet swallow was wrong even in the tolerant
    one):
    - strict=False — the FAILED-fetch path: an original fetch error is in
      flight and must reach the caller, so a bookkeeping failure here
      never masks it — but it is NOT swallowed quietly (r8): it is logged
      at ERROR level and RETURNED, and fetch_url attaches it to the
      original exception as a traceback note, so the degraded-rotation
      risk rides the error evidence instead of hiding in a warning.
    - strict=True — the 304 path: there is NO original error, and a
      silently lost attempt row would quietly re-introduce the exact
      capped-window starvation bug this row exists to prevent. The write
      failure propagates; run_loop's per-source isolation treats it as
      that source's loud failure.

    Returns the bookkeeping exception when strict=False and the write
    failed, else None. A source with no source_id (e.g. the smoke stub)
    records nothing — it is not in the rotation.
    """
    if source_id is None:
        return None
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into raw_fetch(source_id, fetch_url, content_hash,
                                          headers, storage_ref)
                    values (%s,%s,%s,%s::jsonb,%s)
                    """,
                    (
                        source_id,
                        url,
                        f"{ATTEMPT_HASH_PREFIX}{outcome}",
                        json.dumps({"attempt": outcome, "detail": detail[:500]}),
                        None,
                    ),
                )
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — tolerated ONLY when not strict
        if strict:
            raise
        logging.getLogger(__name__).error(
            "attempt-row write FAILED for source %s (%s) — rotation may "
            "under-rotate this source until a write succeeds: %s",
            source_id, outcome, exc,
        )
        return exc
    return None


def fetch_url(
    *,
    source_id: Optional[str],
    url: str,
    user_agent: str = "OneLiveBot/0.1 (+contact: ops@onelive.example)",
    min_interval_s: float = 2.0,
    timeout_s: int = 20,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
) -> Dict[str, Any]:
    os.makedirs(RAW_DIR, exist_ok=True)
    time.sleep(max(0.0, min_interval_s))
    headers = {"User-Agent": user_agent}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    try:
        r = requests.get(url, headers=headers, timeout=timeout_s)
        if r.status_code != 304:
            r.raise_for_status()
    except Exception as exc:
        # Stamp the attempt — the ORIGINAL error must reach the caller,
        # so run_loop's per-source isolation policy is unchanged. If the
        # stamp itself fails, that bookkeeping failure rides the original
        # exception as a traceback note (r8: loud structured evidence in
        # logs/Sentry/replay detail, never a quiet warning).
        bookkeeping_exc = record_fetch_attempt(
            source_id, url, "failed", str(exc), strict=False)
        if bookkeeping_exc is not None:
            exc.add_note(
                "ALSO: raw_fetch attempt-row write failed "
                f"({bookkeeping_exc!r}) — rotation may under-rotate this "
                "source until a write succeeds."
            )
        raise
    if r.status_code == 304:
        # An attempt row keeps 304-stable sources rotating instead of
        # looking ever-staler and re-claiming a budget slot every run.
        # STRICT: with no original error in flight, a lost row would
        # silently re-introduce the starvation bug (r3 finding) — a write
        # failure is this source's loud per-source failure.
        record_fetch_attempt(source_id, url, "not_modified", strict=True)
        return {"status": "not_modified", "url": url}

    content = r.content
    ch = sha256(content)
    path = os.path.join(RAW_DIR, f"{ch}.bin")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(content)

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              insert into raw_fetch(source_id, fetch_url, content_hash, headers, storage_ref)
              values (%s,%s,%s,%s::jsonb,%s)
              returning raw_fetch_id
            """, (
                source_id,
                url,
                ch,
                json.dumps({
                    "status_code": r.status_code,
                    "etag": r.headers.get("ETag"),
                    "last_modified": r.headers.get("Last-Modified"),
                    "content_type": r.headers.get("Content-Type"),
                }),
                path
            ))
            raw_fetch_id = cur.fetchone()[0]
        conn.commit()

    return {
        "status": "ok",
        "raw_fetch_id": str(raw_fetch_id),
        "url": url,
        "content_hash": ch,
        "storage_ref": path,
        "etag": r.headers.get("ETag"),
        "last_modified": r.headers.get("Last-Modified"),
        "content_type": r.headers.get("Content-Type"),
        "bytes": len(content),
    }
