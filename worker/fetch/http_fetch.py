"""HTTP fetch adapter with content-hash dedupe and raw_fetch audit trail.
No login/paywall/bot-protection bypass — policy-safe by construction (see CLAUDE.md).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/fetch/http_fetch.py)
"""
from typing import Optional, Dict, Any
import hashlib
import json
import os
import time

import psycopg2
import requests


DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")
RAW_DIR = os.getenv("ONELIVE_RAW_DIR", "var/raw")


def db():
    return psycopg2.connect(DB_DSN)


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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

    r = requests.get(url, headers=headers, timeout=timeout_s)
    if r.status_code == 304:
        return {"status": "not_modified", "url": url}
    r.raise_for_status()

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
