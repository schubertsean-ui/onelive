#!/usr/bin/env python3
"""Read the printed night next to the title link. Safe to re-run."""
import re
from pathlib import Path

p = Path("worker/locale_pack/desk_read.py")
t = p.read_text()
if "def _print_after(" in t and "extra = _print_after(node)" in t:
    print("desk_read already reads sibling time line")
    raise SystemExit(0)

helper = '''
def _print_after(node: "_Node") -> str:
    """Words printed after this node among its siblings.

    Chronicle prints the night next to the title link. Stop at the next
    /event/ permalink so this is one card, not the whole list.
    """
    parent = getattr(node, "parent", None)
    if parent is None:
        return ""
    parts = []
    seen = False
    for child in parent.children:
        if child is node:
            seen = True
            continue
        if not seen:
            continue
        if isinstance(child, str):
            bits = child.strip()
            if bits:
                parts.append(bits)
            continue
        tag = getattr(child, "tag", "")
        href = ((getattr(child, "attrs", {}) or {}).get("href") or "")
        if tag == "a" and "/event/" in href.lower():
            break
        stack = [child]
        stop = False
        while stack and not stop:
            n = stack.pop()
            if isinstance(n, str):
                bits = n.strip()
                if bits:
                    parts.append(bits)
                continue
            href2 = ((getattr(n, "attrs", {}) or {}).get("href") or "")
            if getattr(n, "tag", "") == "a" and "/event/" in href2.lower():
                stop = True
                break
            kids = list(getattr(n, "children", []) or [])
            stack.extend(reversed(kids))
        if sum(len(x) for x in parts) > 400:
            break
    return " ".join(parts)

'''

if "def _print_after(" not in t:
    mark = "def _identity_rows("
    if mark not in t:
        raise SystemExit("_identity_rows missing")
    t = t.replace(mark, helper + "\n" + mark, 1)
    print("inserted _print_after")

pat = re.compile(
    r'^([ \t]*)card_text = _ws\(" "\.join\(text_parts\)\)\n'
    r'\1occs_here = house_occurrences\(card_text, page_html, as_of\)\n'
    r'\1if not when and len\(occs_here\) == 1:\n'
    r'\1    when = occs_here\[0\]\["when"\]\n',
    re.M,
)

def repl(m):
    i = m.group(1)
    return (
        f'{i}card_text = _ws(" ".join(text_parts))\n'
        f'{i}extra = _print_after(node)\n'
        f'{i}if extra:\n'
        f'{i}    card_text = _ws((card_text + " " + extra).strip())\n'
        f'{i}    if not when_text:\n'
        f'{i}        when_text = extra\n'
        f'{i}occs_here = house_occurrences(card_text, page_html, as_of)\n'
        f'{i}if not when and occs_here:\n'
        f'{i}    when = occs_here[0]["when"]\n'
    )

n, t2 = pat.subn(repl, t, count=1)
if n != 1:
    raise SystemExit(f"date block not matched n={n}")
t = t2
p.write_text(t)
print("desk_read reads sibling time line")
