# 1Live Construction Loop + Root-Cause Analysis v1

Founder directive (2026-07-25), two parts:
1. *"Have you built in a root cause analysis — the world leading, after
   researching it — to get at the root of your failures?"*
2. *"Build in a better code construction method: confirm vision, goals and
   specific objectives; assess all parameters for green and red probable paths;
   check brain for existing green examples/successes; select the most likely
   success path(s); if nothing exists use the probable paths analysis; run agents
   and gather feedback; analyze, score, commit all to brain; measure improvement
   or slippage; commit; inform next actions; repeat."*

Built, not proposed. Code: `brain/rca.py`, `brain/construction.py`. Proof:
`tests/test_construction_and_rca.py` (9 tests). Demo: `python -m
brain.construction_demo`.

## What the research said (and what we took)

The founder's sketched loop is — almost line for line — the canonical
**case-based reasoning (CBR)** cycle, which is the established academic frame for
"learn from prior cases." We adopted the researched methods rather than inventing
our own vocabulary:

| Source | What it contributes | Where it lands in our code |
|---|---|---|
| **CBR: Retrieve → Reuse → Revise → Retain** (Aamodt & Plaza; LLM-agent CBR review [arXiv:2504.06943](https://arxiv.org/html/2504.06943v1)) | "Check brain for green examples" = Retrieve; "select most likely path" = Reuse; adapt = Revise; "commit all to brain" = Retain | `retrieve_green_examples`, `plan`, `record_outcome` |
| **Reflexion** ([Shinn et al.](https://arxiv.org/pdf/2504.06943)) — after a failure, write a post-mortem and feed it to the next attempt; 91% vs 80% pass@1 on HumanEval from a text memory alone | A failure's RCA becomes retrievable as a **red class to avoid** on the next pass | `retrieve_red_classes` + the `risks` penalty in `plan` |
| **PDCA** (Deming) | The outer wheel: Plan → Do → Check → Act; "measure improvement or slippage" is the Check that gates the next Act | `improvement()`, `Outcome.trend`, `next_actions` |
| **5 Whys** ([comparison](https://fivewhys.ai/blog/root-cause-analysis-methods-compared); [Kepner-Tregoe](https://kepner-tregoe.com/blogs/how-5-whys-and-fishbone-diagrams-relate-to-kt-problem-analysis/)) | The causal spine — chain "why?" until a controllable root | `analyze(why_chain=...)`, min 2 links enforced |
| **Ishikawa + Google SRE blameless postmortems** ([sre.google](https://sre.google/sre-book/postmortem-culture/)) | Classify the root into a **systemic** category (missing test, tooling gap, ambiguous spec…), never "someone was careless"; a standard template enables **trend analysis over root-cause types** | `CauseCategory` enum (no "human error" value exists) + `class_frequency()` |
| **Kepner-Tregoe "what changed"** | For regressions — it worked, then it didn't | `what_changed` field |

**Deliberately not adopted:** Fault Tree Analysis (needs Boolean-logic modeling;
overkill for our failure shapes) and Pareto (needs a large defect population we
don't have yet). Both are noted here so the choice is a decision, not an omission.

## The RCA engine (`brain/rca.py`)

`analyze()` runs one blameless RCA and **commits it to the brain**. It fails
closed on a shallow analysis, which is the whole point:

- **≥2 why-links required** — a single "why" finds a symptom, not a root.
- **A systemic `CauseCategory` is required** — blamelessness is enforced by the
  *type system*: there is no value meaning "the agent messed up."
- **A PREVENTIVE action is required**, not just a corrective one. Fixing the
  instance without the systemic control guarantees recurrence (the core SRE
  lesson).

Every root is stored as an inference `Claim` + an `Evaluation` whose rubric
carries the category — so `class_frequency()` gives the **trend line** Google's
template exists to produce, and **OPERATING_RULES §1** ("a repeated error is a
finding, not a rhythm") becomes mechanical: the 3rd occurrence of a class sets
`is_recurring_finding`, which the construction loop escalates automatically.

## The construction loop (`brain/construction.py`)

```
Objective(vision, goal, objective_class, success_criteria)
   ↓ plan()          Retrieve greens + reds → score candidates → Reuse best precedent
   ↓ (run agents)    brain/pipeline.run_pipeline, or any executor
   ↓ record_outcome() Retain run + score; measure improvement/slippage; next actions
   ↺ repeat — each pass plans from more experience than the last
```

**Path scoring:** a candidate starts at its probable-paths estimate. A prior
GREEN example on that path pulls the estimate toward the *proven* score (weight
0.7 — experience beats a prior). A candidate whose named `risks` match a class
with a committed RCA is **halved** (a known red path). Highest wins; ties break
toward a proven precedent.

**What the demo shows** (`python -m brain.construction_demo`): pass 1 has no
precedent, picks the higher-prior AI path, and fails on cost → an RCA is
committed. Pass 2 **retrieves that red class and switches to the deterministic
path**, succeeding. Pass 3 retrieves the green precedent and *reuses* it. Score
series `[0.20, 0.82, 0.90]`, direction `improving` — the loop measurably learns,
and it is durable across a reload (proven in tests).

## Honest limits (recorded, not hidden)

- The loop **structures and remembers**; it does not invent causes. A human or
  agent still supplies the why-chain and the score. Garbage in still scores out.
- `retrieve_red_classes` currently returns every RCA class in the brain, not only
  those tied to this objective class — deliberately conservative (over-warn
  rather than under-warn), refine when the corpus is large enough to be noisy.
- Scores are analyst-supplied in `[0,1]`. Tying them to *automatic* measures
  (tests passed, cost per verified event) is the natural next step and is where
  this connects to the KPI registry.
