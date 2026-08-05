"""Source provenance rides the promote boundary onto the public row
(migration 0020; founder directive 2026-08-05 cards-reflect-updated-content).

The promote insert must carry source_name/source_url so the consumer "How we
know" sheet can name and link the real listing a discovered event was
published from (red class featurability-dimension-missed: origin at every
public emitter). Hermetic string/AST pins, same shape as
test_event_insert_casts_artist_ids_to_uuid_array — fake cursors can never
prove server-side column presence, so the SQL text itself is the contract.
"""
import re

import worker.promote as promote

SRC = open(promote.__file__).read()


def _insert_block() -> str:
    return SRC.split("insert into event(")[1].split("returning event_id")[0]


def test_event_insert_carries_provenance_columns():
    block = _insert_block()
    assert "source_name" in block
    assert "source_url" in block


def test_insert_placeholder_count_matches_column_count():
    # A silent column/placeholder mismatch is exactly the class hermetic tests
    # missed for artist_ids — pin the arity so adding a column without its
    # placeholder (or vice versa) fails here, not live.
    block = _insert_block()
    cols_text = block.split(")")[0]
    n_cols = len([c for c in cols_text.replace("\n", " ").split(",") if c.strip()])
    values_text = block.split("values")[1]
    n_placeholders = len(re.findall(r"%s", values_text))
    # 'scheduled' and false are literals, not placeholders.
    assert n_cols == n_placeholders + 2


def test_source_url_lookup_is_by_unique_lowered_name():
    # The source registry keys name uniquely on lower(name) (0009), so the
    # lookup must match that key — a case-sensitive match would silently drop
    # provenance for a case-variant source_name (swallowed-corrupt-data).
    assert re.search(
        r"select base_url from source where lower\(name\)=lower\(%s\)", SRC)


def test_missing_source_stays_null_never_fabricated():
    # An unnamed source must short-circuit to NULL (the UI's generic wording),
    # never query with NULL or invent a value. Pinned structurally: the lookup
    # is guarded by `if source_name:` and source_url starts as None.
    assert "source_url = None" in SRC
    assert re.search(r"if source_name:\s*\n\s+cur\.execute", SRC)
