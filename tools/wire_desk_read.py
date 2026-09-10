#!/usr/bin/env python3
"""One-shot. Safe to re-run."""
from pathlib import Path


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        if new in text:
            print(label, "already")
            return text
        raise SystemExit("missing: " + label)
    print(label, "patched")
    return text.replace(old, new, 1)


def main() -> int:
    read = Path("worker/locale_pack/desk_read.py")
    t = read.read_text()
    t = must_replace(
        t,
        '            fields.get("when_text") or "", html, as_of)\n',
        '            " ".join(part for part in (
                fields.get("title"), fields.get("when_text"),
                fields.get("place_text")) if part), html, as_of)\n',
        "card-text",
    )
    read.write_text(t)

    pub = Path("worker/locale_pack/desk_publish.py")
    t = pub.read_text()
    t = must_replace(
        t,
        '        return f"url:{url}"\n',
        '        night = (getattr(row, "night", None) or "")\n'
        '        return f"url:{url}~{night}"\n',
        "ingest-key",
    )
    pub.write_text(t)
    print("wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
