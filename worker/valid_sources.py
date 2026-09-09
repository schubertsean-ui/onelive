"""Valid Source Library. Validated door → promote on 1."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "sources" / "valid_sources.json"


@lru_cache(maxsize=1)
def _lib() -> dict:
    return json.loads(LIB.read_text(encoding="utf-8"))


def validated_ids() -> set[str]:
    return {row["id"] for row in _lib().get("validated", []) if row.get("id")}


def validated_classes() -> set[str]:
    extra = {row.get("class") for row in _lib().get("validated", []) if row.get("class")}
    named = set(_lib().get("validated_classes") or [])
    return {c for c in extra | named if c}


def unvalidated_classes() -> set[str]:
    return set(_lib().get("unvalidated_classes") or ["social"])


def is_validated(*, source_class: str | None = None, door_id: str | None = None) -> bool:
    if door_id and door_id in validated_ids():
        return True
    if source_class and source_class in validated_classes():
        return True
    return False
