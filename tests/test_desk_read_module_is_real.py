from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desk_read_is_not_a_stub():
    reader = ROOT / "worker" / "locale_pack" / "desk_read.py"
    text = reader.read_text(encoding="utf-8")
    assert reader.stat().st_size > 10000
    assert "def read(" in text
    assert "def _house_when(" in text


def test_desk_publish_is_not_a_stub():
    pub = ROOT / "worker" / "locale_pack" / "desk_publish.py"
    text = pub.read_text(encoding="utf-8")
    assert pub.stat().st_size > 10000
    assert "def write_for(" in text
