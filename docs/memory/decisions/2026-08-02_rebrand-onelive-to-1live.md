# 2026-08-02 — Rebrand: OneLive → 1Live

**Founder, verbatim (2026-08-02):** "Change all 'OneLive' to '1Live' /
Everywhere, in these last 2 documents and in the repo and in the canon"

## Executed now (this docs-armed session)

- **Both deliverables** — every builder in `docs/strategy/marketing_model/`
  swept (figure text and page copy), all figures re-rendered, both PDFs
  rebuilt; the customer document's filename becomes
  `1Live_Customer_Story_v1.pdf`.
- **Living canon** — brand-name occurrences swept in all living docs:
  `docs/strategy/**`, operating docs (OPERATING_RULES, WORLD_CLASS,
  MODEL_ROUTING, TESTS, KAIZEN policy), review personas, skills, hats,
  design docs, living memory (RED_CLASSES, entities/gotchas), research
  notes, TODOS.md. Rules: `OneLive` → `1Live`; the spaced all-caps brand
  `ONE LIVE` → `1LIVE`.

## Deliberately preserved (with reasons)

1. **Historical, append-only records keep their original text** — past
   changelog entries, session arcs, Kaizen ledger rows, decision records,
   RECORD.md rows, founder-digest/friction logs. They are records of what
   was said and done when the brand was OneLive; rewriting them would
   falsify verbatim quotes and history. All NEW entries use 1Live.
2. **Machine identifiers stay** until their owners change them: the GitHub
   repo name (`onelive`), deployment URLs, the Supabase project ref, env
   var names (`ONELIVE_DB_DSN`, `ONELIVE_APPROVAL_KEY`), and `ONE_LIVE_*`
   FILENAMES (renaming ~50 canon files breaks every cross-reference —
   held as an optional follow-up sweep, R-065).
3. **Runtime code and CLAUDE.md** — the session is docs-armed; the web
   app's user-facing brand (`web/components/BrandMark.tsx` and ~50 other
   runtime files) and the CLAUDE.md charter text are the code-armed
   remainder, recorded as **R-065** with the trigger "next code-armed
   session, before any user-facing deploy". STATE.md is additionally
   frozen by the R-023 arming classification (any STATE.md edit fails
   trust-gate until the next smoke-evidence refresh) and is listed in
   R-065 rather than edited here.
