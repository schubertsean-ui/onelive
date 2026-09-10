"""Place image + venue site from a page the union already fetched.

Hole-fill only. Never invent. Own-domain og:image via first_party.
JSON-LD image and location.url count as the page stating those fields.
Stored on the row so the next page load does not hunt.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

from worker.enrich.first_party import extract_first_party


def _http(url: Optional[str]) -> Optional[str]:
    raw = (url or "").strip()
    if not raw:
        return None
    p = urlparse(raw)
    if p.scheme not in ("http", "https"):
        return None
    return raw


def _first_url(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return _http(value)
    if isinstance(value, dict):
        return _http(value.get("url") or value.get("contentUrl") or value.get("@id"))
    if isinstance(value, list):
        for item in value:
            found = _first_url(item)
            if found:
                return found
    return None


def _location_site(loc: Any) -> Optional[str]:
    if isinstance(loc, dict):
        return _first_url(loc.get("url") or loc.get("sameAs"))
    if isinstance(loc, list):
        for item in loc:
            found = _location_site(item)
            if found:
                return found
    return None


def image_and_site(
    html: str,
    page_url: str,
    ld_event: Optional[dict] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return (image_url, venue_url) the page itself stated. Either may be None."""
    image = None
    site = None
    if isinstance(ld_event, dict):
        image = _first_url(ld_event.get("image"))
        site = _location_site(ld_event.get("location"))
    try:
        fp = extract_first_party(html or "", page_url)
    except Exception:
        fp = None
    if not image and fp is not None:
        image = _http(fp.og_image)
        if image and page_url:
            image = _http(urljoin(page_url, image)) or image
    return image, site
