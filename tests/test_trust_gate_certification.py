"""Tests for trust_gate's extraction-certification re-lock (PR #36).

The compensating control for the golden-exam harness-PR exception, offline
layer: a True ratification flag is only meaningful while the committed
attended-exam certification record is a COMPLETE, well-typed, PASSED record
whose metrics pass the current thresholds AND whose harness hash matches
the current tree. Authenticity of a changed record (real run, artifact
digest, report cross-check) is the base-owned verifier's job in
.github/workflows/extraction-eval.yml — these tests pin the offline
contract, including the evaluator's PR #36 r2 finding: a bare
{harness_sha256, run_id} forgery must be REJECTED, never blessed.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PATH = _ROOT / "tools" / "trust_gate.py"
_spec = importlib.util.spec_from_file_location("trust_gate", _PATH)
trust_gate = importlib.util.module_from_spec(_spec)
sys.modules["trust_gate"] = trust_gate
_spec.loader.exec_module(trust_gate)

import ai.golden_exam as golden_exam
import tools.routing_data as routing_data
from ai.exam_thresholds import HALLUCINATION_MAX, RECALL_MIN, SAMPLE_FLOOR


def _valid_record(**overrides) -> dict:
    """A structurally complete PASSED record bound to the CURRENT harness.

    Metrics sit strictly inside every threshold so each failing test below
    isolates exactly one violated bar.
    """
    rec = {
        "harness_sha256": trust_gate._compute_harness_sha_independent(_ROOT),
        "run_id": "29659010747",
        "artifact_id": "8433778947",
        "artifact_zip_sha256": "ab" * 32,
        "subject_sha": "083c4306e71494baa6348084cffbdd09b8682f62",
        "model": "claude-opus-4-8",
        "verdict": "PASSED",
        "metrics": {
            "examples": 77,
            "asserted_facts": SAMPLE_FLOOR + 16,
            "hallucination_rate": HALLUCINATION_MAX / 2,
            "recall": min(1.0, RECALL_MIN + 0.1),
            "injections": 0,
            "unanswered": 0,
        },
    }
    rec.update(overrides)
    return rec


def _run(monkeypatch, tmp_path, flag, record_text):
    monkeypatch.setattr(routing_data, "EXTRACTION_THRESHOLD_RATIFIED", flag)
    rp = tmp_path / "CERTIFIED_HARNESS.json"
    if record_text is not None:
        rp.write_text(record_text, encoding="utf-8")
    findings = trust_gate.Findings()
    trust_gate.check_extraction_certification(findings, record_path=rp)
    return findings


def _run_record(monkeypatch, tmp_path, record: dict):
    return _run(monkeypatch, tmp_path, True, json.dumps(record))


def test_closed_flag_needs_no_certification(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, False, None)
    assert findings.ok()


def test_true_flag_with_no_record_fails(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, True, None)
    assert any("does not exist" in v for v in findings.violations)


def test_full_valid_record_passes(monkeypatch, tmp_path):
    findings = _run_record(monkeypatch, tmp_path, _valid_record())
    assert findings.ok(), findings.violations


def test_bare_hash_and_run_id_forgery_is_rejected(monkeypatch, tmp_path):
    """The exact PR #36 r2 evaluator fixture: a record carrying only the
    current harness hash and an arbitrary run id previously PASSED this
    gate. It must fail — no verdict, no metrics, no artifact binding."""
    findings = _run_record(
        monkeypatch, tmp_path,
        {"harness_sha256": golden_exam.compute_harness_sha(), "run_id": "12345"},
    )
    assert any("not a valid PASSED" in v for v in findings.violations)


def test_drifted_record_fails(monkeypatch, tmp_path):
    findings = _run_record(
        monkeypatch, tmp_path, _valid_record(harness_sha256="0" * 64)
    )
    assert any("DRIFTED" in v for v in findings.violations)


def test_malformed_record_fails_closed(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, True, "{not json")
    assert any("unreadable" in v for v in findings.violations)


def test_non_object_json_fails_closed(monkeypatch, tmp_path):
    """Valid JSON with the wrong top-level type must produce a controlled
    finding, not a TypeError (PR #36 r2 nit)."""
    for text in ("[]", '"a string"', "42", "null"):
        findings = _run(monkeypatch, tmp_path, True, text)
        assert any("not a JSON object" in v for v in findings.violations), text


def test_failed_verdict_is_rejected(monkeypatch, tmp_path):
    findings = _run_record(monkeypatch, tmp_path, _valid_record(verdict="FAILED"))
    assert any("only PASSED certifies" in v for v in findings.violations)


def test_hallucination_above_ceiling_is_rejected(monkeypatch, tmp_path):
    rec = _valid_record()
    rec["metrics"]["hallucination_rate"] = HALLUCINATION_MAX * 2
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("hallucination_rate" in v for v in findings.violations)


def test_recall_below_floor_is_rejected(monkeypatch, tmp_path):
    rec = _valid_record()
    rec["metrics"]["recall"] = RECALL_MIN - 0.05
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("recall" in v for v in findings.violations)


def test_asserted_facts_below_floor_is_rejected(monkeypatch, tmp_path):
    rec = _valid_record()
    rec["metrics"]["asserted_facts"] = SAMPLE_FLOOR - 1
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("asserted_facts" in v for v in findings.violations)


def test_nonzero_injections_or_unanswered_are_rejected(monkeypatch, tmp_path):
    for key in ("injections", "unanswered"):
        rec = _valid_record()
        rec["metrics"][key] = 1
        findings = _run_record(monkeypatch, tmp_path, rec)
        assert any(key in v for v in findings.violations), key


def test_mistyped_fields_fail_closed_without_crashing(monkeypatch, tmp_path):
    """Wrong types anywhere = controlled rejection, never an exception:
    string counts, boolean counts, NaN rates, non-digit ids, list metrics."""
    cases = [
        _valid_record(run_id="not-a-run-id"),
        _valid_record(artifact_id=8433778947),          # int, not string
        _valid_record(subject_sha="short"),
        _valid_record(metrics=[]),
    ]
    rec = _valid_record(); rec["metrics"]["asserted_facts"] = "316"; cases.append(rec)
    rec = _valid_record(); rec["metrics"]["injections"] = False; cases.append(rec)
    rec = _valid_record(); rec["metrics"]["hallucination_rate"] = float("nan"); cases.append(rec)
    for i, case in enumerate(cases):
        findings = _run_record(monkeypatch, tmp_path, case)
        assert any("not a valid PASSED" in v for v in findings.violations), i


def test_malformed_flag_fails_loud(monkeypatch, tmp_path):
    """stage-6 r1: 'true', 1, None, or any non-bool flag is misconfig,
    never a safely-closed state."""
    for bad in ("true", 1, None, "False", 0.0):
        findings = _run(monkeypatch, tmp_path, bad, None)
        assert any("must be a literal bool" in v for v in findings.violations), bad
    # literal False stays a clean closed state
    assert _run(monkeypatch, tmp_path, False, None).ok()


def test_examples_floor_and_current_set_binding(monkeypatch, tmp_path):
    """stage-6 r2: examples must exist, be >= the 40-example floor, and
    equal the CURRENT golden set's size — set drift re-reds offline."""
    rec = _valid_record()
    del rec["metrics"]["examples"]
    assert not _run_record(monkeypatch, tmp_path, rec).ok()
    for bad in (0, 39, 76, "77", True):
        rec = _valid_record()
        rec["metrics"]["examples"] = bad
        findings = _run_record(monkeypatch, tmp_path, rec)
        assert any("examples" in v for v in findings.violations), bad
    # the real count (77, matching ai/golden/golden_set_v1.jsonl) passes
    assert _run_record(monkeypatch, tmp_path, _valid_record()).ok()


def test_same_count_content_drift_fails(monkeypatch, tmp_path):
    """stage-6 r2: a SAME-SIZE golden-set edit must re-red — the binding
    is content, not count. The tampered set keeps the exact line count
    (so the examples/count check stays green) but changes one byte run."""
    real = trust_gate._golden_bytes_current(_ROOT)
    lines = real.decode("utf-8").splitlines()
    lines[0] = lines[0].replace("{", '{"tampered": true, ', 1)
    tampered = ("\n".join(lines) + "\n").encode("utf-8")
    assert tampered != real
    assert len(lines) == len(real.decode("utf-8").splitlines())
    monkeypatch.setattr(trust_gate, "_golden_bytes_current", lambda root: tampered)
    findings = _run_record(monkeypatch, tmp_path, _valid_record())
    assert any("CONTENT has drifted" in v for v in findings.violations)


def test_git_history_unavailable_fails_closed(monkeypatch, tmp_path):
    import subprocess
    def boom(root, sha):
        raise subprocess.CalledProcessError(128, ["git", "show"])
    monkeypatch.setattr(trust_gate, "_golden_bytes_at_commit", boom)
    findings = _run_record(monkeypatch, tmp_path, _valid_record())
    assert any("cannot be proven, fail closed" in v for v in findings.violations)


def test_relock_manifest_matches_runner_manifest():
    """Lockstep sync (stage-6 r3): the re-lock's own manifest copy must
    equal the runner's. Single-sided drift fails HERE in the same PR;
    changing both copies touches trust_gate.py — trust-path class, whose
    compensation is the mandatory adversarial review."""
    assert trust_gate._RELOCK_HARNESS_MANIFEST == golden_exam.HARNESS_MANIFEST


def test_relock_never_consults_the_runner_hasher(monkeypatch, tmp_path):
    """stage-6 r3 adversarial case: even if the manifest-bound runner's
    hasher LIES (returns garbage or the certified hash), the re-lock's
    verdict is unchanged — it computes independently."""
    monkeypatch.setattr(golden_exam, "compute_harness_sha", lambda: "0" * 64)
    assert _run_record(monkeypatch, tmp_path, _valid_record()).ok()
    monkeypatch.setattr(
        golden_exam, "compute_harness_sha",
        lambda: trust_gate._compute_harness_sha_independent(_ROOT))
    findings = _run_record(
        monkeypatch, tmp_path, _valid_record(harness_sha256="0" * 64))
    assert any("DRIFTED" in v for v in findings.violations)


def test_independent_hasher_detects_a_byte_change(tmp_path):
    """Smoke test: the re-lock's hasher changes when one byte of one
    manifest file changes, with no imported code involved (the algorithm
    hashes every listed file's bytes, so the property generalizes, but
    this test exercises a single mutation)."""
    for rel in ("a.py", "b/c.yml"):
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"original-" + rel.encode())
    manifest = ("a.py", "b/c.yml")
    before = trust_gate._compute_harness_sha_independent(tmp_path, manifest)
    (tmp_path / "a.py").write_bytes(b"original-a.pX")  # same length, one byte
    after = trust_gate._compute_harness_sha_independent(tmp_path, manifest)
    assert before != after


def test_relock_hasher_flag_flip_invariance_and_other_drift(tmp_path):
    """Option A (founder-approved 2026-08-04): flipping ONLY the
    ratification flag must not change the re-lock's hash (the flag gates
    production publishing, not the exam), while any OTHER routing_data
    byte keeps drifting it exactly as before. Synthetic tree, so the
    property is proven without touching the real checkout."""
    rd = tmp_path / "tools" / "routing_data.py"
    rd.parent.mkdir(parents=True)
    other = tmp_path / "a.py"
    other.write_bytes(b"a = 1\n")
    manifest = ("a.py", "tools/routing_data.py")
    body = b'STAGE_MODELS = {"extraction": "claude-opus-4-8"}\n'
    rd.write_bytes(body + b"EXTRACTION_THRESHOLD_RATIFIED = False\n")
    hash_false = trust_gate._compute_harness_sha_independent(tmp_path, manifest)
    rd.write_bytes(body + b"EXTRACTION_THRESHOLD_RATIFIED = True\n")
    hash_true = trust_gate._compute_harness_sha_independent(tmp_path, manifest)
    assert hash_true == hash_false  # the flip is normalized out
    rd.write_bytes(b'STAGE_MODELS = {"extraction": "claude-haiku-4-5"}\n'
                   b"EXTRACTION_THRESHOLD_RATIFIED = True\n")
    assert trust_gate._compute_harness_sha_independent(
        tmp_path, manifest) != hash_false  # non-flag edits still bind
    # A tree whose routing_data LOST its flag line cannot be hashed at
    # all — fail closed, never a silently-unnormalized fingerprint.
    rd.write_bytes(body)
    with pytest.raises(ValueError, match="missing or ambiguous"):
        trust_gate._compute_harness_sha_independent(tmp_path, manifest)


def test_relock_normalizer_fails_closed_on_zero_or_two_flag_lines():
    ok = b"x = 1\nEXTRACTION_THRESHOLD_RATIFIED = True\n"
    out = trust_gate._normalize_ratification_flag_relock(ok)
    assert b"EXTRACTION_THRESHOLD_RATIFIED = False" in out
    with pytest.raises(ValueError, match="missing or ambiguous"):
        trust_gate._normalize_ratification_flag_relock(b"x = 1\n")
    with pytest.raises(ValueError, match="missing or ambiguous"):
        trust_gate._normalize_ratification_flag_relock(
            ok + b"EXTRACTION_THRESHOLD_RATIFIED = False\n")


def test_flag_normalizers_are_in_lockstep():
    """Same discipline as the manifest-copy sync test above: the runner's
    normalizer and the re-lock's own copy must produce identical output
    for identical input (and agree on what is malformed). Single-sided
    drift fails HERE in the same PR; changing both copies touches
    tools/trust_gate.py — trust-path class, mandatory adversarial review."""
    real = (_ROOT / "tools" / "routing_data.py").read_bytes()
    variants = [
        real,
        real.replace(b"EXTRACTION_THRESHOLD_RATIFIED = False",
                     b"EXTRACTION_THRESHOLD_RATIFIED = True"),
        b"EXTRACTION_THRESHOLD_RATIFIED   =   True\n",
        b"pre = 0\nEXTRACTION_THRESHOLD_RATIFIED = False\npost = 1\n",
    ]
    for v in variants:
        assert (trust_gate._normalize_ratification_flag_relock(v)
                == golden_exam._normalize_ratification_flag(v))
    for bad in (b"", b"EXTRACTION_THRESHOLD_RATIFIED = False\n"
                     b"EXTRACTION_THRESHOLD_RATIFIED = True\n"):
        for fn in (trust_gate._normalize_ratification_flag_relock,
                   golden_exam._normalize_ratification_flag):
            with pytest.raises(ValueError):
                fn(bad)


def test_both_hashers_agree_on_the_current_tree():
    """The runner's hash and the re-lock's independent recomputation must
    be identical on the real checkout — the record one mints is the
    record the other verifies."""
    assert (golden_exam.compute_harness_sha()
            == trust_gate._compute_harness_sha_independent(_ROOT))


def test_malformed_flag_line_fails_certification_closed(monkeypatch, tmp_path):
    """A routing_data.py whose flag line went missing makes the harness
    unhashable: check_extraction_certification must emit the existing
    'cannot hash the harness manifest' finding (ValueError joins OSError
    in the fail-closed catch), never crash or pass."""
    rec = _valid_record()  # computed BEFORE the read patch below
    real_read = pathlib.Path.read_bytes
    def stripped_read(self):
        data = real_read(self)
        if self.name == "routing_data.py" and self.parent.name == "tools":
            # FLAG-STATE-AGNOSTIC (fixed 2026-08-04): strip whichever
            # literal is present via the re-lock's own regex — the original
            # hardcoded "= False" and silently no-opped after a flip.
            from tools.trust_gate import _RELOCK_RATIFICATION_FLAG_RE
            data = _RELOCK_RATIFICATION_FLAG_RE.sub(b"", data)
        return data
    monkeypatch.setattr(pathlib.Path, "read_bytes", stripped_read)
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("cannot hash the harness manifest" in v
               for v in findings.violations)
