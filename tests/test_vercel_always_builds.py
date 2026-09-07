"""Vercel must actually build, including on docs-only commits.

Skip-if-unchanged on this project reports as GitHub FAILURE
('Deployment has failed') and leaves master without a production
deploy. ignoreCommand `exit 1` means never skip. Pin it.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_ignore_command_never_skips():
    cfg = json.loads((ROOT / "web" / "vercel.json").read_text())
    assert cfg["ignoreCommand"] == "exit 1", (
        "A skip here paints the GitHub Vercel check red and skips the "
        "production deploy. Always build."
    )
