"""Every committed source-artifact manifest must match its artifact's bytes.

Born from PR #61 r3: the Boris_Cherny manifest shipped with a false line
count (376 vs the artifact's 375 — a count('\n')+1 off-by-one on a
newline-terminated file) and NO gate caught it; a manifest that is wrong
is worse than no manifest, because it lends false authority to the audit
trail it exists to serve. This gate recomputes every field from the
artifact and fails on any mismatch, so a manifest cannot drift from its
bytes without going red.

Definition pinned here so the manifest, the gate, and a reviewer reading
the git diff can never disagree on semantics: "lines" == the newline
count a git hunk header shows — text.count("\n"), plus one if the file
does not end in a newline. (NOT splitlines(): this artifact contains
unicode line separators that splitlines() also splits on, which would
make the manifest disagree with the diff a reviewer audits — the exact
confusion this gate exists to prevent.)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCES = REPO / "docs" / "research" / "sources"

# Schema (r4 nit): recomputation catches drift in the computed fields, but
# an UNKNOWN extra field could carry a misleading claim no gate validates —
# so fields are allowlisted. REQUIRED are recomputed; DESCRIPTIVE are
# free-text provenance the evaluator reads (their content is prose, not
# recomputable — that boundary is this gate's honest limit).
REQUIRED_FIELDS = {"file", "sha256", "bytes", "lines"}
DESCRIPTIVE_FIELDS = {
    "supplied_by", "original_upload_basename", "what_it_is", "role",
    "storage_note",
}


def manifest_mismatches(manifest: dict, artifact_bytes: bytes) -> list[str]:
    """Field-by-field recomputation; returns human-readable mismatches."""
    problems: list[str] = []
    actual = {
        "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "bytes": len(artifact_bytes),
        "lines": (artifact_bytes.count(b"\n")
                  + (0 if artifact_bytes.endswith(b"\n") else 1)),
    }
    for field, want in actual.items():
        got = manifest.get(field)
        if got != want:
            problems.append(f"{field}: manifest says {got!r}, artifact is {want!r}")
    missing = REQUIRED_FIELDS - manifest.keys()
    if missing:
        problems.append(f"missing required field(s): {sorted(missing)}")
    unknown = manifest.keys() - REQUIRED_FIELDS - DESCRIPTIVE_FIELDS
    if unknown:
        problems.append(
            f"unknown field(s) {sorted(unknown)} — a manifest may not carry "
            "claims outside the allowlisted schema (r4 nit)"
        )
    return problems


def test_every_source_manifest_matches_its_artifact():
    manifests = sorted(SOURCES.glob("*.MANIFEST.json")) if SOURCES.exists() else []
    assert manifests, (
        "no manifests found under docs/research/sources — this gate exists "
        "because at least one committed artifact carries one; an empty scan "
        "would be a gate that cannot fail (it proves nothing)"
    )
    failures: list[str] = []
    for mp in manifests:
        manifest = json.loads(mp.read_text())
        artifact = SOURCES / manifest["file"]
        if not artifact.exists():
            failures.append(f"{mp.name}: names missing artifact {manifest['file']}")
            continue
        for problem in manifest_mismatches(manifest, artifact.read_bytes()):
            failures.append(f"{mp.name}: {problem}")
    assert not failures, "manifest/artifact drift:\n" + "\n".join(failures)


def test_gate_goes_red_on_the_r3_defect_shape():
    # The exact shipped defect: newline-terminated 3-line content declared
    # as 4 lines by a count('\n')+1 formula.
    content = b"line1\nline2\nline3\n"
    bad = {
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "lines": content.decode().count("\n") + 1,  # the off-by-one
    }
    problems = manifest_mismatches(bad, content)
    assert problems and problems[0].startswith("lines:"), problems


def test_gate_goes_red_on_content_swap():
    content = b"real bytes\n"
    m = {
        "sha256": hashlib.sha256(b"other bytes\n").hexdigest(),
        "bytes": len(content),
        "lines": 1,
    }
    assert any(p.startswith("sha256:") for p in manifest_mismatches(m, content))


def test_gate_goes_red_on_unknown_extra_field():
    content = b"x\n"
    m = {
        "file": "x.md",
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": 2,
        "lines": 1,
        "verified_by_founder": True,  # unvalidated claim smuggled as a field
    }
    assert any("unknown field" in p for p in manifest_mismatches(m, content))
