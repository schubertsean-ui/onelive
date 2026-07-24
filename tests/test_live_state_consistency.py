"""STATE.md's live handoff must not contradict docs/RECORD.md.

Recurrence surface of the stale-live-incident-state class (third catch,
PR #49 r1, which fired the ledger's threshold-3 repeat-class alarm):
STATE.md's NEXT queue kept instructing "observe the FIRST schedule-event
run -> flip R-008 with its id" after RECORD.md had already resolved
R-008 — the live handoff document directing work at a finished row can
mislead the next operator during an active incident.

The gate is TWO LAYERS (r2 refused the r1 verb-adjacency regex as a
false-confidence gate; r3 refused the r2 tag as a blanket bypass that
could launder a directive — "flip R-008 (RESOLVED ...)" passed while
still directing live work at a resolved row):

1. DEFAULT-DENY tag layer: inside the LIVE NEXT block, ANY mention of a
   Record row that RECORD.md marks RESOLVED fails unless immediately
   tagged "(RESOLVED" — no verb list to evade, and every surviving
   mention displays its resolved status to the reader on its face.
2. DIRECTIVE layer: a directive verb immediately preceding the row id
   fails REGARDLESS of the tag — the tag cannot launder a directive.

Honest limit, stated so the gate never overclaims (the r2/r3 lesson):
layer 2 is a deny-list and deny-lists are incomplete by nature — a novel
directive verb with a tagged id can pass layer 2. What the gate
guarantees is exactly: no untagged stale mention, and no known-directive
laundering; a surviving mention is always visibly "(RESOLVED"-flagged
text whose staleness a reader can see. Intent understanding stays with
the evaluator review, not this gate.

Scope: the FIRST "NEXT (" block only — that is the live imperative
handoff. Preserved historical sections lower in STATE.md legitimately
narrate resolved rows and are out of scope, as is narration outside
NEXT. Ids absent from RECORD.md are out of scope (unknown status). A
STATE.md with NO live NEXT block fails loud (r3 nit) — silent pass on a
missing handoff would itself be a false-confidence gate.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "STATE.md"
RECORD = REPO / "docs" / "RECORD.md"

_ROW = re.compile(r"^\|\s*(R-\d{3})\s*\|")
_ID = re.compile(r"R-\d{3}")
_RESOLVED_TAG = re.compile(r"\s*\(RESOLVED\b")
# Directive verbs that may not immediately precede a RESOLVED row id,
# tagged or not (optionally through "row"/"the"/"on"). Deny-list —
# incomplete by nature; see the module docstring's honest limit.
_DIRECTIVE_BEFORE = re.compile(
    r"(?:flip|resolve|close|finish|work|observe|re-?run|re-?open|complete|"
    r"do|address|action|handle|fix|deliver|drive|escalate)\s+"
    r"(?:row\s+|the\s+|on\s+)?$",
    re.IGNORECASE,
)


def record_statuses(record_text: str) -> dict[str, str]:
    """Map R-### -> its status cell's leading keyword (OPEN/RESOLVED/...)."""
    statuses: dict[str, str] = {}
    for line in record_text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        statuses[m.group(1)] = cells[-1].split("(")[0].strip().upper()
    return statuses


def live_next_block(state_text: str) -> str:
    """The first NEXT block: from its opening line to a blank/heading line.

    Paragraph-aware so a wrapped continuation line cannot evade the gate
    (r2 finding).
    """
    lines = state_text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("NEXT ("):
            block = [line]
            for cont in lines[i + 1 :]:
                if not cont.strip() or cont.lstrip().startswith("#"):
                    break
                block.append(cont)
            return "\n".join(block)
    raise AssertionError(
        "STATE.md has no live 'NEXT (' block — the live handoff is missing, "
        "which this gate must fail loud on rather than silently pass (PR #49 "
        "r3 nit)."
    )


def stale_resolved_mentions(state_text: str, record_text: str) -> list[str]:
    """RESOLVED rows the live NEXT block mishandles.

    A mention is stale when it is untagged (layer 1) OR when a directive
    verb immediately precedes the id, tag or no tag (layer 2).
    """
    statuses = record_statuses(record_text)
    block = live_next_block(state_text)
    stale: list[str] = []
    for m in _ID.finditer(block):
        rid = m.group(0)
        if not statuses.get(rid, "").startswith("RESOLVED"):
            continue
        tagged = bool(_RESOLVED_TAG.match(block[m.end() :]))
        directed = bool(_DIRECTIVE_BEFORE.search(block[: m.start()]))
        if tagged and not directed:
            continue
        if rid not in stale:
            stale.append(rid)
    return stale


def test_live_next_block_tags_every_resolved_row_mention():
    stale = stale_resolved_mentions(
        STATE.read_text(encoding="utf-8"), RECORD.read_text(encoding="utf-8")
    )
    assert stale == [], (
        f"STATE.md's live NEXT block mishandles already-RESOLVED Record "
        f"row(s) {stale} — either an untagged mention or a directive verb "
        f"aimed at a resolved row (the stale-live-incident-state class, "
        f"PR #49 r1/r2/r3). Rewrite the item to the current truth, point it "
        f"at the OPEN successor row, or tag a legitimate non-directive "
        f"reference 'R-### (RESOLVED ...)'."
    )


_RECORD_RESOLVED = (
    "| R-008 | 2026-07-13 | cron unarmed | Sentinel rule | arming PR "
    "| RESOLVED (2026-07-22, citations) |\n"
)


def test_gate_goes_red_on_the_r1_defect_shape():
    state = (
        "NEXT (top of queue): (1) observe the FIRST schedule-event "
        "ingestion run → flip R-008 with its id.\n"
    )
    assert stale_resolved_mentions(state, _RECORD_RESOLVED) == ["R-008"]


def test_gate_goes_red_on_every_r2_evasion_shape():
    evasions = [
        "NEXT (top of queue): (1) R-008 → RESOLVED this commit.",
        "NEXT (top of queue): (1) close row R-008.",
        "NEXT (top of queue): (1) finish R-008.",
        "NEXT (top of queue): (1) work R-008 next.",
        # wrapped continuation line
        "NEXT (top of queue): (1) first item;\n(2) then flip R-008 now.",
    ]
    for state in evasions:
        assert stale_resolved_mentions(state, _RECORD_RESOLVED) == [
            "R-008"
        ], f"evasion shape slipped past the gate: {state!r}"


def test_gate_goes_red_on_every_r3_tag_laundering_shape():
    launderings = [
        "NEXT (top of queue): (1) close row R-008 (RESOLVED ...).",
        "NEXT (top of queue): (1) finish R-008 (RESOLVED ...).",
        "NEXT (top of queue): (1) flip R-008 (RESOLVED ...) with its id.",
    ]
    for state in launderings:
        assert stale_resolved_mentions(state, _RECORD_RESOLVED) == [
            "R-008"
        ], f"tag laundered a directive past the gate: {state!r}"


def test_missing_live_next_block_fails_loud():
    import pytest

    with pytest.raises(AssertionError, match="no live 'NEXT"):
        stale_resolved_mentions("# STATE\nno queue here\n", _RECORD_RESOLVED)


def test_tagged_reference_to_a_resolved_row_is_allowed():
    state = (
        "NEXT (top of queue): (1) density work — R-008 (RESOLVED — arming "
        "proven, do not re-litigate); the open half is R-023.\n"
    )
    record = _RECORD_RESOLVED + (
        "| R-023 | 2026-07-22 | sparse delivery | cadence directive "
        "| 24h measurement | OPEN |\n"
    )
    assert stale_resolved_mentions(state, record) == []


def test_open_row_mentions_are_unrestricted():
    record = (
        "| R-023 | 2026-07-22 | sparse delivery | cadence directive "
        "| 24h measurement | OPEN |\n"
    )
    state = "NEXT (top of queue): (1) measure density, then resolve R-023 per its trigger.\n"
    assert stale_resolved_mentions(state, record) == []


def test_historical_sections_below_the_live_block_are_out_of_scope():
    state = (
        "NEXT (top of queue): (1) current work only.\n"
        "\n"
        "## Where we were (2026-07-18)\n"
        "NEXT (top of queue, historical): then: R-008 cron arming.\n"
    )
    assert stale_resolved_mentions(state, _RECORD_RESOLVED) == []



# ---------------------------------------------------------------------------
# Layer 3 (added 2026-07-24 PR #61; REBUILT at r3 — the first version was a
# cue-proximity allow-list that "was previously reviewed and is marked
# BLOCKED-…" slid straight through, a false-confidence gate offered as the
# structural fix for a repeat class): same-diff paper-trail contradictions
# about LIFECYCLE MARKERS.
#
# Recurrence surface (4th/5th catches of the stale-live-incident-state
# family, PR #61 r2): while one diff replaced the universal-model doc's
# BLOCKED-ON-PRIMARY-VERIFICATION banner with a VERIFIED banner, STATE.md's
# addendum and the decision record BOTH still asserted the doc "is marked
# BLOCKED" — the fix's own paper trail contradicted the fix in the same
# tree.
#
# The design mirrors this family's proven two-layer shape (layers 1+2
# above), because that shape survived three adversarial rounds:
#   A) DEFAULT-DENY + visible tag: while NO doc carries the live banner,
#      EVERY occurrence of the marker in the live-state docs must be
#      IMMEDIATELY followed by a literal "(SUPERSEDED" tag — no grammar
#      guessing, no cue windows; a surviving mention always displays its
#      supersession to the reader on its face.
#   B) PRESENT-TENSE DENY-LIST the tag cannot launder: "is/remains/stays
#      [currently|still|now] [marked]" immediately before the marker fails
#      REGARDLESS of the tag.
# Honest limit (stated so the gate never overclaims, this family's own
# lesson): layer B is a deny-list and deny-lists are incomplete — a novel
# present-tense construction with a tagged marker can pass B. What the
# gate guarantees is exactly: while the banner is dead, no untagged
# mention and no known present-tense assertion laundering; every survivor
# visibly carries "(SUPERSEDED". Semantics stay with the evaluator.
#
# Banner scope (r3 nit): ALL of docs/**/*.md EXCEPT append-only history
# (docs/metrics/, docs/ONE_LIVE_CHANGE_LOG.md) and the claiming live-state
# docs themselves (STATE.md is outside docs/; docs/memory/ is excluded) —
# a history row QUOTING a banner must not count as the banner being live.
# ---------------------------------------------------------------------------

LIFECYCLE_MARKER = "BLOCKED-ON-PRIMARY-VERIFICATION"
_SUPERSEDED_TAG = re.compile(r"\s*\(SUPERSEDED\b")
_PRESENT_ASSERT_BEFORE = re.compile(
    r"\b(?:is|remains|stays)\s+(?:currently\s+|still\s+|now\s+)?(?:marked\s+)?$",
    re.IGNORECASE,
)

DECISIONS_DIR = REPO / "docs" / "memory" / "decisions"
DOCS_DIR = REPO / "docs"
_BANNER_EXCLUDE_PARTS = {"metrics", "memory"}
_BANNER_EXCLUDE_NAMES = {"ONE_LIVE_CHANGE_LOG.md"}


def _banner_live_somewhere(doc_texts: list[str]) -> bool:
    """True when some doc still CARRIES the banner (bold/heading form),
    as opposed to merely mentioning the marker string in prose."""
    return any(("**" + LIFECYCLE_MARKER) in t for t in doc_texts)


def stale_marker_claims(live_state_texts: dict[str, str],
                        banner_docs: list[str]) -> list[str]:
    """Marker occurrences the live-state docs mishandle while no doc
    carries the banner. Returns 'name: ...context...' strings."""
    if _banner_live_somewhere(banner_docs):
        return []
    stale: list[str] = []
    for name, text in live_state_texts.items():
        for m in re.finditer(re.escape(LIFECYCLE_MARKER), text):
            tagged = bool(_SUPERSEDED_TAG.match(text[m.end():]))
            asserted = bool(_PRESENT_ASSERT_BEFORE.search(text[:m.start()]))
            if tagged and not asserted:
                continue
            ctx = text[max(0, m.start() - 45):m.end() + 25].replace("\n", " ")
            stale.append(f"{name}: …{ctx}…")
    return stale


def _real_live_state_texts() -> dict[str, str]:
    texts = {"STATE.md": STATE.read_text()}
    for p in sorted(DECISIONS_DIR.glob("*.md")):
        texts[f"docs/memory/decisions/{p.name}"] = p.read_text()
    return texts


def _real_banner_docs() -> list[str]:
    out = []
    for p in sorted(DOCS_DIR.rglob("*.md")):
        rel = p.relative_to(DOCS_DIR)
        if rel.parts[0] in _BANNER_EXCLUDE_PARTS or p.name in _BANNER_EXCLUDE_NAMES:
            continue
        out.append(p.read_text())
    return out


def test_no_stale_lifecycle_marker_claims_in_live_state_docs():
    stale = stale_marker_claims(_real_live_state_texts(), _real_banner_docs())
    assert not stale, (
        "live-state docs mishandle a lifecycle marker no doc carries — the "
        "paper trail contradicts the tree (stale-live-incident-state, "
        "same-diff surface, PR #61 r2/r3):\n" + "\n".join(stale)
    )


def test_marker_gate_goes_red_on_both_pr61_r2_defect_shapes():
    rec = ("PR #60's Part 1 is marked BLOCKED-ON-PRIMARY-VERIFICATION in the "
           "doc itself (same commit as this record);")
    state = ("founder(Red) Kaizen row, and the universal-model doc's Part 1 "
             "marked BLOCKED-ON-PRIMARY-VERIFICATION (not to be relied on)")
    verified_doc = "> **VERIFIED AGAINST THE FOUNDER-SUPPLIED PRIMARY** …"
    stale = stale_marker_claims(
        {"decision.md": rec, "STATE.md": state}, [verified_doc]
    )
    assert len(stale) == 2, f"both r2 shapes must fail, got: {stale}"


def test_marker_gate_goes_red_on_the_r3_cue_laundering_shape():
    # The shape the first (cue-proximity) version of this gate let through:
    # past-tense words nearby, present-tense assertion at the marker.
    text = ("Part 1 was previously reviewed and is marked "
            "BLOCKED-ON-PRIMARY-VERIFICATION per the earlier session.")
    assert stale_marker_claims({"STATE.md": text}, ["no banner"]), (
        "cue-word laundering must fail — this exact shape passed the "
        "rejected r2 implementation"
    )
    # And the tag must not launder a present-tense assertion (layer B).
    tagged = ("Part 1 is marked BLOCKED-ON-PRIMARY-VERIFICATION (SUPERSEDED "
              "same day) regardless.")
    assert stale_marker_claims({"STATE.md": tagged}, ["no banner"])


def test_marker_gate_goes_red_on_untagged_history():
    # Default-deny: even genuine past tense fails WITHOUT the visible tag —
    # the reader must see the supersession on the mention's face.
    text = "Part 1 was first marked BLOCKED-ON-PRIMARY-VERIFICATION, then…"
    assert stale_marker_claims({"STATE.md": text}, ["no banner"])


def test_marker_gate_allows_tagged_history():
    text = ("Part 1 was first marked BLOCKED-ON-PRIMARY-VERIFICATION "
            "(SUPERSEDED same day — verified against the supplied primary).")
    assert stale_marker_claims({"STATE.md": text}, ["no banner"]) == []


def test_marker_gate_allows_present_claims_while_banner_is_live():
    claim = "Part 1 is marked BLOCKED-ON-PRIMARY-VERIFICATION in the doc."
    live = "> **BLOCKED-ON-PRIMARY-VERIFICATION (added 2026-07-24…)**"
    assert stale_marker_claims({"STATE.md": claim}, [live]) == []
