"""Fail the build if desk_read is a stub. Same class as #273."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "worker" / "locale_pack"
FORBIDDEN = ("SEE_LOCAL", "PLACEHOLDER_SEE", "PLACEHOLDER", "SEE_FILE")


def _assert_not_stub_text(path: Path, text: str) -> None:
    assert path.exists(), f"{path} missing"
    for token in FORBIDDEN:
        assert token not in text, f"{path} contains forbidden stub marker {token}"


def test_desk_read_is_not_a_stub():
    reader = PACK / "desk_read.py"
    text = reader.read_text(encoding="utf-8")
    _assert_not_stub_text(reader, text)
    html = PACK / "_desk_html.py"
    logic = PACK / "_desk_logic.py"
    if html.exists() or logic.exists():
        assert html.exists() and logic.exists(), "split reader must ship both modules"
        h = html.read_text(encoding="utf-8")
        lg = logic.read_text(encoding="utf-8")
        _assert_not_stub_text(html, h)
        _assert_not_stub_text(logic, lg)
        assert html.stat().st_size > 10000, f"_desk_html.py is a stub ({html.stat().st_size} bytes)"
        assert logic.stat().st_size > 10000, f"_desk_logic.py is a stub ({logic.stat().st_size} bytes)"
        blob = text + "\n" + h + "\n" + lg
    else:
        assert reader.stat().st_size > 10000, f"desk_read.py is a stub ({reader.stat().st_size} bytes)"
        blob = text
    assert "def read(" in blob
    assert "def _house_when(" in blob
    assert "place_from_card_text" in blob
    assert "class Happening" in blob


def test_desk_read_exports_event_page_needs():
    from worker.locale_pack import desk_read as dr
    for name in (
        "read",
        "Happening",
        "DeskRead",
        "_TreeBuilder",
        "_Node",
        "_FURNITURE_TAGS",
        "_SCOPED_FURNITURE_TAGS",
        "_in_furniture",
        "_ws",
        "fill_holes",
        "row_key",
    ):
        assert hasattr(dr, name), name


def test_desk_publish_is_not_a_stub():
    pub = PACK / "desk_publish.py"
    text = pub.read_text(encoding="utf-8")
    _assert_not_stub_text(pub, text)
    assert pub.stat().st_size > 10000
    assert "def write_for(" in text
