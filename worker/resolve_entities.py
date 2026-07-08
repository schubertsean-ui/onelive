"""Entity resolution for venues and artists (get-or-create by normalized name).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/resolve_entities.py)
"""
import os
import psycopg2
from typing import List

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def db():
    return psycopg2.connect(DB_DSN)


def resolve_venue_id(venue_name: str, city: str = "Austin") -> str:
    venue_name = (venue_name or "").strip()
    city = (city or "").strip()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select venue_id from venue where lower(name)=lower(%s) and (city is null or lower(city)=lower(%s)) limit 1",
                (venue_name, city))
            row = cur.fetchone()
            if row:
                return str(row[0])
            cur.execute("insert into venue(name, city) values (%s,%s) returning venue_id",
                        (venue_name or "Unknown Venue", city or None))
            vid = cur.fetchone()[0]
        conn.commit()
    return str(vid)


def resolve_artist_ids(artist_names: List[str]) -> List[str]:
    out = []
    with db() as conn:
        with conn.cursor() as cur:
            for name in (artist_names or []):
                n = (name or "").strip()
                if not n:
                    continue
                cur.execute("select artist_id from artist where lower(name)=lower(%s) limit 1", (n,))
                row = cur.fetchone()
                if row:
                    out.append(str(row[0]))
                    continue
                cur.execute("insert into artist(name) values (%s) returning artist_id", (n,))
                out.append(str(cur.fetchone()[0]))
        conn.commit()
    return out
