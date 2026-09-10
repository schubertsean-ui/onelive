#!/usr/bin/env python3
"""Use house_dates on this card only. Stop at the next event link."""
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()
old = '''    if not occs_here and node.parent is not None:
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
new = '''    if not occs_here and node.parent is not None:
        extra = []
        started = False
        for child in node.parent.children:
            if child is node:
                started = True
                continue
            if not started:
                continue
            href = ""
            if getattr(child, "tag", None) == "a":
                href = child.attrs.get("href") or ""
            if "/event/" in href:
                break
            if isinstance(child, str):
                extra.append(child)
            elif getattr(child, "tag", None) not in ("script", "style", None):
                bits = []
                stop = False
                stack = [child]
                while stack:
                    n = stack.pop()
                    for c in n.children:
                        if isinstance(c, str):
                            bits.append(c)
                        elif getattr(c, "tag", None) not in ("script", "style", None):
                            if getattr(c, "tag", None) == "a" and "/event/" in (c.attrs.get("href") or ""):
                                stop = True
                                break
                            stack.append(c)
                    if stop:
                        break
                extra.append(" ".join(bits))
                if stop:
                    break
        occs_here = house_occurrences(_ws(" ".join(extra)), page_html, as_of)
'''
if old in t:
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("stop-at-next-event landed")
elif "if \"/event/\" in href:" in t and "started = False" in t:
    print("already stopped at next event")
else:
    raise SystemExit("parent block not found")
