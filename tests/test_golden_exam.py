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


class WrongValueFake(PerfectFake):
    """Right fields, wrong values — mismatches must count against the gate."""
    def extract_event_json(self, text, schema, system_prompt=None):
        out = super().extract_event_json(text, schema, system_prompt)
        if out.get("venue_name"):
            out["venue_name"] = "Wrong Venue Entirely"
        return out


class SometimesNoneFake(PerfectFake):
    """Simulates transient provider degradation on one example."""
    def __init__(self, rows, none_on):
        super().__init__(rows)
        self._none_on = none_on

    def extract_event_json(self, text, schema, system_prompt=None):
        out = super().extract_event_json(text, schema, system_prompt)
        return None if self._none_on in text else out


class MuteFake:
    """Asserts nothing — a perfect hallucination score by going silent."""
    def extract_event_json(self, text, schema, system_prompt=None):
        return {}


# --- exam outcomes -------------------------------------------------------------
def test_perfect_extractor_passes_at_valid_sample_size():
    report = run_exam(PerfectFake(GOLDEN), GOLDEN)
    assert report["sample_valid"], f"golden set too small: {report['expected_facts']}"
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


def test_wrong_values_count_against_the_gate_not_just_the_report():
    """Evaluator nit (PR #25 r2): mismatched assertions are hallucinations
    in the rate math, not display-only."""
    report = run_exam(WrongValueFake(GOLDEN), GOLDEN)
    assert report["hallucination_rate"] > 0.01
    assert report["passed"] is False


def test_unanswered_questions_invalidate_the_exam():
    """A None provider return (transient degradation) is an unanswered
    question — never silently scored as an empty extraction."""
    target = GOLDEN[0]["text"]
    report = run_exam(SometimesNoneFake(GOLDEN, none_on=target), GOLDEN)
    assert report["unanswered"] == [GOLDEN[0]["id"]]
    assert report["passed"] is False


class UnderAssertingFake(PerfectFake):
    """Correct on what it answers, but skips enough fields to sit under the
    asserted-fact floor while keeping recall above RECALL_MIN's naive read
    of 'answered most examples' — the shape the r6 blocker warned about."""
    def extract_event_json(self, text, schema, system_prompt=None):
        out = super().extract_event_json(text, schema, system_prompt)
        # Drop the title/end_time/rsvp fact classes (~54 of 322): zero
        # hallucinations and recall STILL above RECALL_MIN, but fewer
        # assertions than the documented 1%-claim denominator — the floor
        # must be the binding constraint, not recall.
        for k in ("title", "end_time", "rsvp_link"):
            out.pop(k, None)
        return out


def test_under_asserting_model_fails_on_the_asserted_floor():
    """Evaluator blocker (PR #25 r6): a model asserting fewer than
    SAMPLE_FLOOR facts on the FULL set must FAIL — zero hallucinations at
    an underpowered denominator does not certify the 1% bar."""
    report = run_exam(UnderAssertingFake(GOLDEN), GOLDEN)
    assert report["sample_valid"] is True            # the SET is big enough
    assert report["recall"] >= 0.80                  # recall gate alone would pass
    assert report["asserted_facts"] < SAMPLE_FLOOR   # but the model under-asserts
    assert report["asserted_floor_met"] is False
    assert report["hallucination_rate"] == 0.0       # zero errors, and yet...
    assert report["passed"] is False                 # ...no pass


def test_cli_exit_1_when_asserted_floor_unmet(monkeypatch, capsys):
    import ai.golden_exam as ge
    monkeypatch.setattr(ge, "ClaudeProvider", lambda **kw: UnderAssertingFake(GOLDEN))
    assert ge.main(["--model", "claude-test"]) == 1
    assert "asserted facts" in capsys.readouterr().err


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


def test_exam_mode_constructs_while_ratification_flag_is_false(monkeypatch):
    """The exam IS the flag's evidence-generator — it must run pre-flip
    (and again whenever a failing model re-closes the gate), so the exam
    channel must construct while the flag is False."""
    import tools.model_router as mr
    monkeypatch.setattr(mr, "EXTRACTION_THRESHOLD_RATIFIED", False)
    p = ClaudeProvider(api_key="test", model="claude-haiku-4-5", exam_mode=True)
    assert p.model == "claude-haiku-4-5"
    assert p.exam_mode is True


def test_exam_mode_blank_model_still_fails_closed():
    with pytest.raises(ExtractionConfigError):
        ClaudeProvider(api_key="test", model="  ", exam_mode=True)


def test_html_entities_are_decoded_at_the_provider_boundary():
    """Exam cycle 8 (opus) emitted '&amp;' where the source text has '&' —
    an output-encoding artifact, not content. The provider decodes entities
    deterministically on every string field, nested lists/dicts included."""
    p = ClaudeProvider(api_key="test", model="claude-test", exam_mode=True)
    out = p._stamp({"venue_name": "Empire Control Room &amp; Garage",
                    "artist_names": ["Talia &amp; The Ghost Notes"],
                    "is_private_rsvp": False})
    assert out["venue_name"] == "Empire Control Room & Garage"
    assert out["artist_names"] == ["Talia & The Ghost Notes"]
    assert out["is_private_rsvp"] is False


def test_title_duplicating_artist_or_venue_is_nulled():
    """Production normalization (exam cycles 3-9): every model tier
    sometimes promotes the headline act or the venue to `title`. A title
    equal to an artist/venue name is dropped deterministically; a
    distinct title is never touched."""
    p = ClaudeProvider(api_key="test", model="claude-test", exam_mode=True)
    out = p._stamp({"title": "The Lantern Parade",
                    "artist_names": ["The Lantern Parade"]})
    assert out["title"] is None
    out = p._stamp({"title": "VALHALLA", "venue_name": "Valhalla"})
    assert out["title"] is None
    out = p._stamp({"title": "The Rewire Tour", "artist_names": ["Volt Collective"]})
    assert out["title"] == "The Rewire Tour"


def test_exam_provenance_is_stamped():
    p = ClaudeProvider(api_key="test", model="claude-test", exam_mode=True)
    stamped = p._stamp({"title": "X"})
    assert stamped["_provenance"]["exam_mode"] is True


def test_provenance_carries_prompt_content_hash():
    """Drift audit (po harvest, friction #2; evaluator r7): prompt_version
    says what was intended, the sha256 says what actually ran."""
    import hashlib
    from ai.prompts import EXTRACTION_SYSTEM_PROMPT
    p = ClaudeProvider(api_key="test", model="claude-test", exam_mode=True)
    stamped = p._stamp({"title": "X"})
    assert stamped["_provenance"]["prompt_sha256"] == \
        hashlib.sha256(EXTRACTION_SYSTEM_PROMPT.encode("utf-8")).hexdigest()


def test_exam_mode_denied_in_a_non_exam_process_even_with_forged_filenames(monkeypatch):
    """Evaluator blocker (PR #25 r8): the old stack-filename walk was
    spoofable via compile(..., filename=...). The entrypoint boundary is
    not: simulate a production process (no pytest env, __main__ is not
    the exam program) and prove that even code compiled under the
    runner's own filename is denied — authorization is a property of the
    PROCESS, not of code shape."""
    import types
    import __main__
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(__main__, "__spec__",
                        types.SimpleNamespace(name="celery.__main__"), raising=False)
    forged_ns = {}
    forged_src = (
        "from ai.claude_provider import ClaudeProvider\n"
        "def forged():\n"
        "    return ClaudeProvider(api_key='test', model='claude-test', exam_mode=True)\n"
    )
    exec(compile(forged_src, "ai/golden_exam.py", "exec"), forged_ns)
    with pytest.raises(ExtractionConfigError, match="entrypoint"):
        forged_ns["forged"]()


def test_exam_mode_allowed_when_process_is_the_exam_program(monkeypatch):
    """The one production-shaped entrypoint that must work: a process
    started as `python -m ai.golden_exam` (its __main__ spec is literally
    the runner module)."""
    import types
    import __main__
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(__main__, "__spec__",
                        types.SimpleNamespace(name="ai.golden_exam"), raising=False)
    p = ClaudeProvider(api_key="test", model="claude-test", exam_mode=True)
    assert p.exam_mode is True


def test_full_size_mute_run_fails_on_recall_not_invalid(monkeypatch, capsys):
    """Evaluator nit (PR #25 r5): validity is a property of the golden set,
    not the candidate — a full-size run by a mute model is a FAILED exam
    (recall verdict, exit 1), never an INVALID one (exit 2)."""
    import ai.golden_exam as ge
    monkeypatch.setattr(ge, "ClaudeProvider", lambda **kw: MuteFake())
    assert ge.main(["--model", "claude-test"]) == 1
    assert "FAILED" in capsys.readouterr().err


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


# --- CLI behavior (exit codes, not just report fields) --------------------------
def test_cli_exit_2_on_undersized_run(monkeypatch, capsys):
    import ai.golden_exam as ge
    monkeypatch.setattr(ge, "ClaudeProvider", lambda **kw: PerfectFake(GOLDEN))
    assert ge.main(["--model", "claude-test", "--limit", "5"]) == 2
    assert "INVALID" in capsys.readouterr().err


def test_cli_exit_2_on_unanswered(monkeypatch, capsys):
    import ai.golden_exam as ge
    monkeypatch.setattr(ge, "ClaudeProvider",
                        lambda **kw: SometimesNoneFake(GOLDEN, none_on=GOLDEN[0]["text"]))
    assert ge.main(["--model", "claude-test"]) == 2
    assert "unanswered" in capsys.readouterr().err


def test_cli_exit_0_on_pass_and_1_on_fail(monkeypatch, capsys):
    import ai.golden_exam as ge
    monkeypatch.setattr(ge, "ClaudeProvider", lambda **kw: PerfectFake(GOLDEN))
    assert ge.main(["--model", "claude-test"]) == 0
    monkeypatch.setattr(ge, "ClaudeProvider", lambda **kw: HallucinatingFake(GOLDEN))
    assert ge.main(["--model", "claude-test"]) == 1
    capsys.readouterr()


def test_time_comparison_is_whitespace_insensitive():
    got = comparable({"start_time": "7:45 PM"})
    assert got["start_time"] == "7:45PM"


def test_prompt_shares_no_surface_forms_with_golden_set():
    """Prompt-exam contamination guard (the g060 own-goal, cycle 6): a
    prompt example that even PARAPHRASES a golden text teaches the answer
    shape for that example, so the exam stops measuring generalization.
    No golden venue/artist/title/city string may appear in the prompt.
    'Austin' is exempt: it is the platform's real city, unavoidable in the
    city-discipline rules, and present in both null and non-null keys, so
    it teaches no single answer."""
    from ai.prompts import EXTRACTION_SYSTEM_PROMPT
    prompt = EXTRACTION_SYSTEM_PROMPT.lower()
    names = set()
    for r in GOLDEN:
        e = r["expected"]
        for k in ("title", "venue_name", "city"):
            if e.get(k):
                names.add(e[k])
        names.update(e.get("artist_names") or [])
    offenders = [n for n in sorted(names)
                 if len(n) > 3 and n.lower() != "austin" and n.lower() in prompt]
    assert not offenders, f"golden surface forms leaked into the prompt: {offenders}"


def test_prompt_shares_no_text_shingles_with_golden_set():
    """The stronger half of the contamination guard (evaluator nit, PR #25
    r6): beyond key VALUES, no distinctive PHRASE from a golden text may
    appear in the prompt — a paraphrased example (the g060 own-goal) shares
    word runs long before it shares whole answer strings. Any 5-word
    shingle from any golden text found in the normalized prompt fails."""
    import re
    from ai.prompts import EXTRACTION_SYSTEM_PROMPT
    def words(s):
        return re.findall(r"[a-z0-9']+", s.lower())
    prompt_text = " ".join(words(EXTRACTION_SYSTEM_PROMPT))
    hits = []
    for r in GOLDEN:
        w = words(r["text"])
        for i in range(len(w) - 4):
            shingle = " ".join(w[i:i + 5])
            if shingle in prompt_text:
                hits.append((r["id"], shingle))
                break
    assert not hits, f"golden text phrases leaked into the prompt: {hits}"


def test_evidence_verifier_accepts_only_routed_model_passes(tmp_path):
    """Design v2 (r8/personal-repo redesign): the PR-side verifier accepts
    a report only when it is a PASS, for the production-routed model,
    against this checkout's exact prompt — anything else is rejected."""
    import hashlib
    from ai.prompts import EXTRACTION_SYSTEM_PROMPT
    from tools.model_router import STAGE_MODELS
    from tools.verify_exam_evidence import verify
    good = {
        "passed": True,
        "model": STAGE_MODELS["extraction"],
        "prompt_sha256": hashlib.sha256(
            EXTRACTION_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "hallucination_rate": 0.0, "recall": 1.0, "asserted_facts": 322,
    }
    assert verify(good) == []
    assert verify({**good, "passed": False})
    assert verify({**good, "model": "claude-haiku-4-5"})       # not the routed model
    assert verify({**good, "prompt_sha256": "0" * 64})          # different prompt
    assert verify({})                                           # unreadable/empty


def test_cli_report_carries_evidence_identity(monkeypatch, tmp_path):
    """The dispatch run's report must name what it measured — model,
    prompt_version, prompt content hash — so the verifier can bind the
    evidence to the PR's checkout."""
    import ai.golden_exam as ge
    monkeypatch.setattr(ge, "ClaudeProvider", lambda **kw: PerfectFake(GOLDEN))
    out = tmp_path / "r.json"
    assert ge.main(["--model", "claude-test", "--report", str(out)]) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["model"] == "claude-test"
    assert r["prompt_version"] and len(r["prompt_sha256"]) == 64


# --- golden set structural lint --------------------------------------------------
def test_golden_set_is_structurally_sound():
    ids = [r["id"] for r in GOLDEN]
    assert len(ids) == len(set(ids)), "duplicate example ids"
    assert len(GOLDEN) >= 40
    valid_keys = set(COMPARABLE_FIELDS) | {"is_private_rsvp", "private_access", "notes"}
    documented_shape = {"id", "source_class", "tags", "text", "expected", "forbidden"}
    for r in GOLDEN:
        assert documented_shape <= set(r), \
            f"{r['id']}: missing documented row keys {documented_shape - set(r)}"
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
