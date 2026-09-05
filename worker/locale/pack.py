"""Locale packs — the door list is DATA, the type system is code.

Founder, this session's ticket: "Locale/kind/door/intake/via are the types. No
Austin hardcoded in law or worker defaults." So this module knows the SHAPE of
a locale pack and nothing about any particular place: every brand, URL, county
and phrasing lives in `sources/locale_packs/<locale_id>.json`, and a second
locale is a second FILE, never an edit here.

    hunt(locale_id) -> tuple[Door, ...]

is the whole surface. It has no default argument, deliberately: a caller that
does not name a locale gets a TypeError rather than somebody's home town.

WHY A PACK RATHER THAN MORE CATALOG ROWS. `sources/master_sources_catalog_120.json`
answers "which sources may we fetch, under what declared access posture"
(`worker/sourcing/source_class.py` grades it A–F). That is a per-SOURCE question.
A pack answers a different one: "if a person in this locale went looking, which
desks would they open?" — the consumer's question, with the query phrasings that
find them and the honest grade of each door. The two are complementary, and the
pack states its evidence grade per door so a `found_unverified` URL can never be
mistaken for one we actually read.

THE SIX DOOR TYPES are the founder's, verbatim, and they are a TRUST statement
rather than a topic: `local_desk`, `marketplace`, `civic`, `official_list` are
doors a happening may be listed FROM (ONE-LIVE-TRUST.md: one trusted door is
enough to exist); `wall` is class D — never fetched, never bypassed; `junk` is
the doctrine's own "SEO scrapers / copy farms — lead only, never a listing".

FAIL LOUDLY (CLAUDE.md prime directive 1). An unknown locale, an unknown door
type, an unknown intake, a public door carrying a `blocked_reason`, or a
non-public door carrying none, all raise `LocalePackError` at load. A pack that
half-parses would silently narrow coverage, which is the one direction Coverage
Law forbids.

Pure: stdlib only, no network, no DB, no clock, no import from the pipeline.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

#: Where packs live. A caller may override for tests; there is no other knob.
PACKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "sources", "locale_packs",
)

#: The founder's six door types. Order is the TRUST order used for sorting, most
#: trusted first, so a caller that takes the first N doors takes the best N.
DOOR_TYPES: Tuple[str, ...] = (
    "local_desk", "civic", "official_list", "marketplace", "wall", "junk",
)

#: Door types a happening may be LISTED from — ONE-LIVE-TRUST.md's trusted doors
#: plus marketplaces (which list, but sit in the corroboration tier downstream;
#: that is a promote question, not an existence one).
LISTABLE_DOOR_TYPES = frozenset({"local_desk", "civic", "official_list", "marketplace"})

#: How a door is read. `none` means there is no read path we may use.
INTAKES: Tuple[str, ...] = ("html", "json_ld", "ics", "rss", "api", "none")

#: The kind vocabulary is the PACK's (`query_grammar.kinds`), never this
#: module's — no category weighting (ONE-LIVE-VISION.md). The one kind code
#: knows is the fallback, because "unknown kind = other" is a rule, not data.
KIND_OTHER = "other"

#: Evidence grades a door may carry. `found_unverified` is the honest label for
#: a URL named from a consumer query but never fetched.
EVIDENCE_GRADES: Tuple[str, ...] = ("founder_named", "catalogued", "found_unverified")


class LocalePackError(ValueError):
    """A pack is missing, malformed, or states something the type system does
    not allow. Always raised — never downgraded to a warning and a shorter list.
    """


@dataclass(frozen=True)
class Door:
    """One door in one locale, exactly as the pack states it."""

    door_id: str
    brand: str
    via: Optional[str]
    door_type: str
    url: str
    public: bool
    intake: str
    kind_scope: Tuple[str, ...]
    covers: Tuple[str, ...]
    blocked_reason: Optional[str]
    evidence: str
    locale_id: str

    @property
    def readable(self) -> bool:
        """True when `read()` may be pointed at this door: it is a listable
        door type, it loads without login, and it has a read path.

        This is the ONLY gate on the read path, and it is a DOOR test — never a
        field test on a happening (ONE-LIVE-TRUST.md: "If a gate answers
        existence with a field or mutation test, the gate is wrong").
        """
        return (
            self.door_type in LISTABLE_DOOR_TYPES
            and self.public
            and self.intake != "none"
        )

    @property
    def declared_kind(self) -> str:
        """The kind this door declares for everything behind it, or `other`.

        A door scoped to exactly one kind (a station's concert calendar, a
        family desk) states that kind for its rows. Anything else — `any`, or
        several — is `other`: we do not infer a kind from a title, because
        guessing a category is the fabrication the charter forbids and would
        also weight one category over another.
        """
        if len(self.kind_scope) == 1 and self.kind_scope[0] not in ("any", ""):
            return self.kind_scope[0]
        return KIND_OTHER


@dataclass(frozen=True)
class LocalePack:
    locale_id: str
    label: str
    scale: str
    parent_locale_id: Optional[str]
    query_grammar: Mapping[str, Any]
    doors: Tuple[Door, ...]
    #: IANA timezone this locale keeps its nights on, when the pack states one.
    #: Optional here and REQUIRED by the caller that needs it: a locale's clock
    #: is pack DATA like everything else, so nothing downstream may fall back to
    #: a hardcoded home town (`worker.locale.desk_union` raises instead).
    timezone: Optional[str] = None

    @property
    def kinds(self) -> Tuple[str, ...]:
        """This locale's kind vocabulary — OUR kinds, stated once in the pack.

        Every consumer of "what kinds are there?" reads it from here, so a
        mapping from some desk's taxonomy is validated against the same list the
        query grammar is built from, and no second vocabulary can drift into
        existence.
        """
        return tuple(self.query_grammar.get("kinds") or ())

    def queries(self) -> Tuple[str, ...]:
        """The pack's consumer queries, fully expanded: every template crossed
        with every place, and (for a template naming `{kind}`) every kind.

        Deterministic and de-duplicated, in template × place × kind order, so a
        run is reproducible and two runs are diffable.
        """
        templates = tuple(self.query_grammar.get("templates") or ())
        places = tuple(self.query_grammar.get("places") or ())
        kinds = tuple(self.query_grammar.get("kinds") or ())
        out: list = []
        seen = set()
        for template in templates:
            needs_kind = "{kind}" in template
            for place in places:
                for kind in (kinds if needs_kind else ("",)):
                    q = template.replace("{place}", place).replace("{kind}", kind)
                    if q not in seen:
                        seen.add(q)
                        out.append(q)
        return tuple(out)


def _require(obj: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in obj:
        raise LocalePackError(f"{where}: missing required key {key!r}")
    return obj[key]


def _str_tuple(value: Any, key: str, where: str) -> Tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
        raise LocalePackError(f"{where}: {key!r} must be a list of strings, got {value!r}")
    return tuple(value)


def _door_from(raw: Any, *, locale_id: str, index: int) -> Door:
    where = f"{locale_id} door[{index}]"
    if not isinstance(raw, dict):
        raise LocalePackError(f"{where}: each door must be an object, got {type(raw).__name__}")
    door_id = _require(raw, "door_id", where)
    where = f"{locale_id} door {door_id!r}"

    door_type = _require(raw, "door_type", where)
    if door_type not in DOOR_TYPES:
        raise LocalePackError(
            f"{where}: door_type {door_type!r} is not one of {DOOR_TYPES}")
    intake = _require(raw, "intake", where)
    if intake not in INTAKES:
        raise LocalePackError(f"{where}: intake {intake!r} is not one of {INTAKES}")
    evidence = _require(raw, "evidence", where)
    if evidence not in EVIDENCE_GRADES:
        raise LocalePackError(
            f"{where}: evidence {evidence!r} is not one of {EVIDENCE_GRADES}")
    public = _require(raw, "public", where)
    if not isinstance(public, bool):
        raise LocalePackError(f"{where}: public must be true or false, got {public!r}")
    blocked_reason = raw.get("blocked_reason")
    if blocked_reason is not None and not isinstance(blocked_reason, str):
        raise LocalePackError(
            f"{where}: blocked_reason must be a string or null, got {blocked_reason!r}")

    # The two directions a door can lie about itself, both caught here rather
    # than discovered by a fetch: a door we cannot read must SAY why (otherwise
    # it reads as an unexplained absence), and a door we can read must not carry
    # a reason it is blocked (otherwise the table shows a block that isn't one).
    if not public and not blocked_reason:
        raise LocalePackError(
            f"{where}: a non-public door must state a blocked_reason — an "
            f"unexplained absence is how coverage silently narrows")
    if public and door_type not in ("wall", "junk") and intake != "none" and blocked_reason:
        raise LocalePackError(
            f"{where}: a public, readable door must not carry a blocked_reason "
            f"({blocked_reason!r})")
    if door_type == "wall" and public:
        raise LocalePackError(
            f"{where}: a 'wall' door is class D by definition and cannot be public")

    return Door(
        door_id=door_id,
        brand=_require(raw, "brand", where),
        via=raw.get("via"),
        door_type=door_type,
        url=_require(raw, "url", where),
        public=public,
        intake=intake,
        kind_scope=_str_tuple(raw.get("kind_scope") or [], "kind_scope", where),
        covers=_str_tuple(raw.get("covers") or [], "covers", where),
        blocked_reason=blocked_reason,
        evidence=evidence,
        locale_id=locale_id,
    )


def load_pack(locale_id: str, *, packs_dir: Optional[str] = None) -> LocalePack:
    """Read and validate one locale pack. Raises `LocalePackError` on anything
    it cannot vouch for — there is no partial pack.
    """
    if not isinstance(locale_id, str) or not locale_id.strip():
        raise LocalePackError(f"locale_id must be a non-empty string, got {locale_id!r}")
    # A locale id names a FILE, so it may not steer the path: no separators, no
    # traversal. Refused rather than sanitised, so a typo is visible.
    if locale_id != os.path.basename(locale_id) or locale_id in (".", ".."):
        raise LocalePackError(f"locale_id {locale_id!r} is not a plain pack name")
    directory = packs_dir or PACKS_DIR
    path = os.path.join(directory, f"{locale_id}.json")
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        available = sorted(
            f[:-5] for f in os.listdir(directory) if f.endswith(".json")
        ) if os.path.isdir(directory) else []
        raise LocalePackError(
            f"no locale pack for {locale_id!r} at {path} (have: {available})") from exc
    except (OSError, ValueError) as exc:
        raise LocalePackError(f"locale pack {path} is unreadable: {exc}") from exc

    locale = _require(raw, "locale", "pack")
    if not isinstance(locale, dict):
        raise LocalePackError("pack: 'locale' must be an object")
    declared = _require(locale, "locale_id", "pack.locale")
    if declared != locale_id:
        raise LocalePackError(
            f"pack {path} declares locale_id {declared!r} but is filed as {locale_id!r}")

    doors_raw = _require(raw, "doors", "pack")
    if not isinstance(doors_raw, list) or not doors_raw:
        raise LocalePackError("pack: 'doors' must be a non-empty list")
    doors = tuple(
        _door_from(d, locale_id=locale_id, index=i) for i, d in enumerate(doors_raw)
    )
    seen: Dict[str, int] = {}
    for i, door in enumerate(doors):
        if door.door_id in seen:
            raise LocalePackError(
                f"pack {path}: duplicate door_id {door.door_id!r} "
                f"(doors {seen[door.door_id]} and {i})")
        seen[door.door_id] = i

    grammar = raw.get("query_grammar") or {}
    if not isinstance(grammar, dict):
        raise LocalePackError("pack: 'query_grammar' must be an object")

    # Stated or absent, never half-stated: a `timezone` key that is not a
    # non-empty string raises here rather than reaching a caller as None and
    # reading like a pack that simply said nothing.
    timezone = locale.get("timezone")
    if timezone is not None and (not isinstance(timezone, str) or not timezone.strip()):
        raise LocalePackError(
            f"pack.locale: 'timezone' must be a non-empty IANA name when stated, "
            f"got {timezone!r}")

    return LocalePack(
        locale_id=locale_id,
        label=_require(locale, "label", "pack.locale"),
        scale=locale.get("scale") or "region",
        parent_locale_id=locale.get("parent_locale_id"),
        query_grammar=grammar,
        doors=doors,
        timezone=timezone.strip() if isinstance(timezone, str) else None,
    )


def hunt(locale_id: str, *, packs_dir: Optional[str] = None,
         door_types: Optional[Sequence[str]] = None) -> Tuple[Door, ...]:
    """Every door this locale knows, typed, most-trusted first.

    No default locale: naming the place is the caller's job, and a default here
    would be exactly the hardcoded home town the founder ruled out.

    `door_types` narrows the result to the named types (validated against
    `DOOR_TYPES`, so a typo raises instead of returning an empty list that reads
    like "this locale has no desks").
    """
    pack = load_pack(locale_id, packs_dir=packs_dir)
    doors = pack.doors
    if door_types is not None:
        wanted = tuple(door_types)
        unknown = [t for t in wanted if t not in DOOR_TYPES]
        if unknown:
            raise LocalePackError(
                f"unknown door_type(s) {unknown} — known types are {DOOR_TYPES}")
        doors = tuple(d for d in doors if d.door_type in wanted)
    order = {t: i for i, t in enumerate(DOOR_TYPES)}
    return tuple(sorted(doors, key=lambda d: (order[d.door_type], d.door_id)))


def public_desks(locale_id: str, *, packs_dir: Optional[str] = None) -> Tuple[Door, ...]:
    """The subset of `hunt` that `worker.locale.desk_read.read` may be given."""
    return tuple(d for d in hunt(locale_id, packs_dir=packs_dir) if d.readable)


def available_locales(*, packs_dir: Optional[str] = None) -> Tuple[str, ...]:
    """Every locale id with a pack on disk, sorted. Empty when the directory is
    absent — a missing directory is reported by `load_pack`, not guessed at here.
    """
    directory = packs_dir or PACKS_DIR
    if not os.path.isdir(directory):
        return ()
    return tuple(sorted(f[:-5] for f in os.listdir(directory) if f.endswith(".json")))
