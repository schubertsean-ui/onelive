#!/usr/bin/env python3
"""Check that the founder-facing console links in docs/DEPLOY.md resolve.

Founder directive 2026-07-26: *"Always give me specific and accurate and working
links (it gets me where its supposed to)."* The links live in `docs/DEPLOY.md`
§"The console links". Writing them down was step one; this is the part that
notices when one goes wrong.

**What this can and cannot prove, stated up front because the distinction is the
whole design.** These are dashboard URLs behind authentication. An anonymous
request to a private GitHub settings page returns 404 whether or not the path is
right, and providers redirect to a login instead of answering. So a naive
"expect 200" checker would be a false-confidence gate — green on nothing.

What it CAN prove, and does:

1. **The host resolves and serves HTTPS.** A typo in a hostname, a dead provider
   or a renamed domain is caught. This is a real class of breakage.
2. **The path is not a 404 from a host that answers anonymously** — for pages
   where a wrong path 404s but a right one redirects to a login, that difference
   is real signal and is reported as such.
3. **Anything requiring auth is reported UNVERIFIABLE, never PASS.** A check that
   cannot see the answer must not look like one that did (`CLAUDE.md`: "we failed"
   must never look identical to "there was nothing to do").

Run from a GitHub runner (open egress) — from an agent sandbox every host is
denied by policy and every row honestly reads BLOCKED.

Exit codes: 0 = nothing is provably broken; 1 = at least one link is provably
broken; 2 = tool error.
"""
from __future__ import annotations

import pathlib
import re
import sys
import urllib.error
import urllib.request

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPLOY_DOC = _REPO_ROOT / "docs" / "DEPLOY.md"
SECTION_HEADING = "## The console links"
TIMEOUT = 20

_URL_RE = re.compile(r"<(https://[^>\s]+)>")

# Statuses that mean "the host answered and the path is fine, but you must log in
# to see it" — expected for every dashboard link here, and NOT a failure.
_AUTH_CODES = frozenset({301, 302, 303, 307, 308, 401, 403})

# Hosts serving PRIVATE resources, where an anonymous 404 means "not visible to
# you", NOT "wrong path". Discovered the hard way: the first real run flagged four
# correct github.com links as BROKEN because this repo is private. Treating that
# 404 as a defect is a false-positive gate — worse than no gate, because it
# trains people to ignore it.
_PRIVATE_404_HOSTS = ("github.com/schubertsean-ui/",)

# github.com/<owner>/<repo>/actions/workflows/<file> — the ONE github.com link
# shape whose target is verifiable offline, because the workflow file is in this
# repo. Checked locally instead of guessed at.
_WORKFLOW_LINK_RE = re.compile(
    r"github\.com/[^/]+/[^/]+/actions/workflows/(?P<file>[A-Za-z0-9_.-]+\.ya?ml)$")


def _local_workflow_check(url: str) -> tuple[str, str] | None:
    """Verify an Actions-workflow link against the file it points at.

    A private repo cannot be probed anonymously, but the workflow file lives
    here, so the link's target IS checkable — and a link to a workflow that does
    not exist is a real defect this would otherwise miss entirely.
    """
    match = _WORKFLOW_LINK_RE.search(url)
    if match is None:
        return None
    path = _REPO_ROOT / ".github" / "workflows" / match.group("file")
    if path.is_file():
        return "PASS", f"workflow file exists at {path.relative_to(_REPO_ROOT)}"
    return "BROKEN", (f".github/workflows/{match.group('file')} does not exist — "
                      f"this link points at nothing")


def urls_in_section(text: str) -> list[str]:
    """Every URL inside the console-links section of DEPLOY.md, in order."""
    start = text.find(SECTION_HEADING)
    if start == -1:
        raise LookupError(
            f"{SECTION_HEADING!r} not found in {DEPLOY_DOC} — the link table moved "
            f"or was renamed; fix this tool in the same change")
    rest = text[start + len(SECTION_HEADING):]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    section = rest[:nxt.start()] if nxt else rest
    seen, out = set(), []
    for url in _URL_RE.findall(section):
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def probe(url: str) -> tuple[str, str]:
    """Return (status, detail). PASS, AUTH, PRIVATE, BLOCKED or BROKEN."""
    local = _local_workflow_check(url)
    if local is not None:
        return local
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "onelive-link-check"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return "PASS", f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in _AUTH_CODES:
            return "AUTH", f"HTTP {exc.code} — host answered, login required"
        if exc.code == 404:
            if any(marker in url for marker in _PRIVATE_404_HOSTS):
                return "PRIVATE", ("HTTP 404 — this repo is PRIVATE, so an "
                                   "anonymous 404 means 'not visible', not 'wrong "
                                   "path'; unverifiable from here")
            return "BROKEN", "HTTP 404 — path not found"
        if exc.code == 405:  # HEAD not allowed is not a broken link
            return "AUTH", "HTTP 405 — HEAD refused, host is alive"
        return "AUTH", f"HTTP {exc.code} — reported, not interpreted"
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        # Egress policy denial vs a genuinely dead host: different findings.
        if "403" in reason or "CONNECT" in reason or "Tunnel" in reason:
            return "BLOCKED", f"egress policy denied this host ({reason})"
        return "BROKEN", f"could not reach host ({reason})"
    except (OSError, ValueError) as exc:  # timeouts, malformed URLs
        return "BROKEN", f"{type(exc).__name__}: {exc}"


def main() -> int:
    if not DEPLOY_DOC.is_file():
        print(f"check_console_links: ERROR — {DEPLOY_DOC} is missing",
              file=sys.stderr)
        return 2
    try:
        urls = urls_in_section(DEPLOY_DOC.read_text(encoding="utf-8"))
    except LookupError as exc:
        print(f"check_console_links: ERROR — {exc}", file=sys.stderr)
        return 2
    if not urls:
        print("check_console_links: ERROR — the console-links section contains no "
              "URLs; refusing to report a clean pass over an empty set",
              file=sys.stderr)
        return 2

    broken, unverifiable = [], []
    for url in urls:
        status, detail = probe(url)
        print(f"{status:9} {url}  ({detail})")
        if status == "BROKEN":
            broken.append(url)
        elif status in ("BLOCKED", "PRIVATE"):
            unverifiable.append(url)

    print()
    if broken:
        print(f"check_console_links: {len(broken)} of {len(urls)} link(s) PROVABLY "
              f"BROKEN — fix docs/DEPLOY.md 'The console links' in this change; the "
              f"next session copies from that table.")
        return 1
    if unverifiable:
        print(f"check_console_links: {len(urls) - len(unverifiable)} of {len(urls)} "
              f"link(s) confirmed reachable; {len(unverifiable)} UNVERIFIABLE and "
              f"NOT counted as passing — either the egress policy denied the host, "
              f"or the target is private so an anonymous 404 proves nothing. "
              f"Reported rather than guessed at.")
        return 0
    print(f"check_console_links: OK — {len(urls)} link(s), none provably broken. "
          f"AUTH rows mean the host answered and a login is required, which is "
          f"expected for a dashboard and is not proof the page is the right one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
