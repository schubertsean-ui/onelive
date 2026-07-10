"""Loader for the data-driven source-trust configuration.

All numeric constants for the three trust mechanisms (credibility weighting,
priority ranking, reputation decay/growth) are stored in
``sources/trust_config.json`` rather than hardcoded, so the product owner can
flex and iterate on the values as the platform grows. This module reads that
file and hands typed slices of it to the trust modules.

At runtime the DB config tables (migration 0008) are authoritative; this JSON is
the fallback and the seed source, so the pure-logic modules and tests work with
no database. Point ``ONELIVE_TRUST_CONFIG`` at another file to override.
"""
import json
import os
from functools import lru_cache

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sources",
    "trust_config.json",
)


def config_path() -> str:
    return os.getenv("ONELIVE_TRUST_CONFIG", _DEFAULT_PATH)


@lru_cache(maxsize=None)
def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    """Return the full parsed config (cached per path)."""
    return _load(config_path())


def reload_config() -> None:
    """Drop the cache so a later ``load_config`` re-reads from disk.

    Useful in tests that write a temporary config and set ONELIVE_TRUST_CONFIG.
    """
    _load.cache_clear()


# --- typed accessors -------------------------------------------------------

def source_type_weights(config: dict | None = None) -> dict[str, float]:
    cfg = config or load_config()
    return {k: float(v) for k, v in cfg["source_type_weights"].items()}


def default_source_type_weight(config: dict | None = None) -> float:
    cfg = config or load_config()
    return float(cfg["default_source_type_weight"])


def confidence_weight_thresholds(config: dict | None = None) -> list[dict]:
    """Thresholds as a list of {state, min_weight}, sorted high→low weight."""
    cfg = config or load_config()
    rows = [
        {"state": r["state"], "min_weight": float(r["min_weight"])}
        for r in cfg["confidence_weight_thresholds"]
    ]
    return sorted(rows, key=lambda r: r["min_weight"], reverse=True)


def priority_formula(version: str | None = None, config: dict | None = None) -> tuple[str, dict[str, float]]:
    """Return (version, coefficients) for the priority ranking model.

    Defaults to the config's ``current_version`` so callers get the live formula
    but can pin a specific version for reproducible/audited scoring.
    """
    cfg = config or load_config()
    pf = cfg["priority_formula"]
    ver = version or pf["current_version"]
    if ver not in pf["versions"]:
        raise KeyError(f"unknown priority_formula version: {ver!r}")
    coeffs = {k: float(v) for k, v in pf["versions"][ver]["coefficients"].items()}
    return ver, coeffs


def priority_bands(config: dict | None = None) -> list[dict]:
    """Bands as a list of {band, label, min_score}, sorted high→low min_score."""
    cfg = config or load_config()
    rows = [
        {"band": b["band"], "label": b["label"], "min_score": float(b["min_score"])}
        for b in cfg["priority_bands"]
    ]
    return sorted(rows, key=lambda b: b["min_score"], reverse=True)


def reputation_params(version: str | None = None, config: dict | None = None) -> tuple[str, dict[str, float]]:
    """Return (version, params) for the reputation decay/growth function."""
    cfg = config or load_config()
    dg = cfg["reputation_decay_growth"]
    ver = version or dg["current_version"]
    if ver not in dg["versions"]:
        raise KeyError(f"unknown reputation_decay_growth version: {ver!r}")
    return ver, {k: float(v) for k, v in dg["versions"][ver].items()}
