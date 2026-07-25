"""Construction Loop Stage 3 gate: blocking retrieval, fail-closed physics.

Covers (#67 r4 — the rule ships WITH its mechanism): uncited matched
class blocks; cited passes; no-match prints explicitly; unreadable/empty
index fails closed; explicit-paths mode used hermetically throughout.
"""
import pytest

from tools.construction_gate import load_index, main, match_classes

INDEX = """# test index
| token | triggers | source |
|---|---|---|
| caller-suppliable-custody-inputs | publish_gate, custody | KAIZEN r3 |
| volatile-safety-store | journal | KAIZEN r14 |
"""


@pytest.fixture()
def index_file(tmp_path):
    path = tmp_path / "RED_CLASSES.md"
    path.write_text(INDEX)
    return str(path)


def _contract(tmp_path, text):
    path = tmp_path / "STATE.md"
    path.write_text(text)
    return str(path)


def test_uncited_matched_class_blocks(tmp_path, index_file, capsys):
    contract = _contract(tmp_path, "contract with no citations")
    rc = main(
        ["--index", index_file, "--contract", contract, "--paths", "social/carousel/publish_gate.py"]
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert "does not cite: caller-suppliable-custody-inputs" in out


def test_cited_matched_class_passes(tmp_path, index_file):
    contract = _contract(
        tmp_path, "Stage 3 citations: caller-suppliable-custody-inputs answered in premortem."
    )
    rc = main(
        ["--index", index_file, "--contract", contract, "--paths", "social/carousel/publish_gate.py"]
    )
    assert rc == 0


def test_no_match_is_an_explicit_printed_result(tmp_path, index_file, capsys):
    contract = _contract(tmp_path, "anything")
    rc = main(["--index", index_file, "--contract", contract, "--paths", "web/app/page.tsx"])
    assert rc == 0
    assert "no matched red classes" in capsys.readouterr().out


def test_unreadable_or_empty_index_fails_closed(tmp_path):
    contract = _contract(tmp_path, "anything")
    with pytest.raises(SystemExit, match="unreadable"):
        main(["--index", str(tmp_path / "absent.md"), "--contract", contract, "--paths", "x"])
    empty = tmp_path / "empty.md"
    empty.write_text("# no table here\n")
    with pytest.raises(SystemExit, match="zero rows"):
        main(["--index", str(empty), "--contract", contract, "--paths", "x"])


def test_matching_is_path_substring_case_insensitive(index_file):
    index = load_index(index_file)
    assert match_classes(index, ["Worker/Journal_Writer.py"]) == ["volatile-safety-store"]
    assert match_classes(index, ["README.md"]) == []


def test_real_index_parses_and_covers_the_shipped_classes():
    from tools.construction_gate import DEFAULT_INDEX

    index = load_index(DEFAULT_INDEX)
    # The classes this loop was built from must be retrievable.
    for token in (
        "caller-suppliable-custody-inputs",
        "deferred-trust-work",
        "volatile-safety-store",
    ):
        assert token in index
