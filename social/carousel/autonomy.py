"""Founder autonomy ratification record — the sign-off path out of L0.

Greppable summary: founder-directed 2026-07-24 ("at some point soon I will
want the AI to do everything and remove the human from the loop. So set up
a process for me to sign off on that."). Removing the human from posting
is a trust-invariant change, so it happens ONLY through this record:
social/carousel/AUTONOMY_RATIFICATION.json, committed via the three-step
process in spec §10 (evidence pack -> signed decision record -> PR), and
AUTHENTICATED (evaluator r1): any level above L0 must carry an HMAC-SHA256
signature over the record's canonical payload, keyed by the founder-held
approval key (ONELIVE_APPROVAL_KEY — founder-minted, never in the repo,
never handed to agent sessions), produced via sign_autonomy_record() at
ratification time. Physics: no file = L0 (human approves every post); a
malformed, unsigned, or wrong-signature record makes load_policy raise,
and the publish gate treats that as refuse-everything — a broken or bogus
ratification never fails open into autonomy. Any change to this module or
the record is trust-path (mandatory non-Claude evaluator review).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field

DEFAULT_RECORD_PATH = os.path.join(os.path.dirname(__file__), "AUTONOMY_RATIFICATION.json")

LEVELS = ("L0", "L1", "L2")

_REQUIRED_ATTRIBUTION = ("founder", "ratified_on", "decision_record")


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


def _canonical_payload(data: dict) -> bytes:
    return json.dumps(
        {k: v for k, v in data.items() if k != "signature"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sign_autonomy_record(record: dict, key: str | bytes) -> str:
    """Produce the record's signature. Run by the FOUNDER at ratification
    time with the founder-held key — agents never hold it, so an agent
    cannot mint a grant that verifies."""
    if not key:
        raise AutonomyRecordError("signing requires a non-empty key")
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    return hmac.new(key_bytes, _canonical_payload(record), hashlib.sha256).hexdigest()


def load_policy(path: str | None = None, verification_key: str | bytes | None = None) -> AutonomyPolicy:
    """Read and AUTHENTICATE the ratification record. Absent file -> L0 (the
    safe default is the status quo). Any structural defect, missing key, or
    signature mismatch raises AutonomyRecordError, and the caller must treat
    that as refuse-everything, never as autonomy."""
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
    for key in _REQUIRED_ATTRIBUTION:
        if not data.get(key):
            raise AutonomyRecordError(
                f"autonomy record level {level} missing required field {key!r} — "
                "an unattributed grant is no grant"
            )
    # Authentication (evaluator r1): schema presence is not ratification.
    # The signature must verify under the founder-held key; no key available
    # to verify with = no autonomy, loudly.
    signature = data.get("signature")
    if not signature:
        raise AutonomyRecordError(
            f"autonomy record level {level} is UNSIGNED — a grant that cannot "
            "be authenticated grants nothing"
        )
    if verification_key is None:
        verification_key = os.environ.get("ONELIVE_APPROVAL_KEY") or None
    if not verification_key:
        raise AutonomyRecordError(
            "no verification key available (ONELIVE_APPROVAL_KEY unset) — "
            "cannot authenticate the autonomy grant, refusing"
        )
    expected = sign_autonomy_record(data, verification_key)
    if not hmac.compare_digest(expected, str(signature)):
        raise AutonomyRecordError(
            "autonomy record signature does not verify under the approval key — "
            "refusing the grant"
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
