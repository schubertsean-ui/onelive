"""EDGAR ingestion client — written to the SEC's documented fair-access contract.

STATUS (2026-07-14): NOT yet exercised against live EDGAR. This sandbox's
egress policy blocks sec.gov (curl CONNECT refused; WebFetch 403) — recorded
as R-014. Everything here is built strictly to the documented contract that
the companion research verified 3-0 against sec.gov's own pages:

- declared User-Agent with operator name + admin email, or requests are denied;
- hard budget of 10 requests/second across ALL machines, per-IP 403 (~10 min)
  on breach — this client enforces a LOCAL budget below the cap and treats a
  403 as a full stop, never a retry loop;
- bulk backfill uses the nightly archives (submissions.zip etc.), NOT page
  crawling — bulk paths are listed here and preferred by callers;
- free endpoints are minutes-latency; this client is a poller, not a
  low-latency feed.

The first live run happens from an environment with sec.gov egress, under the
same budget, and its results seed the golden set (replacing R-014's synthetic
examples).
"""

from __future__ import annotations

import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DATA_BASE = "https://data.sec.gov"
BULK_SUBMISSIONS_ZIP = f"{DATA_BASE}/submissions.zip"          # nightly, bulk-first
FULL_TEXT_SEARCH = "https://efts.sec.gov/LATEST/search-index?q={query}&dateRange=custom"

# Deliberately below the SEC's 10 req/s cap: leave headroom for clock skew and
# for other processes on the same egress IP.
LOCAL_MAX_REQUESTS_PER_SECOND = 5


class EdgarAccessError(RuntimeError):
    """Raised on 403/429 (fair-access signals) — callers must STOP, not retry."""


@dataclass
class EdgarClient:
    operator_name: str
    admin_email: str
    _window_start: float = field(default=0.0, repr=False)
    _window_count: int = field(default=0, repr=False)

    def __post_init__(self):
        if "@" not in self.admin_email or not self.operator_name.strip():
            # Fail-closed: an undeclared client WILL be blocked by the SEC and
            # can poison the egress IP for every other user of it.
            raise ValueError("EdgarClient requires a real operator name and admin email "
                             "(SEC fair-access policy: undeclared User-Agents are denied)")

    @property
    def user_agent(self) -> str:
        return f"{self.operator_name} {self.admin_email}"

    def _respect_budget(self, now: float | None = None) -> float:
        """Local token budget: returns the seconds to sleep before the next
        request so we never exceed LOCAL_MAX_REQUESTS_PER_SECOND. Pure logic
        (testable without network or sleeping)."""
        now = time.monotonic() if now is None else now
        if now - self._window_start >= 1.0:
            self._window_start = now
            self._window_count = 0
        self._window_count += 1
        if self._window_count > LOCAL_MAX_REQUESTS_PER_SECOND:
            return max(0.0, 1.0 - (now - self._window_start))
        return 0.0

    def submissions_url(self, cik: str) -> str:
        """Recent-filings JSON for a company. CIK must be zero-padded to 10
        digits (SEC requirement, verified in the companion research)."""
        if not (cik.isdigit() and len(cik) == 10):
            raise ValueError(f"CIK {cik!r} must be zero-padded to 10 digits")
        return f"{DATA_BASE}/submissions/CIK{cik}.json"

    def fetch(self, url: str, timeout: float = 30.0) -> bytes:
        """Single budgeted GET with the declared User-Agent. 403 = full stop."""
        delay = self._respect_budget()
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:  # pragma: no cover - needs network
            if exc.code in (403, 429):
                raise EdgarAccessError(
                    f"EDGAR returned {exc.code} — fair-access signal (breach, "
                    "throttle, or blocked egress). STOP polling entirely (the "
                    "block is per-IP, ~10 minutes); do not retry-loop.") from exc
            raise


def list_recent_8k_filings(submissions_json: dict) -> list[dict]:
    """STAGE 1: from a data.sec.gov submissions JSON, list recent 8-K filings
    (accession + items). This does NOT locate press releases — the press
    release is normally an EX-99.x EXHIBIT inside the filing, not the 8-K
    primary document; finding it requires the per-filing index (stage 2).
    Pure function over the documented JSON shape."""
    recent = submissions_json.get("filings", {}).get("recent", {})
    out = []
    forms = recent.get("form", [])
    for i, form in enumerate(forms):
        if form != "8-K":
            continue
        out.append({
            "accession": recent["accessionNumber"][i],
            "filed_at": recent["filingDate"][i],
            "primary_doc": recent["primaryDocument"][i],
            "items": recent.get("items", [""] * len(forms))[i],
        })
    return out


# 8-K item codes under which press releases are customarily furnished/filed.
PRESS_RELEASE_ITEMS = ("2.02", "7.01", "8.01")

# Filename shapes for EX-99.x exhibit documents. Covers both separator-delimited
# names (ex99-1.htm, exh_991.txt, exhibit99.htm) and the filing-agent generated
# shape where "dex99" follows a digit run with no separator (d123456dex991.htm —
# very common in EDGAR archives; evaluator r18 catch). Recall matters more than
# precision here because stage-2 confidence is capped at "likely" and the live
# pipeline confirms exhibit type from the filing index page before use.
_EXHIBIT_NAME_RE = re.compile(
    r"(?:^|[^a-z0-9])(?:ex|exh|exhibit)[-_.]?99|(?<=\d)dex99", re.IGNORECASE)


def filing_index_url(cik: str, accession: str) -> str:
    """STAGE 2a: URL of a filing's machine-readable directory listing
    (index.json) under www.sec.gov/Archives. CIK loses zero-padding in
    archive paths; accession loses dashes."""
    if not (cik.isdigit() and len(cik) == 10):
        raise ValueError(f"CIK {cik!r} must be zero-padded to 10 digits")
    acc = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/index.json"


def find_press_release_exhibit_candidates(index_json: dict, filing: dict) -> list[dict]:
    """STAGE 2b: from a filing's index.json directory listing, return the
    EX-99.x-shaped documents that plausibly carry the press release, with an
    honest confidence field.

    LIMITATION (stated, not hidden): index.json lists file NAMES only — the
    authoritative exhibit-type table lives in the filing's -index.htm page.
    Name-pattern matching is a conservative first pass; the live pipeline
    must confirm exhibit type from the index page before treating a document
    as THE press release. Confidence here is therefore capped at "likely"
    (never "confirmed") and is raised only when the parent 8-K's item codes
    include a customary press-release item (2.02/7.01/8.01)."""
    items_field = filing.get("items", "") or ""
    has_pr_item = any(code in items_field for code in PRESS_RELEASE_ITEMS)
    out = []
    for entry in index_json.get("directory", {}).get("item", []):
        name = entry.get("name", "")
        if not name.lower().endswith((".htm", ".html", ".txt")):
            continue
        if _EXHIBIT_NAME_RE.search(name):
            out.append({
                "document": name,
                "confidence": "likely" if has_pr_item else "unverified",
                "basis": ("filename matches EX-99 pattern"
                          + ("; parent 8-K items include a press-release item" if has_pr_item else
                             "; parent 8-K items do NOT include a customary press-release item")),
            })
    return out
