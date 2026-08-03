"""Golden-set regression for the Spark Line faithfulness gate.

Each golden case pins a (material, text) pair to an expected verdict — `pass`
(the gate accepts it) or `reject` (the gate refuses, with the class of
violation). This is the machine-consumed regression memory the Construction
Loop requires: a fabricated-fact or mis-shaped line that the gate must keep
refusing forever lives here as a row, not as prose.

The harness is model-free and deterministic — it exercises `assert_faithful`
only, so it runs in CI with no provider and no spend.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .gate import assert_faithful
from .types import DescriptorFoundryError, SourceMaterial

GOLDEN_PATH = os.path.join(os.path.dirname(__file__), "golden", "spark_line_golden_v1.jsonl")


@dataclass(frozen=True)
class GoldenOutcome:
    case_id: str
    expected: str          # "pass" | "reject"
    actual: str            # "pass" | "reject"
    ok: bool
    detail: str            # the refusal message, when rejected


def _load(path: str) -> list[dict]:
    cases: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))
    return cases


def run_golden(path: str = GOLDEN_PATH) -> list[GoldenOutcome]:
    """Run every golden case and return per-case outcomes. Never raises on a
    gate refusal — a refusal is data here; the caller asserts the verdicts."""
    outcomes: list[GoldenOutcome] = []
    for case in _load(path):
        material = SourceMaterial(
            artist=case.get("artist", ""),
            texts=tuple(case.get("texts", ())),
            refs=tuple(case.get("refs", ())),
        )
        expected = case["expect"]
        try:
            assert_faithful(case["text"], material)
            actual, detail = "pass", ""
        except DescriptorFoundryError as exc:
            actual, detail = "reject", str(exc)
        outcomes.append(
            GoldenOutcome(
                case_id=case["id"],
                expected=expected,
                actual=actual,
                ok=(expected == actual),
                detail=detail,
            )
        )
    return outcomes
