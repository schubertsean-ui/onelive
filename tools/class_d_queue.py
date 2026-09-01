"""Class D claim queue — the document that exists so we never scrape a wall.

ONE-LIVE-COVERAGE-LAW.md classifies a login / paywall / bot-walled source as
class D and gives exactly one instruction: "do not fetch; open claim/submit
path". This module is that instruction made mechanical. It writes
`docs/CLASS_D_CLAIM_QUEUE.md` — for every class-D source: its name, its url,
WHY it is D, and a suggested ICS / CSV / email path a human can actually walk.

Two ways a source lands here, and the queue records which:

  * DECLARED — the catalog itself says the source needs a credential, a
    partnership, a human step, or forbids automated ingest. Known before any
    network contact (worker.sourcing.source_class.classify_entry).
  * OBSERVED — the source answered our one polite knock with a wall (401/402/
    403/429, or a redirect to a sign-in page). Learned at fetch time
    (worker.sourcing.source_class.demote_on_response), recorded here, and never
    knocked on again by that run.

The suggestion is deliberately a SUGGESTION, not an automated action: opening a
claim path means a person contacting a venue, and nothing in this repo may send
that mail on its own. What the tool guarantees is that the ask is written down
with everything the person needs, so a wall becomes a task instead of silently
becoming missing coverage.

Regenerating is idempotent: the file is rewritten whole from the catalog plus
whatever observed demotions are handed in, so a stale row cannot outlive the
data that produced it. Pure/deterministic apart from the two file operations →
unit-testable.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.sourcing.source_class import (  # noqa: E402
    CLASS_D_CLOSED_DOOR, CLASS_E_FIRST_PARTY, ClassVerdict, classify_entry,
)

log = logging.getLogger("class_d_queue")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CATALOG = os.path.join(REPO_ROOT, "sources", "master_sources_catalog_120.json")
DEFAULT_QUEUE = os.path.join(REPO_ROOT, "docs", "CLASS_D_CLAIM_QUEUE.md")

ORIGIN_DECLARED = "declared"
ORIGIN_OBSERVED = "observed"


@dataclass(frozen=True)
class QueueRow:
    """One class-D source awaiting a human-opened claim path."""

    source_id: str
    name: str
    url: str
    why: str
    origin: str
    suggested_path: str


# --- Suggested claim paths ----------------------------------------------------
#
# Mapped from the REASON the source is closed, because the reason determines
# what a person should actually ask for. A venue behind a bot wall wants a
# different ask ("publish your .ics") than an OAuth API ("register the app").

def suggest_path(entry: Dict[str, Any], verdict: ClassVerdict) -> str:
    """Plain-language next step for a human, chosen from why the door is shut."""
    reason = verdict.reason.lower()
    name = str(entry.get("name") or entry.get("id") or "the source")

    if "forbids automated ingest" in reason:
        return (
            f"Do not fetch. Ask {name} in writing for an explicit feed permission "
            "or a first-party export (ICS or CSV); if they decline, the source "
            "stays out of the catalog."
        )
    if "no base_url" in reason:
        return (
            f"Find and record {name}'s public calendar URL in the catalog entry, "
            "then re-run classification — it may well be class A or B."
        )
    if "oauth" in reason or "api_key" in reason:
        return (
            f"Register a developer application with {name} and store the "
            "credential as a repo secret (founder-crucial: credential minting). "
            "Until then, ask for a public ICS/RSS export instead."
        )
    if "partnership" in reason or "partner_preferred" in reason:
        return (
            f"Request a partner/data-sharing agreement with {name}; ask "
            "specifically whether they can expose a public ICS or a nightly CSV "
            "drop, which needs no partnership at all."
        )
    if "http 4" in reason or "http 429" in reason or "refused an unauthenticated" in reason:
        return (
            f"Email {name} and ask them to publish (or point us at) a public "
            "iCalendar/.ics feed for their events — their site refuses "
            "unauthenticated reads, and an .ics costs them nothing."
        )
    if "login wall" in reason or "sign-in" in reason:
        return (
            f"Email {name} for a first-party export: an .ics subscription URL, a "
            "CSV drop, or an email opt-in that forwards their event "
            "announcements. Never attempt the login."
        )
    return (
        f"Contact {name} for a first-party feed (ICS preferred, CSV acceptable, "
        "email opt-in as a fallback)."
    )


def rows_from_catalog(catalog: Iterable[Dict[str, Any]]) -> List[QueueRow]:
    """Every DECLARED class-D entry in the catalog, in catalog order."""
    rows: List[QueueRow] = []
    for entry in catalog:
        verdict = classify_entry(entry)
        if verdict.source_class != CLASS_D_CLOSED_DOOR:
            continue
        rows.append(QueueRow(
            source_id=str(entry.get("id") or ""),
            name=str(entry.get("name") or entry.get("id") or "(unnamed)"),
            url=str(entry.get("base_url") or ""),
            why=verdict.reason,
            origin=ORIGIN_DECLARED,
            suggested_path=suggest_path(entry, verdict),
        ))
    return rows


def rows_from_first_party(catalog: Iterable[Dict[str, Any]]) -> List[QueueRow]:
    """Class-E entries — not class D, but they need the same human step.

    Listed in a clearly separate appendix so one document answers "which
    sources need a person to open a door?" without blurring Coverage Law's
    distinction between a wall (D) and an invitation (E).
    """
    rows: List[QueueRow] = []
    for entry in catalog:
        verdict = classify_entry(entry)
        if verdict.source_class != CLASS_E_FIRST_PARTY:
            continue
        rows.append(QueueRow(
            source_id=str(entry.get("id") or ""),
            name=str(entry.get("name") or entry.get("id") or "(unnamed)"),
            url=str(entry.get("base_url") or ""),
            why=verdict.reason,
            origin=ORIGIN_DECLARED,
            suggested_path=suggest_path(entry, verdict),
        ))
    return rows


def _escape_cell(value: str) -> str:
    """Make a value safe inside a markdown table cell."""
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _table(rows: List[QueueRow], *, why_header: str = "why class D") -> List[str]:
    out = [
        f"| source | url | {why_header} | found | suggested claim path |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        url = f"<{r.url}>" if r.url else "_(none recorded)_"
        out.append(
            f"| {_escape_cell(r.name)} | {url} | {_escape_cell(r.why)} | "
            f"{r.origin} | {_escape_cell(r.suggested_path)} |"
        )
    return out


def render_queue(
    declared: List[QueueRow],
    observed: List[QueueRow],
    first_party: List[QueueRow],
    *,
    catalog_name: str,
) -> str:
    """Render the whole queue document. Deterministic — no timestamps.

    No generation timestamp on purpose: this file is regenerated on every run,
    and a moving date would make every run a diff even when the queue is
    unchanged, which trains a reader to stop reading it.
    """
    lines = [
        "# Class D claim queue — sources we must NOT fetch",
        "",
        "Generated by `python tools/class_d_queue.py` from "
        f"`sources/{catalog_name}` plus any walls observed at fetch time. "
        "Do not hand-edit: re-run the tool.",
        "",
        "**Class D** (ONE-LIVE-COVERAGE-LAW.md) is a closed door — login, "
        "paywall, or bot wall. Coverage Law's rule is absolute and this file is "
        "how we obey it: **do not fetch; open a claim/submit path instead.** "
        "Nothing here is scraped, retried, or worked around.",
        "",
        "`found` is how we learned the door was shut:",
        "",
        "- **declared** — the source catalog itself says so (credential, "
        "partnership, manual step, or an explicit no-automated-ingest rule). "
        "Known before any network contact.",
        "- **observed** — the source answered one polite unauthenticated request "
        "with a wall (401/402/403/407/429, or a redirect to sign-in). We knocked "
        "once, recorded it, and stopped.",
        "",
        "The suggested path is a task for a person. No tool in this repo sends "
        "these asks automatically.",
        "",
        f"## Class D — declared by the catalog ({len(declared)})",
        "",
    ]
    lines += _table(declared) if declared else ["_None._"]
    lines += [
        "",
        f"## Class D — observed at fetch time ({len(observed)})",
        "",
    ]
    if observed:
        lines += _table(observed)
    else:
        lines += [
            "_None recorded yet. A run that meets a wall appends its row here._",
        ]
    lines += [
        "",
        f"## Appendix — class E, first-party opt-in ({len(first_party)})",
        "",
        "Not class D: these are invitations, not walls. They need the same thing "
        "from a human (someone must opt in or claim the listing), so they are "
        "listed here to keep the claim work in one document.",
        "",
    ]
    if first_party:
        lines += _table(first_party, why_header="why class E")
    else:
        lines += ["_None._"]
    lines.append("")
    return "\n".join(lines)


def load_catalog(path: str) -> List[Dict[str, Any]]:
    """Read the source catalog. Fails LOUD — a missing catalog is never an
    empty queue, which would read as "no walls" and quietly authorize fetching."""
    with open(path, encoding="utf-8") as handle:
        catalog = json.load(handle)
    if not isinstance(catalog, list):
        raise ValueError(f"{path}: expected a JSON list of source entries")
    return catalog


def write_queue(
    catalog_path: str = DEFAULT_CATALOG,
    queue_path: str = DEFAULT_QUEUE,
    observed: Optional[List[QueueRow]] = None,
) -> int:
    """Regenerate the queue file. Returns the number of class-D rows written."""
    catalog = load_catalog(catalog_path)
    declared = rows_from_catalog(catalog)
    first_party = rows_from_first_party(catalog)
    observed_rows = list(observed or [])
    text = render_queue(
        declared, observed_rows, first_party,
        catalog_name=os.path.basename(catalog_path),
    )
    os.makedirs(os.path.dirname(queue_path), exist_ok=True)
    with open(queue_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return len(declared) + len(observed_rows)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--out", default=DEFAULT_QUEUE)
    args = parser.parse_args(argv)

    written = write_queue(args.catalog, args.out)
    log.info("class D claim queue: %d row(s) -> %s",
             written, os.path.relpath(args.out, REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
