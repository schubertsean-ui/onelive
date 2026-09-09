"""A stub reader or publisher must fail CI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desk_read_is_not_a_stub():
    path = ROOT / "worker" / "locale_pack" / "desk_read.py"
    text = path.read_text(encoding="utf-8")
    assert path.stat().st_size > 10000
    assert "def read(" in text
    assert "def _house_when(" in text
    assert "PLACEHOLDER" not in text


def test_desk_publish_is_not_a_stub():
    path = ROOT / "worker" / "locale_pack" / "desk_publish.py"
    text = path.read_text(encoding="utf-8")
    assert path.stat().st_size > 10000
    assert "def write_for(" in text
    assert "def registration_for(" in text
    assert "PLACEHOLDER" not in text
    assert "see-file" not in text
