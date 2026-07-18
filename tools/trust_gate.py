#!/usr/bin/env python3
"""Deterministic trust-invariant gate for OneLive CI.

This replaces the AI PR-review action with hermetic, in-repo static checks. An AI
reviewer's thoroughness varies run to run; a trust *invariant* must be enforced by
a check that gives the same answer every time. This gate is that check.

It enforces three invariants, each tied to the product's defensible core
("how does OneLive know this show is actually happening tonight?"):

  1. NO DYNAMIC SQL. Every SQL statement is either a static string with %s bound
     parameters, or composed via psycopg2.sql (SQL/Identifier/Literal). f-strings,
     %-formatting, .format(), and string concatenation into SQL are forbidden.
     Rationale: injection is a trust-and-safety hole; parameterization is
     non-negotiable, so we make it mechanically impossible to regress.

  2. ADS/TASTEMAKER CODE MUST NOT TOUCH THE GATING/PROMOTION PIPELINE. Contextual
     ads "cannot influence ranking" (migration 0004) and tastemaker content is
     kept separate from verified events. So no ads/tastemaker module may import
     worker.gating or worker.promote.

  3. AI NEVER PUBLISHES DIRECTLY. The extraction/provider layer (ai/, worker/
     ai_extract) must not import worker.promote — a gate always sits between
     extraction and publish. Extraction may call the gate; it may never promote.

Exit codes: 0 = all invariants hold; 1 = at least one violation (fail LOUDLY with
a specific, actionable message per finding — never a vague "check failed").
"""
from __future__ import annotations

import ast
import hashlib
import math
import pathlib
import re
import sys
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

# Directories whose .py files run SQL and must obey invariant 1.
# NOTE (2026-07-17 enumerated-list audit): kept for the focused checks
# below, but the SQL/promote invariants now ALSO sweep every production
# .py repo-wide via _all_production_py() — a future scripts/ dir is
# covered automatically, the same closure discipline as the exam scan.
SQL_DIRS = ["api", "worker", "tools"]

# Dependency/build trees excluded from repo-wide sweeps.
SKIP_PARTS = {"__pycache__", "node_modules", ".git", ".venv", "venv",
              "dist", "build", ".eggs", ".tox"}


def _all_production_py() -> list[pathlib.Path]:
    """Every .py in the repo except dependency/build trees and tests/.
    tests/ is excluded by DESIGN, not oversight: tests legitimately build
    dynamic SQL against stub cursors and import worker.promote to test
    the guard itself — the invariants govern production code."""
    return [p for p in REPO.rglob("*.py")
            if not (set(p.parts) & SKIP_PARTS)
            and p.relative_to(REPO).parts[0] != "tests"]

# Modules that constitute the gate/promotion pipeline.
PIPELINE_MODULES = ("worker.gating", "worker.promote")

# Substrings that mark a file as ads/tastemaker (invariant 2).
ADS_TASTEMAKER_MARKERS = ("ads", "tastemaker", "advertiser", "ad_campaign", "curat")

# Files allowed to import worker.promote (the only legitimate promoters).
# The orchestrator and its entrypoint are DELIBERATELY absent: the AI loop must
# never be able to publish, so if either re-acquires a worker.promote import
# this gate fails. "AI never auto-promotes" is enforced here structurally, not
# by a runtime flag.
PROMOTE_IMPORT_ALLOWLIST = {
    "api/ops_candidates.py",  # operator action: human-reviewed promote endpoint
}


@dataclass
class Findings:
    violations: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.violations.append(msg)

    def ok(self) -> bool:
        return not self.violations


def _py_files(dirs: list[str]) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for d in dirs:
        out.extend((REPO / d).rglob("*.py"))
    return [p for p in out if "__pycache__" not in p.parts]


# --- Invariant 1: no dynamic SQL ------------------------------------------------
# We detect SQL by AST: any call to `.execute(...)` whose first argument is built
# with an f-string, %-format, .format(), or string '+' is a violation. Static
# string literals and psycopg2.sql.* compositions are allowed.
_SQL_METHODS = {"execute", "executemany", "mogrify"}


class _SqlVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str, findings: Findings):
        self.relpath = relpath
        self.findings = findings

    def _dynamic_reason(self, node: ast.AST) -> str | None:
        # f-string
        if isinstance(node, ast.JoinedStr):
            return "f-string"
        if isinstance(node, ast.BinOp):
            # "..." % (...)  or  "..." + x
            if isinstance(node.op, ast.Mod):
                return "%-format"
            if isinstance(node.op, ast.Add):
                return "string concatenation"
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "format":
                # allow psycopg2.sql.SQL(...).format(...) — that IS the safe path.
                if _is_psycopg_sql(f.value):
                    return None
                return ".format()"
        return None

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in _SQL_METHODS and node.args:
            reason = self._dynamic_reason(node.args[0])
            if reason:
                self.findings.add(
                    f"{self.relpath}:{node.args[0].lineno}: dynamic SQL via {reason} "
                    f"passed to .{f.attr}(). Use a static string with %s bound params, "
                    f"or compose with psycopg2.sql (SQL/Identifier/Literal)."
                )
        self.generic_visit(node)


def _is_psycopg_sql(node: ast.AST) -> bool:
    """True if `node` is a psycopg2.sql.SQL(...) call (so .format() on it is safe)."""
    if isinstance(node, ast.Call):
        fn = node.func
        # sql.SQL(...) or psycopg2.sql.SQL(...)
        if isinstance(fn, ast.Attribute) and fn.attr == "SQL":
            return True
    return False


def check_no_dynamic_sql(findings: Findings) -> None:
    for path in _all_production_py():
        rel = str(path.relative_to(REPO))
        try:
            tree = ast.parse(path.read_text(), filename=rel)
        except SyntaxError as exc:
            findings.add(f"{rel}: could not parse ({exc}); cannot verify SQL safety.")
            continue
        _SqlVisitor(rel, findings).visit(tree)


# --- Import-graph invariants (2 and 3) ------------------------------------------
def _imports_of(path: pathlib.Path) -> set[str]:
    """Return the set of dotted module names imported by a file."""
    mods: set[str] = set()
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # from worker.promote import x  -> worker.promote
            mods.add(node.module)
    return mods


def check_ads_tastemaker_isolation(findings: Findings) -> None:
    for path in _all_production_py():
        rel = str(path.relative_to(REPO))
        name = path.name.lower()
        if not any(m in name for m in ADS_TASTEMAKER_MARKERS):
            continue
        for mod in _imports_of(path):
            if mod.startswith(PIPELINE_MODULES):
                findings.add(
                    f"{rel}: ads/tastemaker file imports {mod}. Contextual ads and "
                    f"tastemaker content must never touch the gating/promotion "
                    f"pipeline (ads cannot influence ranking; tastemaker stays "
                    f"separate from verified events)."
                )


def check_ai_never_promotes(findings: Findings) -> None:
    # ai/* and worker/ai_extract.py may call the gate, never promote directly.
    ai_files = list((REPO / "ai").rglob("*.py")) + [REPO / "worker" / "ai_extract.py"]
    for path in ai_files:
        if not path.exists() or "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(REPO))
        for mod in _imports_of(path):
            if mod.startswith("worker.promote"):
                findings.add(
                    f"{rel}: extraction/AI layer imports worker.promote. AI never "
                    f"publishes directly — a gate must sit between extraction and "
                    f"promote. Route through the gate, never promote from here."
                )


def check_promote_import_allowlist(findings: Findings) -> None:
    # Anything importing worker.promote must be on the allowlist, so new promoters
    # are a deliberate, reviewed decision — not something that slips in silently.
    for path in _all_production_py():
        rel = str(path.relative_to(REPO))
        if rel in PROMOTE_IMPORT_ALLOWLIST:
            continue
        for mod in _imports_of(path):
            if mod.startswith("worker.promote"):
                findings.add(
                    f"{rel}: imports worker.promote but is not on the promote "
                    f"allowlist in tools/trust_gate.py. Promotion is the publish "
                    f"step; if this file legitimately promotes, add it to the "
                    f"allowlist in the same change (deliberate, not silent)."
                )


# The exam channel (R-013's measurement instrument) may only be invoked from
# the golden-exam runner and tests — pipeline code must never construct an
# exam-mode provider (it bypasses the extraction ratification gate).
EXAM_MODE_ALLOWLIST_PREFIXES = (
    "ai/golden_exam.py",        # the exam runner — the channel's only real caller
    "tests/",                    # hermetic tests of the channel itself
    "ai/claude_provider.py",     # where the channel is defined
    "tools/trust_gate.py",       # this check's own detection string
    # CI diff classifier (PR #36 r2): NAMES exam files as inert data in its
    # guarded-surface list — it never imports or invokes the runner. Runs
    # only inside extraction-eval.yml's base checkout, not pipeline code.
    "tools/classify_extraction_surface.py",
)


def check_exam_mode_confined(findings: Findings) -> None:
    # Repo-root *.py files scan too (evaluator r7): a root-level script
    # driving the exam runner must be as visible as a worker/ one.
    # REPO-WIDE scan (r23 nit): future directories (scripts/, etc.) are
    # covered automatically; only dependency/build trees are excluded
    # (SKIP_PARTS, single-sourced — this scan INCLUDES tests/, which the
    # allowlist below then admits deliberately).
    candidates = [p for p in REPO.rglob("*.py")
                  if not (set(p.parts) & SKIP_PARTS)]
    for path in candidates:
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(REPO))
        if any(rel.startswith(pref) for pref in EXAM_MODE_ALLOWLIST_PREFIXES):
            continue
        # ANY mention — not just the literal `exam_mode=True` — so
        # `exam_mode = True`, **{"exam_mode": True}, aliasing, or wrapper
        # construction cannot slip past (evaluator finding, PR #25 r1).
        # Deliberately over-broad: this guards a ratification-gate bypass,
        # and a false positive is a rename away from clean.
        text = path.read_text(encoding="utf-8", errors="replace")
        if "exam_mode" in text:
            findings.add(
                f"{rel}: references exam_mode outside the exam channel "
                f"allowlist (ai/golden_exam.py, tests/). exam_mode bypasses "
                f"the extraction ratification gate and is reserved for the "
                f"golden-set exam runner only — any reference here is a "
                f"violation, however constructed."
            )
        # Same-hole closure at the static layer (evaluator, PR #25 r5):
        # pipeline code must not import or invoke the exam RUNNER either —
        # a wrapper that drives ai.golden_exam would put the allowlisted
        # runner on the call stack without ever containing "exam_mode".
        # The runtime stack-walk allowlists repo frames (r7); this scan
        # makes the same wrapper visible in CI before it can run.
        if "golden_exam" in text:
            findings.add(
                f"{rel}: references golden_exam outside the exam channel "
                f"allowlist. Driving the exam runner from pipeline code "
                f"would reach the ratification-gate bypass transitively — "
                f"the runner may only be invoked by CI, tests, or a human "
                f"(python -m ai.golden_exam), never by pipeline code."
            )




# The re-lock's OWN manifest copy + hasher (stage-6 r3): the re-lock must
# never trust ai/golden_exam.py — that file is itself manifest-bound, so
# the exact PR class this control compensates could otherwise alter the
# hasher or manifest to preserve the certified hash (circular trust).
# Kept in lockstep with the runner's HARNESS_MANIFEST by a sync test in
# tests/test_trust_gate_certification.py: single-sided drift fails pytest
# in the same PR; a coordinated change of both copies necessarily touches
# tools/trust_gate.py — trust-path class, whose named compensation is the
# mandatory adversarial review on that very PR. Threshold imports from
# ai/exam_thresholds stay safe for the same reason: that file's BYTES are
# pinned by this independent hash, so lowering a threshold re-reds drift
# before the lowered value could ever judge a record.
_RELOCK_HARNESS_MANIFEST = (
    ".github/workflows/extraction-exam-dispatch.yml",
    "ai/claude_provider.py",
    "ai/eval_harness.py",
    "ai/exam_thresholds.py",
    "ai/golden_exam.py",
    "ai/prompts.py",
    "ai/provider.py",
    "tools/__init__.py",
    "tools/extract_prompt_text.py",
    "tools/model_router.py",
    "tools/pure_data.py",
    "tools/routing_data.py",
    "worker/ai_models.py",
    "worker/requirements.lock",
    "worker/requirements.txt",
)


def _compute_harness_sha_independent(root: pathlib.Path,
                                     manifest: tuple = _RELOCK_HARNESS_MANIFEST) -> str:
    """Same algorithm as the runner's compute_harness_sha, implemented
    here so no manifest-bound code participates in verifying itself."""
    h = hashlib.sha256()
    for rel in manifest:
        h.update(rel.encode("utf-8") + b"\x00")
        h.update((root / rel).read_bytes() + b"\x00")
    return h.hexdigest()


def _golden_bytes_current(root: pathlib.Path) -> bytes:
    """Seam for tests; reads the CURRENT golden set's bytes."""
    return (root / "ai/golden/golden_set_v1.jsonl").read_bytes()


def _golden_bytes_at_commit(root: pathlib.Path, sha: str) -> bytes:
    """Seam for tests; the golden set AS THE ATTENDED EXAM SAW IT, read
    from git history at the record's authenticated subject commit
    (requires full history — CI checkouts fetch-depth 0)."""
    import subprocess
    return subprocess.run(
        ["git", "-C", str(root), "show", f"{sha}:ai/golden/golden_set_v1.jsonl"],
        capture_output=True, check=True).stdout


def check_extraction_certification(findings: Findings, record_path: "pathlib.Path | None" = None) -> None:
    """Flag-True extraction must be certified against the CURRENT harness.

    Compensating control demanded by the evaluator on PR #36 (and made live
    by PR #35, which changed a manifest-bound exam file after the flag
    flipped): EXTRACTION_THRESHOLD_RATIFIED=True is only meaningful while
    the attended exam's evidence matches the harness as it exists NOW.

    TWO layers, division of labor explicit (evaluator, PR #36 r2 — a
    hash-only check accepted a self-authored record):

    * THIS check (offline; every validate/pre-commit run; no network) proves
      STRUCTURAL VALIDITY and the hash re-lock: the record must be a
      complete, well-typed PASSED certification whose measured metrics pass
      the CURRENT thresholds (ai/exam_thresholds — manifest-bound, so a
      threshold change re-reds this check via drift) and whose
      harness_sha256 equals the tree's recomputed compute_harness_sha().
    * AUTHENTICITY — that run_id is a real successful maintainer-dispatched
      attended run on the default branch, that the artifact zip hashes to
      artifact_zip_sha256, and that the run's uploaded exam-report.json
      agrees with every recorded field — is enforced by the BASE-OWNED
      secretless verifier (.github/workflows/extraction-eval.yml, on
      pull_request_target: a PR cannot edit the copy that judges it), which
      authenticates this record against the GitHub Actions API on any PR
      that changes it. A record can only ENTER the tree authenticated; this
      offline check keeps it bound to the tree it certifies afterward.

    Missing, malformed, non-PASSED, threshold-failing, or drifted record =
    extraction is formally uncertified: FAIL, with the founder action named.
    The record file is deliberately NOT in the harness manifest, so writing
    it cannot change the hash it certifies.

    SCOPE, stated precisely (stage-6 r4): this offline layer compensates
    harness drift for the UNCHANGED, previously-authenticated record. It
    cannot and does not authenticate a CHANGED record — that is entry-time
    work: the base-owned authenticator runs on record-changing PRs, and a
    record change riding a harness refusal (where the authenticator never
    runs) is EXCEPTION-INELIGIBLE by the classifier's canonical marker,
    failed closed mechanically by the review's evidence step.
    """
    root = pathlib.Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tools.routing_data import EXTRACTION_THRESHOLD_RATIFIED

    if EXTRACTION_THRESHOLD_RATIFIED is False:
        return  # extraction closed; nothing to certify
    if EXTRACTION_THRESHOLD_RATIFIED is not True:
        # Fail LOUD on misconfig (evaluator, stage-6 r2): "true", 1, None,
        # or any non-bool is a malformed flag, not a safely-closed state —
        # the same rule the classifier applies to routing_data's flag.
        findings.add(
            f"extraction-certification: EXTRACTION_THRESHOLD_RATIFIED is "
            f"{EXTRACTION_THRESHOLD_RATIFIED!r} — the ratification flag "
            f"must be a literal bool; a malformed flag is a "
            f"misconfiguration, fail closed."
        )
        return

    from ai.exam_thresholds import HALLUCINATION_MAX, RECALL_MIN, SAMPLE_FLOOR

    if record_path is None:
        record_path = root / "ai/golden/CERTIFIED_HARNESS.json"
    try:
        current = _compute_harness_sha_independent(root)
    except OSError as exc:
        findings.add(
            f"extraction-certification: cannot hash the harness manifest "
            f"({exc}) — a missing manifest file is drift, fail closed."
        )
        return
    if not record_path.exists():
        findings.add(
            "extraction-certification: EXTRACTION_THRESHOLD_RATIFIED is True "
            "but ai/golden/CERTIFIED_HARNESS.json does not exist — the flag's "
            "evidence is bound to a harness this tree can no longer prove. "
            "Founder action: dispatch the attended exam on the current "
            "default-branch harness; the passing run's harness_sha256 + run "
            "id are then committed as the certification record."
        )
        return
    import json as _json

    try:
        record = _json.loads(record_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        findings.add(
            f"extraction-certification: certification record unreadable "
            f"({exc}) — fail closed."
        )
        return
    if not isinstance(record, dict):
        findings.add(
            "extraction-certification: certification record is not a JSON "
            "object — fail closed."
        )
        return

    # Shape helpers mirror tools/verify_exam_evidence.py: bools are not
    # counts, NaN/Infinity are not rates, and every field is validated
    # before use — a mistyped record fails closed, never crashes.
    def _hexstr(v, n: int) -> bool:
        return isinstance(v, str) and re.fullmatch(rf"[0-9a-f]{{{n}}}", v) is not None

    def _digits(v) -> bool:
        return isinstance(v, str) and v.isdigit()

    def _count(v) -> "int | None":
        return v if isinstance(v, int) and not isinstance(v, bool) else None

    def _rate(v) -> "float | None":
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
            return float(v)
        return None

    problems = []
    if not _hexstr(record.get("harness_sha256"), 64):
        problems.append("harness_sha256 missing or not 64 lowercase hex")
    if not _digits(record.get("run_id")):
        problems.append("run_id missing or not a numeric GitHub run id")
    if not _digits(record.get("artifact_id")):
        problems.append("artifact_id missing or not a numeric artifact id")
    if not _hexstr(record.get("artifact_zip_sha256"), 64):
        problems.append("artifact_zip_sha256 missing or not 64 lowercase hex")
    if not _hexstr(record.get("subject_sha"), 40):
        problems.append("subject_sha missing or not a 40-hex commit sha")
    if not (isinstance(record.get("model"), str) and record["model"]):
        problems.append("model missing")
    if record.get("verdict") != "PASSED":
        problems.append(f"verdict={record.get('verdict')!r} (only PASSED certifies)")
    m = record.get("metrics")
    if not isinstance(m, dict):
        problems.append("metrics missing or not an object")
    else:
        asserted = _count(m.get("asserted_facts"))
        rate = _rate(m.get("hallucination_rate"))
        recall = _rate(m.get("recall"))
        if asserted is None or asserted < SAMPLE_FLOOR:
            problems.append(f"asserted_facts={m.get('asserted_facts')!r} "
                            f"fails the >= {SAMPLE_FLOOR} floor")
        if rate is None or not (0.0 <= rate <= 1.0) or rate > HALLUCINATION_MAX:
            problems.append(f"hallucination_rate={m.get('hallucination_rate')!r} "
                            f"out of [0,1] or above {HALLUCINATION_MAX}")
        if recall is None or not (0.0 <= recall <= 1.0) or recall < RECALL_MIN:
            problems.append(f"recall={m.get('recall')!r} out of [0,1] or "
                            f"below {RECALL_MIN}")
        if _count(m.get("injections")) != 0:
            problems.append(f"injections={m.get('injections')!r} (need integer 0)")
        if _count(m.get("unanswered")) != 0:
            problems.append(f"unanswered={m.get('unanswered')!r} (need integer 0)")
        # Examples floor + current-set binding (evaluator, stage-6 r2: a
        # record with passing asserted_facts but zero/missing examples was
        # a false-confidence certification). The 40-example floor is
        # R-013's documented requirement (also pinned by
        # tests/test_golden_exam.py); the golden set is NOT in the harness
        # manifest, so the exam-time binding (golden_sha in the report,
        # verified per-run) is invisible offline — requiring the recorded
        # example count to equal the CURRENT set's size closes that gap:
        # growing or shrinking the set re-reds this check until a fresh
        # attended exam re-certifies.
        golden_path = root / "ai/golden/golden_set_v1.jsonl"
        try:
            golden_count = sum(
                1 for line in golden_path.read_text(encoding="utf-8").splitlines()
                if line.strip())
        except OSError:
            golden_count = -1  # unreadable set can never match a real count
        examples = _count(m.get("examples"))
        if examples is None or examples < 40 or examples != golden_count:
            problems.append(
                f"examples={m.get('examples')!r} missing, below the "
                f"40-example floor (R-013), or != the current golden set's "
                f"{golden_count} examples — the certification does not "
                f"describe the current set")
    if problems:
        findings.add(
            "extraction-certification: record is not a valid PASSED "
            "attended-exam certification — " + "; ".join(problems) + " — an "
            "invalid record certifies nothing (fail closed; authenticity of "
            "a CHANGED record is separately enforced by the base-owned "
            "verifier in .github/workflows/extraction-eval.yml)."
        )
        return
    # CONTENT binding for the golden set (stage-6 r2: the count-only
    # binding was false confidence — a same-size edit stayed green). The
    # record's subject_sha is AUTHENTICATED against the attended run's
    # head commit, and the exam verified the report's golden hash against
    # that commit's set — so the current set must be byte-identical to
    # the set at subject_sha. Any content change, same-size included,
    # re-reds this check until a fresh attended exam re-certifies.
    import hashlib as _hashlib
    import subprocess as _subprocess
    try:
        exam_set = _golden_bytes_at_commit(root, record["subject_sha"])
    except (OSError, _subprocess.CalledProcessError) as exc:
        findings.add(
            f"extraction-certification: cannot read the golden set at the "
            f"certified subject commit {record['subject_sha'][:12]} from git "
            f"history ({exc}) — content drift cannot be proven, fail closed "
            f"(a shallow clone needs full history for this check)."
        )
        return
    try:
        current_set = _golden_bytes_current(root)
    except OSError as exc:
        findings.add(
            f"extraction-certification: golden set unreadable ({exc}) — "
            f"fail closed."
        )
        return
    if _hashlib.sha256(current_set).hexdigest() != _hashlib.sha256(exam_set).hexdigest():
        findings.add(
            f"extraction-certification: the golden set's CONTENT has drifted "
            f"since the attended exam (current sha256 differs from the set at "
            f"the certified subject commit {record['subject_sha'][:12]}) — the "
            f"recorded metrics no longer describe this set. Re-dispatch the "
            f"attended exam and land a fresh record."
        )
        return
    if record["harness_sha256"] != current:
        findings.add(
            f"extraction-certification: harness has DRIFTED since the "
            f"attended exam (certified {record['harness_sha256'][:16]}…, run "
            f"{record['run_id']}; current {current[:16]}…) — extraction is "
            f"uncertified against this tree. Re-dispatch the attended exam "
            f"and update the record."
        )


def main() -> int:
    findings = Findings()
    check_no_dynamic_sql(findings)
    check_ads_tastemaker_isolation(findings)
    check_ai_never_promotes(findings)
    check_promote_import_allowlist(findings)
    check_exam_mode_confined(findings)
    check_extraction_certification(findings)

    if findings.ok():
        print("trust_gate: OK — all trust invariants hold "
          "(no dynamic SQL; ads/tastemaker isolated; AI never promotes; "
          "extraction certification matches the current harness).")
        return 0

    print("trust_gate: FAIL — trust invariant violation(s):", file=sys.stderr)
    for v in findings.violations:
        print(f"  - {v}", file=sys.stderr)
    print(f"\n{len(findings.violations)} violation(s). "
          f"These are trust-and-safety invariants; fix in-change, do not defer.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
