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
    # Content binding (r10): the grant covers EXACTLY this render surface —
    # publish_gate refuses when the live renderer_fingerprint() differs.
    renderer_version: str = ""
    # Enumerated series the grant covers (empty tuple on L2 = all).
    series_keys: tuple[str, ...] = field(default_factory=tuple)
    # Founder-stated cadence ceiling; mechanically enforced at release
    # time by publish_gate against its registered release journal (r11) —
    # no journal, no auto-release.
    max_releases_per_day: int = 0

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


def load_policy() -> AutonomyPolicy:
    """Read and AUTHENTICATE the ratification record from its CANONICAL
    committed path only (r11 nit: the arbitrary-path parameter is gone —
    a path argument on a custody loader is a standing invitation to point
    it somewhere else; hermetic tests monkeypatch DEFAULT_RECORD_PATH
    instead). Absent file -> L0 (the safe default is the status quo). The
    verification key comes from the deployment environment ONLY (r3: never
    a parameter — the subject of a grant must not choose the key that
    verifies it). Any structural defect, missing key, or signature
    mismatch raises AutonomyRecordError, and the caller must treat that as
    refuse-everything, never as autonomy."""
    record_path = DEFAULT_RECORD_PATH
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
    # Content binding (r10): a grant not tied to a frozen renderer and a
    # stated cadence ceiling is too broad to be a grant.
    if not data.get("renderer_version"):
        raise AutonomyRecordError(
            f"autonomy record level {level} missing renderer_version — the "
            "grant must freeze the exact render surface it covers"
        )
    if not isinstance(data.get("max_releases_per_day"), int) or data["max_releases_per_day"] < 1:
        raise AutonomyRecordError(
            f"autonomy record level {level} missing a positive "
            "max_releases_per_day cadence ceiling"
        )
    if level == "L1" and not data.get("series_keys"):
        raise AutonomyRecordError(
            "L1 record must enumerate series_keys — standing approval covers "
            "named series, never everything"
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
    verification_key = os.environ.get("ONELIVE_APPROVAL_KEY")
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
        renderer_version=data["renderer_version"],
        series_keys=tuple(data.get("series_keys") or ()),
        max_releases_per_day=data["max_releases_per_day"],
    )
