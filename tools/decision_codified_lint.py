#!/usr/bin/env python3
"""Every decision record must name what carries it in the repo.

Founder directive 2026-07-26: *"confirm once a decision is made it has been
codified in the code and not left in the session."* A decision that lives only
in a chat reply did not happen — the next session starts from disk and will not
know it exists. Prose in a decision record is better than chat, but prose alone
still does not change behaviour (`docs/HOW_WE_WORK.md` §10, "a prose-only lesson
is an open defect").

So each file in ``docs/memory/decisions/`` must carry a line beginning
``**Codified by:**`` naming the commit, file, gate or RECORD row that implements
it. Staged work is a legitimate answer — cite the ``R-###`` row and its trigger.
"Nothing yet" is also legitimate, stated explicitly, because an honest gap is
findable and a silent one is not.

Exit codes (``tools/README.md`` convention): 0 clean, 1 findings, 2 tool error.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DECISIONS_DIR = _REPO_ROOT / "docs" / "memory" / "decisions"

# Must START the line: a mention buried mid-paragraph is prose, not a field a
# reader or a machine can find.
_CODIFIED_RE = re.compile(r"^\*\*Codified by:\*\*\s*(\S.*)$", re.MULTILINE)

# CITATION SHAPES, and every one of them is then CHECKED AGAINST REALITY.
#
# Matching a shape was all this did, so any `.md`-looking string passed even when
# the file did not exist, any `R-###` passed with no such Record row, any 7 hex
# characters passed as a "commit" without asking git, and a bare `NOTHING YET`
# passed with none of the reason and trigger it promises. A gate that certifies a
# decision as codified when nothing in the repo carries it is worse than no gate —
# `CLASS:codification-gate-nonbinding`, PR #76 r2, and it is the identical defect
# the escape-closure gate had: a plausible-looking string is not evidence.
_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|ts|tsx|yml|yaml|sql|md|sh)\b")
# `tools/validate` is the most important gate file in the repo and has NO
# extension, so an extension-anchored pattern alone would reject the single most
# likely citation. Any backticked repo path counts, extension or not, provided it
# resolves — which is the actual rule.
_BACKTICKED_RE = re.compile(r"`([A-Za-z0-9_./-]+)`")
_ROW_RE = re.compile(r"\bR-(\d{3})\b")
_SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")
_NOTHING_YET_RE = re.compile(r"NOTHING YET\b")


def _resolves_inside(candidate: str) -> bool:
    """An existing file INSIDE the repo. Absolute paths and `..` escapes rejected:
    `Path(root) / "/etc/x.md"` discards the root, so an absolute path to any host
    file would otherwise count as a repo citation."""
    if candidate.startswith("/"):
        return False
    try:
        target = (_REPO_ROOT / candidate).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    return target.is_file() and _REPO_ROOT in target.parents


def _record_row_exists(number: str) -> bool:
    try:
        text = (_REPO_ROOT / "docs" / "RECORD.md").read_text(encoding="utf-8")
    except OSError:
        return False
    return f"| R-{number} |" in text


def _commit_exists(sha: str) -> bool:
    """Ask git. A hex-looking string is not a commit until git says so."""
    try:
        proc = subprocess.run(["git", "-C", str(_REPO_ROOT), "cat-file", "-e",
                               f"{sha}^{{commit}}"],
                              capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def cited_mechanisms(value: str) -> list[str]:
    """The citations in a `Codified by:` value that RESOLVE to something real.

    Empty means the line names nothing checkable — which is the finding.
    `NOTHING YET` is honest and accepted, but only WITH its promised reason and
    trigger: the bare token was the escape hatch that made this gate optional.
    """
    found: list[str] = []
    found += [c for c in _PATH_RE.findall(value) if _resolves_inside(c)]
    found += [c for c in _BACKTICKED_RE.findall(value)
              if c not in found and _resolves_inside(c)]
    found += [f"R-{n}" for n in _ROW_RE.findall(value) if _record_row_exists(n)]
    # A sha only counts if it is not part of a path already credited above.
    for sha in _SHA_RE.findall(value):
        if sha not in "".join(found) and _commit_exists(sha):
            found.append(sha)
    if _NOTHING_YET_RE.search(value):
        # It must carry a reason AND a trigger, or "NOTHING YET" is just a way to
        # pass. Length is the crude proxy for "there is an explanation here".
        tail = _NOTHING_YET_RE.sub("", value).strip(" —-:.")
        if len(tail) >= 30:
            found.append("NOTHING YET (with reason and trigger)")
    return found


def _display(path: pathlib.Path) -> str:
    """Repo-relative when possible, absolute otherwise.

    `relative_to` RAISES for anything outside the repo root, which would crash
    the tool on a path it was merely asked to check rather than reporting a
    finding about it. A checker that dies on unexpected input is worse than one
    that prints an ugly path.
    """
    try:
        return str(path.relative_to(_REPO_ROOT))
    except ValueError:
        return str(path)


def audit(paths: list[pathlib.Path]) -> list[str]:
    """Return one finding per decision record that fails the rule."""
    findings: list[str] = []
    for path in sorted(paths):
        rel = _display(path)
        text = path.read_text(encoding="utf-8")
        match = _CODIFIED_RE.search(text)
        if match is None:
            findings.append(
                f"{rel}: no '**Codified by:**' line — name the commit, file, gate "
                f"or R-### row that carries this decision in the repo, or write "
                f"'**Codified by:** NOTHING YET — <why, and the trigger>'. "
                f"CLAUDE.md prime directive 6.")
            continue
        value = match.group(1).strip()
        if not cited_mechanisms(value):
            findings.append(
                f"{rel}: '**Codified by:**' names nothing that EXISTS ({value!r}) — "
                f"a plausible-looking string is not evidence. Cite a file path that "
                f"is in this repo, an R-### row that is in docs/RECORD.md, a commit "
                f"git can resolve, or 'NOTHING YET' WITH its reason and trigger.")
    return findings


def main() -> int:
    if not DECISIONS_DIR.is_dir():
        print(f"decision_codified_lint: ERROR — {DECISIONS_DIR} is not a directory",
              file=sys.stderr)
        return 2
    records = [p for p in DECISIONS_DIR.glob("*.md") if p.name != "README.md"]
    if not records:
        # A checker that passes by finding nothing proves nothing.
        print("decision_codified_lint: ERROR — no decision records found; refusing "
              "to report a clean pass over an empty set", file=sys.stderr)
        return 2
    findings = audit(records)
    for finding in findings:
        print(finding)
    if findings:
        print(f"decision_codified_lint: {len(findings)} violation(s) of "
              f"{len(records)} record(s) — a decision only in chat did not happen.")
        return 1
    print(f"decision_codified_lint: OK — {len(records)} decision record(s), "
          f"every one names what carries it in the repo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
