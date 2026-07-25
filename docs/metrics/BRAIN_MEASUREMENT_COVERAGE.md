# BRAIN MEASUREMENT COVERAGE — measured vs NOT-yet-measured (Goodhart honesty)

Greppable summary: the Brain IQ score (`brain/iq.py`,
`docs/metrics/BRAIN_IQ_LEDGER.md`) measures SOME kinds of smartness, not all. A
score that pretends to cover everything is a Goodhart trap: it invites optimising
the measured proxy while the unmeasured kinds silently rot. So this doc names
EXACTLY what is measured and — more importantly — what is known but NOT yet
measured, each with WHY it is unmeasured and an objective TRIGGER to close the
gap. The gap is therefore visible and shrinking, never hidden.

The canonical list is in code (`brain/iq.py`: `MEASURED` and `NOT_YET_MEASURED`),
rendered by `python tools/brain_iq.py --print` and asserted non-empty + honest by
`tests/test_brain_iq.py`. This doc is the prose companion; if the two ever drift,
the code is truth (a test binds them).

## Measured today

| Dimension | What is measured | How |
|---|---|---|
| KNOWLEDGE (gated) | Accuracy on 6 agent-memory competencies: single-fact, multi-hop, knowledge-update (bi-temporal), contradiction, entity resolution, abstention — folded with provenance-citation and abstention-correctness into one 0..1 | Deterministic exact-match over `brain/eval/` (free, reproducible) |
| EFFICIENCY (gated) | Average graph nodes+edges materialised per benchmark query — "same answers at less work" | Deterministic work counter over the real query traversal (`brain/iq.py`) |
| LEARNING (trend) | Adoption (recipes engaged by >=2 distinct runs), durability (recipes still valid, not `needs_rediscovery`), shared-findings count | Fixed seeded+simulated acquisition history over `brain/acquisition.py` |

## Known but NOT yet measured (each with a trigger)

| Not-yet-measured | Why it is not measured | Objective trigger to close it |
|---|---|---|
| **Reasoning depth beyond ~3 hops** | The benchmark's deepest chain is 3 hops; deeper multi-step joins are not exercised, so "reasoning IQ" is only partially covered | Add >=4-hop labeled questions to `brain/eval/benchmark.py` + a reasoning-depth sub-metric when a real query needs that depth |
| **Real production extraction yield** | LEARNING uses a SEEDED toolkit history — no live code reads `recipe_for`/`record_outcome` yet (R-040), so real adoption and yield-per-source are unmeasured | When the live orchestrator is toolkit-guided (R-040), fold real per-source yield + adoption into LEARNING |
| **Real wall-latency under load** | Only a single-run OBSERVED latency is recorded, and it is never gated (machine-dependent, flaky); throughput and tail latency under concurrent load are unmeasured | Add a load/throughput harness when the brain serves live query traffic; gate on p50/p95 work-per-query, never raw wall time |
| **External LongMemEval (public leaderboard)** | KNOWLEDGE is OUR OWN benchmark scored by exact match (R-041); NOT comparable to public LongMemEval figures (public dataset + LLM judge + real spend) | Founder-crucial spend decision (G-BRAIN-1D): run real LongMemEval via the budgeted model router; the `brain/eval` read surface is the adapter seam |

## Why latency is recorded but never gated

Efficiency is measured two ways. The GATED number is graph WORK (nodes+edges per
query) — deterministic and reproducible, so "smarter = less work" is a fact the
ratchet can defend. Wall LATENCY is ALSO recorded (for the trend), because
founders and operators care about it — but it is machine-dependent and flaky
(CPU, load, noisy neighbours), so gating on it would make a green build depend on
which machine ran it. Latency therefore never enters the score, the composite, or
the ratchet; `tests/test_brain_iq.py` proves a slow run does not fail `--check`.
The staged upgrade above (load-latency under concurrency) is the honest path to a
gated latency number, and it is named here so its absence is not silent.
