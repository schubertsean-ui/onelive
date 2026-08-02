# 1LIVE — Brain IQ v1: continuously scoring how much smarter the brain gets

Status: BUILT 2026-07-25 (this session). Gate-custody: evaluator-reviewed on the
PR that adds it (it wires a new one-way ratchet into `tools/validate`).

## Why this exists (founder directive, plain language)

The founder asked us to "write into the model a continuous scoring and rating of
improvement of the brain — it gets quantifiably smarter, one or even 3 kinds of
smartness." The existing memory eval (`brain/eval/`) already proves the brain is
accurate as a MEASURED fact, but it is a single accuracy benchmark and a snapshot
gate — it does not, by itself, TREND improvement over time or separate the
different KINDS of getting-smarter. Brain IQ closes that: a continuous,
multi-dimensional score, trended row-by-row in a ledger, so "the brain is getting
smarter" stops being a claim and becomes a chart.

We chose to REUSE the existing measurement machinery rather than build a parallel
one: KNOWLEDGE folds the existing `MemoryEvalReport`, EFFICIENCY instruments the
existing benchmark traversal, and LEARNING reads the existing acquisition
toolkit. The alternative — a fresh benchmark and a fresh harness — was rejected
as duplicated surface that would drift from the real one; this is the same
family as `KAIZEN_LEDGER` and `brain/eval/baselines.json`, and it mirrors their
discipline instead of reinventing it.

## The three kinds of smartness

### 1. KNOWLEDGE — is the brain RIGHT? (gated)

Folds the deterministic memory-eval report into one 0..1, with a documented
weighting (`brain/iq.py::KNOWLEDGE_WEIGHTS`):

- overall accuracy — 0.40 (the backbone: fraction of all questions answered
  correctly across the six agent-memory competencies);
- abstention-correctness — 0.25 (weighted heavily because fabricating an answer
  to an unanswerable question is the worst failure — never-fabricate is a trust
  invariant, not a nicety);
- provenance-citation rate — 0.20 (an answer without its source is half an
  answer);
- knowledge-update (bi-temporal / point-in-time recall) — 0.15, ON TOP of its
  share of overall accuracy, because temporal recall is the hard, historically
  open capability (R-010/R-031/R-041) we most want to keep watching as it moves.

Why weight, not just average: the four numbers are not equally load-bearing for
"is this brain trustworthy," and a flat average would let a provenance collapse
hide behind perfect recall. The weights make the trust-critical properties
(being right, and abstaining instead of fabricating) dominate. The tradeoff: any
fixed weighting is a judgment call, so the per-sub-metric numbers are ALSO carried
in the ledger sub-metrics and printed by the CLI — the fold is a convenience, not
the whole truth.

### 2. EFFICIENCY — same answers at LESS WORK (gated on work, never on latency)

"Smarter" is not only "more correct" — a brain that reaches the SAME answers
while touching FEWER pieces of the graph is smarter too. So we measure the WORK a
query costs: a transparent proxy over the graph counts the nodes+edges each
bounded `subgraph()` neighbourhood and each point-in-time `claims_valid_at()` read
materialises, summed per benchmark query and averaged. Lower work = smarter.

The gated score normalises work against a naive "scan the whole graph" reference
(the average full-graph size, derived from the fixed benchmark):

    efficiency_score = ref / (ref + avg_work_per_query)

so a brain that scans everything scores near 0, a brain that reaches answers
touching almost nothing scores near 1, improvement is always visible (nothing is
capped away), and the number is reproducible byte-for-byte.

Wall LATENCY is ALSO recorded — operators care about it — but it is NEVER gated.
Latency is machine-dependent and flaky (CPU, load, noisy neighbours); gating on it
would make a green build depend on which machine ran it. So latency lives in the
sub-metrics and the trend, never in the score, the composite, or the ratchet.
`tests/test_brain_iq.py` proves a slow run does not fail `--check`. Why not gate a
smoothed latency now: we have no load harness yet, and a single-run wall time is
not a trustworthy number — the honest path (gated p50/p95 under concurrency) is a
staged item, named in the coverage doc, not faked here.

### 3. LEARNING — does the shared toolkit COMPOUND across runs? (trended, not gated)

The brain's thesis is "the agent forgets, the toolkit does not." LEARNING measures
whether that shared know-how actually compounds, from a FIXED seeded+simulated
acquisition history (fixed source ids, fixed run ids, fixed yields, fixed integer
timestamps passed in — no wall clock):

- adoption_rate — fraction of recipes ENGAGED by >=2 distinct runs (a write is
  always preceded by a read-before-acquire, so a recipe advanced by two different
  runs is shared know-how genuinely reused across runs);
- durability — fraction of learned recipes still valid (not flagged
  `needs_rediscovery`) after the simulated history;
- findings_shared — count of reusable techniques (the cross-source library every
  agent reads), normalised against a documented mature-toolkit target.

LEARNING is TRENDED but NOT gated, because the scenario is seeded and illustrative
rather than a live workload — gating a real ratchet on a synthetic history would
be measuring an idle factory. When the live orchestrator becomes toolkit-guided
(R-040), real yield/adoption fold in and LEARNING can earn a gate.

## The composite (and why the per-dimension numbers govern)

    composite = 0.50·knowledge + 0.30·efficiency + 0.20·learning

Knowledge is primary (being right dominates being fast or well-read); efficiency
is a real second axis; learning is the compounding third but least mature. The
honest caveat, stated loudly in the ledger and printed by the CLI: **a composite
HIDES detail.** A single 0.90 could be a knowledge dip masked by an efficiency
gain. So the ledger trends all three dimensions in separate columns, the ratchet
gates the dimensions INDIVIDUALLY (not the composite), and the composite is a
headline, never the governor.

## The continuous trend + the one-way ratchet

Every measured run appends one timestamped row to
`docs/metrics/BRAIN_IQ_LEDGER.md` (`tools/brain_iq.py --append TIMESTAMP`, the
instant supplied by the caller/CI — code never reads the wall clock). Each row
carries the three dimension scores, the composite, and a TREND arrow (↑/→/↓ vs the
previous row's composite). That is the continuous "is it getting smarter" record.

The GUARD is a one-way ratchet (`tools/brain_iq.py --check`, wired into
`tools/validate`): each GATED dimension (KNOWLEDGE, EFFICIENCY) must stay >= its
best recorded value in the ledger, minus a tiny float-safe epsilon. Knowledge
dropping, or graph-work rising, turns the gate RED. When the brain genuinely
improves, the fix is to re-measure and append a row that RAISES the recorded best
— exactly the pattern of `brain/eval/baselines.json` and
`tools/surface_regression_exam.py`. The number only ratchets up; a regression is
never merged on green. A gate that cannot fail is worthless, so the tests plant a
regression in EACH gated dimension (a fabricating answerer drops knowledge; a
wasteful answerer raises work) and prove the ratchet fires; a slow run proves
latency does NOT.

## Measurement-completeness / Goodhart honesty

A score that pretends to measure ALL smartness is a Goodhart trap — optimise the
proxy, let the unmeasured kinds rot. So Brain IQ ships an explicit coverage
control (`brain/iq.py::MEASURED` / `NOT_YET_MEASURED`,
`docs/metrics/BRAIN_MEASUREMENT_COVERAGE.md`, rendered by `--print`, asserted
non-empty + honest by the tests). It names what is measured (knowledge accuracy,
per-query graph work, seeded learning) AND what is known but NOT yet measured,
each with a why + an objective trigger:

- reasoning depth beyond ~3 hops (add >=4-hop benchmark questions);
- real production extraction yield (awaits live toolkit wiring, R-040);
- real wall-latency under load (awaits a load/throughput harness);
- external LongMemEval public leaderboard (founder-crucial spend, R-041).

These staged parts are recorded in `docs/RECORD.md` R-042, so the gap is visible
and shrinking, never silent. That is the whole point: the brain gets quantifiably
smarter along the axes we measure, and we are honest, in the same artifact, about
the axes we do not measure yet.
