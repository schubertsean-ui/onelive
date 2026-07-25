"""Unit tests for worker.promote.card_fields — the pure derivation of the
user-facing card columns (title/category/subsegment/ticket_url) written into the
canonical `event` row at promotion. No DB: card_fields is a pure function so the
"populate the documented card columns, but NEVER fabricate a category" invariant
is testable without a database (mirrors assert_promotable's design)."""
from worker.promote import card_fields


def test_title_and_ticket_pass_through():
    c = card_fields("Spoon at Stubb's", "https://tix.example/x")
    assert c["title"] == "Spoon at Stubb's"
    assert c["ticket_url"] == "https://tix.example/x"


def test_category_derived_from_real_title_words_only():
    # Deterministic keyword read of the event's OWN title — the same charter-
    # blessed classifier used to recover Ticketmaster 'Undefined' events.
    assert card_fields("An Evening of Standup Comedy", None)["category"] == "comedy"
    assert card_fields("Austin Symphony: Mahler 2", None)["category"] == "performing-arts"


def test_no_title_signal_stays_null_never_a_guessed_domain():
    # No cultural signal in the title => category NULL (feed shows 'Other'),
    # never a fabricated domain on a public surface.
    c = card_fields("XZ Event 9910", None)
    assert c["category"] is None
    assert c["subsegment"] is None


def test_empty_inputs_normalize_to_none_not_empty_string():
    c = card_fields(None, "")
    assert c["title"] is None
    assert c["ticket_url"] is None
    assert c["category"] is None
