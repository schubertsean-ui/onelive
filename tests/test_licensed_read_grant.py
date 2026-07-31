"""Regression guard for the licensed_event public-read grant.

The feed (web/lib/licensed.ts) reads licensed_event with the anon/publishable key,
so EVERY column it selects must be covered by a column-level GRANT to `anon` in a
migration. They drifted once — 0014 added venue_url/venue_phone to the table and
the feed selected them, but no migration granted them, so PostgREST 401'd the
whole request ("permission denied for table licensed_event") and the feed showed
zero events. This test recomputes both sides from the source files and fails if
the feed ever again selects a column outside the granted set — the raw `raw`
column must also stay OUT of both.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS = REPO / "supabase" / "migrations"
FEED = REPO / "web" / "lib" / "licensed.ts"

_GRANT_RE = re.compile(
    r"grant\s+select\s*\(([^)]*)\)\s*on\s+licensed_event\s+to\s+[^;]*\banon\b",
    re.IGNORECASE | re.DOTALL,
)


def _granted_columns() -> set[str]:
    cols: set[str] = set()
    for sql in MIGRATIONS.glob("*.sql"):
        for m in _GRANT_RE.finditer(sql.read_text(encoding="utf-8")):
            cols |= {c.strip() for c in m.group(1).split(",") if c.strip()}
    return cols


def _feed_selected_columns() -> set[str]:
    text = FEED.read_text(encoding="utf-8")
    m = re.search(r"const COLUMNS\s*=\s*\[(.*?)\]", text, re.DOTALL)
    assert m, "could not find the COLUMNS constant in web/lib/licensed.ts"
    return {c.strip() for c in re.findall(r'"([^"]+)"', m.group(1))}


def test_feed_columns_are_all_granted_to_anon():
    granted = _granted_columns()
    selected = _feed_selected_columns()
    missing = selected - granted
    assert not missing, (
        f"feed selects columns not granted to anon → PostgREST 401 / blank feed: "
        f"{sorted(missing)}. Add them to a `grant select (...) on licensed_event "
        f"to anon, authenticated;` migration (raw stays excluded)."
    )


def test_raw_is_never_publicly_granted_or_selected():
    # The audit payload must never be publicly readable.
    assert "raw" not in _granted_columns()
    assert "raw" not in _feed_selected_columns()


def test_venue_contact_columns_are_now_granted():
    # The specific regression: the two columns 0014 added and 0017 grants.
    granted = _granted_columns()
    assert {"venue_url", "venue_phone"} <= granted
