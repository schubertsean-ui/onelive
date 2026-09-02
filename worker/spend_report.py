"""What a tick actually cost — fetches, extract calls, tokens, dollars.

Founder, 2026-09-02: "Report fetches/extracts/$ as outcomes." An outcome is a
measurement, so every number here is measured:

  * FETCHES and EXTRACT CALLS are counted by the loop as it makes them
    (worker/crawl_state.py::TickBudget).
  * TOKENS are what the provider itself reported — ai/claude_provider.py stamps
    the SDK's `usage` object onto each extraction, worker/ai_extract.py sums it
    per page, and the loop sums those. Nothing is estimated from text length.
  * DOLLARS are those tokens priced from the COMMITTED table in
    docs/MODEL_ROUTING.md, keyed by the model id that actually ran.

The one rule that makes this trustworthy: an unknown model id, or a provider
that reported no usage, yields "unknown" — never a guessed price and never
$0.00. A fabricated cost number is worse than no cost number, because someone
would budget against it. `estimate_cost_usd` returns None for those cases and
`format_spend` prints the reason.

Extraction is the ONLY stage that may call Anthropic (fetch, sensor, page
discovery and the trust gate are all deterministic code), so extract calls ARE
the AI spend of a tick — there is no second place for cost to hide.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

#: USD per 1,000,000 tokens (input, output), copied from the committed ladder in
#: docs/MODEL_ROUTING.md ("The ladder (prices per 1M tokens, in/out)"). Keys are
#: model-id PREFIXES because Anthropic ids carry dated suffixes
#: (claude-haiku-4-5-20251001) and a table keyed on exact ids would silently
#: fall to "unknown" on the next dated release.
#:
#: This is a COPY of a documented price, so it can go stale. It fails in the
#: safe direction: a model whose prefix is not listed prices as unknown and the
#: report says so, rather than quietly pricing a $25/1M model at $5/1M.
PRICES_USD_PER_MTOK: Dict[str, Tuple[float, float]] = {
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-8": (5.0, 25.0),
}


def price_for(model_id: Optional[str]) -> Optional[Tuple[float, float]]:
    """The (input, output) price per 1M tokens for `model_id`, or None.

    Longest matching prefix wins, so a more specific entry always beats a
    shorter one that happens to be a prefix of it.
    """
    if not model_id:
        return None
    matches = [k for k in PRICES_USD_PER_MTOK if model_id.startswith(k)]
    if not matches:
        return None
    return PRICES_USD_PER_MTOK[max(matches, key=len)]


def estimate_cost_usd(
    *, model_id: Optional[str], input_tokens: int, output_tokens: int,
) -> Optional[float]:
    """Dollars for the tokens a tick really used, or None when unknowable.

    None means exactly one of two honest things, and the caller must print the
    difference rather than a number: the model id is not in the committed price
    table, or the provider reported no token usage at all. Zero tokens with a
    known model is NOT free — it means we were told nothing — so it returns
    None too.
    """
    price = price_for(model_id)
    if price is None:
        return None
    if input_tokens <= 0 and output_tokens <= 0:
        return None
    in_price, out_price = price
    return (input_tokens * in_price + output_tokens * out_price) / 1_000_000.0


def format_spend(
    *, model_id: Optional[str], input_tokens: int, output_tokens: int,
) -> str:
    """The cost cell of the outcomes line: a dollar figure, or why there isn't one."""
    cost = estimate_cost_usd(
        model_id=model_id, input_tokens=input_tokens, output_tokens=output_tokens)
    if cost is not None:
        return f"${cost:.4f}"
    if price_for(model_id) is None:
        return (f"unknown (model {model_id or '<unset>'!s} is not in the "
                "docs/MODEL_ROUTING.md price table)")
    return "unknown (the provider reported no token usage)"
