"""Input-quality / context-hygiene sensor — the Sensors layer of the Harness.

Gates fetch -> extract. An AI extraction call is expensive (money, latency,
and it produces an auditable candidate row even on failure per
worker/ai_extract.py's "never silently drop" rule) so obviously-junk input
(empty pages, truncated fragments, binary blobs, error/placeholder pages)
should never reach it in the first place. Rejecting junk here is a *normal*
pipeline outcome, not a failure: it means the source had nothing usable this
run, not that something broke.

Deliberately does NOT import worker.promote or worker.gating — this module
only inspects raw fetched text, it has no opinion on corroboration or
publishing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

MIN_TEXT_LENGTH = 40

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

    return SensorReading(ok=True, reason="input passes hygiene checks", signals=signals)
