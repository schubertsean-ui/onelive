"""design/proposals/direction-4-flow.html must match its generator.

The generated HTML carries "do not hand-edit" (all content derives from
generate_flow.py's single dataset so cards, counts, and lenses cannot
disagree) — but prose alone enforces nothing (evaluator nit, PR #45 r1).
This test regenerates into a temp path and compares bytes: a hand-edit
to the HTML, or a generator change committed without regenerating,
fails here in the same PR.
"""
import pathlib
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_GEN = _ROOT / "design" / "proposals" / "generate_flow.py"
_HTML = _ROOT / "design" / "proposals" / "direction-4-flow.html"


def test_committed_prototype_matches_its_generator(tmp_path):
    out = tmp_path / "regenerated.html"
    r = subprocess.run([sys.executable, str(_GEN), str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert out.read_text() == _HTML.read_text(), (
        "committed direction-4-flow.html differs from generate_flow.py's "
        "output — regenerate (python3 design/proposals/generate_flow.py) "
        "or revert the hand-edit; generator and artifact move together")
