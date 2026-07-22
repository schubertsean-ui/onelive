"""Static integrity of the generated FLOW prototype (no browser needed).

Mechanizes what previously lived in changelog prose (evaluator r3 nit,
PR #45) — the properties that made the founder's no-JS viewer rounds
fail, checked structurally on the committed HTML:

1. Every show in the dataset renders as a CARD with a visible title —
   bound to the room element itself, not to any `.who` anywhere in the
   document (evaluator r4: the first version could pass on a lens title
   while the card's was missing — a test that cannot fail for the
   property it claims is false confidence).
2. Every card carries the visible on-surface fixture note (evaluator
   r4: cards are deep-linkable surfaces; a disclosure hidden behind the
   `?` sheet is not a visible local boundary).
3. Every in-page anchor (#x) resolves to a real element id — a broken
   door is a dead tap in a no-JS viewer, invisible to a JS-based check.
4. EVERY lens carries the on-surface fixture note (evaluator r3:
   deep-linkable surfaces need a local truth boundary).
5. The CSS that makes lenses open without JavaScript (:target) and stay
   closed otherwise is present.

Scope honesty: this proves structure, not pixels — visual verification
still happens in the headless pass before founder delivery.
"""
import importlib.util
import pathlib
import re
from html.parser import HTMLParser

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_HTML = (_ROOT / "design" / "proposals" / "direction-4-flow.html").read_text()

_spec = importlib.util.spec_from_file_location(
    "generate_flow", _ROOT / "design" / "proposals" / "generate_flow.py")
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)  # import is side-effect free (writes live in main())


class _Scan(HTMLParser):
    """Track cards and lenses SEPARATELY so assertions bind to the right
    surface (r4: a title or note elsewhere must never satisfy a card's
    requirement)."""

    def __init__(self):
        super().__init__()
        self.ids = set()
        self.hrefs = []
        self.rooms = {}           # room id -> {"title": str|None, "fixnote": bool}
        self.lenses = {}          # lens id -> has_fixnote
        self._room = None         # id of the room section we are inside
        self._lens = None         # id of the lens section we are inside
        self._who_depth = 0
        self._who_buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if "id" in a:
            self.ids.add(a["id"])
        if a.get("href", "").startswith("#"):
            self.hrefs.append(a["href"][1:])
        if tag == "section" and "room" in cls:
            self._room = a.get("id", "?")
            self.rooms[self._room] = {"title": None, "fixnote": False}
        if tag == "section" and "lens" in cls:
            self._lens = a.get("id", "?")
            self.lenses[self._lens] = False
        if "fixnote" in cls:
            if self._room is not None:
                self.rooms[self._room]["fixnote"] = True
            elif self._lens is not None:
                self.lenses[self._lens] = True
        if "who" in cls and self._room is not None:
            self._who_depth += 1
            self._who_buf = []

    def handle_endtag(self, tag):
        if tag == "section":
            # rooms and lenses are sibling top-level sections, never nested
            if self._room is not None:
                self._room = None
            elif self._lens is not None:
                self._lens = None
        if self._who_depth and tag in ("h2", "h3"):
            self._who_depth -= 1
            if self._room is not None and self.rooms[self._room]["title"] is None:
                self.rooms[self._room]["title"] = " ".join(self._who_buf).strip()

    def handle_data(self, data):
        if self._who_depth and data.strip():
            self._who_buf.append(data.strip())


_scan = _Scan()
_scan.feed(_HTML)


def test_every_show_renders_as_a_card_with_its_title():
    assert len(_scan.rooms) == len(_gen.SHOWS), (
        f"{len(_gen.SHOWS)} shows in the dataset, {len(_scan.rooms)} cards rendered")
    titles_by_room = {rid: r["title"] for rid, r in _scan.rooms.items()}
    for s in _gen.SHOWS:
        assert titles_by_room.get(s["id"]) == s["artist"], (
            f"card {s['id']} missing its visible title (expected "
            f"{s['artist']!r}, found {titles_by_room.get(s['id'])!r}) — a "
            "title in a lens does not count (r4)")


def test_every_card_carries_the_onsurface_fixture_note():
    missing = sorted(rid for rid, r in _scan.rooms.items() if not r["fixnote"])
    assert not missing, (
        "cards without the visible local truth boundary (evaluator r4: the "
        f"? sheet is not a visible boundary): {missing}")


def test_every_anchor_resolves():
    broken = sorted({h for h in _scan.hrefs if h and h != "_"} - _scan.ids)
    assert not broken, f"anchors pointing at nothing (dead taps, no-JS): {broken}"


def test_every_lens_carries_the_onsurface_fixture_note():
    missing = sorted(k for k, ok in _scan.lenses.items() if not ok)
    assert not missing, (
        "lenses without the local truth boundary (evaluator r3: deep-linkable "
        f"surfaces need their own fixture note): {missing}")


def test_lenses_open_via_css_target_without_js():
    assert re.search(r"\.lens\s*\{[^}]*display:\s*none", _HTML), \
        "lenses must default closed"
    assert re.search(r"\.lens:target\s*\{[^}]*display:\s*flex", _HTML), \
        "lenses must open via :target (the no-JS path)"
