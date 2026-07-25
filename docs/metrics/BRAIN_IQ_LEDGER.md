# BRAIN IQ LEDGER — continuous, multi-dimensional smartness trend (append-only)

Greppable summary: the CONTINUOUS trend of how smart the brain is, across THREE
kinds of smartness, so improvement is quantified and trended over time rather
than asserted once. Founder directive: "write into the model a continuous
scoring and rating of improvement of the brain — it gets quantifiably smarter,
one or even 3 kinds of smartness." This ledger MIRRORS `docs/metrics/KAIZEN_LEDGER.md`
discipline: one timestamped row per measured run, append-only (never edit a row;
corrections append a new row referencing the old), and the numbers are computed
by `tools/brain_iq.py` (over `brain/iq.py`), never hand-written.

The three dimensions (full design: `docs/strategy/ONE_LIVE_BRAIN_IQ_v1.md`):
- **KNOWLEDGE** (GATED) — is the brain RIGHT? Folds the memory-eval report
  (`brain/eval/`): overall accuracy, provenance-citation, abstention-correctness,
  and the temporal (knowledge-update) competency into one 0..1.
- **EFFICIENCY** (GATED) — same answers at LESS WORK. A deterministic count of
  graph nodes+edges materialised per benchmark query, normalised so lower work =
  higher score. A wall-latency figure is recorded for the trend but NEVER gated
  (machine-dependent, flaky).
- **LEARNING** (trend only) — does the shared acquisition toolkit COMPOUND across
  runs? Adoption (recipes engaged by >=2 distinct runs), durability (learned
  recipes still valid), and shared-findings count, from a fixed seeded scenario.

The **one-way ratchet** (`python tools/brain_iq.py --check`, wired into
`tools/validate`) guards the two GATED dimensions: KNOWLEDGE and EFFICIENCY must
each stay >= their best recorded value (minus a tiny epsilon). Knowledge dropping
or work rising turns the gate RED. When the brain improves, the next `--append`
row raises the recorded best — the gate only ever ratchets up. LEARNING and
latency are trended, not gated. Gate-custody: evaluator-reviewed on the PR that
adds it.

The **composite** is a documented weighted blend (knowledge 0.50, efficiency
0.30, learning 0.20). A composite HIDES detail, so the per-dimension columns
govern — read them, not just the composite. Weightings live in `brain/iq.py`
(`KNOWLEDGE_WEIGHTS`, `LEARNING_WEIGHTS`, `COMPOSITE_WEIGHTS`) and are explained
in the strategy doc.

`trend` = direction of the composite vs the PREVIOUS row (↑ up / → flat / ↓ down;
`-` for the first row, which has no predecessor).

## Rows (append-only; computed by tools/brain_iq.py, never hand-typed)

| timestamp | knowledge | efficiency | learning | composite | trend |
|---|---|---|---|---|---|
| 2026-07-25T00:00:00Z | 1.0000 | 0.8050 | 0.7800 | 0.8975 | - |

## Measurement coverage (Goodhart honesty)

You cannot measure every kind of smartness at once, so this ledger names exactly
what it does and does NOT cover — the gap is visible and shrinking, never hidden.
The canonical, machine-checked list lives in `brain/iq.py` (`MEASURED` and
`NOT_YET_MEASURED`) and is rendered in full by `python tools/brain_iq.py --print`;
the prose companion is `docs/metrics/BRAIN_MEASUREMENT_COVERAGE.md`. In short —
MEASURED: knowledge accuracy, per-query graph work, seeded learning/adoption.
NOT YET MEASURED (each with a trigger): reasoning depth beyond ~3 hops, real
production extraction yield (awaits live toolkit wiring, R-040), real
wall-latency under load, and the external LongMemEval public leaderboard
(founder-crucial spend, R-041). See the coverage doc for the WHY + trigger of
each.
