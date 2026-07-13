G-BRAIN ratified: build brain = 1A (this directory) + 1B (pgvector recall in existing Supabase); platform brain at Sprint Step 7; option 1D (graph infra) deferred behind a standing trigger — recorded as [R-010] in docs/RECORD.md.

Founder verbatim (2026-07-13): "Brain: 1A+1B, platform at Step 7" plus the
directive to never lose: "if it ever needs graph infrastructure, that's the
moment option 1D becomes worth it, one investment serving both brains."

Why 1A+1B won: zero new vendors/spend, builds on infrastructure we already
run (RLS'd Supabase), preserves disk-is-truth (files stay canonical; the
vector index is a rebuildable finding aid), and doesn't foreclose 1C/1D
later. Known cost: ~15-point gap vs Zep on temporal-recall benchmarks —
acceptable at current history size; that exact weakness is trigger T2.

The 1D trigger (G-BRAIN-1D) fire conditions T1/T2/T3 and the on-fire
protocol (friction attack → founder, because new infra = money) live in
docs/strategy/ONE_LIVE_BRAIN_OPTIONS_v1.md §RATIFIED and as a STANDING
TODOS item ("G-BRAIN-1D trigger watch") so every session's queue carries it.
