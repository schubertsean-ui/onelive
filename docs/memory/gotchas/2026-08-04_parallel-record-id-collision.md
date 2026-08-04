# Gotcha: parallel sessions double-allocate RECORD ids (and contract numbers)

**Date:** 2026-08-04 · **Sessions involved:** the 2026-08-03 UI/UX session (PR #152) and
the GeoLibre/wording session (PRs #156/#157), resolved by the successor UI/UX session.

**What happened.** Two sessions running the same day each took "the next free R-###" from
the RECORD register on their own branch: #152 allocated R-068–R-072 (browserless skip,
human a11y pass, field CWV, light theme, glyph display) while #156/#157 allocated
R-068/R-069/R-070 (geo-spec citations, heal marker bug, wording sweep). Same ids,
different meanings. Session-contract numbers collided the same way (three different
"Contract #39"s, then two "#40"s). Deferral tags (`[R-###]`) bind code comments to rows,
so a blind merge would have made tags ambiguous — corrupting the no-silent-deferrals
mechanism itself. The first run of the new guard also surfaced three OLDER duplicates
(R-023/R-024/R-029) that had survived the 2026-07-25 merge era unnoticed.

**Resolution rule (now precedent):** earliest-allocated AND first-merged keeps the ids —
especially when they are code-tag-bound; later rows renumber to the next free ids with a
"(RENUMBERED from …)" decoder note in the row, and every LIVING-doc cross-reference
updates in the same change (historical/append-only text keeps its original ids; the row
note is the decoder). Contract numbers renumber the same way at merge.

**Machine-consumed leg (charter 2.5 — the lesson is a gate, not prose):**
`tests/test_record_ids_unique.py` — hermetic, runs in the full suite, fails any tree whose
RECORD.md carries a duplicate row id. Whichever branch lands second goes red until it
renumbers. Retrieval tokens: `parallel-record-id-collision`, `scripted-transform-order`
(the companion self-caught defect: a script inserting decoder text BEFORE its blanket
transform garbles its own note — sequence narrative after transforms).

**Residual (not mechanized):** contract-number collisions in STATE.md have no gate — they
are cosmetic (no tag binds to a contract number) and the merge-conflict resolution catches
them naturally; mechanize only if a third collision proves otherwise.
