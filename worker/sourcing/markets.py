"""Market registry — Layer 2 of the sourcing model (docs/strategy/SOURCING_MODEL_v1.md).

A MARKET is a data file (sources/markets/<id>.json): boundary + timezone +
locale + source catalog + declared specials. Austin is market #1; a new market
is a new file plus a seeded catalog — never new pipeline code, because the
pathway adapters (Layer 1) are protocol-keyed and market-agnostic.

Fail-closed by design, matching the house convention (ai/claude_provider.py):
an unknown market id, a missing/malformed file, an invalid timezone, a
catalog path that does not exist, or a boundary module/symbol that cannot be
resolved is a loud MarketConfigError — never a silent default to "everywhere"
(which would quietly widen the display boundary, a trust surface).

The boundary is REFERENCED (module + symbol), never mirrored into the market
file: the county set in worker/region/capcog.py stays the single source of
truth, and this module resolves it by import — mechanical identity, no
hand-copied drift (the same rule the harness manifest follows).

Pure/deterministic and file-only (no network, no DB) → unit-testable.
"""
from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MARKETS_DIR = os.path.join(_REPO_ROOT, "sources", "markets")

#: Env var selecting the active market; absent → DEFAULT_MARKET_ID. This is a
#: SELECTION among vetted market files, not a widening: every candidate value
#: still passes the full fail-closed validation below.
MARKET_ENV_VAR = "ONELIVE_MARKET"
DEFAULT_MARKET_ID = "austin"

_REQUIRED_KEYS = ("id", "name", "country", "timezone", "locales", "boundary", "catalog")
_REQUIRED_BOUNDARY_KEYS = ("kind", "module", "counties_symbol", "row_verdict_symbol")
_REQUIRED_SPECIAL_KEYS = ("id", "kind", "description", "impl", "status")


class MarketConfigError(RuntimeError):
    """A market file is missing, malformed, or references something unresolvable."""


@dataclass(frozen=True)
class SpecialSituation:
    """A declared local/regional deviation from the shared pathway behavior.

    Specials are DECLARED here and IMPLEMENTED in the named code path — the
    registry documents and locates them; it never executes them. `status` is
    honest: 'built' (impl live), 'accepted' (a recorded operational tradeoff),
    or 'planned' (declared before its impl lands — visible, never silent).
    """

    id: str
    kind: str
    description: str
    impl: str
    status: str


@dataclass(frozen=True)
class Market:
    """One market, fully resolved. Boundary access is lazy (resolved on call)
    so constructing the registry never imports region modules it doesn't need."""

    id: str
    name: str
    country: str
    timezone: str
    locales: Tuple[str, ...]
    boundary_kind: str
    boundary_module: str
    boundary_counties_symbol: str
    boundary_row_verdict_symbol: str
    catalog_relpath: str
    specials: Tuple[SpecialSituation, ...] = field(default_factory=tuple)

    # -- resolved accessors (fail loud, never guess) --

    def _boundary_attr(self, symbol: str):
        try:
            mod = importlib.import_module(self.boundary_module)
        except ImportError as exc:
            raise MarketConfigError(
                f"market '{self.id}': boundary module "
                f"'{self.boundary_module}' does not import: {exc}"
            ) from exc
        try:
            return getattr(mod, symbol)
        except AttributeError as exc:
            raise MarketConfigError(
                f"market '{self.id}': boundary symbol '{symbol}' not found "
                f"in '{self.boundary_module}'"
            ) from exc

    def boundary_counties(self) -> FrozenSet[str]:
        """The county allowlist, resolved live from the boundary module."""
        counties = self._boundary_attr(self.boundary_counties_symbol)
        if not counties:
            raise MarketConfigError(
                f"market '{self.id}': resolved county set is empty — an empty "
                f"boundary would drop every event; refusing."
            )
        return frozenset(counties)

    def row_verdict(self) -> Callable:
        """The row-level in/out/unknown predicate from the boundary module."""
        fn = self._boundary_attr(self.boundary_row_verdict_symbol)
        if not callable(fn):
            raise MarketConfigError(
                f"market '{self.id}': '{self.boundary_row_verdict_symbol}' "
                f"is not callable"
            )
        return fn

    def catalog_path(self) -> str:
        """Absolute path to this market's source catalog (existence enforced
        at load; re-checked here because loads and reads can be sessions apart)."""
        path = os.path.join(_REPO_ROOT, self.catalog_relpath)
        if not os.path.isfile(path):
            raise MarketConfigError(
                f"market '{self.id}': catalog '{self.catalog_relpath}' not found"
            )
        return path

    def load_catalog(self) -> List[dict]:
        with open(self.catalog_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list) or not data:
            raise MarketConfigError(
                f"market '{self.id}': catalog is not a non-empty list"
            )
        return data


def _fail(market_id: str, msg: str) -> MarketConfigError:
    return MarketConfigError(f"market '{market_id}': {msg}")


def _parse(market_id: str, raw: dict) -> Market:
    for key in _REQUIRED_KEYS:
        if key not in raw:
            raise _fail(market_id, f"missing required key '{key}'")
    if raw["id"] != market_id:
        raise _fail(market_id, f"file id '{raw['id']}' != filename id")

    try:
        ZoneInfo(raw["timezone"])
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise _fail(market_id, f"invalid timezone '{raw['timezone']}'") from exc

    locales = raw["locales"]
    if not isinstance(locales, list) or not locales or not all(
        isinstance(l, str) and l.strip() for l in locales
    ):
        raise _fail(market_id, "locales must be a non-empty list of strings")

    boundary = raw["boundary"]
    if not isinstance(boundary, dict):
        raise _fail(market_id, "boundary must be an object")
    for key in _REQUIRED_BOUNDARY_KEYS:
        if not boundary.get(key):
            raise _fail(market_id, f"boundary missing required key '{key}'")
    if boundary["kind"] != "county_allowlist":
        # The only kind built today. A new kind (e.g. polygon, postal-code set
        # for non-US markets) lands with its resolver — declaring one that
        # nothing can resolve is a config defect, refused loudly.
        raise _fail(
            market_id,
            f"unknown boundary kind '{boundary['kind']}' — known: county_allowlist",
        )

    catalog_rel = raw["catalog"]
    if not isinstance(catalog_rel, str) or not os.path.isfile(
        os.path.join(_REPO_ROOT, catalog_rel)
    ):
        raise _fail(market_id, f"catalog '{catalog_rel}' not found in repo")

    specials: List[SpecialSituation] = []
    for i, s in enumerate(raw.get("specials") or []):
        if not isinstance(s, dict):
            raise _fail(market_id, f"specials[{i}] is not an object")
        missing = [k for k in _REQUIRED_SPECIAL_KEYS if not s.get(k)]
        if missing:
            raise _fail(market_id, f"specials[{i}] missing {missing}")
        if s["status"] not in ("built", "accepted", "planned"):
            raise _fail(
                market_id,
                f"specials[{i}] status '{s['status']}' — known: built/accepted/planned",
            )
        specials.append(
            SpecialSituation(
                id=s["id"], kind=s["kind"], description=s["description"],
                impl=s["impl"], status=s["status"],
            )
        )

    return Market(
        id=raw["id"],
        name=raw["name"],
        country=raw["country"],
        timezone=raw["timezone"],
        locales=tuple(locales),
        boundary_kind=boundary["kind"],
        boundary_module=boundary["module"],
        boundary_counties_symbol=boundary["counties_symbol"],
        boundary_row_verdict_symbol=boundary["row_verdict_symbol"],
        catalog_relpath=catalog_rel,
        specials=tuple(specials),
    )


def available_markets(markets_dir: Optional[str] = None) -> List[str]:
    """Sorted ids of every market file present (existence, not validity)."""
    d = markets_dir or MARKETS_DIR
    if not os.path.isdir(d):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".json")
    )


def get_market(
    market_id: Optional[str] = None, markets_dir: Optional[str] = None
) -> Market:
    """Load and validate one market. Selection order: explicit arg →
    $ONELIVE_MARKET → DEFAULT_MARKET_ID. Every path is fully validated;
    there is no lenient mode."""
    d = markets_dir or MARKETS_DIR
    mid = (market_id or os.environ.get(MARKET_ENV_VAR) or DEFAULT_MARKET_ID).strip()
    if not mid:
        raise MarketConfigError("empty market id")
    path = os.path.join(d, f"{mid}.json")
    if not os.path.isfile(path):
        raise MarketConfigError(
            f"unknown market '{mid}' — available: {available_markets(d) or 'none'}"
        )
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise MarketConfigError(f"market '{mid}': unreadable/malformed: {exc}") from exc
    if not isinstance(raw, dict):
        raise MarketConfigError(f"market '{mid}': top level is not an object")
    return _parse(mid, raw)
