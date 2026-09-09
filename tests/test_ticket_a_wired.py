"""CI fails until ingest calls apply_to_writes and the reader is not a stub."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_desk_ingest_calls_apply_to_writes():
    text = (ROOT / "tools" / "desk_ingest.py").read_text(encoding="utf-8")
    assert "apply_to_writes" in text
    assert "ticket_a_apply" in text


def test_desk_read_is_not_a_stub():
    path = ROOT / "worker" / "locale_pack" / "desk_read.py"
    text = path.read_text(encoding="utf-8")
    assert path.stat().st_size > 10000
    assert "PLACEHOLDER" not in text
    assert "def _house_when(" in text
