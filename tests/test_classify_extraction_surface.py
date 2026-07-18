"""Tests for tools/classify_extraction_surface.py — the extraction-surface
diff classifier extraction-eval.yml runs from the BASE checkout.

This is the CLASSIFIER whose harness-refusal output the charter's
enumerated golden-exam exception keys on; while it lived inline in the
workflow YAML it was untestable (PR #36 r2). Every class and fail-closed
branch is pinned here: harness refusal (including renames and the
routing-values-as-data reclassification), subject-certifiable pass, the
certification-record third class, and the API-shape failure modes.
"""
import json
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import classify_extraction_surface as ces


def _compare(*names, renames=()):
    files = [{"filename": n} for n in names]
    for new, old in renames:
        files.append({"filename": new, "previous_filename": old})
    return {"files": files}


def _routing_pair(tmp_path, base_body, subj_body):
    base = tmp_path / "base"; subj = tmp_path / "subject"
    for d, body in ((base, base_body), (subj, subj_body)):
        (d / "tools").mkdir(parents=True, exist_ok=True)
        (d / "tools" / "routing_data.py").write_text(body, encoding="utf-8")
    return base, subj


_ROUTING = (
    'STAGE_MODELS = {"extraction": "%s", "evaluator": "gpt-5.5"}\n'
    "EXTRACTION_THRESHOLD_RATIFIED = %s\n"
)


def test_harness_change_refuses(tmp_path):
    with pytest.raises(SystemExit):
        ces.classify(_compare("ai/golden_exam.py"), tmp_path, tmp_path)


def test_rename_out_of_surface_still_refuses(tmp_path):
    """r16: a harness file renamed away must classify on BOTH paths."""
    with pytest.raises(SystemExit):
        ces.classify(
            _compare(renames=[("worker/renamed.py", "worker/ai_extract.py")]),
            tmp_path, tmp_path)


def test_own_files_are_guarded_surface(tmp_path):
    """The classifier and authenticator are verifier trust-path code:
    changing them is a harness change (they cannot certify themselves)."""
    for name in ("tools/classify_extraction_surface.py",
                 "tools/authenticate_certification_record.py"):
        with pytest.raises(SystemExit):
            ces.classify(_compare(name), tmp_path, tmp_path)


def test_prompt_swap_is_certifiable(tmp_path):
    out = ces.classify(_compare("ai/prompts.py", "docs/whatever.md"), tmp_path, tmp_path)
    assert out["record_changed"] is False
    assert out["surface_beyond_record"] is True


def test_record_is_neither_harness_nor_certifiable(tmp_path):
    out = ces.classify(_compare("ai/golden/CERTIFIED_HARNESS.json"), tmp_path, tmp_path)
    assert out["record_changed"] is True
    assert out["surface_beyond_record"] is False


def test_record_plus_prompt_sets_both_flags(tmp_path):
    out = ces.classify(
        _compare("ai/golden/CERTIFIED_HARNESS.json", "ai/prompts.py"),
        tmp_path, tmp_path)
    assert out["record_changed"] is True
    assert out["surface_beyond_record"] is True


def test_record_plus_harness_still_refuses(tmp_path):
    """A record must never ride the harness change it certifies."""
    with pytest.raises(SystemExit):
        ces.classify(
            _compare("ai/golden/CERTIFIED_HARNESS.json", "ai/eval_harness.py"),
            tmp_path, tmp_path)


def test_no_file_list_fails_closed(tmp_path):
    with pytest.raises(SystemExit):
        ces.classify({}, tmp_path, tmp_path)


def test_file_cap_fails_closed(tmp_path):
    compare = {"files": [{"filename": f"docs/f{i}.md"} for i in range(300)]}
    with pytest.raises(SystemExit):
        ces.classify(compare, tmp_path, tmp_path)


def test_routing_extraction_value_change_is_certifiable(tmp_path):
    base, subj = _routing_pair(
        tmp_path,
        _ROUTING % ("claude-haiku-4-5-20251001", "False"),
        _ROUTING % ("claude-opus-4-8", "True"),
    )
    out = ces.classify(_compare("tools/routing_data.py"), base, subj)
    assert out["surface_beyond_record"] is True


def test_routing_other_value_change_refuses(tmp_path):
    base, subj = _routing_pair(
        tmp_path,
        _ROUTING % ("claude-opus-4-8", "True"),
        _ROUTING.replace("gpt-5.5", "weaker-model") % ("claude-opus-4-8", "True"),
    )
    with pytest.raises(SystemExit):
        ces.classify(_compare("tools/routing_data.py"), base, subj)


def test_routing_non_bool_flag_refuses(tmp_path):
    """r26: a truthy STRING flag must reclassify as harness, not certify."""
    base, subj = _routing_pair(
        tmp_path,
        _ROUTING % ("claude-opus-4-8", "False"),
        _ROUTING % ("claude-opus-4-8", '"True"'),
    )
    with pytest.raises(SystemExit):
        ces.classify(_compare("tools/routing_data.py"), base, subj)


def test_routing_unparseable_refuses(tmp_path):
    base, subj = _routing_pair(
        tmp_path,
        _ROUTING % ("claude-opus-4-8", "True"),
        "import os\nSTAGE_MODELS = os.environ\n",  # not pure data
    )
    with pytest.raises(SystemExit):
        ces.classify(_compare("tools/routing_data.py"), base, subj)


def test_cli_print_flags(tmp_path, capsys):
    cj = tmp_path / "compare.json"
    cj.write_text(json.dumps(_compare("ai/golden/CERTIFIED_HARNESS.json")), encoding="utf-8")
    args = [str(cj), "--base-dir", str(tmp_path), "--subject-dir", str(tmp_path)]
    assert ces.main(args + ["--print", "record-changed"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert ces.main(args + ["--print", "surface-beyond-record"]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_cli_rejects_bad_usage(tmp_path, capsys):
    assert ces.main([]) == 1
    cj = tmp_path / "compare.json"
    cj.write_text("{}", encoding="utf-8")
    assert ces.main([str(cj), "--base-dir", str(tmp_path),
                     "--subject-dir", str(tmp_path), "--print", "bogus"]) == 1
    capsys.readouterr()


def test_surface_list_mirrors_workflow_triggers():
    """The workflow's trigger paths and the classifier's guarded surface
    must stay in sync — a file added to one but not the other is a gap."""
    import yaml
    wf = yaml.safe_load(
        (_ROOT / ".github/workflows/extraction-eval.yml").read_text(encoding="utf-8"))
    trig = wf[True]["pull_request_target"]["paths"]  # yaml parses `on` as True
    explicit = {p for p in trig if not p.endswith("/**")}
    globs = {p for p in trig if p.endswith("/**")}
    assert "ai/**" in globs
    for p in ces._SURFACE_FILES:
        assert p in explicit, f"{p} guarded by classifier but not a trigger path"
    for p in explicit:
        assert ces.on_surface(p), f"{p} triggers the workflow but is off-surface"
