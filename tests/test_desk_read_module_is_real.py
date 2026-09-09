"""A stub reader must fail CI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "worker" / "locale_pack" / "desk_read.py"


def test_desk_read_is_not_a_stub():
    text = READER.read_text(encoding="utf-8")
    assert READER.stat().st_size > 10000
    assert "def read(" in text
    assert "def _house_when(" in text
