# Red-Team Adjudication — Crawler/Extraction Handoff (2026-08-06)

**Reviewers (four, independent):**
ChatGPT (structural critique of the handoff document) ·
Gemini (engineering review; Deliverables 5–8 delivered, 1–4 blocked on sandbox) ·
Perplexity (senior process review + execution package; read all 2,784 lines) ·
Grok (Fix 01 review + root-cause analysis).

**Adjudicator:** this session, checking every load-bearing claim against the
committed code — file and line cited, or the function run and its output pasted.

**Scope honesty.** `HANDOFF_ONE_FILE.md` is not in this repo, so I could not
read the document three of the four reviewers cite by line number. This
adjudicates **their claims about our code**, which is the axis that decides
what we do. Claims purely about the document's shape are marked UNVERIFIABLE
HERE and judged on logic, not evidence.

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

**M2. Grok alone got close to the other gap** (§8: "how do parked
`_provenance.structured` fields survive candidate → promote"). Extending it:
`worker/promote.py:132` bypasses deduplication entirely for dateless
candidates —
`dups = find_possible_duplicates(...) if start_time else []` (Gemini's DISCARD
#2, confirmed verbatim) — so the invisible rows are also **un-deduplicated**.
V2 and this compound: we hoard invisible duplicates and score it as throughput.

---

## 4. REJECTED — with reasons

### ChatGPT: "Do not iterate. Redesign the entire AI engineering workflow."

**REJECTED.** The context-weight observation behind it is right (see V4) and is
adopted there. The prescription is not.

1. **It recommends building what already exists.** Its ten-artifact "AI
   Engineering Operating System" is: a Mission Charter (`CLAUDE.md`), an
   Engineering Constitution (`docs/OPERATING_RULES.md` +
   `docs/CODING_CONVENTIONS.md`), Interface Contracts (`contracts/`),
   verification gates (`tools/validate`, `trust_gate.py`, `deferral_scan.py`,
   the eval harness), a Decision Log (`docs/memory/decisions/`), an append-only
   Record (`docs/RECORD.md`), and model-tier routing (`docs/MODEL_ROUTING.md`,
   `tools/model_router.py`). It reviewed a document without the codebase and
   prescribed the codebase.
2. **The remedy is larger than the disease** — trading a live, publishing
   engine for a months-long meta-project, on a critique that produced no
   defects.
3. **Zero findings.** Same blocker as everyone else; three others returned
   verifiable claims. **Grading is not review.** The ratings (2/10 token
   efficiency, 9.5/10 vision) carry no measurement and no method.
4. **Wrong on mechanism where it is testable.** "A model doesn't remember
   because something is repeated" is asserted as fact and used to justify
   deleting repetition. Load-bearing invariants that must survive compaction are
   exactly what is worth restating.

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

**The cheaper path to the same benefit.** The ceremony cost R1 is trying to
escape is concentrated in one fact: `worker/ai_models.py` is bound into
`HARNESS_MANIFEST`, so touching the schema takes extraction offline pending a
founder-attended exam. You do not need a new worker to escape that. You need
either (a) the schema to stop being manifest-bound, or (b) **one batched exam
that covers the whole schema extension at once** instead of several. That is a
scalpel where R1 is an amputation, and it is what makes Fix 01's Phase 1 /
Phase 2 split correct — which is exactly what Gemini, Grok, and Perplexity's own
R6.4 all independently concluded.

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
