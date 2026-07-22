# ONE LIVE — Autonomous AI Attribution System (v1)

**Status:** PROPOSAL (founder-directed 2026-07-22: "at some point we need to be
able 'use AI' to do this. Research and develop a world class autonomous AI
attribution system with world class checks and balances that could be used with
sources, identifiable and readable and somehow, discreetly in terms of mindshare
of a user, noted, and accessible to and acted upon by our current or a revised /
enhanced … Kaizen model."). Session Contract #21.

**Invariant statement, first and unambiguous:** nothing in this document changes
prime directive 1. "AI never publishes" remains physics today and until the
founder ratifies a specific revised invariant text through the founder-crucial
path. This document defines what would have to be TRUE — mechanically, not as
policy prose — before any AI-assisted publishing surface could be ratified, and
builds the attribution machinery that is valuable even if that day never comes
(today's gated pipeline already needs world-class provenance).

**Evidence quality:** the standards research below was gathered 2026-07-22 by a
web fan-out whose direct page fetches were ALL blocked by this sandbox's egress
proxy — every external claim is a SEARCH-SNIPPET (search-index read), none
primary-verified. Load-bearing items (exact EU AI Act Article 50 text, C2PA
version status) carry re-verification triggers in docs/RECORD.md (R-023).
Repo-internal claims are file-cited and verifiable here.

---

## 1. Plain-language framing

When AI helps make something a user reads, three questions must have excellent
answers, always, automatically:

1. **Where did this come from?** (sources — identifiable, readable, linked)
2. **Who and what made it?** (which model, which prompt version, which human
   approved it — a complete, machine-readable record)
3. **How is the user told?** (discreetly — a quiet mark that costs almost no
   attention, but opens to the full story on demand)

And a fourth, which is the founder's distinctive addition: **the records must
feed the improvement loop** — attribution isn't a label, it's an instrument the
Kaizen system reads and acts on.

## 2. What world-class looks like (external research, all SEARCH-SNIPPET)

1. **A shared vocabulary for "AI-made" vs "AI-assisted" exists and is winning:**
   the IPTC Digital Source Type terms — `trainedAlgorithmicMedia` (fully
   AI-generated) and `compositeWithTrainedAlgorithmicMedia` (AI-assisted /
   partly AI) — are the values C2PA manifests, Google's and Meta's labels all
   consume. Using this vocabulary makes our records interoperable for free.
2. **C2PA / Content Credentials** (spec 2.3, Jan 2026; ISO-track) is the
   provenance standard with real adoption (OpenAI, Google, TikTok, LinkedIn,
   camera makers; reported 6,000+ consortium members — snippet, unverified).
   Notable: as of 2.3 it covers TEXT, via invisible Unicode
   variation-selector embedding or comment blocks. **Deliberate divergence for
   us:** invisible-codepoint embedding is exactly the character class our
   planned unicode-safety lint bans (Trojan-Source surface), and embedded
   manifests are stripped by re-encoding anyway (their own known limitation).
   We therefore attribute via **sidecar records at stable URLs**, not invisible
   in-band bytes — same record content, honest transport.
3. **EU AI Act Article 50** transparency obligations become applicable
   **2 August 2026** (snippet-confirmed repeatedly; re-verify exact text —
   R-023): machine-readable marking of AI-generated content including text, and
   a deployer disclosure duty for AI-generated public-interest text **with a
   human-editorial-review carve-out**. Our human gate likely qualifies for the
   carve-out — and the world-class move is to disclose anyway, exceeding the
   floor. (Our market analysis already flagged Art. 50 as turning provenance
   from cost into brand — combinatorial play #4.)
4. **Text watermarking is not viable for short copy** (SynthID-Text works but
   weakens sharply on short/edited text; OpenAI withheld theirs; no
   cross-vendor detection). For descriptor-length text, records and disclosure
   — not watermarks — are the mechanism. This closes a design dead-end early.
5. **The transparency dilemma (the hardest finding):** peer-reviewed work
   (2025–2026: Toff & Simon IJPP; FAccT 2026 "Full Disclosure, Less Trust?")
   consistently finds AI labels REDUCE perceived trust/accuracy even when
   accuracy is unchanged — and *more detailed* disclosure reduces it further —
   while ~61% of consumers simultaneously say publishers should always
   disclose. Practice answer, converged on by the industry: **quiet, neutral,
   progressive disclosure** — a small persistent mark with neutral wording
   ("AI info", not "Made with AI"; Meta renamed theirs after mislabel
   complaints), full "nutrition label" one tap away. This is, almost exactly,
   the trust-display pattern our design brief already ratified (no badges;
   quiet icon → dismissible sheet). Known failure mode to design against:
   label habituation ("digital background noise").
6. **No single standard exists for agentic attribution records** (model +
   prompt version + human approver + source lineage per output). Best practice
   is composed: **W3C PROV-O** (the provenance graph: Entities, Activities,
   Agents), model/system cards (the model artifact), AIBOM (dependency
   inventory), IPTC term (the AI-involvement claim), NIST AI RMF / AI 600-1
   (governance framing). We compose the same way — and our composition is ahead
   of most of the market because the pipeline was built auditable from birth.

## 3. What OneLive already has (the system is half-built)

- **Per-item provenance at extraction:** `extracted._provenance` carries model
  id, prompt_version, `prompt_sha256` (content-hash drift audit, PR #25), and
  even refused-claim records (`unstored_datetime_claims`, R-021) — evidence of
  what the AI did NOT assert. `worker/ai_extract.py`.
- **Stage lineage:** Sources → Raw Fetch → Extract → Candidate → Evidence →
  Gate → Promote is independently auditable by design (charter architecture);
  candidate rows retain evidence links and gate outcomes; replay artifacts
  preserve run-level provenance.
- **Certified competence:** the golden-exam certification record binds model,
  prompt, harness hash, and thresholds (`ai/golden/CERTIFIED_HARNESS.json`) —
  attribution can cite the exam under which an extraction ran.
- **Ratified display pattern:** Certainty Display Stack axis 3 (provenance
  class) + the brief's quiet-marker/dismissible-sheet rules; the Emotion Glyph
  spec already carries `{model, prompt_version}` provenance with AI-disclosure
  treatment pending ratification (G-EG).
- **Descriptor Foundry mandate:** all AI-generated descriptors already require
  provenance + golden-set regression + independent judge (charter §Stitch-4).
- **The loop:** Kaizen measures M1–M8, ledger discipline, escapes-are-absolute.

What's missing is the formalization: one record schema, one public resolution
surface, one disclosure mark, and a measure that makes attribution enforceable.

## 4. The proposed system — three layers

### Layer 1 — the Attribution Record (machine-readable, per published item)

A PROV-O-shaped JSON record, created at gate-pass time, append-only,
content-bound:

- **Entities:** the published text/fields (content-hashed), each source
  document (id, URL, `retrieved_at`, raw-fetch ref), intermediate candidates.
- **Activities:** extraction / synthesis / review steps, each with model id,
  `prompt_sha256`, exam-certification ref, timestamps.
- **Agents:** the model (as software agent), the human approver (as
  responsible agent — the gate decision id), and for autonomous classes (if
  ever ratified) the ratification decision record it operated under.
- **Classification:** the IPTC term — `compositeWithTrainedAlgorithmicMedia`
  for AI-assisted human-approved content; `trainedAlgorithmicMedia` reserved
  for any future ratified autonomous class.
- **Resolution:** every published item gets a stable public provenance URL
  (`/provenance/{event_id}` style) rendering the record readably: sources
  named and linked, "how this was made" in plain language, full JSON beneath.
  Sidecar-by-URL, not invisible embedding (§2.2). Records are immutable;
  corrections append (the promise-ledger storage rule, reused).

### Layer 2 — the disclosure surface (discreet in mindshare)

Reuse the ratified pattern outright: one small, neutral, consistent mark on
AI-assisted content (wording class: "AI-assisted · reviewed", never a badge,
never a verdict), placed once per card/sheet, ≥44px touch target, opening the
dismissible sheet: two-sentence plain-language explanation, the named sources
with links, the human-review statement, and the "full record" link (Layer 1
URL). Design constraints from evidence: neutral wording (§2.5), progressive
disclosure, ONE consistent mark to resist habituation, and the disclosure
never crowds the content it describes. Facts derived from sources without
generative AI (the normal extraction path) disclose provenance through the
existing axis-3 surface — the AI mark is for AI-*written* surfaces
(descriptors, glyph copy), which is what users mean by "AI made this."

### Layer 3 — the loop (Kaizen reads and acts on the records)

1. **Mechanical completeness gate:** a blocking check (deferral_scan-class) —
   no AI-origin string ships without a bound, resolvable attribution record;
   fail closed. Attribution without enforcement is decoration.
2. **Drift audits:** periodic sampled re-verification that records match
   reality — `prompt_sha256` vs live prompt, model id vs router config, source
   URLs still resolve, record content-hash matches published content. Findings
   are ledger rows.
3. **Proposed measure M9 — attribution integrity** (KAIZEN.md amendment,
   founder ratifies): coverage must be 100%; **escape definition:** any
   user-visible AI-touched content lacking a resolvable record, or carrying a
   wrong one — an M3-class escape (zero, absolute). Defect classes:
   `missing-record`, `wrong-source`, `stale-record`, `unreadable-disclosure`.
   Hat custody per the registry: White verifies mechanically (audits), Black
   attacks records at review, escapes land in the existing ledger.

## 5. The ratification path ("use AI" without breaking what makes us trustworthy)

Staged, each stage founder-crucial, each with the compensating-control
discipline the charter already uses (enumerated closed classes, mechanical
classifiers, no agent judgment in the gate):

- **Stage 0 (today):** all AI output human-gated. The attribution system ships
  here first — it makes the CURRENT pipeline world-class and is required
  regardless of what follows.
- **Stage A — attributed assist (nearest ask):** AI-written, human-approved
  surfaces (Descriptor Foundry output is the existing shape) publish WITH the
  full three-layer system. No invariant change: a human still publishes. Ask:
  name Descriptor Foundry as the first attributed surface.
- **Stage B — bounded autonomous classes (future, not asked now):** IF ever
  wanted, autonomous publishing exists only as founder-ratified, enumerated,
  closed classes (e.g., freshness-timestamp updates), each with: exam-proven
  thresholds, full Layer-1 records marked `trainedAlgorithmicMedia`, real-time
  M9 auditing, a kill switch, and a mechanical classifier deciding class
  membership — the same architecture as the extraction-exam exception. The
  invariant text itself would be revised by the founder to name exactly this;
  until then it stands unmodified.
- **Never-list (unchanged by any stage):** trust-state assignment, dispute
  handling, ranking, and anything pay-to-rank-adjacent stay outside autonomous
  scope permanently.

## 6. Tradeoffs, honestly

- **Disclosure costs trust on labeled items** (the transparency dilemma is
  real, replicated, and gets worse with detail). We pay it because: users
  demand disclosure; Art. 50 is days from applicability; and a trust-first
  product caught NOT disclosing loses more than the label ever costs. Neutral
  wording and progressive disclosure minimize (not eliminate) the penalty.
- **Sidecar-vs-embedded:** our records don't travel inside copied text the way
  C2PA embedding would. Accepted: embedding is strippable anyway, collides
  with our unicode-safety posture, and our content lives primarily on our own
  surfaces where the URL resolves.
- **Cost:** low. Records ride existing provenance plumbing; the UI reuses the
  ratified sheet; the gates are small scripts. The real cost is discipline —
  which is the point of M9.

## 6b. Cross-venture applicability — the Promise Ledger (founder-directed addendum, 2026-07-22: "This work should also be useful re: press release aggregator")

The ledger is arguably this system's FIRST-best consumer, not its second:

1. **Its failure mode demands it.** The venture's stated defamation-adjacent
   risk — a wrong "broken promise" stamp — is precisely an attribution
   failure. Invariant 2 (verdicts graded and evidence-linked, never binary)
   already requires per-claim provenance; the Layer-1 record is its formal
   shape: filed document (accession-numbered Entity) → extraction Activity
   (model, prompt_sha256, golden-set certification) → verdict + reviewing
   Agent. One record schema serves both products.
2. **It IS the whitespace.** Market-analysis whitespace row 5
   ("text-disclosure provenance/verification — 'matches the filed 8-K,
   verified issuer, unaltered' as a product property") and combinatorial play
   #4 (verification × AI-slop crisis, Art. 50 turning compliance into brand)
   describe exactly Layers 1–2 sold as a feature. The attribution engine
   built for OneLive's gate is the mechanism behind that product property —
   build once, deploy twice.
3. **Art. 50 lands harder there.** The ledger publishes AI-derived text about
   public companies — squarely the "public interest" deployer-disclosure
   territory (human-review carve-out likely applies via the gate; disclose
   anyway, per §2.3). Its agent-facing MCP feed should carry the Layer-1
   record inline: agent consumers are the audience that READS machine
   attribution, making the record itself a differentiator (Daloopa-class
   buyers pay for auditability).
4. **M9 transfers unchanged** — attribution integrity coverage/escape
   semantics apply to claims exactly as to events.

## 7. Founder asks (consolidated — nothing proceeds without these)

1. Ratify the three-layer design direction (§4) as the attribution canon.
2. Ratify M9 (attribution integrity) as a KAIZEN.md amendment.
3. Name Descriptor Foundry as the first attributed surface (Stage A scope).
4. Confirm Stage B remains unasked/unbuilt until you raise it (this doc's
   default).

## 8. Sources

External: the 2026-07-22 attribution-standards research fan-out (C2PA/Content
Credentials spec + adoption; EU AI Act Art. 50 Commission FAQ/guidelines
trackers; IPTC Digital Source Type; AP/Reuters/Guardian policies; Trust
Project; Toff & Simon IJPP 2025; FAccT 2026; arXiv 2506.16202; SynthID-Text
Nature 2024 + robustness critiques; NIST AI 600-1; CycloneDX ML-BOM; SPDX 3.0
AI; W3C PROV-O) — the agent's full report with the complete URL list is
committed VERBATIM at
`docs/strategy/attribution_sources/APPENDIX_A_ATTRIBUTION_STANDARDS_REPORT.md`
(in-diff evidence rule, PR #47 evaluator r1); ALL SEARCH-SNIPPET,
re-verification gated by R-023.
Internal: CLAUDE.md (prime directive 1, Descriptor Foundry, Kaizen),
docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md, docs/KAIZEN.md,
worker/ai_extract.py, docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md,
docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md §11.4,
docs/research/WORLDMONITOR_APPLICABILITY_REVIEW_v1.md §2.
