"""Static integrity of the generated FLOW prototype (no browser needed).

Mechanizes what previously lived in changelog prose (evaluator r3 nit,
PR #45) — the properties that made the founder's no-JS viewer rounds
fail, checked structurally on the committed HTML:

1. Every show in the dataset renders as a card with a visible title.
2. Every in-page anchor (#x) resolves to a real element id — a broken
   door is a dead tap in a no-JS viewer, invisible to a JS-based check.
3. EVERY lens carries the on-surface fixture note (evaluator r3 BLOCKER:
   lenses are deep-linkable, so the truth boundary must be local — a
   lens without it fails here mechanically, forever).
4. The CSS that makes lenses open without JavaScript (:target) and stay
   closed otherwise is present.

Scope honesty: this proves structure, not pixels — visual verification
still happens in the headless pass before founder delivery.
"""
import pathlib
import re
from html.parser import HTMLParser

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_HTML = (_ROOT / "design" / "proposals" / "direction-4-flow.html").read_text()


class _Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.hrefs = []
        self.rooms = 0
        self.lens_stack = []
        self.lenses = {}          # id -> has_fixnote
        self._in_who = 0
        self.who_texts = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if "id" in a:
            self.ids.add(a["id"])
        if a.get("href", "").startswith("#"):
            self.hrefs.append(a["href"][1:])
        if "room" in cls:
            self.rooms += 1
        if "lens" in cls:
            self.lens_stack.append(a.get("id", "?"))
            self.lenses[a.get("id", "?")] = False
        if "fixnote" in cls and self.lens_stack:
            self.lenses[self.lens_stack[-1]] = True
        if "who" in cls:
            self._in_who += 1

    def handle_endtag(self, tag):
        if tag == "section" and self.lens_stack:
            # sections never nest inside lenses in this document
            self.lens_stack.pop()
        if self._in_who and tag in ("h2", "h3"):
            self._in_who -= 1

    def handle_data(self, data):
        if self._in_who and data.strip():
            self.who_texts.append(data.strip())


_scan = _Scan()
_scan.feed(_HTML)


def test_every_show_renders_as_a_card():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gen", _ROOT / "design" / "proposals" / "generate_flow.py")
    # Importing executes the generator against a temp target, giving us
    # the dataset without touching the committed file.
    import sys, tempfile
    with tempfile.TemporaryDirectory() as td:
        argv = sys.argv
        sys.argv = ["generate_flow.py", str(pathlib.Path(td) / "x.html")]
        try:
            gen = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gen)
        finally:
            sys.argv = argv
    assert _scan.rooms == len(gen.SHOWS), (
        f"{len(gen.SHOWS)} shows in the dataset, {_scan.rooms} cards rendered")
    for s in gen.SHOWS:
        assert s["artist"] in _scan.who_texts, f"card missing: {s['artist']}"


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
