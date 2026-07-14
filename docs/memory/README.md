# docs/memory — the build agent's long-term memory (Brain 1A)

Greppable summary: the sharpened file brain ratified under G-BRAIN
("1A+1B, platform at Step 7"). Lessons, decisions, and entity notes the
agent writes for its future self, structured for retrieval. STATE.md stays
the always-current rollup and arcs stay the chronology; THIS directory holds
the distilled, reusable knowledge — the things a future session must not
re-learn the hard way. Brain 1B (pgvector semantic index in Supabase) will
index these files for meaning-based recall; the files remain the source of
truth (disk is truth) and the index is a rebuildable finding aid.

## Structure

- `decisions/` — ratified choices with their why (one decision per file).
- `gotchas/` — hard-won operational lessons (one lesson per file).
- `entities/` — durable notes on external things we integrate with
  (services, APIs, tools) that chat history won't reliably resurface.

## Writing conventions (enforced by review, mirrored from the charter)

1. One lesson/decision per file; filename `YYYY-MM-DD_slug.md`.
2. First line: a one-line summary (it becomes the retrieval snippet).
3. Record corrections AND confirmed approaches, including why they mattered.
4. Don't save what STATE.md, the arcs, or the changelog already record —
   memory is for distilled reusable knowledge, not duplication.
5. Update the existing note rather than creating a near-duplicate; DELETE
   notes proven wrong (a wrong memory is worse than none).
6. Never store secrets, keys, or tokens here — memory files are replayed
   into future contexts verbatim.

## Reading convention

Session start (after reconcile): skim this README's directory listing and
open anything relevant to the session contract. Once Brain 1B ships,
`tools/brain_recall.py "<question>"` replaces the manual skim.
