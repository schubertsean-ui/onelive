#!/usr/bin/env python3
from pathlib import Path
P = Path("worker/locale_pack/desk_read.py")
OLD = '''    if not occs_here and node.parent is not None:
        parent_bits = []
        def _pt(n):
            for c in n.children:
                if isinstance(c, str):
                    parent_bits.append(c)
                elif getattr(c, "tag", None) not in ("script", "style", None):
                    _pt(c)
        _pt(node.parent)
        occs_here = house_occurrences(_ws(" ".join(parent_bits)), page_html, as_of)
'''
NEW = '''    if not occs_here and node.parent is not None:
        seen = False
        bits = []
        stop = False
        def event_link(n):
            if getattr(n, "tag", None) != "a":
                return False
            href = (n.attrs.get("href") or "").lower()
            return "/event/" in href or "/events/" in href
        def collect(n):
            nonlocal stop
            for c in n.children:
                if stop:
                    return
                if isinstance(c, str):
                    bits.append(c)
                elif getattr(c, "tag", None) in ("script", "style", None):
                    continue
                elif event_link(c):
                    stop = True
                    return
                else:
                    collect(c)
        for child in node.parent.children:
            if child is node:
                seen = True
                continue
            if not seen or stop:
                continue
            if isinstance(child, str):
                bits.append(child)
            elif event_link(child):
                break
            elif getattr(child, "tag", None) not in ("script", "style", None):
                collect(child)
        occs_here = house_occurrences(_ws(" ".join(bits)), page_html, as_of)
'''

def main():
    t = P.read_text()
    if OLD not in t:
        if "event_link(n)" in t or "stop at the next" in t:
            print("sibling already")
            return 0
        raise SystemExit("parent block missing")
    P.write_text(t.replace(OLD, NEW, 1))
    print("sibling-only patched")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
