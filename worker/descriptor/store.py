"""DB access for the spark_line store (migration 0018).

Writes AI-drafted Spark Lines as `candidate` rows ONLY — approval is a
separate, gated step this module cannot perform. Reads only `approved` rows for
the feed, joined by artist key (lower(trim(name))). Every query is
parameterized; the core functions take an injectable cursor so they are testable
with no live DB, and psycopg2 is imported lazily so importing this module never
requires the driver.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from .types import FoundryResult, STATUS_CANDIDATE, VALID_WORD_COUNTS


def artist_key(name: str) -> str:
    """The join key: lower-cased, trimmed artist name. The one value present on
    both the licensed feed (`performer`) and the promoted feed (`artist.name`)."""
    return (name or "").strip().lower()


def _db():
    # Lazy import: the module (and its tests) load without psycopg2 present.
    import psycopg2

    from worker.db_config import resolve_dsn

    return psycopg2.connect(resolve_dsn())


def insert_candidate(result: FoundryResult, artist_name: str, *, cur) -> str:
    """Insert one Spark Line CANDIDATE on `cur`; return its id. Refuses a
    non-candidate result — this writer never lands an approved row (that is the
    separate approval step's job, with its own custody)."""
    if result.status != STATUS_CANDIDATE:
        raise ValueError(
            f"spark_line writer only inserts candidates, got status "
            f"{result.status!r} — approval is a separate gated step"
        )
    word_count = len(result.text.split())
    cur.execute(
        """
        insert into spark_line(
          artist_key, artist_name, text, word_count, tier, attribution,
          status, provenance
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        returning spark_line_id
        """,
        (
            artist_key(artist_name),
            artist_name,
            result.text,
            word_count,
            result.tier,
            result.provenance.get("attribution"),
            STATUS_CANDIDATE,
            json.dumps(result.provenance),
        ),
    )
    return str(cur.fetchone()[0])


def record_human_spark_line(
    artist_name: str,
    text: str,
    *,
    tier: str,
    attribution: str | None = None,
    source_ref: str | None = None,
    cur,
) -> str:
    """Record a HUMAN-authored Spark Line (tier A = artist's own words, tier B =
    a named critic) as a candidate — zero model, zero spend. Tiers A/B do NOT
    flow through the AI Foundry (types.py); their faithfulness is inherent (a
    real person's words), and the human take-live approval is their trust gate.
    Word count is still constrained (display consistency, UI Canon §4); a tier-B
    line must name its source. Returns the new candidate's id."""
    if tier not in ("A", "B"):
        raise ValueError(f"human Spark Line tier must be 'A' or 'B', got {tier!r}")
    words = text.split()
    if len(words) not in VALID_WORD_COUNTS:
        raise ValueError(
            f"Spark Line must be {'/'.join(map(str, VALID_WORD_COUNTS))} words; "
            f"got {len(words)}: {text!r}"
        )
    if tier == "B" and not (attribution or "").strip():
        raise ValueError("a tier-B (critic) Spark Line must name its attribution")
    provenance = {
        "provider": "human",
        "tier": tier,
        "attribution": attribution,
        "source_refs": [source_ref] if source_ref else [],
    }
    cur.execute(
        """
        insert into spark_line(
          artist_key, artist_name, text, word_count, tier, attribution,
          status, provenance
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        returning spark_line_id
        """,
        (
            artist_key(artist_name),
            artist_name,
            text,
            len(words),
            tier,
            attribution,
            STATUS_CANDIDATE,
            json.dumps(provenance),
        ),
    )
    return str(cur.fetchone()[0])


def store_candidate(result: FoundryResult, artist_name: str) -> str:
    """Convenience wrapper opening its own short-lived transaction."""
    with _db() as conn:
        with conn.cursor() as cur:
            sid = insert_candidate(result, artist_name, cur=cur)
        conn.commit()
    return sid


def fetch_approved(artist_names: Iterable[str], *, cur) -> dict[str, dict[str, Any]]:
    """Return {artist_key: {text, tier, attribution}} for the APPROVED Spark
    Lines of the given artists, in ONE parameterized query. Names are normalized
    to keys; the unique-approved index guarantees at most one row per artist."""
    keys = sorted({artist_key(n) for n in artist_names if artist_key(n)})
    if not keys:
        return {}
    cur.execute(
        """
        select artist_key, text, tier, attribution
        from spark_line
        where status = 'approved' and artist_key = any(%s)
        """,
        (keys,),
    )
    out: dict[str, dict[str, Any]] = {}
    for k, text, tier, attribution in cur.fetchall():
        out[k] = {"text": text, "tier": tier, "attribution": attribution}
    return out
