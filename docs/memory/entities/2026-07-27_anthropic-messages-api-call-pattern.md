# Anthropic Messages API — the canonical call pattern (founder-directed, 2026-07-27)

Greppable summary: founder directive to use a standard `anthropic.Anthropic()`
Messages-API call shape in current and all future sessions, PLUS the correction
that makes its prompt-caching actually work. The directive's intent was caching;
the snippet as supplied cached nothing. Both are recorded so a future session
writes the working form, not the supplied form.

## The directive (founder, verbatim intent)

Use `client = anthropic.Anthropic()` with `client.messages.create(...)`,
`model="claude-opus-5"`, an explicit `system=` prompt, prompt caching enabled,
and `print(response.usage.model_dump_json())` to observe cache behaviour.

## What was wrong with the supplied snippet — and why it was invisible

The supplied form put `cache_control={"type": "ephemeral"}` at the top level of
`messages.create()` alongside a ~30-token `system=` string and a per-request
user question. That is valid API syntax and raises no error, but it never
produces a cache hit, for two independent reasons:

1. **Auto-placement lands on the wrong block.** Top-level `cache_control`
   auto-places the breakpoint on the LAST cacheable block, which is the user
   message. The user question varies per request, so every call writes a
   distinct cache entry and no call ever reads one. Caching is a prefix match:
   the breakpoint must sit at the end of the SHARED prefix (the system prompt),
   not at the end of the whole prompt. This is the "shared prefix, varying
   suffix" anti-pattern.
2. **The prefix is below the minimum.** Claude Opus 5's minimum cacheable
   prefix is 512 tokens. A ~30-token system prompt is nowhere near it. Short
   prefixes silently do not cache — no error, just
   `cache_creation_input_tokens: 0`.

Failure mode is silent-by-construction: `usage` reports zeros and the caller has
no signal distinguishing "misplaced breakpoint" from "prefix too short" from
"caching working but nothing to reuse". Whoever reads the printed usage must
know to interpret a persistent zero as a defect, not as normal.

## The corrected canonical form

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-5",
    max_tokens=8000,
    system=[
        {
            "type": "text",
            "text": LARGE_SHARED_SYSTEM_PROMPT,   # must be >= 512 tokens to cache
            "cache_control": {"type": "ephemeral"},
        }
    ],
    messages=[
        {"role": "user", "content": "Analyze the major themes in 'Pride and Prejudice'."}
    ],
)
print(response.usage.model_dump_json())
```

Changes and why each one:

- **`cache_control` moved onto the last `system` block.** Anchors the breakpoint
  to the shared prefix so the varying user question sits after it and each
  request reads the same entry. Tools render before system, so a breakpoint on
  the last system block caches tools + system together.
- **`system` became a list of text blocks.** A bare `system="..."` string has no
  block to hang `cache_control` on.
- **`max_tokens` raised from 1024.** On Claude Opus 5 thinking is ON by default
  (a change from Opus 4.8, where omitting `thinking` meant no thinking), and
  `max_tokens` is a hard cap on thinking PLUS response text. 1024 truncates
  analysis-length output mid-thought with `stop_reason: "max_tokens"`.

## Verification rule (do not skip)

Caching is only real if `response.usage.cache_read_input_tokens` is non-zero on
the SECOND and later requests sharing the prefix. A persistent zero across
repeated identical-prefix calls means a silent invalidator is present — most
often a timestamp, UUID, or per-user id interpolated into the system prompt, a
non-deterministic `json.dumps` (use `sort_keys=True`), or a varying tool list.
Do not add `cache_control` to a prompt whose prefix changes per request: it only
pays the ~1.25x cache-write premium with zero reads.

## Scope boundary — this does NOT override extraction routing

`ai/claude_provider.py` resolves its model through
`_resolve_extraction_model()`, which is threshold-gated and ratified. This
directive governs the CALL SHAPE for Anthropic Messages API work generally; it
is not a licence to hardcode `model="claude-opus-5"` into the extraction path or
to bypass that resolver. Changing extraction model routing remains a
gate-threshold matter and is founder-crucial. The extraction call is also a poor
caching candidate as written: its shared prefix (system prompt + tool schema) is
what would need to clear 512 tokens, and its per-source `text` correctly sits
after any breakpoint.
