"""CI fails until apply_to_writes is on the ingest path and the reader is not a stub."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apply_to_writes_is_on_the_path():
    ingest = (ROOT / "tools" / "desk_ingest.py").read_text(encoding="utf-8")
    boot = (ROOT / "worker" / "locale_pack" / "__init__.py").read_text(encoding="utf-8")
    assert "apply_to_writes" in ingest or "apply_to_writes" in boot
    assert "ticket_a_apply" in ingest or "ticket_a_apply" in boot


def test_desk_read_is_not_a_stub():
    path = ROOT / "worker" / "locale_pack" / "desk_read.py"
    text = path.read_text(encoding="utf-8")
    assert path.stat().st_size > 10000
    assert "PLACEHOLDER" not in text
    assert "def _house_when(" in text
