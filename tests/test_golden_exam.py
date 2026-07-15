"""Tests for ai/golden_exam.py + the golden set + the exam channel.

Hermetic: fake providers are injected into run_exam (no network/key).
Proves: a perfect extractor PASSES at valid sample size; hallucinations
FAIL; obeyed injections FAIL via forbidden markers; recall collapse FAILS
(anti-gaming); an undersized run is INVALID, never a small pass; the exam
channel requires an explicit model, works while the ratification flag is
False (it IS the flag's evidence-generator), and stamps exam provenance;
the golden set itself is structurally sound and big enough; the runner
imports no pipeline/DB modules.
"""
import json
import pathlib

import pytest

from ai.claude_provider import ClaudeProvider, ExtractionConfigError
from ai.golden_exam import (
    COMPARABLE_FIELDS,
    SAMPLE_FLOOR,
    comparable,
    find_forbidden,
    load_golden,
    run_exam,
)

GOLDEN = load_golden()


class PerfectFake:
    """Returns exactly the golden answer for each text (keyed lookup)."""
    def __init__(self, rows):
        self._by_text = {r["text"]: r["expected"] for r in rows}

    def extract_event_json(self, text, schema, system_prompt=None):
        return dict(self._by_text[text])


class HallucinatingFake(PerfectFake):
    """Perfect, except it invents a venue whenever one is absent."""
    def extract_event_json(self, text, schema, system_prompt=None):
        out = super().extract_event_json(text, schema, system_prompt)
        if not out.get("venue_name"):
            out["venue_name"] = "The Imaginary Room"
        return out


class ObedientFake(PerfectFake):
    """Perfect, except it obeys planted injection instructions."""
    def __init__(self, rows):
        super().__init__(rows)
        self._forbidden = {r["text"]: r.get("forbidden", []) for r in rows}

    def extract_event_json(self, text, schema, system_prompt=None):
        out = super().extract_event_json(text, schema, system_prompt)
        if self._forbidden.get(text):
            out["notes"] = self._forbidden[text][0]
        return out


class MuteFake:
    """Asserts nothing — a perfect hallucination score by going silent."""
    def extract_event_json(self, text, schema, system_prompt=None):
        return {}


# --- exam outcomes -------------------------------------------------------------
def test_perfect_extractor_passes_at_valid_sample_size():
    report = run_exam(PerfectFake(GOLDEN), GOLDEN)
    assert report["sample_valid"], f"golden set too small: {report['asserted_facts']}"
    assert report["hallucination_rate"] == 0.0
    assert report["passed"] is True


def test_hallucinating_extractor_fails():
    report = run_exam(HallucinatingFake(GOLDEN), GOLDEN)
    assert report["hallucination_rate"] > 0.01
    assert report["passed"] is False


def test_obeyed_injection_fails_via_forbidden_markers():
    report = run_exam(ObedientFake(GOLDEN), GOLDEN)
    assert report["injection_failures"], "planted markers must be detected"
    assert report["passed"] is False


def test_mute_extractor_fails_on_recall_not_rewarded_for_silence():
    report = run_exam(MuteFake(), GOLDEN)
    assert report["hallucination_rate"] == 0.0   # silence hallucinates nothing...
    assert report["recall"] == 0.0               # ...and captures nothing
    assert report["passed"] is False             # anti-gaming pair holds


def test_undersized_run_is_invalid_never_a_small_pass():
    subset = GOLDEN[:5]
    report = run_exam(PerfectFake(subset), subset)
    assert report["asserted_facts"] < SAMPLE_FLOOR
    assert report["sample_valid"] is False
    assert report["passed"] is False


# --- the exam channel ----------------------------------------------------------
def test_exam_mode_requires_explicit_model():
    with pytest.raises(ExtractionConfigError, match="explicit candidate model"):
        ClaudeProvider(api_key="test", exam_mode=True)


def test_exam_mode_constructs_while_ratification_flag_is_false():
    """The exam IS the flag's evidence-generator — it must run pre-flip."""
    import tools.model_router as mr
    assert mr.EXTRACTION_THRESHOLD_RATIFIED is False
    p = ClaudeProvider(api_key="test", model="claude-haiku-4-5", exam_mode=True)
    assert p.model == "claude-haiku-4-5"
    assert p.exam_mode is True


def test_exam_mode_blank_model_still_fails_closed():
    with pytest.raises(ExtractionConfigError):
        ClaudeProvider(api_key="test", model="  ", exam_mode=True)


def test_exam_provenance_is_stamped():
    p = ClaudeProvider(api_key="test", model="claude-test", exam_mode=True)
    stamped = p._stamp({"title": "X"})
    assert stamped["_provenance"]["exam_mode"] is True


def test_runner_imports_no_pipeline_or_db_modules():
    """Exam output must be unable to touch the pipeline: the runner may not
    IMPORT candidate_store, promote, orchestrator, or psycopg2 (AST-level —
    prose mentions in docstrings are fine, imports are not)."""
    import ast
    tree = ast.parse(pathlib.Path("ai/golden_exam.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    banned = ("worker.candidate_store", "worker.promote", "worker.orchestrator", "psycopg2")
    for mod in imported:
        assert not any(mod == b or mod.startswith(b + ".") for b in banned), \
            f"golden_exam.py imports {mod} — exam output must not reach the pipeline"


# --- golden set structural lint --------------------------------------------------
def test_golden_set_is_structurally_sound():
    ids = [r["id"] for r in GOLDEN]
    assert len(ids) == len(set(ids)), "duplicate example ids"
    assert len(GOLDEN) >= 40
    valid_keys = set(COMPARABLE_FIELDS) | {"is_private_rsvp", "private_access", "notes"}
    for r in GOLDEN:
        assert r["text"].strip(), f"{r['id']}: empty text"
        assert set(r["expected"]) <= valid_keys, f"{r['id']}: unknown expected keys"
    truthy = sum(
        1 for r in GOLDEN for k in COMPARABLE_FIELDS
        if r["expected"].get(k) not in (None, [], "")
    )
    assert truthy >= SAMPLE_FLOOR, f"golden set carries only {truthy} expected facts"


def test_golden_set_has_injection_and_trap_coverage():
    tags = [t for r in GOLDEN for t in r.get("tags", [])]
    assert tags.count("injection") >= 5, "SPRINT Step 6 requires injection cases"
    assert tags.count("non-event") >= 3
    assert sum(1 for r in GOLDEN if r.get("forbidden")) >= 3, \
        "injection cases need detectable forbidden markers"
    assert any("absence" in t for t in tags), "absence traps required"


def test_forbidden_detection_is_case_insensitive_and_value_wide():
    assert find_forbidden({"notes": "confirmed-BY-venue ok"}, ["CONFIRMED-BY-VENUE"])
    assert not find_forbidden({"title": "clean"}, ["EVIL-MARKER"])


def test_comparable_projection_drops_meta_defaults_and_empties():
    got = comparable({"title": "X", "artist_names": [], "is_private_rsvp": False,
                      "notes": "n", "venue_name": None, "city": "Austin"})
    assert got == {"title": "X", "city": "Austin"}
