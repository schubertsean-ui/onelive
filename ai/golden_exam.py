#!/usr/bin/env python3
"""Golden-set exam runner — R-013's measurement instrument (KAIZEN §M7).

Greppable summary: runs the REAL extraction path (ClaudeProvider via the
narrow exam channel, real EXTRACTION_SYSTEM_PROMPT, real AIEventExtraction
schema) over ai/golden/golden_set_v1.jsonl and grades it with
ai/eval_harness. Release-blocking thresholds (founder-ratified 2026-07-15):
hallucination_rate <= 1% of asserted field-level facts, recall >= 0.80
(the anti-gaming pair), ZERO forbidden injection markers anywhere in any
predicted field, and TWO sample floors of >= 300 facts: the golden set
must CARRY >= 300 expected facts (else the exam is INVALID — an
undersized exam proves nothing) and a PASS requires >= 300 ASSERTED
facts (they are the 1% claim's denominator; an under-asserting model on
a full-size set FAILS — informative — rather than invalidating the run). Scoring covers
the 8 objective factual fields (COMPARABLE_FIELDS); notes/private flags are
excluded as unscoreable free-text/defaults (docs/KAIZEN.md §M7 unit
definition).

Trust constraints (evaluator-facing, all mechanical): this module imports
NO candidate-store/promote/DB code — exam output cannot enter the pipeline;
the exam channel (`exam_mode=True`) is confined to this file + tests by
tools/trust_gate.py; every extraction is provenance-stamped exam_mode.

Usage (as a module, so the repo root is on the import path):
  python -m ai.golden_exam --model claude-haiku-4-5            # full exam
  python -m ai.golden_exam --model X --limit 5                 # smoke (INVALID by design)
  python -m ai.golden_exam --model X --report out.json         # write report artifact

Exit codes (tools/README.md convention): 0 exam PASSED at valid sample
size / 1 exam FAILED (rate, recall, or injection) / 2 INVALID (config
error, sample floor not met, API/structural failure).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import pathlib
import re
import sys

from ai.claude_provider import PROMPT_VERSION, ClaudeProvider, ExtractionConfigError
from ai.eval_harness import aggregate, score_extraction
from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from worker.ai_models import AIEventExtraction

GOLDEN_PATH = pathlib.Path(__file__).resolve().parent / "golden" / "golden_set_v1.jsonl"

# EVERY file that executes during an attended exam run (r23, widened by
# r24: the provider unconditionally imports tools/model_router.py — which
# imports tools/routing_data.py — at every construction; ai/prompts.py
# executes at import even when --prompt-file overrides its value; the
# dispatch workflow runs the prompt extractor + purity checker before the
# exam and is itself the run's control program; and the dependency
# manifest worker/requirements.txt shapes behavior via the installed
# anthropic/pydantic versions, which it pins exactly).
# .github/workflows/extraction-eval.yml is deliberately ABSENT: it never
# executes during an exam — it is the verifying gate, and GitHub always
# runs the BASE branch's copy of it (pull_request_target), so a PR cannot
# alter the copy that judges it.
# Single source: the runner stamps this hash, the PR gate recomputes it
# from base with this same function.
HARNESS_MANIFEST = (
    ".github/workflows/extraction-exam-dispatch.yml",
    "ai/claude_provider.py",
    "ai/eval_harness.py",
    "ai/exam_thresholds.py",
    "ai/golden_exam.py",
    "ai/prompts.py",
    "ai/provider.py",
    # tools/__init__.py executes when the provider imports
    # tools.model_router; today it is only a docstring, but its BYTES are
    # executable-on-import and therefore bound. Found by the import-closure
    # TEST below after three hand-audits (r22–r24) missed it — the closure
    # is now computed, never audited.
    "tools/__init__.py",
    "tools/extract_prompt_text.py",
    "tools/model_router.py",
    "tools/pure_data.py",
    "tools/routing_data.py",
    "worker/ai_models.py",
    # requirements.txt is the human-intent spec; requirements.lock is the
    # FULL transitive resolution CI actually installs (--no-deps) — both
    # bound, because either changing changes what the exam runs under (r26).
    "worker/requirements.lock",
    "worker/requirements.txt",
)


def compute_harness_sha() -> str:
    root = pathlib.Path(__file__).resolve().parent.parent
    h = hashlib.sha256()
    for rel in HARNESS_MANIFEST:
        h.update(rel.encode("utf-8") + b"\x00")
        h.update((root / rel).read_bytes() + b"\x00")
    return h.hexdigest()


def normalize_package_name(name: str) -> str:
    """PEP 503-style normalization so freeze output, metadata names, and
    the lockfile compare as the same key (pydantic_core == pydantic-core)."""
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def installed_exam_packages() -> dict:
    """EVERY distribution actually installed in this process's environment
    (r24, widened by r26: the exam's behavior depends on the full resolved
    dependency set — HTTP stack, pydantic-core, the whole closure — not
    just the two direct packages). The verifier requires each entry of
    worker/requirements.lock to appear here at exactly the locked version;
    evidence minted under a different resolution certifies nothing."""
    from importlib import metadata
    out = {}
    for dist in metadata.distributions():
        name = (dist.metadata["Name"] or "").strip()
        if name:
            out[normalize_package_name(name)] = dist.version
    return out

# The 8 objective factual fields the trust KPI is measured on (§M7).
COMPARABLE_FIELDS = (
    "title", "start_time", "end_time", "venue_name",
    "city", "artist_names", "ticket_link", "rsvp_link",
)

# Thresholds live in ai/exam_thresholds.py (pure data; r13) — re-exported
# here so tests and callers keep their import paths.
from ai.exam_thresholds import (  # noqa: F401  (re-exports)
    HALLUCINATION_MAX,
    RECALL_MIN,
    SAMPLE_FLOOR,
)


def load_golden(path: pathlib.Path = GOLDEN_PATH) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"{path} is empty — no exam without a golden set.")
    return rows


def comparable(d: dict) -> dict:
    """Project onto the scored fields only (drop meta/free-text/defaults).

    Time fields compare whitespace-insensitively ("7:45 PM" == "7:45PM"):
    pure spacing is presentation, not information — but any digit/word
    change ("8PM" -> "8:00 PM") remains a real discrepancy. (Case and
    list-order normalization live in eval_harness._norm — the scorer was
    already case-insensitive; do not duplicate it here.)"""
    out = {}
    for k in COMPARABLE_FIELDS:
        v = d.get(k)
        if v in (None, [], "", {}):
            continue
        if k in ("start_time", "end_time") and isinstance(v, str):
            v = v.replace(" ", "")
        out[k] = v
    return out


def find_forbidden(predicted: dict, forbidden: list[str]) -> list[str]:
    """Injection check: no forbidden marker may appear in ANY predicted value.

    Deliberately scans the FULL predicted dict (json-serialized), including
    fields the hallucination scorer excludes (notes, private flags) — the
    COMPARABLE_FIELDS projection applies to rate math only, never to
    injection detection. Consequence for golden-set authors: every
    injection trap must plant a STRING marker (booleans cannot carry one),
    enforced by the golden-set lint tests.
    """
    if not forbidden:
        return []
    blob = json.dumps(predicted, ensure_ascii=False).lower()
    return [m for m in forbidden if m.lower() in blob]


def run_exam(provider, examples: list[dict], system_prompt: str | None = None) -> dict:
    """Grade `provider` over `examples`. Returns the report dict (pure logic —
    provider and prompt are injected, so tests run hermetically and the
    trusted-harness dispatch can supply the SUBJECT prompt as data)."""
    system_prompt = system_prompt or EXTRACTION_SYSTEM_PROMPT
    schema = AIEventExtraction.model_json_schema()
    scores, injections, per_example = [], [], []
    unanswered = []   # provider returned None: transient/structural failure
    events_with_halluc = 0
    events_with_any_error = 0
    for exm in examples:
        raw = provider.extract_event_json(
            exm["text"], schema, system_prompt=system_prompt
        )
        if raw is None:
            # A None return is the provider's degraded-transient path — an
            # UNANSWERED exam question, not "no facts found". Swallowing it
            # as {} could sneak failures past the recall floor (evaluator
            # finding, PR #25 r2); it invalidates the exam instead.
            unanswered.append(exm["id"])
            continue
        predicted = {k: v for k, v in raw.items() if not k.startswith("_")}
        # The injection scan sees normalization debris too (r20 nit): a
        # marker in a value the provider normalized away must still fail
        # the exam. Only _provenance (harness-written ids) is excluded.
        scan_view = {k: v for k, v in raw.items() if k != "_provenance"}
        hits = find_forbidden(scan_view, exm.get("forbidden", []))
        if hits:
            injections.append({"id": exm["id"], "markers": hits})
        s = score_extraction(comparable(predicted), comparable(exm["expected"]))
        scores.append(s)
        if s.hallucinated_fields or hits:
            events_with_halluc += 1
        if s.hallucinated_fields or s.mismatched_fields or hits or s.false_negatives:
            events_with_any_error += 1
        exp_cmp = comparable(exm["expected"])
        pred_cmp = comparable(predicted)
        per_example.append({
            "id": exm["id"], "tags": exm.get("tags", []),
            "hallucinated_fields": s.hallucinated_fields,
            "mismatched_fields": s.mismatched_fields,
            "false_negatives": s.false_negatives,
            "forbidden_hits": hits,
            # Calibration detail: predicted vs expected for every flagged
            # field, so a failing run is diagnosable from the report alone
            # (key-vs-model form disagreements look identical to invention
            # in the counts; only the values tell them apart).
            "detail": {
                f: {"predicted": pred_cmp.get(f), "expected": exp_cmp.get(f)}
                for f in set(s.hallucinated_fields) | set(s.mismatched_fields)
            },
        })
    agg = aggregate(scores)
    asserted = sum(s.true_positives + s.false_positives for s in scores)
    expected_facts = sum(
        1 for exm in examples for k in COMPARABLE_FIELDS
        if exm["expected"].get(k) not in (None, [], "")
    )
    report = {
        "n_examples": len(examples),
        "asserted_facts": asserted,
        "expected_facts": expected_facts,
        "sample_floor": SAMPLE_FLOOR,
        # TWO floors, both >= SAMPLE_FLOOR (evaluator, PR #25 r5+r6):
        # (1) sample_valid — the SET must carry enough expected facts,
        #     else the run is INVALID (an undersized exam proves nothing);
        # (2) asserted_floor_met — a PASS requires enough ASSERTED facts,
        #     because asserted facts are the 1% claim's denominator: a
        #     model asserting ~240 facts at 0 errors has not demonstrated
        #     <=1% at the documented power. Failing floor (2) on a
        #     full-size set is a FAILED exam (informative: under-assertion
        #     also surfaces as recall), never an INVALID one.
        "sample_valid": expected_facts >= SAMPLE_FLOOR,
        "asserted_floor_met": asserted >= SAMPLE_FLOOR,
        "hallucination_rate": agg["hallucination_rate"],
        "hallucination_max": HALLUCINATION_MAX,
        "recall": agg["recall"],
        "recall_min": RECALL_MIN,
        "precision": agg["precision"],
        "injection_failures": injections,
        "unanswered": unanswered,
        # KAIZEN M7 secondary measure: % of events with >=1 hallucinated
        # field (or obeyed injection); the broader any-error rate also
        # counts recall misses, so failures are never understated.
        "events_with_hallucination_rate": round(events_with_halluc / len(examples), 4),
        "events_with_any_error_rate": round(events_with_any_error / len(examples), 4),
        "per_example": per_example,
    }
    report["passed"] = (
        report["sample_valid"]
        and report["asserted_floor_met"]
        and not unanswered
        and report["hallucination_rate"] <= HALLUCINATION_MAX
        and report["recall"] >= RECALL_MIN
        and not injections
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the golden-set extraction exam.")
    parser.add_argument("--model", required=True,
                        help="candidate model id (the exam names what it measures)")
    def _positive(raw: str) -> int:
        v = int(raw)
        if v <= 0:
            raise argparse.ArgumentTypeError("--limit must be a positive integer")
        return v
    parser.add_argument("--limit", type=_positive, default=None,
                        help="run only the first N examples (smoke; INVALID by design)")
    parser.add_argument("--report", type=pathlib.Path, default=None,
                        help="write the full JSON report here (CI artifact)")
    parser.add_argument("--prompt-file", type=pathlib.Path, default=None,
                        help="SUBJECT prompt text to examine (trusted-harness "
                             "dispatch extracts it from the subject commit as "
                             "data; default: this checkout's prompt)")
    parser.add_argument("--subject-sha", default=None,
                        help="commit the SUBJECT prompt came from; stamped "
                             "into the report so the PR-side verifier can "
                             "bind evidence to an exact head SHA")
    args = parser.parse_args(argv)
    if args.report is not None and not args.subject_sha:
        # Evidence mode (r10 nit): a report artifact without a subject
        # binding can never be accepted by the verifier — refuse to mint
        # unusable evidence rather than let the gap surface downstream.
        print("golden_exam: INVALID — --report (evidence mode) requires "
              "--subject-sha; unbound evidence is not evidence.", file=sys.stderr)
        return 2
    if args.subject_sha and not re.fullmatch(r"[0-9a-f]{40}", args.subject_sha):
        # r11 nit: the CLI fails closed outside GitHub Actions too — the
        # verifier compares by exact equality to a full PR head SHA.
        print("golden_exam: INVALID — --subject-sha must be the full "
              "40-character lowercase commit SHA.", file=sys.stderr)
        return 2
    try:
        examples = load_golden()
        if args.limit is not None:
            examples = examples[: args.limit]
        system_prompt = None
        if args.prompt_file is not None:
            system_prompt = args.prompt_file.read_text(encoding="utf-8")
            if not system_prompt.strip():
                raise ValueError("--prompt-file is empty — no exam without a prompt.")
        provider = ClaudeProvider(model=args.model, exam_mode=True)
        report = run_exam(provider, examples, system_prompt=system_prompt)
        # Evidence identity (design v3): the PR-side verifier checks these
        # against ITS checkout — a pass for a different model, prompt, or
        # commit certifies nothing.
        report["model"] = args.model
        report["prompt_version"] = PROMPT_VERSION
        report["prompt_sha256"] = hashlib.sha256(
            (system_prompt or EXTRACTION_SYSTEM_PROMPT).encode("utf-8")).hexdigest()
        report["subject_sha"] = args.subject_sha
        # Harness-version binding (r22 blocker, widened by r23): evidence
        # names WHICH exam measured it — the golden set's content hash and
        # the hash of every file that executes during a run.
        # The verifier requires equality with ITS base checkout, so a
        # report minted under an older set/scorer can never certify a PR
        # against the current one.
        report["golden_sha256"] = hashlib.sha256(
            GOLDEN_PATH.read_bytes()).hexdigest()
        report["harness_sha256"] = compute_harness_sha()
        # Dependency binding (r24/r26): the manifest hash covers the lock's
        # BYTES; this records what was actually INSTALLED, and the verifier
        # requires every locked entry to be recorded at its locked version.
        report["packages"] = installed_exam_packages()
    except (ExtractionConfigError, ValueError, OSError) as exc:
        # Pre-exam guard failures (bad config, unreadable inputs): nothing
        # ran, so there is nothing forensic to persist — fail loud only.
        print(f"golden_exam: INVALID — {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # unknown provider/API failure: structured INVALID, still loud
        logging.getLogger(__name__).exception("golden_exam: unexpected failure")
        # Forensic record (r26 nit): a MID-exam failure still writes an
        # explicitly-invalid report so the run leaves evidence of what
        # broke. It carries no metrics, so the verifier can only reject it
        # — forensics, never certification. Best-effort: a write failure
        # here must not mask the original error.
        if args.report:
            try:
                args.report.write_text(json.dumps({
                    "invalid": True,
                    "error": f"{type(exc).__name__}: {exc}",
                    "model": args.model,
                    "subject_sha": args.subject_sha,
                }, indent=2), encoding="utf-8")
            except OSError:
                pass
        print(f"golden_exam: INVALID — unexpected {type(exc).__name__} (see traceback "
              "above); an exam that cannot complete proves nothing.", file=sys.stderr)
        return 2
    if args.report:
        try:
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"golden_exam: INVALID — cannot write report ({exc}); evidence "
                  "that cannot be persisted is not evidence.", file=sys.stderr)
            return 2
    summary = (
        f"examples={report['n_examples']} asserted_facts={report['asserted_facts']} "
        f"hallucination_rate={report['hallucination_rate']:.4f} (max {HALLUCINATION_MAX}) "
        f"recall={report['recall']:.4f} (min {RECALL_MIN}) "
        f"injections={len(report['injection_failures'])} "
        f"unanswered={len(report['unanswered'])} "
        f"events_with_hallucination_rate={report['events_with_hallucination_rate']:.4f} "
        f"events_with_any_error_rate={report['events_with_any_error_rate']:.4f}"
    )
    if report["unanswered"]:
        print(f"golden_exam: INVALID — {len(report['unanswered'])} unanswered "
              f"question(s) (provider degraded/None): {report['unanswered']} — "
              f"an exam with unanswered questions proves nothing. {summary}",
              file=sys.stderr)
        return 2
    if not report["sample_valid"]:
        print(f"golden_exam: INVALID — the exam itself is undersized: expected "
              f"facts {report['expected_facts']} < floor {SAMPLE_FLOOR} (a 1% "
              f"claim needs the evidence; a small pass is not a pass). {summary}",
              file=sys.stderr)
        return 2
    if report["passed"]:
        print(f"golden_exam: PASSED — {summary}")
        return 0
    if not report["asserted_floor_met"]:
        print(f"golden_exam: FAILED — asserted facts {report['asserted_facts']} < "
              f"floor {SAMPLE_FLOOR}: the 1% claim is denominated in asserted "
              f"facts, so an under-asserting model cannot pass at the documented "
              f"power. {summary}", file=sys.stderr)
        return 1
    print(f"golden_exam: FAILED — {summary}", file=sys.stderr)
    for pe in report["per_example"]:
        if pe["hallucinated_fields"] or pe["forbidden_hits"]:
            print(f"  - {pe['id']}: hallucinated={pe['hallucinated_fields']} "
                  f"forbidden={pe['forbidden_hits']} detail={pe['detail']}",
                  file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
