"""A stub publisher or reader must fail CI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "worker" / "locale_pack" / "desk_publish.py"
READER = ROOT / "worker" / "locale_pack" / "desk_read.py"


def test_desk_publish_is_not_a_stub():
    text = PUBLISH.read_text(encoding="utf-8")
    assert PUBLISH.stat().st_size > 10000
    assert "def write_for(" in text
    assert "existence_hold" in text or "from worker.locale_pack.existence import" in text
    assert "PLACEHOLDER" not in text
    assert text.strip() != "see-file"


def test_desk_read_is_not_a_stub():
    text = READER.read_text(encoding="utf-8")
    assert READER.stat().st_size > 10000
    assert "def read(" in text
    assert "def _house_when(" in text
    assert "PLACEHOLDER" not in text
