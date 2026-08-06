# Fix 01 — Structured event data is found and destroyed

Engineering record for a single defect, in the discipline the founder
specified: problem → severity → cascade → measured effort → plan → testing →
go/no-go/delay → proof.

**Status: GO — ruled by the founder 2026-08-06, unconditionally and not
contingent on the census (§6).** The standard is not "clears a threshold"; it is
*world class, fixed, and working perfectly*: every field the source states is
extracted, nothing is invented, cancelled and postponed are never shown as live.

---

## 1. The problem

`worker/segment.py:252` `_jsonld_event_text()` locates schema.org `Event`
JSON-LD — the typed object in which a site states its own facts — and reduces
it to a pipe-joined **string**:

```python
for key in ("name", "startDate", "start_date"):
    ...
text = " | ".join(parts)
```

Re-derived from the tree by `lab/verify_claims.py` C7, the only keys this
function reads are:

```
address · addressLocality · event · location · name · startDate · start_date
· streetAddress · url
```

It never reads `offers` (price), `description`, `endDate`, `performer`,
`image`, `eventStatus`, `doorTime`, `organizer`, `location.geo`,
`typicalAgeRange`.

The resulting string is then handed to a language model (`ai_extract.py:224`)
to extract, from prose, values that arrived as typed fields.

## 2. Severity: CRITICAL

Three independent defects in one function.

**2a. Correctness.** An ISO timestamp `2026-08-06T20:00:00-05:00` becomes a
substring inside `"MASEGO | 2026-08-06T20:00:00-05:00 | ACL Live | ..."`, and a
model must find it again. Every failure mode of free-text date extraction —
the six defect variants PR #189 spent eight review rounds on — is *manufactured
here*, on pages that had already stated the answer unambiguously.

**2b. Cost.** We pay per model call for data that was free and exact. One call
per block, capped at 50 per page (`ai_extract.py`, `EXTRACT_MAX_EVENTS_PER_PAGE`).

**2c. Coverage.** Price, description, end time, performer, image and
cancellation status are discarded *at this line*, before anything downstream
could store them. This is a second, independent cause of the "we cannot fill
the card" problem — separate from the schema being too narrow.

## 3. The cascade

```
segment.py:252 drops offers/description/eventStatus/endDate/image/performer
      │
      ├─► candidate rows carry no price, no description, no image
      │        └─► promote writes NULLs into event.price_min/price_max
      │                 (columns that have existed since migration 0010)
      │                      └─► the card renders a listing with no price and
      │                          no image beside Ticketmaster rows that have both
      │                               └─► the venues the product exists to serve
      │                                   look like stubs next to the ticketing giants
      │
      ├─► no is_free / price ⇒ the feed's `price` and `free` filters cannot
      │   apply to any discovered event ⇒ 2 of 6 filters dead for our own supply
      │
      ├─► no eventStatus ⇒ a CANCELLED show is published as live.
      │        This is worse than absence: it sends someone to a locked door.
      │
      └─► date arrives as prose ⇒ the model must re-derive it ⇒ failures ⇒
          the entire date_callback machinery of PR #189 exists to repair
          ambiguity that this line created ⇒ 8 review rounds, 21 re-arm cycles,
          6 variants of one defect class, still unmerged
```

**Reversal test:** if this line read the typed fields, most of #189 would have
no job, price and description would arrive for free on every site that
publishes them, and cancelled events would be markable.

## 4. Measured effort — read from the tree, not estimated

### 4a. Blast radius

| Fact | Value | How derived |
|---|---|---|
| Production callers of `segment_events` | **1** — `ai_extract.py:224` | `grep -rn` across the tree |
| Current contract | `segment_events(...) -> List[str]` | `worker/segment.py:362` |
| Tests calling `segment_events` | **11** in `tests/test_segment.py` | `grep -c "def test_"` |
| Tests monkeypatching it | **2** in `test_surface_regression_exam.py`, **1** in `test_ai_extract_integration.py` (9 tests in that file) | grep |
| `worker/segment.py` in the arming runtime closure | **YES** (closure = 27 files) | `tools.arming_runtime.runtime_files()` |
| `worker/segment.py` in `HARNESS_MANIFEST` | **NO** | `ai.golden_exam.HARNESS_MANIFEST` |
| `worker/ai_models.py` in `HARNESS_MANIFEST` | **YES** | same |

### 4b. The two findings that change the plan

**Finding 1 — this fix is NOT manifest-bound.** `segment.py` is absent from
`HARNESS_MANIFEST`, so the golden-exam refusal it triggers is the *eligible*
class: compensated by base-owned execution plus the mandatory non-Claude
review, with **extraction staying ON**.

**Finding 2 — the schema fix IS manifest-bound.** `worker/ai_models.py` is in
the manifest. Adding `price`/`description` there means the same PR must set
`EXTRACTION_THRESHOLD_RATIFIED = False` — **extraction goes OFF at merge** and
only returns via the standing three-step: founder's attended exam on the new
harness → authenticated record PR → head-bound flag-flip PR.

I previously told the founder both fixes were "hours of work each." That was
wrong on process cost, and the manifest is where the difference lives. **The
work splits into two phases with very different costs, and the cheap one
delivers the date fix on its own.**

### 4c. Effort, by phase

**Phase 1 — structured extraction for fields the schema already holds.**
No `ai_models.py` change, so extraction stays ON.

| Item | Measure |
|---|---|
| New code | one additive function in `segment.py` (~50 lines) returning typed records, plus ~20 lines in `ai_extract.py` to prefer them |
| Contract change | **none** — `segment_events` keeps `List[str]`; the new path is a separate function |
| Existing tests requiring edits | **0** (additive design; the 11 + 9 + 2 above keep passing unchanged) |
| New tests | ~8 (typed read, missing fields, malformed JSON-LD, multi-event page, price present but unstorable, model-path fallback, no-JSON-LD fallback, cost assertion) |
| Arming re-bind | **1** ingest dispatch + evidence commit (segment.py is in the closure) |
| Golden exam | red by design, eligible class, extraction stays ON |
| Adversarial review | 1+ rounds; historical mean on this repo is 6.1 rounds and falling (`kaizen_trends`), so budget 2–3 |
| Wall-clock | dominated by review rounds and re-arm, not by typing |

**Phase 2 — extend the schema for price/description/image/status.**

| Item | Measure |
|---|---|
| New code | ~10 fields across `ai_models.py`, `candidate_store.py` INSERT, `promote.py` INSERT, one migration |
| Process cost | **extraction OFF at merge**; return requires a founder attended exam, an authenticated record PR, and a flag-flip PR |
| Founder involvement | **required** — this is not an agent decision |

## 5. The plan

### Phase 1 design — additive, no contract break

1. `structured_events(html) -> list[dict]` in `segment.py`: parse JSON-LD/
   microdata and return **typed records** with every field the source states,
   including the ones currently discarded, each carrying its JSON path as
   provenance.
2. `ai_extract`: if a page yields structured records, build candidates from
   them **directly, with no model call**, mapping only into fields the current
   schema can hold. Fields the schema cannot yet store are preserved in the
   candidate's `extracted` jsonb under `_provenance.structured` — captured now,
   storable after Phase 2, never silently dropped.
3. Pages with no structured data fall through to today's path, byte-identical.
4. `segment_events` is untouched.

### Testing

| Test | Asserts |
|---|---|
| typed read | a JSON-LD event yields the exact ISO `startDate`, not a re-parse |
| field completeness | `offers.price`, `description`, `endDate`, `performer`, `image`, `eventStatus` all captured |
| no fabrication | a field absent from the source is absent from the record — never inferred |
| malformed input | broken JSON-LD degrades to the text path, does not raise |
| fallback identity | a page with no JSON-LD produces byte-identical output to today |
| cost | a structured page makes **zero** model calls (assert on a mock provider) |
| cancellation | `eventStatus: EventCancelled` is preserved and distinguishable |
| golden set | the existing extraction golden set still passes |

Plus the standing gates: `tools/validate` (20 checks, 1,953 tests) and the
non-Claude adversarial panel.

### Proof-before-adopt (runs in `lab/`, no production change)

Against the 16 agreed proving sites, from CI:
- how many publish JSON-LD;
- for those, field-by-field precision/recall against hand-built ground truth;
- model calls and dollars, structured path vs today's path.

## 6. Go / No-Go / Delay — RULED: **GO**, unconditionally

**Founder ruling, 2026-08-06, verbatim:**

> O don't want sharpens - I want world class fixed and working perfectly.

**The original gate asked the wrong question, and that was an engineering error,
not a wording one.** It read:

> GO if the census shows ≥30% of sites publish JSON-LD; NO-GO under 10%.

That makes fixing the defect conditional on how common the defect's payoff is.
But `_jsonld_event_text` **already parses the complete schema.org object** and
then deletes `offers`, `description`, `endDate`, `performer`, `image`,
`eventStatus`, `doorTime`, `organizer` and `location.geo` before returning. Data
that has already been fetched and already been parsed is thrown away. That is
wrong at 30% coverage and equally wrong at 5% — a low census would not make it
correct to keep destroying parsed fields; it would only mean fewer sites are
rescued by this one fix.

The census therefore measures **how much of the corpus tier 0 finishes**, which
is a sequencing input for tiers 2–5. It never was a build-or-don't-build input,
and treating it as one gave a real defect a way to survive a number.

**The gates that remain are quality gates on the finished work, not permission
to start.** None may be relaxed by any census result:

| Gate | Criterion | Fails how |
|---|---|---|
| **Faithfulness** | Zero fabricated values. A field is emitted only if the source states it | One fabrication ends the phase — see §6 abort below |
| **Required fields** | ≥98% correct across the proving set, on the Tier-B-required list (D4) | Below 98% is not done |
| **Cancelled / postponed** | 100% correct, and never rendered as live (D4) | Any miss is a stop |
| **No regression** | Every field extraction gets today, it still gets | Any loss is a stop |

**Decision point B — before Phase 2 (founder-only).** Extending the schema
takes extraction OFFLINE until an attended exam re-certifies. That is a founder
decision about downtime, not an engineering call. Present: expected offline
window, what stops during it, and what is gained.

**Abort at any point** if a structured read produces a value the source does
not state. One fabrication ends the phase.

## 7. Proof required on completion — indisputable, not asserted

On GO and completion, all of the following, each independently re-derivable:

1. **Committed page snapshots** for every site scored, so any third party can
   re-run the scoring without network access.
2. **Field-level precision/recall** against hand-built truth, computed by a
   scorer, with every miss and wrong value printed.
3. **A zero-model-call assertion** on a structured page: the spend ledger shows
   `$0.00` for pages that used to cost a call per block.
4. **Before/after on the same page**: today's pipe-joined string beside the
   typed record, showing which fields were being lost.
5. **A live read-back**: an event ingested through the structured path, read
   from the public feed API, showing a date and price the old path could not
   produce.
6. **`lab/verify_claims.py` extended** with the new claims, so this document's
   numbers cannot rot.
7. **All 20 validate checks green**, and a non-Claude panel APPROVE.

Proof 5 is the one that matters. Everything before it can be true while the
number of events a visitor can see stays at 1.
