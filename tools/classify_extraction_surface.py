#!/usr/bin/env python3
"""Classify a PR's extraction-surface diff (BASE-owned; design v4).

Ported verbatim from the inline heredoc in extraction-eval.yml (PR #36 r2):
as a file the classifier is unit-testable (it is the CLASSIFIER whose
harness-refusal output the charter's enumerated golden-exam exception is
keyed on — an untestable classifier was a gap), and the workflow shell
shrinks to glue that tools/workflow_env_lint.py can verify. Trust
placement unchanged: in CI this runs from the BASE checkout under
pull_request_target, so the PR cannot edit the copy that judges it.

Three classes of surface change:
  * HARNESS code (runner, provider, scoring, golden set, extractors,
    verifier, the workflows) -> refuse, exit 1: the exam never certifies
    code it did not run. Harness changes merge first through the mandatory
    adversarial review, then subjects re-exam against the merged harness.
  * SUBJECT-CERTIFIABLE (ai/prompts.py; tools/routing_data.py scoped to
    the values the exam binds) -> allowed with head-bound attended
    evidence.
  * The CERTIFICATION RECORD (ai/golden/CERTIFIED_HARNESS.json) —
    evidence ABOUT the harness, deliberately outside the harness manifest,
    never executed by an exam (PR #36 r2): neither harness nor
    subject-certifiable. A change to it is gated by the workflow's own
    fail-closed authentication steps (tools/authenticate_certification_record.py).

Usage:
  classify_extraction_surface.py <compare.json> --base-dir <dir> --subject-dir <dir>
      [--print record-changed|surface-beyond-record]

Exit 0 = classification passed (with --print, also prints "1"/"0").
Exit 1 = refusal or fail-closed error (message on stderr as ::error::).
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

RECORD = "ai/golden/CERTIFIED_HARNESS.json"

# The extraction surface the gate guards (mirror of the workflow's
# trigger paths — keep the two lists in sync).
_SURFACE_FILES = (
    "worker/ai_models.py", "worker/ai_extract.py",
    "worker/requirements.txt", "worker/requirements.lock",
    "tools/__init__.py",
    "tools/model_router.py", "tools/routing_data.py",
    "tools/pure_data.py", "tools/verify_exam_evidence.py",
    "tools/extract_prompt_text.py", "tools/extract_routed_model.py",
    "tools/golden_lint.py", "tools/trust_gate.py",
    "tools/classify_extraction_surface.py",
    "tools/authenticate_certification_record.py",
    "tests/test_golden_exam.py",
    ".github/workflows/extraction-eval.yml",
    ".github/workflows/extraction-exam-dispatch.yml",
)

# Files a prompt-swap exam GENUINELY certifies: the prompt is run as
# data; the routing values/gate flag are bound via the report's model
# field and the flip evidence rule.
SUBJECT_CERTIFIABLE = {"ai/prompts.py", "tools/routing_data.py"}


def on_surface(p: str) -> bool:
    return p.startswith("ai/") or p in _SURFACE_FILES


def _err(msg: str) -> None:
    print(f"::error::{msg}", file=sys.stderr)


def read_harness_manifest(base_dir: "pathlib.Path | str") -> "tuple | None":
    """HARNESS_MANIFEST read AS DATA from base's ai/golden_exam.py (AST,
    never import — the exam channel stays confined). This is the
    MECHANICAL identity the charter exception's scope split keys on
    (evaluator, PR #36 r3): manifest-bound files are the exact set the
    certification hash covers, derived from the same single source the
    runner stamps — never hand-mirrored. None = unreadable (callers
    fail closed)."""
    try:
        src = (pathlib.Path(base_dir) / "ai" / "golden_exam.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                    and isinstance(node.targets[0], ast.Name) \
                    and node.targets[0].id == "HARNESS_MANIFEST":
                value = ast.literal_eval(node.value)
                if isinstance(value, tuple) and value and \
                        all(isinstance(v, str) for v in value):
                    return value
        return None
    except (OSError, ValueError, SyntaxError):
        return None


def load_routing_data(path: "pathlib.Path | str"):
    """Both routing_data versions are PURE DATA — diff them AS DATA (r14)."""
    src = pathlib.Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


def routing_ok(b, s) -> bool:
    """True iff the routing_data diff is confined to the values the exam
    binds: STAGE_MODELS['extraction'] and the ratification flag."""
    if b is None or s is None:
        return False  # new/removed/unparseable file = harness change
    # The ratification flag must be an exact BOOL on both sides (r26
    # blocker): pure-data certification accepts any constant literal, so a
    # subject could smuggle the truthy STRING "False"/"yes" through this
    # exemption. The provider gate requires `is True`, and this gate
    # refuses to certify a non-bool flag at all (fail closed = harness
    # change).
    if not (isinstance(b.get("EXTRACTION_THRESHOLD_RATIFIED"), bool)
            and isinstance(s.get("EXTRACTION_THRESHOLD_RATIFIED"), bool)):
        return False
    bm, sm = dict(b.get("STAGE_MODELS") or {}), dict(s.get("STAGE_MODELS") or {})
    bm.pop("extraction", None); sm.pop("extraction", None)
    if bm != sm:
        return False  # a non-extraction tier changed
    bf = {k: v for k, v in b.items() if k != "STAGE_MODELS"}
    sf = {k: v for k, v in s.items() if k != "STAGE_MODELS"}
    bf.pop("EXTRACTION_THRESHOLD_RATIFIED", None)
    sf.pop("EXTRACTION_THRESHOLD_RATIFIED", None)
    return bf == sf  # no other constants changed


def classify(compare: dict, base_dir: pathlib.Path, subject_dir: pathlib.Path) -> dict:
    """Return {"record_changed": bool, "surface_beyond_record": bool} or
    raise SystemExit(1) after printing the fail-closed reason."""
    files = compare.get("files")
    if files is None:
        _err("compare API returned no file list — cannot classify the diff "
             "(fail closed).")
        raise SystemExit(1)
    if len(files) >= 300:
        _err("diff has 300+ files — beyond the compare API's file-list cap, "
             "this gate cannot prove the surface classification (fail "
             "closed; split the PR).")
        raise SystemExit(1)
    # Renames fail closed (r16): the compare API reports a renamed file
    # under its NEW path with the old path in previous_filename — classify
    # BOTH sides, so renaming a harness file out of the guarded set is
    # still a harness change.
    changed = []
    for f in files:
        changed.append(f["filename"])
        if f.get("previous_filename"):
            changed.append(f["previous_filename"])
    record_changed = RECORD in changed
    harness_touched = [p for p in changed
                       if on_surface(p) and p not in SUBJECT_CERTIFIABLE
                       and p != RECORD]
    if "tools/routing_data.py" in changed:
        try:
            base_d = load_routing_data(base_dir / "tools/routing_data.py")
        except (OSError, ValueError, SyntaxError):
            base_d = None
        try:
            subj_d = load_routing_data(subject_dir / "tools/routing_data.py")
        except (OSError, ValueError, SyntaxError):
            subj_d = None
        if not routing_ok(base_d, subj_d):
            harness_touched.append("tools/routing_data.py (non-extraction "
                                   "routing values changed — the exam does "
                                   "not certify those)")
    if harness_touched:
        # The refusal is PARTITIONED (evaluator, PR #36 r3: the classified
        # surface is broader than the certification hash, so "the red moves
        # to trust_gate" was only true for part of it — the exception's
        # compensation must name each class's own executable channel):
        #   * MANIFEST-BOUND — in HARNESS_MANIFEST, read as data from the
        #     same single source the runner stamps: covered by the
        #     certification hash, so merging under the charter exception
        #     turns trust_gate red EVERYWHERE until an attended re-exam
        #     re-certifies (the red moves).
        #   * NOT manifest-bound (verifier/trust-path code and exam data
        #     outside the manifest): never covered by that hash — their
        #     re-verification channels are base-owned execution
        #     (pull_request_target: a PR's copy never judges itself), the
        #     per-run data bindings re-derived from base at every evidence
        #     verification (golden/prompt/model/dependency-lock hashes),
        #     and the mandatory non-Claude adversarial review that blocks
        #     THIS very PR (no path filter).
        # The charter exception's eligibility keys on this partition
        # (PR #36 r4): a refusal is exception-ELIGIBLE only when it is
        # proven to contain NO manifest-bound file. An unreadable manifest
        # therefore makes the refusal INELIGIBLE — never "everything
        # unbound", which would be fail-open for the exception itself.
        manifest = read_harness_manifest(base_dir)
        detail = []
        if manifest is None:
            detail.append("unclassifiable — HARNESS_MANIFEST unreadable from "
                          "base, so the manifest-bound partition cannot be "
                          "proven: this refusal is NOT covered by the charter "
                          "exception (fail closed): "
                          + ", ".join(sorted(harness_touched)))
        else:
            bound = sorted(p for p in harness_touched if p in manifest)
            unbound = sorted(p for p in harness_touched if p not in manifest)
            if bound:
                # Compensated by the LIVE trust_gate re-lock (bootstrap
                # final stage): merging under the charter exception turns
                # the whole tree red until an attended re-exam re-certifies.
                detail.append("manifest-bound (certification-hash covered; a "
                              "merge under the charter exception turns "
                              "trust_gate red everywhere until an attended "
                              "re-exam re-certifies — the red moves): "
                              + ", ".join(bound))
            if unbound:
                detail.append("NOT manifest-bound (re-verified instead by "
                              "base-owned execution, per-run data bindings, and "
                              "the blocking adversarial review on this PR): "
                              + ", ".join(unbound))
        # The first sentence is the charter-referenced classifier output for
        # the enumerated golden-exam exception — change it only with the
        # charter (founder-crucial).
        _err("This PR changes extraction HARNESS code that the "
             "attended exam does not execute, so prompt-swap evidence "
             "cannot certify it: " + ", ".join(sorted(harness_touched)) +
             ". Split the harness change into its own PR, merge it "
             "through the mandatory adversarial review first, then "
             "re-exam this subject against the merged harness "
             "(fail closed; the exam never certifies code it did not run). "
             + " | ".join(detail))
        raise SystemExit(1)
    surface_beyond_record = [p for p in changed if on_surface(p) and p != RECORD]
    return {
        "record_changed": record_changed,
        "surface_beyond_record": bool(surface_beyond_record),
        "surface": sorted(p for p in changed if on_surface(p)),
    }


def main(argv: "list[str] | None" = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def take(flag: str) -> "str | None":
        if flag not in argv:
            return None
        i = argv.index(flag)
        try:
            value = argv[i + 1]
        except IndexError:
            return None
        del argv[i:i + 2]
        return value

    base_dir = take("--base-dir")
    subject_dir = take("--subject-dir")
    to_print = take("--print")
    if len(argv) != 1 or not base_dir or not subject_dir or \
            to_print not in (None, "record-changed", "surface-beyond-record"):
        _err("usage: classify_extraction_surface.py <compare.json> "
             "--base-dir <dir> --subject-dir <dir> "
             "[--print record-changed|surface-beyond-record]")
        return 1
    try:
        compare = json.loads(pathlib.Path(argv[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _err(f"cannot read compare file ({exc}) — fail closed.")
        return 1
    if not isinstance(compare, dict):
        _err("compare file is not a JSON object — fail closed.")
        return 1
    result = classify(compare, pathlib.Path(base_dir), pathlib.Path(subject_dir))
    if to_print == "record-changed":
        print("1" if result["record_changed"] else "0")
    elif to_print == "surface-beyond-record":
        print("1" if result["surface_beyond_record"] else "0")
    else:
        print("surface diff is subject-certifiable:",
              ", ".join(result["surface"]) or "(none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
