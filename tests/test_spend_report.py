"""worker/spend_report.py — the cost figure, and the binding that keeps it true.

The dollar amount printed in a tick's outcomes is the only number in this
pipeline an operator would budget against, so it has exactly one job: be right,
or say it does not know. These tests pin both halves.

THE BINDING (evaluator finding, seat openai / lens absence-only, PR #213): the
prices in PRICES_USD_PER_MTOK are a COPY of the committed ladder in
docs/MODEL_ROUTING.md. The module's own docstring said so and warned it could
go stale — and then nothing checked it, which is a comment doing a test's job.
A stale copy would not fail loudly; it would print a precise, wrong cost, which
is worse than printing nothing. So the doc is parsed here and compared field by
field: change one side and this test fails until the other side agrees.
"""
import pathlib
import re

import pytest

from worker.spend_report import (
    PRICES_USD_PER_MTOK,
    estimate_cost_usd,
    format_spend,
    price_for,
)

_ROUTING_DOC = (pathlib.Path(__file__).resolve().parent.parent
                / "docs" / "MODEL_ROUTING.md")

#: A ladder row: | Tier | `model-id` | $IN / $OUT | Use for |
_LADDER_ROW = re.compile(
    r"^\|[^|]+\|\s*`([^`]+)`\s*\|\s*\$([0-9.]+)\s*/\s*\$([0-9.]+)\s*\|",
    re.MULTILINE)


def _documented_prices():
    """The price table as docs/MODEL_ROUTING.md actually states it.

    Parsed rather than restated: a hand-copied "expected" dict here would be a
    third copy, and three copies of a price drift even faster than two.
    """
    text = _ROUTING_DOC.read_text(encoding="utf-8")
    rows = {m.group(1): (float(m.group(2)), float(m.group(3)))
            for m in _LADDER_ROW.finditer(text)}
    assert rows, (
        "no price rows parsed out of docs/MODEL_ROUTING.md — the ladder's "
        "table shape changed, and this binding must be repaired rather than "
        "skipped (a binding that silently matches nothing is not a binding)")
    return rows


def test_every_price_matches_the_committed_ladder():
    """The mechanical binding. Change either side and this fails."""
    documented = _documented_prices()
    for model_id, price in PRICES_USD_PER_MTOK.items():
        assert model_id in documented, (
            f"{model_id} is priced in worker/spend_report.py but is not in the "
            "docs/MODEL_ROUTING.md ladder — an unsourced price must never "
            "reach the outcomes surface as a precise dollar figure")
        assert price == documented[model_id], (
            f"{model_id}: code says {price}, docs/MODEL_ROUTING.md says "
            f"{documented[model_id]} — the copy has gone stale, and a stale "
            "price prints a wrong cost rather than failing loudly")


def test_the_extraction_tier_is_priced_because_that_is_what_a_tick_spends():
    """Extraction is the only stage that may call Anthropic, so whatever tier
    extraction runs at MUST be in the table or every tick reports "unknown"."""
    assert price_for("claude-haiku-4-5") is not None


def test_dated_model_ids_still_price():
    """Anthropic ids carry dated suffixes; a table keyed on exact ids would
    silently fall to "unknown" on the next dated release."""
    assert price_for("claude-haiku-4-5-20251001") == price_for("claude-haiku-4-5")


def test_the_longest_matching_prefix_wins():
    """So a more specific entry always beats a shorter one it contains."""
    assert price_for("claude-sonnet-4-6-20260101") == PRICES_USD_PER_MTOK["claude-sonnet-4-6"]


def test_a_real_cost_is_arithmetic_not_a_guess():
    # 1M input at $1 + 1M output at $5 on the Cheap tier.
    assert estimate_cost_usd(
        model_id="claude-haiku-4-5", input_tokens=1_000_000,
        output_tokens=1_000_000) == pytest.approx(6.0)


@pytest.mark.parametrize("model_id,tokens_in,tokens_out,expect", [
    ("some-unreleased-model", 100, 10, "not in the docs/MODEL_ROUTING.md price table"),
    ("claude-haiku-4-5", 0, 0, "the provider reported no token usage"),
    (None, 100, 10, "not in the docs/MODEL_ROUTING.md price table"),
])
def test_unknowable_cost_says_so_rather_than_printing_a_number(
        model_id, tokens_in, tokens_out, expect):
    """A fabricated cost is worse than no cost, because someone budgets against
    it. Zero tokens with a known model is NOT free — it means we were told
    nothing — so it is unknown too."""
    out = format_spend(model_id=model_id, input_tokens=tokens_in,
                       output_tokens=tokens_out)
    assert "unknown" in out and expect in out
    assert "$" not in out.replace("$IN", ""), "no dollar figure on an unknown"
    assert estimate_cost_usd(
        model_id=model_id, input_tokens=tokens_in, output_tokens=tokens_out) is None
