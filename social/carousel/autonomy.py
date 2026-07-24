"""Founder autonomy ratification record — the sign-off path out of L0.

Greppable summary: founder-directed 2026-07-24 ("at some point soon I will
want the AI to do everything and remove the human from the loop. So set up
a process for me to sign off on that."). Removing the human from posting
is a trust-invariant change, so it happens ONLY through this record:
social/carousel/AUTONOMY_RATIFICATION.json, committed via the three-step
process in spec §10 (evidence pack -> signed decision record -> PR).
Physics: no file = L0 (human approves every post); a malformed file makes
load_policy raise, and the publish gate treats that as refuse-everything —
a broken ratification never fails open into autonomy. Any change to this
module or the record is trust-path (mandatory non-Claude evaluator review).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

DEFAULT_RECORD_PATH = os.path.join(os.path.dirname(__file__), "AUTONOMY_RATIFICATION.json")

LEVELS = ("L0", "L1", "L2")


class AutonomyRecordError(ValueError):
    """A ratification record exists but cannot be trusted — fail closed."""


@dataclass(frozen=True)
class AutonomyPolicy:
    """The in-memory shape of the founder's standing autonomy grant."""

    level: str
    # L1 only: the exact (surface, tier) combinations auto-release covers.
    scopes: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    founder: str = ""
    ratified_on: str = ""
    decision_record: str = ""

    def allows_auto_release(self, surface: str, tier: str) -> bool:
        if self.level == "L0":
            return False
        if self.level == "L2":
            return True
        return (surface, tier) in self.scopes


L0_POLICY = AutonomyPolicy(level="L0")


def load_policy(path: str | None = None) -> AutonomyPolicy:
    """Read the ratification record. Absent file -> L0 (the safe default is
    the status quo). Any structural defect raises AutonomyRecordError, and
    the caller must treat that as refuse-everything, never as L2."""
    record_path = path or DEFAULT_RECORD_PATH
    if not os.path.exists(record_path):
        return L0_POLICY
    try:
        with open(record_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise AutonomyRecordError(f"unreadable autonomy record {record_path}: {exc}") from exc

    level = data.get("level")
    if level not in LEVELS:
        raise AutonomyRecordError(f"autonomy record has unknown level {level!r}")
    if level == "L0":
        return L0_POLICY
    for key in ("founder", "ratified_on", "decision_record"):
        if not data.get(key):
            raise AutonomyRecordError(
                f"autonomy record level {level} missing required field {key!r} — "
                "an unattributed grant is no grant"
            )
    scopes: list[tuple[str, str]] = []
    if level == "L1":
        raw_scopes = data.get("scopes")
        if not raw_scopes:
            raise AutonomyRecordError("L1 record must enumerate scopes (surface, tier)")
        for item in raw_scopes:
            if (
                not isinstance(item, dict)
                or not item.get("surface")
                or not item.get("tier")
            ):
                raise AutonomyRecordError(f"malformed L1 scope entry: {item!r}")
            scopes.append((item["surface"], item["tier"]))
    return AutonomyPolicy(
        level=level,
        scopes=tuple(scopes),
        founder=data["founder"],
        ratified_on=data["ratified_on"],
        decision_record=data["decision_record"],
    )
