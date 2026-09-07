"""Identity patterns — which link on a page IS one happening, as DATA.

ONE-LIVE-ENTITY-SPLIT-LAW.md §2 tier 2: "an `href` that matches a **committed
identity pattern** for that host family (data, not a one-off regex in Python)".
This module is the loader and the matcher; the table itself is
`sources/identity_patterns.json`, and a new desk is a new ROW there. There is no
per-host function here, and adding one would be the Chronicle-only branch the
ticket forbids.

Three properties are deliberate:

  * PATH ONLY. A match is tried against the URL's path, never its query. A list
    page and the filter links it prints share one path with different queries
    (`/EventSearch?section=music`), so letting a query confer identity would
    turn a desk's own navigation into happenings.
  * GRADE IS PROVENANCE, NOT PERMISSION. `desk_observed` may be written only
    after a live page carrying the shape was actually read; everything else is
    `fixture_shape`. A `fixture_shape` pattern still splits — refusing to split
    until someone has fetched the page would mean a first read of any new desk
    produces the mash this law exists to stop — but the grade rides along on the
    match so no table can present an unconfirmed shape as an observed one.
  * FAIL LOUDLY. A missing file, an unknown grade, a non-compiling or absurdly
    long regex, or a duplicate pattern_id raises `IdentityPatternError` at load.
    A half-parsed table would silently narrow coverage, which is the one
    direction Coverage Law forbids.

Pure: stdlib only, no network, no DB, no clock, no model.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

#: Where the committed table lives. Callers may override for tests; there is no
#: other knob, and no caller may pass patterns that were not read from a file.
PATTERNS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "sources", "identity_patterns.json",
)

#: The law's two grades, verbatim.
GRADES: Tuple[str, ...] = ("desk_observed", "fixture_shape")

#: A committed pattern is a path shape, not a program. The cap is a blast radius
#: on a data file, not a claim that every shorter regex is safe.
MAX_PATTERN_CHARS = 200


class IdentityPatternError(ValueError):
    """The identity table is missing, malformed, or states something the type
    system does not allow. Always raised — never downgraded to a shorter table.
    """


@dataclass(frozen=True)
class IdentityPattern:
    """One row of the committed table."""

    pattern_id: str
    host_family: str
    path_re: str
    grade: str
    owned: bool
    note: str

    @property
    def rx(self) -> "re.Pattern[str]":
        return _compiled(self.path_re)

    def covers_host(self, host: str) -> bool:
        """True when `host` is this row's host family or a subdomain of it.

        Suffix matching on a DOT boundary, so `do512.com` covers
        `family.do512.com` and `www.do512.com` and never `notdo512.com`.
        """
        host = (host or "").lower().strip().rstrip(".")
        if host.startswith("www."):
            host = host[4:]
        family = self.host_family.lower()
        return host == family or host.endswith("." + family)

    def matches_path(self, path: str) -> bool:
        r"""True when this pattern names the WHOLE path, not a prefix of it.

        A committed pattern names a permalink. `/event/foo-123` is a happening;
        `/event/foo-123/comments`, `/events/2026/9/12/name/tickets` and
        `/e/show-987654/refunds` are SUBPAGES OF one, and a plain `re.search`
        accepts all three — each with a different URL, so each would enter as
        its own identity and publish a duplicate of the same happening
        (evaluator finding, PR #234). So the match must reach the end of the
        path; a trailing slash is the same address and is trimmed first.

        Every match position is tried, not just the leftmost: a leftmost match
        that stops short must not veto a later one that does name the whole
        path. Anchoring here rather than in the table keeps the committed rows
        readable (`/event/[^/]+-\d+`, exactly as the law writes it) and applies
        the rule to every row that is ever added.
        """
        trimmed = (path or "").rstrip("/")
        if not trimmed:
            return False
        return any(m.end() == len(trimmed) for m in self.rx.finditer(trimmed))


_COMPILED: Dict[str, "re.Pattern[str]"] = {}


def _compiled(path_re: str) -> "re.Pattern[str]":
    rx = _COMPILED.get(path_re)
    if rx is None:
        rx = re.compile(path_re)
        _COMPILED[path_re] = rx
    return rx


def _require(obj: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in obj:
        raise IdentityPatternError(f"{where}: missing required key {key!r}")
    return obj[key]


def _pattern_from(raw: Any, *, index: int) -> IdentityPattern:
    where = f"identity pattern[{index}]"
    if not isinstance(raw, dict):
        raise IdentityPatternError(
            f"{where}: each pattern must be an object, got {type(raw).__name__}")
    pattern_id = _require(raw, "pattern_id", where)
    if not isinstance(pattern_id, str) or not pattern_id.strip():
        raise IdentityPatternError(f"{where}: pattern_id must be a non-empty string")
    where = f"identity pattern {pattern_id!r}"

    host_family = _require(raw, "host_family", where)
    if not isinstance(host_family, str) or not host_family.strip() or "/" in host_family:
        raise IdentityPatternError(
            f"{where}: host_family must be a bare host, got {host_family!r}")
    path_re = _require(raw, "path_re", where)
    if not isinstance(path_re, str) or not path_re.strip():
        raise IdentityPatternError(f"{where}: path_re must be a non-empty string")
    if len(path_re) > MAX_PATTERN_CHARS:
        raise IdentityPatternError(
            f"{where}: path_re is {len(path_re)} chars, over the "
            f"{MAX_PATTERN_CHARS}-char cap for a committed path shape")
    try:
        _compiled(path_re)
    except re.error as exc:
        raise IdentityPatternError(f"{where}: path_re does not compile: {exc}") from exc
    grade = _require(raw, "grade", where)
    if grade not in GRADES:
        raise IdentityPatternError(f"{where}: grade {grade!r} is not one of {GRADES}")
    owned = _require(raw, "owned", where)
    if not isinstance(owned, bool):
        raise IdentityPatternError(f"{where}: owned must be true or false, got {owned!r}")
    note = raw.get("note") or ""
    if not isinstance(note, str):
        raise IdentityPatternError(f"{where}: note must be a string when present")
    return IdentityPattern(
        pattern_id=pattern_id, host_family=host_family.lower().strip(),
        path_re=path_re, grade=grade, owned=owned, note=note,
    )


def load_patterns(path: Optional[str] = None) -> Tuple[IdentityPattern, ...]:
    """Read and validate the committed identity table. Raises on anything it
    cannot vouch for — there is no partial table.
    """
    target = path or PATTERNS_PATH
    try:
        with open(target, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise IdentityPatternError(
            f"no identity pattern table at {target}. Without it every list page "
            f"falls to a committed desk selector or to `unsplit` — never to a "
            f"mashed row (ONE-LIVE-ENTITY-SPLIT-LAW.md §2)") from exc
    except (OSError, ValueError) as exc:
        raise IdentityPatternError(f"identity pattern table {target} is unreadable: {exc}") from exc
    if not isinstance(raw, dict):
        raise IdentityPatternError(f"{target}: top level must be an object")
    rows = _require(raw, "patterns", target)
    if not isinstance(rows, list):
        raise IdentityPatternError(f"{target}: 'patterns' must be a list")
    out = tuple(_pattern_from(r, index=i) for i, r in enumerate(rows))
    seen: Dict[str, int] = {}
    for i, pattern in enumerate(out):
        if pattern.pattern_id in seen:
            raise IdentityPatternError(
                f"{target}: duplicate pattern_id {pattern.pattern_id!r} "
                f"(patterns {seen[pattern.pattern_id]} and {i})")
        seen[pattern.pattern_id] = i
    return out


def patterns_for_url(url: str, patterns: Sequence[IdentityPattern]) -> Tuple[IdentityPattern, ...]:
    """The rows whose host family covers this URL's host, in table order."""
    host = urlsplit(url or "").hostname or ""
    return tuple(p for p in patterns if p.covers_host(host))


def match(url: str, patterns: Iterable[IdentityPattern]) -> Optional[IdentityPattern]:
    """The first committed pattern this URL's host and WHOLE PATH satisfy, else None.

    None is the honest answer for every other link on the page — a nav item, a
    category filter, a ticket vendor, the desk's own logo, and an event's own
    subpages (`/comments`, `/tickets`). It is what keeps tier 2 from turning a
    list page's furniture, or one happening's other pages, into happenings.
    """
    parts = urlsplit(url or "")
    if parts.scheme not in ("http", "https"):
        return None
    host = parts.hostname or ""
    for pattern in patterns:
        if pattern.covers_host(host) and pattern.matches_path(parts.path):
            return pattern
    return None
