# OneLive KPI Framework v1 — quarterly-prioritization process

Status: PROPOSAL for the process and per-area KPIs (agent-designed, ready to
run); the **North Star metric is explicitly FOUNDER-RATIFY** (see below) — an
agent does not get to pick the one number the whole company optimizes for.

Greppable summary: a lightweight process so the team can work on MANY areas
at once (ingestion, extraction quality, cost, the brain, the consumer app,
trust/safety) while still choosing, ON PURPOSE, what matters most THIS
QUARTER. It does not invent a new measurement system — it is the
**aggregation layer** over ledgers that already exist: `docs/metrics/
KAIZEN_LEDGER.md` (defect/catch discipline), `docs/metrics/BRAIN_IQ_LEDGER.md`
(brain smartness), the extraction certification record, the trust gate, and
`docs/RECORD.md` (the deviations register). Read this once, then use
`docs/metrics/KPI_LEDGER.md` + `python tools/kpi_report.py` day to day.

Written for a plain-language reader — a smart, busy founder, not an
engineer. Any term that sounds like jargon is explained where it first
appears.

---

## 1. Why this exists

OneLive has real areas of work happening at once — getting more shows into
the feed, making sure the AI never states a fact that isn't true, keeping
the AI bill small, making the "brain" (the pipeline's shared knowledge)
smarter over time, making the app itself good to use, and keeping the trust
rules airtight. Each area already has SOME measurement (the Kaizen ledger for
defects, the Brain IQ score for the brain, the extraction certification for
hallucinations, the trust gate for the hard rules). What was missing was a
**single, simple habit**: once a quarter, look at all of it together, and
consciously choose 3–5 things to push hardest on — instead of every area
quietly competing for attention with no explicit call.

This document is that habit, written down. It is NOT a rewrite of the
existing measurement — it reads from it.

---

## 2. The North Star metric — FOUNDER-RATIFY

**Proposed candidate:** *"Verified live events on /tonight per served locale,
trust-weighted."* In plain terms: on any given night, in a city we cover, how
many REAL, verifiably-happening events does a person actually see in the
feed — counting a `confirmed` event as a full "1", a `likely` event as a
partial "0.6", and an `unverified` event as a small "0.25" (the trust states
are defined in this repo's architecture section; `disputed` events are always
shown but do not count toward the star, since they are flagged as
contested). This rewards BOTH coverage (more real events) and trust (higher-
confidence events) at once, and it cannot be gamed by flooding the feed with
low-confidence guesses.

**Why this is FOUNDER-RATIFY, not agent-decided:** the North Star is the one
number the whole team is meant to orient around. Picking it is a strategic
call about what OneLive IS — a strictly-verified utility vs. a broader
discovery feed vs. something else — and CLAUDE.md reserves exactly this kind
of "what are we, and what do we optimize for" decision for the founder, the
same way trust-invariant changes and go-live decisions are founder-crucial.
An agent proposing a plausible candidate and then quietly treating it as
final would be picking OneLive's strategy without being asked to. **This
proposal is not measured or reported anywhere as if it were ratified — see
`docs/RECORD.md` R-046.**

Two runner-up candidates considered and set aside (for the founder to
revisit if the above doesn't fit): (a) "sources actively contributing at
least one verified event per week" — a pure coverage metric, but it does not
penalize hallucination risk; (b) "events promoted per dollar of extraction
spend" — a pure efficiency metric, already tracked as its own KPI below
(cost-efficiency) rather than elevated to North Star, since efficiency
without a trust floor is the wrong thing to maximize first.

---

## 3. Areas and their KPIs

Each KPI below states: **leading** (an early signal you can act on before the
outcome lands) vs. **lagging** (the outcome itself, known only after the
fact); its **target**; **how it's measured** (the real, cited source — never
a made-up number); and its **owner** (which loop/agent is accountable for
moving it). Live current values are in `docs/metrics/KPI_LEDGER.md`, kept
current by `python tools/kpi_report.py --append TIMESTAMP`.

### 3.1 Ingestion / Coverage
*Are we finding and importing the real events that exist?*

| KPI | Kind | Target | Measured by | Owner |
|---|---|---|---|---|
| Source catalog size (enabled sources) | lagging | ≥120 sources (docs/RECORD.md R-007) | `select count(*) from source where enabled` against the live DB | ingestion loop (Sentinel) |
| Scheduled cron slot-fire density | leading | ≥80% of eligible 20-minute slots actually fire (R-023) | the healthchecks.io read-only API + GitHub Actions run history | ingestion loop (Sentinel) |

Both are currently **not yet instrumented** in `tools/kpi_report.py` (it is
a stdlib-only, no-network tool by design) — see §5.

### 3.2 Extraction Correctness — the zero-escaped-defects reputation metric
*When the AI reads a page and pulls out facts, are those facts TRUE?* This is
the area with the most to lose reputationally: one confidently-wrong fact
that reaches a user is worse than ten pages of missed coverage.

| KPI | Kind | Target | Measured by | Owner |
|---|---|---|---|---|
| Field-level hallucination rate @ last certification | lagging | ≤1%, one-way ratchet only tightens (`docs/KAIZEN.md` §M7, `ai/exam_thresholds.HALLUCINATION_MAX`) | the attended golden-exam certification record, `ai/golden/CERTIFIED_HARNESS.json` | extraction loop / evaluator gate |
| Recall @ last certification (anti-gaming pair) | leading | ≥80% (`ai/exam_thresholds.RECALL_MIN`) — stops the extractor from "passing" by asserting almost nothing | same certification record | extraction loop / evaluator gate |
| All-time escaped defects (M3) | lagging | **0, absolute** — the Deming zero-escaped-defects goal (`docs/KAIZEN.md`) | `docs/metrics/KAIZEN_LEDGER.md` via `tools/kaizen_trends.py::escapes()` | Kaizen / evaluator gate |
| Production trailing hallucination rate | lagging | tracked weekly; ratchets the certified bar down when it holds at ≤ half the current bar for 4 cycles | KAIZEN §M7 names admin-review verdicts + user reports as the input — **not yet instrumented**, see §5 | extraction loop / Kaizen M7 ratchet |

### 3.3 Cost-efficiency
*Are we spending the least money that still clears every quality bar?*
(CLAUDE.md "Cost discipline": cheapest-capable tier first, escalate
deliberately, never relax a gate to save money.)

| KPI | Kind | Target | Measured by | Owner |
|---|---|---|---|---|
| Cost per verified published event (§14.2 — the canonical unit economic) | lagging | no baseline yet ("it becomes your own baseline" — §14.2) | tokens + fetch cost + ops-minutes ÷ events promoted — **not yet instrumented**, see §5 | FinOps / model router |
| Loop-stage model routing wired (no hardcoded model ids) | leading | every declared stage (`mechanical`/`standard`/`critical`/`extraction`/`evaluator`) resolves via the router, never a hardcoded id | `tools/model_router.py::resolve_model()` over every stage | model_router / Generator |

### 3.4 Brain quality
*Is the shared "brain" (the pipeline's persistent knowledge) getting
smarter, not just bigger?*

| KPI | Kind | Target | Measured by | Owner |
|---|---|---|---|---|
| Brain IQ composite (knowledge / efficiency / learning) | lagging | one-way ratchet: the two GATED dimensions (knowledge, efficiency) must never regress below their best recorded value | `brain/iq.py::compute_brain_iq()`, trended in `docs/metrics/BRAIN_IQ_LEDGER.md`, gated by `tools/brain_iq.py --check` (already wired into `tools/validate`) | brain loop |

Brain IQ's own known measurement gaps (reasoning depth beyond ~3 hops, real
production extraction yield, real wall-latency under load, the external
LongMemEval leaderboard) are tracked in `docs/metrics/
BRAIN_MEASUREMENT_COVERAGE.md` — this framework reads that list, it does not
duplicate it.

### 3.5 UX / consumer
*Is the app itself good to use, and are real people finding value in it?*

| KPI | Kind | Target | Measured by | Owner |
|---|---|---|---|---|
| Web app test suite (vitest) green | leading | 100% green on every web PR | the web CI job — a different toolchain (Node/vitest); **not yet instrumented** in the stdlib-Python `tools/kpi_report.py`, see §5 | web loop |
| Real user engagement / retention | lagging | to be DEFINED at public launch (charter §15 growth, still a PROPOSAL) | product analytics once the site is public — **not yet instrumented**, see §5 (the site is behind the Clerk stealth gate today) | web loop / growth |

### 3.6 Trust / safety
*Do the hard rules — AI never publishes, disputed is always shown, no
pay-to-rank — actually hold, mechanically, every time?*

| KPI | Kind | Target | Measured by | Owner |
|---|---|---|---|---|
| `trust_gate` clean (trust invariants hold) | lagging | PASS, always (CLAUDE.md prime directive 1) | `tools/trust_gate.py` exit code | gate custody / evaluator |
| Kaizen repeat-class alarms active | lagging | 0 active (`docs/KAIZEN.md` repeat-class rule: 3+ catches of the same defect class with no structural fix is itself a finding) | `tools/kaizen_trends.py::build_report()` | Kaizen / evaluator gate |
| `docs/RECORD.md` open deviations | leading | not a fixed number — every OPEN row must carry a LIVE, objective trigger; a row whose trigger fired and wasn't acted on is a defect | parsed directly from `docs/RECORD.md`'s table | gate custody / Generator |
| pytest suite size (breadth) | leading | grows or holds steady; never silently shrinks | `pytest --collect-only` | Generator |

---

## 4. The quarterly cadence

Once a quarter (roughly aligned to calendar quarters — the framework's first
cycle is **Q3 2026, now through 2026-09-30**):

1. **Read the ledgers.** Pull the latest snapshot from `docs/metrics/
   KPI_LEDGER.md` (run `python tools/kpi_report.py --append TIMESTAMP` first
   if it's stale), alongside the trend direction in `docs/metrics/
   KAIZEN_LEDGER.md` and `docs/metrics/BRAIN_IQ_LEDGER.md`. This is "White
   hat" fact-gathering (`docs/hats/white.md`) — fact-only, no opinions yet.
2. **Score candidate initiatives with RICE (or ICE).** For everything in
   `TODOS.md` that's a real candidate for the quarter's focus, score it:

   > **RICE score = (Reach × Impact × Confidence) ÷ Effort**
   > - **Reach** — how many events/users/runs does this touch per period
     (a rough count, not a guess-free science)?
   > - **Impact** — on a simple scale (3 = massive, 2 = high, 1 = medium,
     0.5 = low, 0.25 = minimal) — how much does this move a KPI above?
   > - **Confidence** — 100% / 80% / 50% as a plain multiplier — how sure are
     we of the Reach/Impact estimates?
   > - **Effort** — person-weeks (or agent-session-count) to ship it.
   >
   > **ICE** (simpler, use when Reach is hard to estimate) = (Impact ×
   > Confidence × Ease) ÷ 3, each scored 1–10.

   Neither score is precise — it is a **forcing function for an honest
   conversation**, not a formula that removes judgment. Ties, and anything
   trust-critical, are broken by the invariant that trust/safety work is
   never traded away for a higher RICE score elsewhere (CLAUDE.md prime
   directive 1 always wins).
3. **Set 3–5 objectives with measurable key results (OKR-style).** Each
   objective names 1–3 Key Results, each of which is one of the KPIs in §3
   (or a clearly-scoped sub-metric of one) moving from a stated current value
   to a stated target value, by the end of the quarter. No objective may
   silently touch a trust invariant — that still requires the founder
   (CLAUDE.md "Founder-crucial escalations").
4. **Ratify.** The founder reviews the proposed 3–5 objectives (plain
   language, via the standard founder-communication rules — plain language,
   "why this not that", honest tradeoffs, direct links, one consolidated
   list) and either approves, adjusts, or asks a clarifying question.
5. **Run the quarter.** `TODOS.md` items get tagged with the objective they
   serve; session closes keep updating the KPI ledger (`tools/kpi_report.py
   --append`) so drift is visible mid-quarter, not just at the end.
6. **Quarterly review.** Re-read the ledgers (step 1), score what actually
   moved vs. what was planned, and feed the honest gap into next quarter's
   RICE scoring. A KPI that stayed flat despite being an objective is itself
   a finding — write it down, don't quietly re-propose the same objective
   with no root cause.

### Q3 2026 objectives — DRAFT, for founder ratification

Built directly from `STATE.md`'s "top of queue" and `TODOS.md`'s P0/P1 rows,
scored illustratively (numbers below are a first-pass RICE estimate, not a
committed fact — the founder may reweight or replace any of them):

| # | Objective (draft) | Key Result(s) | Illustrative RICE |
|---|---|---|---|
| 1 | Get the licensed ticketed spine flowing end-to-end | migrations 0011/0012 applied + first real Ticketmaster/SeatGeek rows visible on `/tonight` (R-030) | Reach 9 · Impact 3 · Confidence 80% · Effort 2 → **10.8** |
| 2 | Make the promote path a real, working habit, not a trickle | ≥1 ops-promote review cycle/week on `ready_to_promote` candidates; R-030's crawl-path items (multi-event, per-source listing URLs) each move one step | Reach 7 · Impact 2 · Confidence 70% · Effort 3 → **3.3** |
| 3 | Close the sparse-cron-delivery decision | R-023's founder decision (metronome / alarm rematch / accept) made and acted on | Reach 8 · Impact 2 · Confidence 90% · Effort 1 → **14.4** |
| 4 · trust/safety, non-negotiable floor | Zero escaped defects, zero repeat-class alarms, all quarter | M3 escapes stays 0; no repeat-class alarm crosses threshold unaddressed | not RICE-scored — this is the floor every other objective must clear, not a competing initiative |

These are a **starting proposal**, not a decision — step 4 in §4 above
(founder ratification) is what makes any of this live.

---

## 4a. How to change a KPI, its target, or its frequency

Founder directive: this must be **easy and low-effort**, not a code change.
The whole list of tracked KPIs — what they are, their targets, how often
each is reviewed, who owns them, and whether they're on at all — lives in
one plain-data file: `docs/metrics/kpi_registry.json`. `tools/kpi_report.py`
only reads and validates that file; it never hardcodes the list.

**The 3-step recipe:**

1. **Edit `docs/metrics/kpi_registry.json`.** Find the KPI (or add a new
   entry) and change whatever needs changing:
   - `target` — the bar you're aiming for (any human-readable string).
   - `frequency` — how often it's worth looking at: `per_run`, `daily`,
     `weekly`, `monthly`, or `quarterly`.
   - `area`, `owner` — which part of the business it belongs to and who's
     accountable.
   - `enabled` — set to `false` to stop tracking a KPI without deleting its
     history (a `true`/`false` flip, not a code change either way).
2. **Verify it took.** Run `python tools/kpi_report.py --print` and read the
   scorecard — your edit is right there (a changed target, a changed
   frequency line, a KPI turned on/off, added, or removed).
3. **Commit.** That's it — no Python file changes needed for any of the
   above.

**What is JSON-only vs. what needs code:** target, frequency, area, owner,
and enable/disable are ALWAYS a JSON-only edit, whether on an existing KPI
or a brand-new one — as long as the new KPI either reuses a measurement that
already exists (name it in the `compute` field, e.g. `"compute":
"trust_gate"`) or is a KPI nobody can measure yet (`"compute": "manual_gap"`,
with a `why` and a `trigger` explaining what would need to happen for it to
become measurable). The **only** case that needs a code change is teaching
the tool a genuinely **new way to measure something** — a new source of
truth nothing else already reads. Even then, the change is small and
bounded: one new Python function in `tools/kpi_report.py`, registered by
name in its `_COMPUTE_FUNCTIONS` map, referenced from the JSON by that name.

A malformed entry (a typo'd field name, an unrecognized `frequency` value,
a `compute` key that doesn't exist) makes the tool refuse to run at all,
with a specific error naming the bad entry and field — it never silently
drops a KPI or guesses a value (fail-closed, per CLAUDE.md's no-silent-
deferrals rule).

---

## 5. How this feeds from (not duplicates) the existing ledgers

This framework and its two artifacts — `docs/metrics/KPI_LEDGER.md` and
`tools/kpi_report.py` — are the **aggregation layer only**:

- **Extraction correctness** numbers come from the already-existing golden-
  exam certification (`ai/golden/CERTIFIED_HARNESS.json`) and the Kaizen
  ledger's M3-escape count — nothing here re-runs an exam or re-scores a
  hallucination rate.
- **Brain quality** comes straight from `brain/iq.py` / `docs/metrics/
  BRAIN_IQ_LEDGER.md` — the ratchet stays owned by `tools/brain_iq.py
  --check` (already wired into `tools/validate`); this framework only reads
  and displays it alongside everything else.
- **Trust/safety** comes from `tools/trust_gate.py`'s own exit code and
  `tools/kaizen_trends.py`'s own repeat-class-alarm logic — again, read not
  recomputed.
- **Cost discipline** reads `tools/model_router.py` directly (the same
  router already wired into CI).

If any of the source ledgers change their format, `tools/kpi_report.py`
fails LOUD (a parse error, never a guessed number) rather than silently
drifting — see `tests/test_kpi_report.py`.

---

## 6. The Goodhart-honesty control — "KPIs we have NOT yet instrumented"

Mirrors `brain/iq.py`'s `MEASURED` / `NOT_YET_MEASURED` split
(`docs/metrics/BRAIN_MEASUREMENT_COVERAGE.md`): a scorecard that quietly
claims to cover everything is a Goodhart trap — it invites optimizing the
measured proxy while the unmeasured parts silently rot. So every KPI this
tool cannot yet compute is named explicitly, with WHY and an objective
TRIGGER, never silently skipped. The canonical, machine-checked list is
`tools/kpi_report.py::NOT_YET_INSTRUMENTED_SLOTS`, rendered in full (tagged
`[GAP]`) by `python tools/kpi_report.py --print`, and asserted non-empty +
honest by `tests/test_kpi_report.py`.

| Not yet instrumented | Why | Objective trigger |
|---|---|---|
| Source catalog size | needs a live DB connection; `tools/kpi_report.py` is stdlib-only/no-network by design | a session with `ONELIVE_DB_DSN` present runs the count and folds it in |
| Scheduled cron slot-fire density | needs the read-only healthchecks.io API + GitHub Actions API, neither reachable from this offline tool | a session with `HEALTHCHECKS_API_KEY_RO` + `gh` computes the trailing 24h slot-fire rate |
| Production trailing hallucination rate | `docs/KAIZEN.md` §M7 names admin-review verdicts + user "Something off?" reports as the input, but no code yet tallies confirmed errors against total assertions | first batch of admin-review verdicts and/or user reports flows, and a script tallies confirmed errors ÷ total field assertions |
| Cost per verified published event (§14.2) | no live cost meter exists yet — tokens+fetch+ops-minutes per promoted event is not logged anywhere | first real scheduled ingestion run with per-event cost logging wired, and at least one promoted event to divide by |
| Web app test suite (vitest) green | a different toolchain (Node/vitest); this stdlib-only Python tool does not shell into npm, to keep its own no-network determinism | a stdlib-safe reader of the web CI job's test-count artifact/log is wired into `tools/kpi_report.py` |
| Real user engagement / retention | the site is behind the Clerk stealth gate; there is no public traffic to measure yet | public launch + analytics wired (Vercel Analytics, `TODOS.md` P1) define and start reporting real engagement |

See `docs/RECORD.md` R-046 for the same list recorded as a deferral, per the
charter's no-silent-deferrals rule, and for the North Star's own
founder-ratification gap.

---

## 7. What this is not

- Not a new gate. It never blocks a merge or a session close (`tools/
  kpi_report.py --check` exists for visibility, but nothing in `tools/
  validate` currently depends on it — the existing gates keep their own
  custody).
- Not a replacement for the Kaizen ledger, the Brain IQ ledger, the trust
  gate, or RECORD.md. It reads all four; none of them are superseded.
- Not a license to relax any existing gate to make a KPI look better —
  CLAUDE.md's "gate-threshold relaxations are founder-crucial" applies with
  full force here; a KPI never outranks a trust invariant.
- Not the North Star decision itself — that is explicitly reserved for the
  founder (§2).
