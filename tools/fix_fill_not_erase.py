#!/usr/bin/env python3
from pathlib import Path


def one(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    t = p.read_text()
    if old not in t:
        if new in t or label + " already" in t:
            print(label, "already")
            return
        raise SystemExit("missing " + label)
    p.write_text(t.replace(old, new, 1))
    print(label, "patched")


def main() -> int:
    one(
        "worker/locale_pack/event_page.py",
        """            visit.when_conflict = True
            visit.listed_when = row.when
            visit.page_when = statement.when
            changes[\"when\"] = None
            changes[\"when_precision\"] = None
            changes[\"when_text\"] = None
""",
        """            visit.when_conflict = True
            visit.listed_when = row.when
            visit.page_when = statement.when
""",
        "apply-keep-night",
    )
    one(
        "tools/desk_ingest.py",
        """        if not _same_host(url, row.source_url):
            continue
        seen.add(key)
        out.append(url)
""",
        """        if not _same_host(url, row.source_url):
            continue
        if row.when and row.place_text:
            continue
        seen.add(key)
        out.append(url)
""",
        "follow-holes",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
