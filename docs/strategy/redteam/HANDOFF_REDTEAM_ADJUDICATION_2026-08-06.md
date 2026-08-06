# Red-Team Adjudication — Crawler/Extraction Handoff (2026-08-06)

**Reviewers (four, independent):**
ChatGPT (structural critique of the handoff document) ·
Gemini (engineering review; Deliverables 5–8 delivered, 1–4 blocked on sandbox) ·
Perplexity (senior process review + execution package; read all 2,784 lines) ·
Grok (Fix 01 review + root-cause analysis).

**Adjudicator:** this session, checking every load-bearing claim against the
committed code — file and line cited, or the function run and its output pasted.

**Scope.** *(Corrected mid-session — the first version of this document said the
handoff was not in the repo. It is: `lab/HANDOFF_ONE_FILE.md` on branch
`claude/crawler-lab`, **2,784 lines**, matching Perplexity's stated line count
exactly. I had checked `master` only. The correction is kept visible rather than
edited away, because a scope claim that was wrong is exactly the kind of thing
this document exists to catch.)*

This adjudication is still built primarily on **the reviewers' claims about our
code**, checked against the tree — that is the axis that decides what we do.
Where the handoff itself settles a question, it is now cited directly.

---

## VERDICT

**The convergent findings are real. I verified the three that matter and one is
worse than any reviewer said.** Priority order and the plan are in §6.

Reviewer quality, since running four models is only worth it if we say what we
learned: **Grok and Perplexity are the strongest; Gemini is solid with two
factual errors; ChatGPT's is the weakest and its central recommendation is
rejected.** All four hit the same blocker (no network, no repo). Three
documented it and delivered findings anyway. One used the document's size as
the reason not to engage with its contents. That difference — not the
scorecards — is the useful output of running a panel.

---

## 1. CONVERGENT AND VERIFIED — act on these

### V1. Range dates are fabricated, silently. (Gemini · Perplexity · Grok)

**CONFIRMED, AND WORSE THAN ANY REVIEWER REPORTED.** Run against the live
function (`worker/datetime_normalize.py::normalize_datetime_claim`, wired into
production at `worker/ai_extract.py:164` and `worker/vision_extract.py:213`):

```
'SEPT 04-27'            -> ('2027-09-04T00:00:00', None)
'Sept 4-27'             -> ('2027-09-04T00:00:00', None)
'Sept 4-27, 2026'       -> ('2027-09-04T20:26:00', None)
'September 04-27, 2026' -> ('2027-09-04T20:26:00', None)
'Sept 4'                -> (None, {'reason': 'no-full-date-evidence'})
```

Read line three. Given a string that **states the year 2026 explicitly**, the
parser discards that year, promotes the range's end day `27` to the year, and
**invents a clock time of 20:26 from the digits of the year it just threw
away**. The second tuple element is `None` — **no refusal was raised.** The
module exists to refuse rather than guess; its own docstring says guessing
"would assert an unverified fact, the exact thing the pipeline exists to
prevent." On this input it does precisely that, silently, with full confidence.

`tests/test_datetime_normalize.py` contains no range case.

Reviewers reported the wrong year. Nobody caught the invented time, and nobody
caught that an explicit year is overridden. This is a live trust-invariant
violation on a product whose canon is "never assert a fact you have not read
from the source."

*Records note:* Grok cites this as **R-081**. `docs/RECORD.md` tops out at
**R-079** — R-080/R-081 exist in the handoff but not in the committed record.
Minor, but the record is the thing we claim is truth, so it gets reconciled.

### V2. Nothing anywhere asserts that a published event is visible. (Perplexity · Grok)

**CONFIRMED FROM BOTH ENDS OF THE PIPE.**

- `worker/gating.py` — **zero occurrences of `start_time`** in 142 lines. The
  gate that decides whether a candidate may be promoted never asks whether the
  event has a date.
- `web/lib/promoted.ts:94-95` — the feed filters `start_time=gte.<from>` and
  `start_time=lte.<to>`. In Postgres a NULL fails both comparisons, so **every
  dateless row is silently dropped from the feed.**

So: a candidate with no date passes the gate, promotes, counts as success in
every internal metric, and **cannot be seen by any user.** That is the
mechanism behind the reported 2,214-invisible/1-visible number, verified in
code without needing the database.

Grok's framing is the correct one: this is the **meta-defect**. Every green run
above it was false progress. Perplexity's version — "20 gates, 1,953 tests, and
not one that asks whether a user can see the row" — is the same point stated as
a process failure, and it is fair.

### V3. Typed JSON-LD is parsed, then destroyed. (Gemini · Perplexity · Grok)

**CONFIRMED.** `worker/segment.py::_jsonld_event_text` receives the fully typed
schema.org dict and reduces it to `" | ".join(parts)` from `name`, `startDate`,
`location.name`, `location.address`, `url` — and nothing else. `eventStatus`,
`offers`, `performer`, `doorTime`, `endDate`, `location.geo` are read by nobody.

The destruction is structural, not incidental: `worker/ai_models.py` carries
exactly **11 fields** (`title`, `start_time`, `end_time`, `venue_name`, `city`,
`artist_names`, `ticket_link`, `rsvp_link`, `is_private_rsvp`,
`private_access`, `notes`). **There is no status field anywhere in the
extraction schema**, so an explicit `eventStatus: EventCancelled` has nowhere to
land even if it were parsed. Cancelled shows publish as live. Gemini's
escalation from CRITICAL to EXISTENTIAL is accepted in kind — a truth
violation, not a coverage gap.

Grok's cascade addition is the sharpest: this function is **the manufacturing
site** for the free-text date ambiguity that the entire downstream date
machinery (and PR #189's eight review rounds) exists to repair. Fixing it
should let us *delete* code, not only add it.

**One correction on the "it's a one-line fix" claim (Perplexity R6).** The
premise is right — the typed `obj` is already in hand, we destructure it for no
reason. But `_jsonld_event_blocks` returns `List[str]`, `_segment_html` returns
`List[str]`, and `segment_events`' contract is `List[str]` with tests bound to
it. Changing what `_jsonld_event_text` returns means changing that contract
through three call sites and the extractor prompt. Perplexity concedes this in
its own R6.5. Calling it "one line" is rhetoric; the additive
`structured_events()` path that Gemini and Grok both endorse is the honest
shape. **Adopt additive.**

### V4. Process cost is real and measurable. (ChatGPT abstractly · Perplexity concretely)

The standing context weight, measured rather than argued:

| File | Size | ≈ tokens |
|---|---|---|
| `docs/ONE_LIVE_CHANGE_LOG.md` | 380 KB | ~95,000 |
| `STATE.md` | 280 KB | ~70,000 |
| `docs/RECORD.md` | 102 KB | ~26,000 |
| `TODOS.md` | 64 KB | ~16,000 |
| `docs/OPERATING_RULES.md` | 31 KB | ~7,700 |
| `CLAUDE.md` | 23 KB | ~5,800 |

Any session that reads its own bookends before doing anything spends real
budget on narration. Perplexity's inverted-ratio framing — engineering measured
in hours, ceremony measured in days — is the honest reading, and its list of
taxes (`staleness_check`, `construction_gate` on prose, the 27-file arming
re-bind, the golden exam that is red by design on the file it protects) is
accurate to the tools that exist in `tools/`.

**How to settle it without arguing.** Perplexity's own test is the right one:
*has this gate ever caught a defect that would have reached a user?* We already
built the instrument that answers it — `docs/metrics/KAIZEN_LEDGER.md` records
every internal catch with its gate and defect class, by charter. So this is a
**measurement**, not a debate. Run it per gate, then decide. See §5.

---

## 2. FACTUAL CORRECTIONS — do not act on these

**C1. "`@graph` arrays are ignored / multiple Event objects unhandled."**
(Gemini §1.8, Grok §8) — **FALSE.** `worker/segment.py::_iter_jsonld_objects`
is an explicit stack walker handling a bare object, a top-level list, **and**
`@graph` wrappers. Multiple Events on one page is the path that already works.
Already built; two reviewers independently invented the same gap.

**C2. "Microdata is ignored."** (Gemini §1.8) — **MOSTLY FALSE.**
`_segment_html` step (2) detects `itemtype="…schema.org/Event"` containers and
segments on them. The true, narrower claim is Grok's, which is correctly
worded: the *JSON-LD function* is JSON-LD-only, and microdata `itemprop`
**values** are never read as typed fields. That is the same defect as V3, not a
separate one.

**C3. "Flattening strips the UTC offset."** (Gemini) — **OVERSTATED.** The
offset survives inside the flattened string, and a full ISO timestamp
round-trips correctly (`'2026-09-04T20:00:00-05:00'` → unchanged). The real
risk is the model **re-emitting** an offset it was shown as prose. Still an
argument for typed passthrough, just not the stated one.

**C4. "Delete `tools/scan_new_sources.py`."** (Gemini DISCARD #1) — **REJECTED
as premature.** The scanner is blocked on a broken credential. Deleting a tool
because its key doesn't work destroys work to fix a config problem. Its design
*is* too narrow (20 phrases, one city) — that is an argument for the discovery
redesign all three substantive reviewers want, not for deletion.

**C5. "Commit the following script to `lab/census_structured.py` and run it."**
(Gemini §5, and Grok §"$0 census") — **ALREADY BUILT.** On
`claude/crawler-lab`: `lab/census_structured.py` (188 lines) and
`lab/discover_sources.py` (208 lines) both exist, each substantially more
developed than Gemini's ~60-line sketch. Gemini asked the founder to hand-commit
a file that is already in the repo, and its discovery design §2 partly
re-specifies `discover_sources.py`.

**The real gap is one step later, and Grok named it correctly: the census has
never been RUN.** No results are committed anywhere on the branch — no
`census.json`, no `spend.jsonl`. So the instruments are built and the
measurement is missing. That is the true blocking step for tiers 2–5, and it
costs $0 to take.

---

## 3. WHAT ALL FOUR MISSED

**M1. On a single-event detail page, the JSON-LD path never fires at all.**

```
# worker/segment.py, _segment_html()
blocks = _jsonld_event_blocks(content)
if len(blocks) >= 2:
    return blocks
```

The helper's docstring states the rule outright: *"Returns [] unless the parse
is clean and finds >= 2 events, so a single JSON-LD event never diverts from
the whole-page single-block path."*

So every single-event **detail page** — exactly where a ticketing hop lands,
exactly where the richest JSON-LD lives — has its machine-declared typed data
**ignored entirely**, and the whole page goes to the model as raw text.

Three reviewers attacked the flattening. This is the layer above it: on detail
pages there is nothing to flatten, because the structured path never runs. Any
"Tier 0 structured-first" ladder that doesn't fix this gate is decorative on the
pages that matter most. **Both must be fixed together or the fix is cosmetic.**

**Confirmed absent from the source document too**, now that it is readable:
`grep -nE "_jsonld_event_blocks|_segment_html|len\(blocks" lab/HANDOFF_ONE_FILE.md`
returns nothing on `claude/crawler-lab`. The handoff names the destroying
function (`_jsonld_event_text`) but never the segmentation gate above it. So
this defect is missed by the handoff and by all four reviewers — it is the one
genuinely new finding of this exercise, and Fix 01 as currently specified would
ship without it.

**M2. Grok alone got close to the other gap** (§8: "how do parked
`_provenance.structured` fields survive candidate → promote"). Extending it:
`worker/promote.py:132` bypasses deduplication entirely for dateless
candidates —
`dups = find_possible_duplicates(...) if start_time else []` (Gemini's DISCARD
#2, confirmed verbatim) — so the invisible rows are also **un-deduplicated**.
V2 and this compound: we hoard invisible duplicates and score it as throughput.

---

## 3b. A LIVE CHARTER VIOLATION, found while chasing a reviewer's citation

Grok cited the fabricated-year defect as **R-081**. Chasing that ID down turned
up something worse than a stale reference.

**R-081, R-082, R-083 and R-084 do not exist in `docs/RECORD.md` — on `master`
or on `claude/crawler-lab`.** Both branches top out at R-079. Yet the ids are
cited as recorded authority across **six** documents on the lab branch
(`HANDOFF_ONE_FILE.md`, `EXTERNAL_AI_BRIEF.md`, `NEW_SESSION_PROMPT.md`,
`PIPELINE_COMPONENTS.md`, `PLAN.md`, `docs/ops/CODE_EVALUATION_2026-08-06.md`),
including a summary row that reads:

> `docs/RECORD.md` R-081/082/083/084 | Open defects: fabricated year, exam never
> re-runs, bad catalog URLs, unmeasured cause split

**So four known open defects — one of them the live fabrication path — are
described everywhere as "recorded" and are recorded nowhere.** That is precisely
what CLAUDE.md's *"The Record — no silent deferrals"* forbids: every deferral is
written to `docs/RECORD.md` **in the same commit**, with the bar it deviates from
and an objective resolution trigger. Grok relayed the id in good faith; the
handoff is the source of the error.

**Why the machinery missed it.** `lab/verify_claims.py` re-derives claims **from
the source tree** — extraction field count, card field count, `start_time` hits
in the trust gate, query-pack size, the promote dedupe line, the flattening
function and the fields it keeps, the render trigger — and the assembler refuses
to build when any drifts. Every one of those is a CODE claim. A cited `R-###` is
not checked against `RECORD.md` at all. Meanwhile `tools/deferral_scan.py`
enforces live `[R-###]` tags only on **code comments**; the charter states that
prose is "covered by this rule + evaluator review," i.e. not mechanically. These
citations are prose. **The escape went straight through the one documented gap
between the two enforcers.**

This is the concrete instance of Perplexity's §2.3 argument — that the tree
cannot be trusted, so a verifier was built downstream — and it is stronger than
the version Perplexity could make without the tree: the verifier itself has a
blind spot, and four defects fell into it.

**IMPORTANT COUNTERWEIGHT — the handoff is otherwise accurate, and the gap is
exactly the shape of the verifier's coverage.** Spot-checking its load-bearing
numbers against the tree:

| Handoff claim | Checked | Result |
|---|---|---|
| The card contract is **30 fields** | `LicensedEvent` in `web/lib/licensed.ts` | **EXACT** — 30 |
| Extraction schema is 11 fields, filling 7 card fields | `worker/ai_models.py` | **EXACT** — 11 |
| `gating.py` has zero `start_time` | `grep -c` | **EXACT** — 0 |
| The dateless dedupe bypass line | `worker/promote.py:132` | **EXACT**, verbatim |
| `_jsonld_event_text` flattens to a joined string | `worker/segment.py` | **EXACT** |
| 1,953 tests | not checkable here — pytest is not installed in this sandbox | **UNVERIFIED**, stated rather than guessed |

Every claim that `lab/verify_claims.py` covers holds up precisely. The one class
it does NOT cover — record-id citations — is exactly where four fabrications
sit. **That is not general unreliability; it is a coverage hole with a crisp
edge.** The remedy is correspondingly small: extend the same assembler that
already refuses to build on code-claim drift so it also resolves every `R-###`
in the prose against `RECORD.md`. One more claim function, same refusal
behaviour, and this class cannot recur.

Note also that Gemini's "we extract 11" and the handoff's "fills 7 of 30" are
both correct and not in conflict — 11 extracted fields, 7 of which map onto card
fields. Neither reviewer was wrong here.

**Consequences, in order:**
1. The date fix must **carry the R-081 row that was never written**, not assume
   it exists. Same for the other three when their fixes land.
2. **New escape class for the ledger:** *a record id cited as authority when no
   record exists.* It is mechanically detectable — every `R-###` in prose either
   resolves to a row in `RECORD.md` or fails — and `tests/test_record_ids_unique.py`
   already proves this family of check is cheap to write.
3. It is a genuine **ESCAPED** row, not an internal catch: the ids reached four
   external reviewers, and one of them repeated the fabricated citation back to
   the founder as fact.

---

## 4. REJECTED — with reasons

### ChatGPT: "Do not iterate. Redesign the entire AI engineering workflow."

**REJECTED — but my first stated reason was OVERSTATED, and the correction is
recorded here rather than quietly dropped.**

I originally wrote that its ten-artifact "AI Engineering Operating System"
already exists in this repo. Challenged to prove it, I checked all ten. **Six
exist. Four are real gaps.**

| # | ChatGPT artifact | In the tree? | Evidence |
|---|---|---|---|
| 1 | Mission Charter | **YES** | `CLAUDE.md`, 127 lines |
| 2 | Engineering Constitution | **YES** | `OPERATING_RULES.md` 497 + `CODING_CONVENTIONS.md` 97 + `MODEL_ROUTING.md` 96 (budget policy included) |
| 3 | System Architecture Spec | **PARTIAL** | `docs/Final_ONE_Live_Authoritative_Technical_Spec.md` is **37 lines** |
| 4 | Component Specs (one per subsystem) | **GAP** | READMEs exist for `ai/golden`, `sources`, `tools`, `docs/memory`, `docs/hats` — **none for `worker/`, `api/`, or `web/`**, the three core subsystems |
| 5 | Interface Contracts | **PARTIAL** | `contracts/` holds exactly **one** file (`ops_inbox.contract.json`) + 19 SQL migrations |
| 6 | Task Packs (minimal per-job context) | **PARTIAL** | Six kickoff prompts exist, but each is 11–14 KB; no minimal-context-loading mechanism |
| 7 | Verification Packs | **YES** | `tools/validate`, `trust_gate.py`, `deferral_scan.py`, `lint.py` |
| 8 | Decision Log (append-only) | **YES** | `docs/memory/decisions/` — **73 records** |
| 9 | Evidence Store | **YES** | `docs/RECORD.md` + `docs/metrics/KAIZEN_LEDGER.md` (351 rows) |
| 10 | Project Memory Index | **YES** | `docs/memory/` — README, RED_CLASSES, brain.jsonl, decisions, entities, gotchas |

**So "it prescribes what already exists" was 6/10 true, not 10/10, and I should
not have stated it as flatly as I did.** Items 3–6 are genuine gaps, and they
are precisely the ones tied to the context-efficiency complaint — which makes
ChatGPT's *diagnosis* on those four better than I credited.

**The rejection nevertheless stands, on the corrected basis:**

1. **The remedy is disproportionate to the disease it correctly names.** Four
   missing artifacts are filled by writing four artifacts — three subsystem
   READMEs, a real architecture spec, more interface contracts, and a
   context-packing convention. That is a week of work inside the existing
   system. "Do not iterate — redesign the entire AI engineering workflow" trades
   a live, publishing engine for a months-long meta-project to reach the same
   place.
2. **Zero findings.** Same blocker as everyone else; three others returned
   verifiable claims. **Grading is not review.** The ratings (2/10 token
   efficiency, 9.5/10 vision) carry no measurement and no method — and this
   session's own gate-cost table (§5b) shows what it looks like when the same
   question IS measured.
3. **Wrong on mechanism where it is testable.** "A model doesn't remember
   because something is repeated" is asserted as fact and used to justify
   deleting repetition. Load-bearing invariants that must survive compaction are
   exactly what is worth restating.

**ADOPTED as a consequence of being challenged:** items 3–6 go into TODOS as a
scoped documentation contract. That is ChatGPT's real contribution, and it took
proving the rejection to find it.

### Perplexity R1: "Retire `worker/`, build `worker_v2/` from empty."

**REJECTED AS FRAMED; DIAGNOSIS ADOPTED.** The ceremony-cost diagnosis is
correct. The remedy is the single riskiest proposal across all four reviews, and
Perplexity's own Part C red-teams it ("greenfield rewrite failure mode") — I
agree with its self-critique.

The specific danger: **the trust invariants are implemented in `worker/`** — the
promote-path custody, the structural guarantee that the orchestrator cannot
import promote, the gate physics, the RLS interaction. R1's stated appeal is
that `worker_v2/` "starts empty" and gets "to design its verification story from
scratch." That is the exact mechanism by which those invariants would be lost,
and per the charter they are physics, not policy.

**PROOF, not judgement — the invariants are enforced by literal module paths,
and a rename voids them silently.** `tools/trust_gate.py` hardcodes:

```python
PIPELINE_MODULES = ("worker.gating", "worker.promote")
PROMOTE_IMPORT_ALLOWLIST = {"api/ops_candidates.py", "worker/autopromote.py"}
```

and `check_ai_never_promotes` scans exactly `REPO/ai/**` plus the single
hardcoded path `worker/ai_extract.py`, guarded by `if not path.exists():
continue`. Every check keys on the string `worker.` — so I built the tree R1
proposes and ran the real gate against it.

The fake tree deliberately violates all three invariants: `orchestrator.py`
imports promote (the AI loop publishing — the one thing the charter calls
physics), `ai_extract.py` imports promote (extraction publishing), and
`ads_ranking.py` imports the gating pipeline. Renamed to `worker_v2`, running
the repo's own `check_ai_never_promotes` + `check_promote_import_allowlist` +
`check_ads_tastemaker_isolation`:

```
files in the fake tree: ['worker_v2/ads_ranking.py', 'worker_v2/ai_extract.py',
                         'worker_v2/promote.py', 'worker_v2/orchestrator.py']

violations on a DELIBERATELY-violating worker_v2 tree: 0

VERDICT: OK - all trust invariants hold
```

**Zero violations. The gate prints that the trust invariants hold, on a tree
with no protection whatsoever.** The `path.exists()` guard skips the missing
`worker/ai_extract.py` silently; nothing imports `worker.promote` because it no
longer exists; `PIPELINE_MODULES` matches nothing.

This is not "R1 risks losing the invariants through inattention." **R1 voids
their enforcement mechanically while `trust_gate` continues to report OK** —
their own `false-confidence-gate` red class ("a gate's self-description never
claims more than its implementation"), triggered at the maximum possible blast
radius. Any greenfield move must port these checks FIRST, path by path, and
prove they fail on a violating tree before a single line moves.

**The cheaper path to the same benefit.** The ceremony cost R1 is trying to
escape is concentrated in one fact: `worker/ai_models.py` is bound into
`HARNESS_MANIFEST`, so touching the schema takes extraction offline pending a
founder-attended exam. You do not need a new worker to escape that. You need
either (a) the schema to stop being manifest-bound, or (b) **one batched exam
that covers the whole schema extension at once** instead of several. That is a
scalpel where R1 is an amputation, and it is what makes Fix 01's Phase 1 /
Phase 2 split correct — which is exactly what Gemini, Grok, and Perplexity's own
R6.4 all independently concluded.

**Second-order finding, worth its own fix regardless of R1:** the same proof
shows `trust_gate` is *path-coupled*. Any future refactor that moves or renames
`worker/promote.py`, `worker/gating.py`, or `worker/ai_extract.py` silently
disarms it. A guard that passes vacuously when its subject disappears should
fail closed instead — assert the subjects EXIST before asserting things about
them. That is a gate-hardening change, not a relaxation, so it is not
founder-crucial; queued in §6.

---

## 5. FOUNDER-CRUCIAL — I cannot decide these

Flagged rather than actioned, per CLAUDE.md prime directive 1 and the
founder-crucial list. Surfacing the tension instead of resolving it toward
execution:

1. **Perplexity R2 — kill `staleness_check`, downgrade `construction_gate`,
   put the arming re-bind on a diet.** Each of these is a **gate-threshold
   relaxation**, which the charter states is *"never an agent decision."* The
   reviewer is very likely right that some of these gates cost more than they
   catch. That does not let me switch them off. **What I can do — and propose
   to do — is make the decision evidential:** run Perplexity's own test against
   `docs/metrics/KAIZEN_LEDGER.md`, per gate, and bring you a table of *catches
   vs. cost* so the call is made on data rather than on either of our
   intuitions.
2. **Perplexity R3 — open outbound network in the sandbox.** Security posture
   plus possibly a new service. Your call. The diagnosis is sound: the
   "typed URLs from memory" failures were a tooling problem being treated as a
   discipline problem.
3. **Perplexity R8 — batch founder-attended exams into one weekly window.**
   Pure process, entirely yours, and it is the cheapest item in all four
   reviews.
4. **Schema extension (Fix 01 Phase 2)** takes extraction offline until an
   attended exam. Needs your scheduling decision, not a technical one.

---

## 5b. GATE-COST MEASUREMENT (run, not argued)

Perplexity's test — *has this gate ever caught a defect that would have reached
a user?* — run against `docs/metrics/KAIZEN_LEDGER.md`, the instrument the
charter created for exactly this.

**First result is about the instrument, not the gates: the ledger cannot answer
the question it exists to answer.** Its header promises one row per PR with
"M2 catches by gate/class", but the M2 column is free prose, so a per-gate count
is not queryable. 263 table rows, and the structured field is structured in name
only. That is a fixable instrument defect and it is why this decision has been
argued rather than measured until now.

Proxy used instead — gate name mentioned in the same clause as catch language
(`caught|catches|blocked|failed the|refused|flagged|surfaced`):

| Gate | mentions | with catch-language |
|---|---|---|
| evaluator (non-Claude review) | 368 | **30** |
| `tools/validate` (aggregate) | 85 | 11 |
| golden exam | 46 | 4 |
| `trust_gate` | 18 | 2 |
| `construction_gate` | 13 | 2 |
| `deferral_scan` | 6 | 1 |
| `test_audit` | 3 | 1 |
| `staleness_check` | 3 | 1 |
| `commit_sweep` | 5 | 0 |
| `visual_regression` | 3 | 0 |
| `lint.py` | 2 | 0 |
| `sca_gate` / `eval_harness` / db-integration | 0–1 | 0 |

**Stated limits, because this proxy is weak in a specific direction.** Mention
counting rewards gates that fire and punishes gates that DETER. A gate nobody
tries to violate produces no ledger prose and looks worthless by this measure —
`trust_gate` is the obvious case, and its low score is an artifact, not a
verdict. Read the table as "which gates have a recorded history of catching
things", never as "which gates are worth keeping."

**What it supports, honestly:**

1. **The independent evaluator is doing the overwhelming majority of the real
   catching** — an order of magnitude above every mechanical gate. Whatever else
   changes, that seat stays.
2. **`construction_gate` is the one with a genuinely poor cost/catch ratio on
   PROSE commits**, and this session is the evidence: it demanded citations for
   43 red classes on a records-only document, then 4 more, then 1 more — three
   rounds — because the prose NAMES defect classes. It caught nothing.
   **Recommended fix is surgical, not deletion: scope its content matching to
   code diffs and leave prose to the evaluator.** That keeps the retrieval
   discipline where builds happen and stops taxing documentation.
3. **`staleness_check` should be KEPT — I disagree with Perplexity's "Delete."**
   It caught a real defect in this very session: a mistyped
   `reconciled_through_commit` SHA, refused as INDETERMINATE rather than
   accepted. A fail-closed guard that rejects a fabricated identifier is doing
   precisely the job this project's canon exists to do, and it runs in
   under a second. Its ledger score of 3/1 understates it.
4. **Genuinely unevidenced:** `commit_sweep`, `visual_regression`, `lint.py`,
   `sca_gate`. Worth asking of each whether it deters or merely costs — but that
   question needs the M2 fix below before it can be answered rather than guessed.

**The one change that makes this permanently measurable:** give M2 a real
structured field (`gate=<name> class=<token> n=<int>`) and have the close ritual
write it mechanically. Then "which gates earn their keep" is a query, not an
argument, and the next reviewer who raises this gets a table instead of a
debate. This is a gate-INSTRUMENTATION change, not a relaxation, so it is not
founder-crucial — but it is queued behind the live trust defects in §6.

---

## 6. ADJUDICATED PRIORITY

Ordered by *user harm*, with the ceremony cost of each stated honestly.

| # | Defect | Status | Manifest-bound? | Size |
|---|---|---|---|---|
| 1 | Range dates fabricated (V1) | **Live trust violation** | **No** — `datetime_normalize.py` is deliberately outside the manifest (its own docstring, R-021/PR #43) | Small |
| 2 | No visibility assertion (V2) | **Live; the meta-defect** | No — `gating.py` + a test | Small |
| 3 | Detail-page JSON-LD never fires (M1) | Cost + accuracy | No — `segment.py` | Medium |
| 4 | Typed JSON-LD destroyed (V3 Phase 1) | Cost + accuracy | No — additive `structured_events()` | Medium |
| 5 | Dateless dedupe bypass (M2) | Data hygiene | No | Small |
| 6 | Schema width / `eventStatus` (V3 Phase 2) | **Cancelled shown as live** | **Yes** — takes extraction offline | Larger |
| 7 | Discovery redesign | Deeper failure; 9 of 23 segments unrepresented | No | Own contract |

**Items 1–5 are all outside `HARNESS_MANIFEST`.** They can ship without an
attended exam and without taking extraction offline. That is the single most
useful scheduling fact in this adjudication, and no reviewer stated it: **the
four highest-harm defects carry none of the ceremony cost that R1 proposed
rebuilding the worker to escape.**

Item 6 is the one that needs your exam window. Item 7 needs its own contract.

---

## 7. What this session did NOT do

No code changed. Under OPERATING_RULES §4a the build waits on founder approval
of the plan. This document is records-only.
