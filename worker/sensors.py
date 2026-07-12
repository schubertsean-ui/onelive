"""Input-quality / context-hygiene sensor — the Sensors layer of the Harness.

Gates fetch -> extract. Two distinct jobs, both first-class:

1. Cost/hygiene: an AI extraction call is expensive (money, latency, and it
   produces an auditable candidate row even on failure per ai_extract's "never
   silently drop" rule) so obviously-junk input (empty, too-short, binary,
   error pages) should never reach it.

2. Class-D defense (the load-bearing one): per Wu (2026)'s silent-failure
   taxonomy, the dominant production failure mode is NOT a weak model — it is
   *polluted input laundered into a fluent, confident, wrong output*. A
   truncated page, mojibake from a charset mismatch, a boilerplate-only
   nav/cookie shell, or a page carrying prompt-injection text are all inputs
   that an LLM will happily "extract an event" from by fabricating the missing
   parts. Catching these BEFORE extraction is cheaper and safer than trying to
   catch the fabricated output afterwards. This is why the sensor tags input
   quality as provenance (signals), not just returns a boolean: a candidate's
   trustworthiness depends on the quality of the input it came from.

Rejecting input here is a *normal* pipeline outcome, not a failure: the source
had nothing usable this run, not that something broke.

Deliberately does NOT import worker.promote or worker.gating — this module
only inspects raw fetched text, it has no opinion on corroboration or
publishing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

MIN_TEXT_LENGTH = 40

# A page that ends mid-token (no sentence/element terminator in its final run
# of characters) is likely a truncated fetch. We only flag this when the tail
# is also non-trivial in length, so a short-but-complete blurb isn't caught.
_TRUNCATION_TAIL_WINDOW = 80
_TRUNCATION_TERMINATORS = ".!?)]}>\"'”’"

# Mojibake / encoding-corruption markers: the U+FFFD replacement char plus the
# classic sequences seen when UTF-8 bytes are misdecoded and then rendered via
# Windows-1252 (the overwhelmingly common real-world form). Examples: a UTF-8
# right-single-quote (U+2019) misdecoded shows as "â€™"; an accented é shows as
# "Ã©"; a non-breaking space shows as "Â ". A non-trivial density of these
# means the bytes were decoded with the wrong charset and the "text" is corrupt.
_MOJIBAKE_MARKERS = (
    "\ufffd",           # U+FFFD replacement character
    "\u00e2\u20ac\u2122",  # â€™  -> right single quote
    "\u00e2\u20ac\u009c",  # â€  -> left double quote (partial)
    "\u00e2\u20ac",        # â€    -> dash/quote family lead-in
    "\u00c3\u00a9",        # Ã©   -> é
    "\u00c3\u00a8",        # Ã¨   -> è
    "\u00c3\u00a2",        # Ã¢   -> â
    "\u00c2\u00a0",        # Â    -> non-breaking space
)

# Boilerplate-only markers: if after removing these the remaining text is
# negligible, the page is a nav/cookie/consent shell with no real content.
_BOILERPLATE_MARKERS = (
    "accept all cookies",
    "we use cookies",
    "cookie policy",
    "privacy policy",
    "terms of service",
    "skip to main content",
    "enable javascript",
    "your browser is not supported",
)

# Prompt-injection markers: fetched *source* content must never be able to
# steer the extractor. Text that tries to issue instructions to the model is a
# Class-D adversarial input and is escalated out of the auto path, not fed in.
_INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "you are now",
    "system prompt",
    "<|im_start|>",
    "[[system]]",
)

# Case-insensitive substrings that mark a page as an error/placeholder page
# rather than real content, seen across common site failure modes.
_ERROR_PAGE_MARKERS = (
    "404 not found",
    "403 forbidden",
    "page not found",
    "access denied",
    "this page isn't working",
    "service unavailable",
    "under maintenance",
    "just a moment...",  # common bot-check interstitial text
)

# Content-type prefixes that indicate non-text payloads (images, video,
# generic binary octet streams) which extraction cannot use regardless of
# apparent decodability.
_BINARY_CONTENT_TYPE_PREFIXES = ("image/", "video/", "audio/", "application/octet-stream")

# Above this fraction of mojibake markers, the text is treated as charset-
# corrupt. Kept low: real content essentially never contains these sequences.
MOJIBAKE_MAX_RATIO = 0.005


@dataclass
class SensorReading:
    ok: bool
    reason: str
    signals: Dict[str, Any] = field(default_factory=dict)


def _looks_binary(text: str) -> bool:
    """Heuristic: real listing/event text is printable. A high proportion of
    non-printable characters (or an embedded NUL byte, impossible in valid
    text) indicates a binary blob that decoded without raising but is not
    actually text.
    """
    if "\x00" in text:
        return True
    if not text:
        return False
    non_printable = sum(1 for ch in text if not (ch.isprintable() or ch in "\n\r\t"))
    return (non_printable / len(text)) > 0.05


def _looks_truncated(text: str) -> bool:
    """True if the fetched text appears cut off mid-content. A complete page
    ends on a terminator (sentence punctuation or a closing bracket/quote); a
    fetch that was truncated by a byte cap or a dropped connection ends mid-
    word. We require the text to be reasonably long first, so a short complete
    blurb (which may legitimately end without punctuation) is never flagged —
    truncation is only a meaningful signal on content that claims to be full.
    """
    if len(text) < _TRUNCATION_TAIL_WINDOW * 2:
        return False
    tail = text.rstrip()
    if not tail:
        return False
    return tail[-1] not in _TRUNCATION_TERMINATORS


def _mojibake_ratio(text: str) -> float:
    """Fraction of the text made up of known encoding-corruption markers. A
    non-trivial ratio means the bytes were decoded with the wrong charset and
    the resulting 'text' is corrupt — exactly the kind of garbled input an LLM
    will confidently paper over.
    """
    if not text:
        return 0.0
    hits = sum(text.count(m) for m in _MOJIBAKE_MARKERS)
    return hits / max(len(text), 1)


def _is_boilerplate_only(text: str) -> bool:
    """True if, after stripping known nav/cookie/consent boilerplate, almost no
    real content remains — a chrome-only shell the fetcher captured before the
    real content loaded (or that requires JS the fetcher doesn't run).
    """
    lowered = text.lower()
    residual = lowered
    matched_any = False
    for marker in _BOILERPLATE_MARKERS:
        if marker in residual:
            matched_any = True
            residual = residual.replace(marker, " ")
    if not matched_any:
        return False
    # Collapse whitespace and see how much substantive text is left.
    residual_compact = re.sub(r"\s+", " ", residual).strip()
    return len(residual_compact) < MIN_TEXT_LENGTH


def _injection_marker(text: str) -> Optional[str]:
    """Return the first prompt-injection marker found in the source text, or
    None. Fetched source content trying to issue instructions to the model is
    an adversarial Class-D input; it must be kept out of the auto-extract path.
    """
    lowered = text.lower()
    for marker in _INJECTION_MARKERS:
        if marker in lowered:
            return marker
    return None


def assess_input(*, text: Optional[str], content_type: Optional[str] = None) -> SensorReading:
    """Deterministic input-quality check. All checks are cheap/local — no
    network, no DB, no AI call — by design, since this function's entire
    purpose is to run BEFORE the AI call.
    """
    signals: Dict[str, Any] = {
        "content_type": content_type,
        "raw_length": len(text) if text else 0,
    }

    if text is None:
        return SensorReading(ok=False, reason="input text is None", signals=signals)

    stripped = text.strip()
    signals["stripped_length"] = len(stripped)

    if not stripped:
        return SensorReading(ok=False, reason="input is empty after stripping whitespace", signals=signals)

    if content_type and any(content_type.lower().startswith(p) for p in _BINARY_CONTENT_TYPE_PREFIXES):
        return SensorReading(
            ok=False,
            reason=f"content_type {content_type!r} indicates binary, not text",
            signals=signals,
        )

    if _looks_binary(stripped):
        return SensorReading(ok=False, reason="input looks like binary data, not text", signals=signals)

    if len(stripped) < MIN_TEXT_LENGTH:
        return SensorReading(
            ok=False,
            reason=f"input too short ({len(stripped)} chars; need >= {MIN_TEXT_LENGTH})",
            signals=signals,
        )

    lowered = stripped.lower()
    for marker in _ERROR_PAGE_MARKERS:
        if marker in lowered:
            return SensorReading(
                ok=False,
                reason=f"input looks like an error/placeholder page (matched {marker!r})",
                signals=signals,
            )

    # --- Class-D context-hygiene checks (fabrication-from-polluted-input) ---
    # These run after the cheap structural checks above. Each records its
    # measured signal so a downstream reviewer can see WHY input was rejected
    # (input-quality provenance), not just that it was.

    # Prompt injection: adversarial source text must never reach the extractor.
    injection = _injection_marker(stripped)
    signals["injection_marker"] = injection
    if injection is not None:
        return SensorReading(
            ok=False,
            reason=f"input contains a prompt-injection marker ({injection!r}); refusing to feed to extractor",
            signals=signals,
        )

    # Mojibake / charset corruption.
    mojibake = _mojibake_ratio(stripped)
    signals["mojibake_ratio"] = mojibake
    if mojibake > MOJIBAKE_MAX_RATIO:
        return SensorReading(
            ok=False,
            reason=f"input looks charset-corrupt (mojibake ratio {mojibake:.4f} > {MOJIBAKE_MAX_RATIO})",
            signals=signals,
        )

    # Boilerplate-only shell (nav/cookie/consent with no real content).
    boilerplate_only = _is_boilerplate_only(stripped)
    signals["boilerplate_only"] = boilerplate_only
    if boilerplate_only:
        return SensorReading(
            ok=False,
            reason="input is boilerplate-only (nav/cookie/consent shell, no substantive content)",
            signals=signals,
        )

    # Truncated fetch (ends mid-content).
    truncated = _looks_truncated(stripped)
    signals["looks_truncated"] = truncated
    if truncated:
        return SensorReading(
            ok=False,
            reason="input appears truncated (ends mid-content without a terminator); likely an incomplete fetch",
            signals=signals,
        )

    return SensorReading(ok=True, reason="input passes hygiene checks", signals=signals)
