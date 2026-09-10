from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("SEE_LOCAL", "PLACEHOLDER_SEE", "PLACEHOLDER", "SEE_FILE")


def _assert_real(path: Path, *must_contain: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert path.stat().st_size > 10000, f"{path} is a stub ({path.stat().st_size} bytes)"
    for token in FORBIDDEN:
        assert token not in text, f"{path} contains forbidden stub marker {token}"
    for token in must_contain:
        assert token in text, f"{path} missing {token}"


def test_desk_read_is_not_a_stub():
    _assert_real(
        ROOT / "worker" / "locale_pack" / "desk_read.py",
        "def read(",
        "def _house_when(",
        "place_from_card_text",
        "class Happening",
    )


def test_desk_publish_is_not_a_stub():
    _assert_real(
        ROOT / "worker" / "locale_pack" / "desk_publish.py",
        "def write_for(",
    )
