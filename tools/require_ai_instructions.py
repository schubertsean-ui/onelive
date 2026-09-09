"""Fail CI if agent entrypoints do not require docs/AI_INSTRUCTIONS.md."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDLE = "docs/AI_INSTRUCTIONS.md"

REQUIRED = [
    "CLAUDE.md",
    "AGENTS.md",
    ".github/workflows/claude.yml",
    "docs/AI_INSTRUCTIONS.md",
    "ONE-LIVE-VISION.md",
    "docs/TICKET_B_AUTOMATIONS.md",
]


def missing() -> list[str]:
    bad = []
    for rel in REQUIRED:
        p = ROOT / rel
        if not p.is_file():
            bad.append(f"missing file {rel}")
            continue
        text = p.read_text(encoding="utf-8")
        if NEEDLE not in text:
            bad.append(rel)
    return bad


def main() -> int:
    bad = missing()
    if bad:
        print("require_ai_instructions FAIL:")
        for row in bad:
            print(" -", row)
        return 1
    print("require_ai_instructions PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
