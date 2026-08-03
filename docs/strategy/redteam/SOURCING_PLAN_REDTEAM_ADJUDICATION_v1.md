# Red-Team Adjudication — Sourcing Scale Plan v1 (2026-08-03)

**Reviewers:** ChatGPT (Architect+Skeptic+Adversary in one session, incl. §3d
extension) · ChatGPT deep Adversary run (22 findings) · Gemini (Architect +
§3d deep dive). Grok was not used. **Adjudicator:** the authoring session,
verifying every finding against the actual repo (code cited), the committed
research (docs/strategy/research/), and the plan text.

**Reviewer verdicts:** PROCEED WITH FIXES (ChatGPT 3-role) · HALT AND
REDESIGN (ChatGPT deep Adversary) · PROCEED WITH FIXES (Gemini).

**ADJUDICATED VERDICT: PROCEED WITH FIXES** — the HALT verdict's
substance is ADOPTED as sequencing amendments (probation, shadow, canary,
reversibility) but its central premise is partially refuted: P1 does not
publish "before the safety architecture exists." P1 publishes through the
EXISTING live gate (2-source corroboration, curated-source anchor classes,
fail-closed, double gate re-assertion in worker/autopromote.py +
worker/promote.py), behind a founder flag, from the 180 curated sources
only. The genuine exposure the Adversary found is P3 (mass auto-enrollment)
landing BEFORE P4's source-trust machinery — fixed below by the probation
class and by moving sentinels/syndication-caps into P3.

---

## 1. CONFIRMED CRITICAL — fixes adopted (blocking where marked)

**C1. `claimed_upload` solo-promote is a corroboration bypass (ALL THREE —
the strongest convergent finding).** Verified in code: `worker/gating.py`
ANCHOR_CLASSES includes `claimed_upload`; one anchor source promotes solo.
Today this is dormant (no claim flow exists, flag OFF) but it is a real
design hole for §3d. ADOPTED (BLOCKING for any claim flow):
- **Anchor-tier stratification**: Tier 0 institutional (licensed APIs) —
  solo-promote; Tier 1 verified-claimed (DNS TXT / domain-email proof) —
  solo-promote ONLY within verified identity scope + 24h background
  corroboration cross-check; Tier 2 unverified-claimed — strong fusion
  prior, NEVER solo-promote.
- **Claim defense**: DNS/domain verification before Tier 1; claim-divergence
  alert (>40% from crawled history → human review); 48h challenge window;
  claim rate-limiting; 72h shadow window for a new claimant's first events.
- **Honest language fix**: stop saying "gate custody unchanged" for claimed
  entities — the honest statement is "verified claimed entities earn
  expedited publication subject to 24h background corroboration."

**C2. Phase-order exposure at P3 (deep Adversary E-1; Architect A-IV;
Gemini F5).** ADOPTED as amendments, not halt:
- **Source probation class**: every auto-enrolled source enters PROBATION —
  cannot be an anchor, corroboration weight capped (~0.5), promoted to
  TRUSTED only after 2 temporally-separated successful extractions + no
  domain-mismatch + family classification. (DISCOVERED→PROBATION→TRUSTED→
  QUARANTINED lifecycle.)
- **Sentinels + provenance-family caps move INTO P3** (were P4): per-source
  yield/parse anomaly quarantine and syndication-family weight caps ship
  with enrollment, not after it.
- **Canary + reversibility before flag flip**: DRY_RUN report mode for
  autopromote (evaluate + founder-readable report, no writes); first-flip
  canary limited to curated anchor-class sources; provenance-based bulk
  retract (unpublish by source/template/policy version) built before P3.

**C3. Promotion atomicity (deep Adversary I-6) — PARTIALLY CONFIRMED.**
Code already double-asserts (autopromote re-runs gate fresh; promote.py
re-asserts inside its transaction), so the window is small but non-zero.
ADOPTED: status CAS (`WHERE status='ready_to_promote'`) + idempotency
guard + row lock in the promoter. Small hardening; evaluator-gated.

**C4. DB-level enforcement of "AI never publishes" (ChatGPT A-III-3).**
CONFIRMED: today the invariant is application-structural (tested) but not
DB-enforced; the human ops path writes directly. ADOPTED: Postgres trigger
requiring a matching gate-audit row for any promotion write. 1 day.

**C5. Extraction-model drift has no sentinel (ChatGPT A-I-3).** CONFIRMED:
the golden exam is point-in-time; hosted-model drift would be invisible.
ADOPTED (founder spend ask, small): weekly shadow mini-exam (golden subset)
with alert + auto-pause of extraction on pass-rate drop. Uses existing exam
harness; never re-certifies — detects drift only.

**C6. Cancellation/lifecycle authority (deep Adversary C-4).** CONFIRMED
design gap in the fusion spec: a venue's cancellation must beat N stale
syndicated "scheduled" copies. ADOPTED into P4 design: field-level
authority matrix + explicit lifecycle states (SCHEDULED/CANCELLED/
POSTPONED/RESCHEDULED/MOVED/SOLD_OUT), existence-confidence separated from
attribute-confidence. (Status fields partially exist in licensed imports.)

**C7. Capture-recapture as ground truth (Skeptic S-II-1; deep Adversary
L-5).** CONFIRMED methodological error: source families are syndication-
correlated → Lincoln-Petersen independence fails. ADOPTED: hand-census is
PRIMARY ground truth; capture-recapture demoted to sensitivity analysis
with explicit dependency modeling; Coverage reported as intervals, not
points; targets restated as lower-confidence bounds.

## 2. CONFIRMED HIGH — fixes adopted

**H1. Byte-hash defeated by dynamic pages (ALL THREE).** ADOPTED: semantic
hashing — normalize DOM (strip script/style/volatile), hash the extracted
event-fragment set; byte-hash stays as pre-filter. Plus: 2-week empirical
unchanged-rate measurement BEFORE P2 efficiency claims are treated as real.

**H2. Cost numbers are targets, not estimates (Skeptic S-II-2; deep
Adversary L-3/L-4).** ADOPTED: §3b rows relabeled TARGET until the ledger
measures them; budget against P90 not mean; add missing ledger categories
(fixed platform, human review hours at shadow rate, verification infra,
incident response); ±2× uncertainty band on all multi-metro rows.
Scheduler-funnel metrics defined (scheduled→triggered→started→completed→
successful) — also fixes the 15%-vs-7% wording inconsistency the deep
Adversary caught (7% slot-delivery is the correct figure; "15% delivery"
in the red-team package Section A was an editorial error, corrected).

**H3. §3d economics at 0% adoption (ALL THREE).** ADOPTED: all P1-P5
financial models assume 0% adoption; §3d is a post-scale lever. The carrot
is re-based on TANGIBLE UTILITY that works at zero consumer scale: free
embeddable events widget + free ICS feed + "did we get this right?"
concierge-email correction loop + venue analytics. Adoption-probability is
modeled inversely to extraction cost (Gemini F14 — the expensive long tail
adopts last).

**H4. Template strategy contradiction (deep Adversary I-2).** CONFIRMED
(plan said per-source in §2.2, per-platform in §3c). ADOPTED: two-layer —
versioned platform-base template + per-source overlay; activation only
after validation against multiple stored pages (schema, date-plausibility,
count bounds, certified-extractor sample comparison); versioned rollback.

**H5. Escalation queue at 5k sources (Skeptic S-I-3) — PARTIALLY REFUTED,
then adopted.** Refutation: ESCALATE → needs_review is fail-closed; nothing
publishes from the queue, so the TRUST invariant cannot bend via queue
pressure. Confirmed as a COVERAGE/ops bottleneck: ADOPTED — weekly human
review budget set first; enrollment rate throttled by it; auto-resolution
rules for low-risk classes; queue-aging telemetry.

**H6. Multi-protocol sources (ChatGPT A-I-1).** ADOPTED: probe stores a
RANKED pathway list per source (not one kind); fallback semantics defined.
Gemini's Wasm plugin sandbox REJECTED as over-engineering at this stage.

**H7. Observability floor (ChatGPT A-III-2; Gemini F8/F9/F10) — PARTIALLY
REFUTED, then adopted.** Refutation: dead-man alarms DO exist on both crons
and DID catch R-023 (recorded). Confirmed gaps ADOPTED into P1: per-source
yield-velocity alerts (template drift detection), funnel-drop counts
between stages, snapshot-job failure alert, seasonally-aware quarantine
thresholds (SXSW spike ≠ anomaly) with quarantine-to-review never silent-drop.

**H8. Claims-fusion shadow migration (ChatGPT A-II-1; Gemini F5).**
ADOPTED: P4 split into P4a (claims table + fusion in SHADOW alongside the
live gate; divergence review; cutover only at ≥95% agreement) and P4b
(resolver, sentinels-remainder, recurrence). Legacy events get a
`legacy_gate_pass` claim row — confidence semantics stay consistent.

**H9. Yield transportability (deep Adversary L-2; Skeptic S-III-3).**
ADOPTED: segment-specific zero-inflated yield distributions measured on the
first 500 enrolled sources; coverage-vs-source-count curve fitted before
M2/M3 targets are ratified; P3's gate restated from "≥2,500 sources" to
"measured incremental verified-event yield + audited coverage."

**H10. Scheduler (ChatGPT A-IV-2 vs deep Adversary E-5 vs Gemini F2) —
3-OPTION ADJUDICATION.**
- A: defer metronome to post-P2 (plan as written) — leaves P1/P2 metrics
  measured on a 7%-delivery system.
- B: minimal metronome in P1 at PARTIAL cadence (hourly, not 20-min), no
  catch-up, existing concurrency group prevents overlap.
- C: durable job-queue architecture now (deep Adversary) — correct at
  national scale, over-built today.
**CHOSEN: B**, with C's key protections adopted cheaply (no-catch-up rule,
per-host politeness already host-sharded, spend circuit breaker = existing
budget ceiling) and C scheduled as a P5-entry criterion. Rationale: P2
efficiency must be measured at representative cadence; hourly×24 ≈ 24
runs/day caps naive spend at ~$100/day worst case pre-optimization, inside
tolerance for a 1-2 week measurement window.

## 3. REFUTED or OUT OF SCOPE (with evidence)

**R1. "P1 publishes unvalidated" (deep Adversary headline).** REFUTED as
stated: publishing goes through the live 3-way gate + double re-assertion +
founder flag + (now) canary/DRY_RUN; sources at P1 are the 180 curated.
The valid core (P3 exposure) is adopted in C2.
**R2. NoSQL/DynamoDB data-plane split (Gemini F6).** REFUTED on volume
math: reviewer assumed ~50 events/source/day; measured reality is ~35
events/venue/YEAR (Bandsintown constant, our calibration). National-scale
claims volume ≈ <1M rows/day worst case — Postgres with (market, week)
partitioning + Parquet cold archive handles this. Partitioning-before-P3
ADOPTED; NoSQL migration rejected.
**R3. Wasm/Lua adapter sandbox (Gemini F1).** Rejected: H6's ranked-pathway
fix + the existing 10-kind adapter registry covers the seam at ~1/20 the
build cost. Revisit only if P5 pilot shows >10% adapter-exception rate
(the Skeptic's S-I-1 pilot measure, adopted).
**R4. "Trust invariants can't survive 5k sources" (Skeptic S-I-3, trust
half).** Refuted: fail-closed means junk sources cost coverage and money,
never trust. The ops half is adopted (H5).
**R5. Contributor-first inversion (deep Adversary C-1) vs cold-start
findings (everyone else).** The reviews contradict each other; adjudicated:
crawl-first for coverage (adoption carrot demonstrably needs scale), with
H3's free-utility adoption seeds shipped early. §3d stays post-scale.
**R6. "Independent evaluator can't be the release gate" (deep Adversary
E-2).** Partially refuted: the evaluator is ONE of several gates (full
deterministic test suite ~2,000 tests, trust_gate invariant checks, arming
smoke runs on real infrastructure, golden-exam certification). Adopted in
spirit: replay fixtures + fault-injection tests grow over P2-P4.
**R7. Gemini's "user decision success" co-north-star (C-2).** Valid PRODUCT
metric, out of sourcing-engine scope; forwarded to the UI/UX lane and the
founder as a KPI-stack addition candidate.

## 4. What changes in the plan (v1.1 amendments, committed with this file)

1. Phase table restructured: P1 gains DRY_RUN+canary+observability floor+
   minimal metronome; P3 gains probation class+sentinels+family caps+
   review-budget throttle+partitioning; P4 split P4a/P4b with shadow gate;
   P5 entry requires durable-scheduler decision + pilot-metro exception-rate
   report.
2. §3d rewritten: anchor tiers, claim defense, 0%-adoption economics,
   utility carrot. Blocking precondition: identity verification built first.
3. §3b relabeled TARGETS; ledger categories added; P90 budgeting; funnel
   metrics defined; 7% figure canonical.
4. §5 ground truth: hand-census primary; capture-recapture → sensitivity;
   intervals not points.
5. §2.2 template layer: two-layer model + validation harness + rollback.
6. New: model-drift shadow exam (weekly, founder ask); DB-level promotion
   trigger; semantic hashing; unchanged-rate measurement precedes P2 claims.

## 5. Residual risks accepted (recorded, not hidden)

Hidden syndication below detection; founder key-person dependency (decision
queue + delegation design mitigate, cannot remove); long-tail source
maintenance cost until §3d matures; KPI gaming pressure at partner/investor
surfaces (honest-count canon + series-collapsed twin are the defense);
model-provider deprecation of the certified tier (drift exam detects;
re-certification path exists but costs founder time).
