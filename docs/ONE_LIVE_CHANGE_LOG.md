# ONE LIVE — CHANGE LOG


## 2026-07-12 — Deep review of WORLD_CLASS bar + MASTER doc; v1.1 expansion proposed

**Session type:** Independent deep review ("best technologists / company-spin-up" lens). Output: `OneLive_WORLD_CLASS_v1.1_DEEP_REVIEW.md`. Status: PROPOSAL — pending founder gap-by-gap ratification (per §0.3 contract-first).

### Reviewed
- `OneLive_WORLD_CLASS_bar.md` (§0–§9, per-clause cited) — read in full.
- `OneLive_MASTER_the_whole_enchilada.md` (Parts 0–8) — read in full.

### Findings — defects (fix regardless of ratification)
- D1: Test-count drift between the two docs (196+25 / 221 vs 219 passed + 27 skipped) — pick one canonical number.
- D2: §2/§3 "Meets" verdicts are self-graded, conflicting with §0.7 — relabel or route through non-Claude evaluator.
- D3: Anon SELECT RLS policy on `event` is dead policy while the stealth gate blocks all public traffic — state as intentional future surface.
- D4: visual_regression gate permanently skipped — a gate that never fires proves nothing.
- D5: Single external evaluator (GPT-5.5) — add a second non-Claude lens for trust-critical merges.

### Findings — closed `n.a.` markers (research links in review doc §4)
- §4.1a: ASVS 5.0 levels sourced; proposal: target **L2**, L1 as pre-launch floor.
- §7.5a: DORA 2024 elite thresholds sourced: on-demand deploys, <1 day lead time, ~5% CFR, <1 hr recovery.

### Findings — new domains proposed (v1.1 §10–§15)
- §10 Legal/regulatory: TDPSA (eff. 2024-07-01; GPC since 2025-01-01; SBA carve-out to document) + **TRAIGA (eff. 2026-01-01, no small-business exemption; NIST AI RMF substantial compliance = affirmative defense)** + processor DPA inventory + SOC 2 on revenue clock.
- §11 AI governance: NIST AI RMF Govern/Map/Measure/Manage profile; ratified eval-harness thresholds; model/prompt change control; scheduled prompt-injection red-teaming of extraction.
- §12 Incident response & resilience: NIST SP 800-61r3 / CSF 2.0 runbook + tabletop; backup restore test with declared RTO/RPO.
- §13 Privacy engineering: data map, DSAR/appeal flow, no PII in audit_log free-text.
- §14 FinOps: Inform/Optimize/Operate; canonical unit economic = cost per verified published event; budget alarms BEFORE scheduling the recurring loop (critical-path Step 5 dependency).
- §15 Growth/product measurement: activation/retention/trust-KPI definitions; experimentation discipline; external grounding queued (n.a. this pass).

### Advisory council
- Proposed 3 new seats: software-delivery performance (exemplar: Nicole Forsgren / DORA), AI-law & privacy counsel (TRAIGA/TDPSA practice), FinOps/unit-economics practitioner.

### Open questions carried forward
- Q1–Q6 from MASTER Part 2 (trust-framework naming; monitoring/Sentry; Stripe vs Trolley; Year-1 revenue reconciliation; native mobile timing; sync licensing) — still open, now with recommendations logged in chat.
- NEW Q7: SOC 2 timing trigger. NEW Q8: growth-metrics research pass. NEW Q9: declared RTO/RPO numbers. NEW Q10: second external evaluator model.

### Next action
- Founder reviews gaps one-by-one (G1 = §10 legal) and ratifies/rejects each; ratified clauses merge into `docs/WORLD_CLASS.md` v1.1 via PR with non-Claude review.

## 2026-07-12 (later) — Independent verification attempted; Autonomous Build Charter + API Manifest drafted

### Verification probes (hard results, no guessing)
- GitHub `schubertsean-ui/onelive`: 404 unauthenticated → private confirmed; needs read-only fine-grained PAT.
- Supabase `vqipjlvzfiwnandjumvx`: endpoint LIVE, 401 without key → needs anon key (Tier 1) or read-only role DSN (Tier 2).
- Chat sandbox env: zero stored credentials confirmed. Prior session credentials do not carry over.

### New artifacts
- `OneLive_AUTONOMOUS_BUILD_CHARTER_and_API_MANIFEST.md`: 6-agent org (Generator, Independent Evaluator, Friction Agent, Sentinel, Librarian, Ingestion Orchestrator); founder-crucial escalation protocol (money / legal / trust invariants / go-live / key minting — everything else autonomous with weekly digest); 12-entry API manifest with owner, rationale, key-acquisition steps, env var names; scheduler comparison (GitHub Actions cron recommended now, Fly.io on time-limit breach); key-handling rules.

### Friction Agent
- Framed as gap G-F with 3 interpretations; recommended A+B fusion (pre-work adversarial challenger + irreversible-action speed-bump gate), non-Claude model, block-but-never-write charter. Awaiting founder confirmation of intent.

### Open questions delta
- NEW Q11: credential handoff (PAT + Supabase Tier 1 vs Tier 2). NEW Q12: Friction Agent interpretation (G-F). Q2 (Sentry) upgraded to Step-5 prerequisite in manifest. G1–G6 from prior review still awaiting one-by-one ratification.

## 2026-07-12 (later still) — Four founder-named agents chartered (Friction / Thrive / Fastidious / Protection)

- Gap G-F RESOLVED by founder definition: Friction = kaizen toward zero defects (supersedes prior A/B/C framing).
- New artifact `OneLive_AGENT_CHARTERS_v2.md`: full charters with mandate, owned bar sections, loop cadence, gate powers, KPIs, escalation triggers.
  - Friction → Part 5 Kaizen, §0.8 pruning, §1/§9, mutation testing, defects D1–D5.
  - Thrive → WORLD_CLASS.md lifecycle, §6 UX, Part 4 trust stewardship, §15 growth, council liaison.
  - Fastidious → chief of staff; ABSORBS Librarian + Sentinel (comparison table §3; split trigger defined); second brain, dead-man switch, spend meters, weekly digest, open-question ledger.
  - Protection → §4/§3.5/§8/§12/§13/§10 evidence; encryption posture; penetration two-tier (ZAP in CI + external pen test pre-launch, founder-crucial); reputation monitoring (brand/press/disclosures).
- Cross-agent constitution: write/grade separation org-wide; disk is truth; trust invariants outrank agents; founder-crucial list unchanged + breach-bypass for Protection.
- NEW Q13: does "reputation" mean brand monitoring (assumed) or in-product reputation scoring? Awaiting founder.

## 2026-07-12 (later) — UX/UI co-design prototype v1 delivered
- Artifact: `OneLive_TonightFeed_CoDesign.jsx` — interactive /tonight prototype with a co-design panel.
- Canon honored (from project knowledge): <10s "what should I do tonight", chronological feed, genre + Free/Ticketed markers, subtle confidence ("Info may change"), disputed sorts last but ALWAYS rendered ("Shown, never hidden"), "Something off?" link, Surprise-me minimal-input chip.
- Grounded options: 3 directions (A Marquee dark / B Daylight utility / C Poster wall); 3 trust-marker treatments (Provenance edge [recommended signature] / Status pill / Text whisper); 2 densities (44–48pt per Apple HIG & Material 3 vs WCAG 2.2 SC 2.5.8 24px AA floor). Grounding: W3C WCAG 2.2, NN/g heuristics, Apple HIG, Material 3, GOV.UK Design System, web.dev CWV.
- Open co-design decisions logged: UX-1 direction, UX-2 trust marker, UX-3 density (founder to paste selection line back).
- Q11 (verification credentials) still pending; G1–G6 + G-F still awaiting ratification.

## 2026-07-12 (later) — Prototype v2 built from FOUNDER'S OWN wireframe; palette research completed
- Founder confirmations received: flow = Tonight feed + filters + event detail; style = research-based palette (distinctive/fun/trustworthy); copy = verbatim with options.
- Artifact: `OneLive_Tonight_Prototype_v2.jsx`. Implements PRD §4.1–4.5 exactly: chronological feed, genre markers, Free/Ticketed, "Hear it" inline preview, Today/Tomorrow/This Week tabs, slide-in filter panel (8 PRD genres, show type, venue search, 3 neighborhoods), full event-detail field set (player, exact start, duration, venue+address, map, parking, ticket new-tab, add-to-calendar, share), trust copy verbatim ("Info may change", "Time TBD", "Something off?").
- Palette selected: P1 "Indigo Stage" (blue-dark base = trust per Labrecque & Milne 2012 JAMS + Trustworthy-Blue study; dark immersion per Spotify best-in-class analyses; coral accent = energy). Alternates P2 Violet Hour, P3 Daylight included as switcher for confirmation.
- Copy: verbatim default; Claude alternatives toggleable and flagged as suggestions.
- Awaiting founder: UX-P1 palette confirmation, UX-C1 copy verdict per string. Q11 (repo/DB credentials) still open.

## 2026-07-12 (later) — Master Design Brief v1 for AI design tool created
- Founder direction: not a human designer; write a maximally rich description (emotion/feel/mood/functionality/payoff) + vision/goals/objectives + trust-founded philosophy and its foundational importance; feed to an AI design tool; require 3 distinct directions differentiated from all competitors.
- Artifact: `ONE_LIVE_MASTER_DESIGN_BRIEF_v1.md` — paste-ready master prompt (Part A), 3-direction splitting instruction (Part B), 7-criterion evaluation rubric (Part C), run steps.
- Canon embedded verbatim: Vision ("easy to find, fairly represented, culturally valued"), Mission ("assemble truth… protect discovery from distortion… help real culture travel"), "calm, useful, real", "Less chaos. Real shows.", <10s / <2s / no-login PRD spec, 8 genres, 3 neighborhoods, full detail-page fields.
- Trust rules encoded: no badges/labels ever; automagic (50-bit bottleneck expressed plainly); low-confidence = single quiet icon → dismissible sheet with venue link; nothing hidden; money never decides. Trust Equation formula withheld per Part VII "internal-only" governance; philosophy expressed in plain language.
- Differentiation avoid-list: Spotify, DICE, Resident Advisor, Bandsintown, Ticketmaster/Eventbrite/AXS, Songkick, Luma, generic AI-gradient purple.
- Tool selected: Google Stitch (free, ~350+200 gens/mo, parallel direction agent, vibe-design intake, Figma export) over Figma Make ($20/mo) and v0 ($20/mo) — sources logged in brief.
- Open: founder runs Stitch (Google sign-in, no key) and returns 3 directions for rubric scoring. Q11 credentials, G1–G6, G-F unchanged.

## 2026-07-12 (later) — Design Brief upgraded to v2: "Make me want to click" behavioral architecture
- New §6 in Part A: (A) Nir Eyal Hooked model mapped to OneLive (internal trigger = the 6–9 PM "what's happening tonight" feeling; variable reward = the city's genuinely-new nightly lineup — hunt/tribe/self; investment = saves/genre taps/corrections visibly compounding); (B) Thaler–Sunstein choice architecture (defaults carry ~80% of users → default view must be the perfect answer; bounded genre categories; honest salience; zero dark patterns); (C) Loewenstein information-gap curiosity (cards engineered to open a question resolvable in one tap; "Hear it" as a 3-second gap-closer); (D) synthesized common structure of the most returned-to products (7 elements: near-zero activation energy, natural daily reset, variable-but-bounded feed, compounding investment, shareable artifact, liveness, gentle identity).
- Ethical guardrail encoded: white-hat reflection test; charter rule "not an algorithm chasing engagement"; celebrate-return-never-guilt.
- Rubric extended to 8 criteria (added click-pull). Behavioral sources appended to brief.
- File: ONE_LIVE_MASTER_DESIGN_BRIEF_v2.md (v1 preserved).

## 2026-07-12 (later) — "Spark Line" feature added; brief bumped to v2.1
- Founder proposal: 3/5/7-word vivid emotional description of each act's work, from the artist's own words (ideal) or a recognized critic/tastemaker, cited, positive/accurate only.
- Encoded in brief §4 (card anatomy: Spark Line + tiny attribution; never invent — card runs without one if unsourced) and §6C (Spark Line = the primary Loewenstein gap-opener).
- Legal posture (researched, counsel ratification pending under G1): 3–7-word phrases are below copyright's protection threshold per US Copyright Office Circular 33 / 37 C.F.R. §202.1 ("words and short phrases… uncopyrightable"); residual risks flagged = implied endorsement (frame as description of the artist, never platform endorsement), no alteration/fabrication of quotes, attribution accuracy.
- Sourcing waterfall recommended (Gap G-SL, awaiting founder verdict): (A) artist's own words via claim flow → (B) attributed critic/tastemaker ≤7 words with citation → (C) blank. AI-generated fallback deliberately excluded pending founder call + AI-disclosure labeling.
- Data model note: spark_line {text, source_type: artist|critic, author, source_url, consented: bool} — rides existing provenance architecture.

## 2026-07-12 (later) — Spark Line loosened to free-form; Emotion Glyph Engine specified; brief v2.2
- Spark Line: no sentence structure required — words, fragments, letters, punctuation, typographic play permitted ("brass. menace. amen.").
- NEW: Emotion Glyph Engine appendix added to brief. Invisible backend attaches one expressive glyph per listing from the creator's own self-description. Pipeline: creator text → Claude → Plutchik coordinates (8 primaries × 3 intensities + dyads ≈ 56+ states) → deterministic lookup into a curated 40–60 glyph lexicon.
- Research-driven rules: lexicon admits only low-ambiguity glyphs (Novak et al. Emoji Sentiment Ranking; Miller et al.: only ~4.5% of emoji have consistently low interpretation variance); SELF-RENDERED single SVG set (never native platform emoji — cross-platform sentiment flips documented); rating-adjacent glyphs banned (🔥⭐💯👑❤️👍) to protect discovery neutrality; aria-label text equivalent per WCAG 2.2; creator one-tap override (feeds eval loop); full provenance record; no description → no glyph, never scraped/inferred.
- Open gap G-EG for founder: (1) AI-disclosure labeling for glyphs (creator-approved after override offer vs. explicit "AI-assigned" note), (2) glyph default = single vs pair, (3) approve ranking-glyph ban list.

## 2026-07-12 (later) — Emotion & Vibe Layer spec v1 (consolidates founder concepts: emotion cloud, Feel search, venues, taxonomy)
- New artifact: ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md
- Two-axis taxonomy DRAFTED for ratification: Axis 1 Emotions ("what will I feel") — 16 fan-facing terms pinned to Plutchik coordinates; Axis 2 Vibes ("what is the room") — 7 dimensions (energy, intimacy, texture, light, sound pressure, hour, social mode) + ~40-word launch vocabulary; follows locked "global taxonomy with local mappings" strategy.
- Composition rule proposed: artist = emotion signature; venue/location = vibe signature; event cloud = artist × venue × hour. Extends to all future verticals (food, art, theater).
- Emotion Cloud: multiple generative variants allowed; deterministic from coordinates; same guardrails as glyph engine; signal waterfall = self-description → attributed critic → opt-in post-event fan feels; never biometric/scraped/invented.
- "Feel" search mode: declared emotional intent (now / want to feel / want to experience); FILTERED never ranked — preserves no-ranking + discovery-neutrality invariants.
- Emotion Graph named as third Intelligence-tier moat (beside Heartbeat, Predictive). Concierge = explicit opt-in lens only; user emotion data consent-gated, retention-limited, never sold, aggregate-only to partners.
- Legal researched: EU AI Act Art. 5(1)(f) biometric-inference prohibition + Art. 50(3) transparency — design stays outside scope via declared-preference architecture; GDPR consent/retention practices cited. Counsel ratification under G1.
- Comparison logged: declared-feel search vs inferred-mood personalization → A now, B never by default.
- New gaps: G-VT-1..4 (taxonomy, composition rule, feels prompt, concierge charter rule).

## 2026-07-12 (later) — Founder ratified AI-drafted Spark Line fallback (tier C); brief v2.3
- Waterfall now: (A) artist's own words → (B) attributed critic → (C) AI-drafted with subtle disclosure → (D) blank.
- Tier C rules encoded: composed ONLY from the artist's own public materials; faithfulness-gated via eval harness; renders in a quieter register (italic, one shade muted) with small "✳" mark + "— first notes" attribution; tap opens dismissible sheet: "Drafted from [artist]'s own materials. [Artist] can make it theirs anytime."; replaced the moment the artist claims (doubles as claim incentive); never invents facts.
- Disclosure posture: subtle-but-discoverable satisfies platform AI-disclosure policy + TRAIGA documentation posture (sources previously logged §10/§11); counsel confirms wording under G1.
- G-SL closed as ratified-with-C; G-EG (glyph disclosure) now inherits the same "✳ + sheet" pattern pending founder confirmation.

## 2026-07-12 (later) — Descriptor Foundry pipeline mandated for all AI descriptors; brief v2.4
- Founder rule: every AI-created descriptor passes a multi-option creation test producing best-of-best, which may fuse multiple candidates + add new (style-only) material.
- Encoded as 5-stage Descriptor Foundry: (1) N=6 varied-style candidates from creator's own materials; (2) pairwise knockout tournament vs fixed checklist (pointwise scoring rejected — research shows 67% tie rate and weak selection; pairwise recovers 21%→61%, arXiv:2603.12520); (3) Fusion-of-N synthesis pass — combine fragments + new connective tissue, facts never new (arXiv:2510.00931); (4) independent non-generator judge with traceability gate, blank over "good enough"; (5) full provenance (candidates, bracket, fusion diff) + golden-set regression + creator override supremacy.
- Applies to Spark Lines tier C, Emotion Glyphs, Emotion Clouds, and all future AI surface text.

## 2026-07-12 (later) — Claude Code autonomous-build kit delivered
- Founder directive: run agent loops with the harness to build the live site, working directly with the designer AI(s), via Claude Code.
- Boundary stated honestly: chat-Claude designs and prepares; Claude Code (founder's machine or claude.ai/code) is the loop runtime with repo + credentials.
- Artifacts: CLAUDE.md (repo-root standing charter: prime directives, 6-agent org incl. evaluator + friction gate wiring, founder-crucial-only escalation, Stitch→design/inbox→implementation loop, Descriptor Foundry mandate, env/key rules, current mission = Steps 5→10 behind stealth gate) + CLAUDE_CODE_KICKOFF_PROMPT.md (Session Contract #1: reconcile, independent verification, adversarial_review.py online, friction log online, Sentry/dead-man minimum, sprint plan only — zero deploy/migrate/spend in session 1).
- Setup steps verified via product docs (install script, subscription requirement, claude command, CLAUDE.md memory, claude.ai/code web option).

## 2026-07-12 (later) — Founder audit question: does CLAUDE.md contain everything? Answer: no (by design); gap closed via repo docs package
- CLAUDE.md confirmed as thin standing charter (pointers + rules), per §0.8 pruning principle and Claude Code per-session read cost.
- Gap identified: session artifacts lived only in chat downloads, unreadable by Claude Code.
- Fix shipped: ONE_LIVE_repo_docs_package_2026-07-12.zip — full tree (CLAUDE.md w/ new Document Index section, MANIFEST.md, docs/source [both original session inputs], docs/strategy [deep review, charter+manifest, emotion-vibe spec], docs/design [brief v2.4 + prototypes + archives], docs/ops [kickoff, changelog]). 21 files. Ratification states labeled: brief v2.4 ratified; §10–§15/taxonomy/G-gaps = PROPOSALS, explicitly marked "PROPOSAL ≠ license to build."

## 2026-07-12 (later) — RATIFIED: Google Stitch as the design-generation tool
- Founder approved Stitch (free, parallel-direction agent, vibe-design intake, Figma/Tailwind export) over Figma Make, v0, Lovable et al. Rationale + cons logged in prior entry and in the brief's HOW TO RUN section.
- Fallbacks remain on file (Figma Make, v0) — same Part A brief, zero rework. v0 designated stage-2 (component code after direction is chosen).
- Kickoff sequence active: (1) commit repo docs package; (2) mint OpenAI key + Anthropic spend cap; (3) optional Q11 read-only credentials to chat-Claude; (4) three Stitch passes with brief v2.4 Part A + Part B lines; (5) Claude Code Session Contract #1.

## 2026-07-12 (later) — GENESIS package built: single-file, phone-droppable kickoff
- ONELIVE_GENESIS.md (≈124KB): self-installing bundle for Claude Code (mobile app Code feature or claude.ai/code). Contains founder 3-step phone instructions + executable Steps 0–4 for Claude Code (install 9 embedded files verbatim, commit, verify canon presence, execute Session Contract #1, report, stop) + all documents embedded with FILE/END FILE delimiters: CLAUDE.md, kickoff contract, brief v2.4, deep review, charter+manifest, emotion-vibe spec, reference prototype, changelog append, manifest.
- Safety preserved: Session 1 remains zero-deploy/zero-migrate/zero-spend; missing OPENAI_API_KEY degrades gracefully (flag, don't block); no push to auto-deploy branches.

## 2026-07-13 — GENESIS executed in-repo; Session Contract #1 complete (zero deploy/migrate/spend)

- Genesis package installed and committed (charter merged with pre-existing CLAUDE.md — both in force; brief v2.4, deep review, charter+manifest, emotion-vibe spec, prototype, kickoff, manifest).
- Verified via GitHub API: PRs #9 (stealth gate + orchestrator reconcile) and #10 (world-class bar) MERGED — STATE.md's "GAP 1 blocked" claim superseded. Open: #4 (draft), #7 (recommend close as superseded by #9's port).
- Evaluator online: `tools/adversarial_review.py` (stdlib, exit 0/1/2, SKIPPED-loud without OPENAI_API_KEY, `--require` for CI) + hermetic tests; exercised on PR #9's merge diff (skip path — key not minted).
- Friction gate online: `docs/FRICTION_LOG.md` entry #1 = the sprint plan attacked (PROVISIONAL: generator-model attack, non-Claude re-attack required before Step 5).
- Sentinel minimum: `worker/sentinel.py` (Sentry init fail-loud-on-misconfig/no-op-unset + healthchecks dead-man ping) wired into `api/main.py` + `worker/run_once.py`; `@sentry/nextjs` via `web/instrumentation*.ts`. New deps noted in STATE.md. All no-op until founder mints DSNs.
- Sprint plan written: `docs/SPRINT_LIVE_SITE.md` (Steps 5→10, done-criteria + gating agent per step; preconditions P1–P5).
- Suite: 218 passed/27 skipped as root + 25 vitest; root-only test-precondition fix (skipif euid==0 on unwritable-dir test). D1 python count reconciled: 219/27 non-root.
- The one missing item: `OPENAI_API_KEY` (founder-crucial minting) — evaluator + friction attacks degrade gracefully until then.

## 2026-07-13 (later) — Evaluator armed in CI
- Founder minted `OPENAI_API_KEY` and added it as a GitHub Actions repository secret (session-env copy pending — environments UI has a known bug upstream).
- New workflow `.github/workflows/adversarial-review.yml`: runs `tools/adversarial_review.py --require` (non-Claude, VERDICT: APPROVE demanded) with the full pytest log on every PR touching trust-critical paths (api/worker/ai/supabase/tools/auth-surface/workflows); `workflow_dispatch` variant reviews an arbitrary git range from the Actions tab.

## 2026-07-13 (later) — Evaluator LIVE: first non-Claude review ran, blocked its own gate, findings fixed
- First end-to-end `adversarial-review` run (gpt-5.5) on PR #11 returned REQUEST-CHANGES with 4 blocking + 4 nit findings — the write/grade separation working as chartered, on its first real diff.
- Fixed in-change: (1) evaluator script now executes from the TRUSTED base ref with `python -I` (a PR can no longer edit the reviewer to self-approve or leak the key; loud bootstrap fallback for the first PR); (2) `--require` mode refuses truncated diffs (partial diff ≠ review) and lockfiles are excluded-by-policy with a note to the evaluator; (3) web-touching PRs now ship npm typecheck/vitest/build logs to the evaluator; (4) path filter widened to all of `web/**` (disputed-never-hidden applies to display code); (5) verdict must be the final line; (6) prototype's pre-ratification "✓ Confirmed" line annotated as forbidden-to-ship; (7) `persist-credentials: false`.
- Justified skip (nit): `api/main.py` importing `worker.sentinel` matches the repo's existing api→worker layering (deps/public/ops_candidates already do); revisit only if api/ ever packages standalone.

## 2026-07-13 (later) — Evaluator round 2 findings fixed: gate now unbypassable, SCA policy live, critical dev-chain vuln killed
- Round 2 verdict (gpt-5.5): REQUEST-CHANGES — 3 blocking (path-filter bypass via docs/charter files; bootstrap fallback still handed the secret to PR code; npm audit criticals swallowed) + 3 nits.
- Fixed: workflow now runs on EVERY PR (no path filter — "mandatory must not depend on where a file sits"); bootstrap now HARD-FAILS without the secret ever entering the job (the tool-introducing PR is human-reviewed and merged with the check red, once); blocking SCA step `npm audit --omit=dev --audit-level=high` + full audit shown to the evaluator + `docs/SCA_BASELINE.md` exception register.
- Dependency fix: vitest 3→4 (dev-only chain carried the 1 critical + 1 high; 25/25 tests pass). Remaining 4 moderates = postcss-via-next, no upstream fix — baselined with clear-when trigger + TODOS item.
- Nits: evaluator output now ends with the model's own VERDICT line; trust-gate/validate cross-linked in the workflow header; dead-man ping failures log structured context (url/event/error).
- Consequence: this PR's adversarial-review check stays RED by design (tool not on master yet = bootstrap hard-fail). The two completed evaluator rounds are the non-Claude review evidence for this PR; founder merges past the red bootstrap check after human review.

## 2026-07-13 (later) — PR #11 MERGED by founder; sprint GO; Step 5 scaffolding shipped
- Founder reviewed and merged PR #11 (squash `9d40eb5`) past the by-design-red bootstrap check — the adversarial-review gate is now armed and self-consistent on master (trusted script exists on the base branch; the bootstrap exception can never recur).
- Founder: **"proceed with the sprint plan"** → Session Contract #2 (STATE.md): unblocked Step 5 scaffolding only, zero spend/migrations/cron.
- Shipped: per-run budget ceiling on real ingestion (`worker/run_once.py --max-sources` / `ONELIVE_MAX_SOURCES_PER_RUN`, CLI>env>uncapped-loud, garbage env fails loud; tests) — §14.3 caps exist BEFORE the recurring loop.
- Shipped: `.github/workflows/ingest.yml` — manual-only (`workflow_dispatch`, required max_sources input); **no cron on purpose** until founder arms P2/P3 (Anthropic key w/ console spend cap, DB DSN, healthchecks URL as Actions secrets) + friction re-attack; preconditions fail loud, replay log uploaded as artifact, deadman+Sentry ride the existing run_once wiring.
- Arming = a follow-up PR adding the `schedule:` block, which itself passes the (now armed) adversarial gate.

## 2026-07-13 (later) — Armed gate's first steady-state verdict: REQUEST-CHANGES on PR #12; budget guard made fail-closed
- The armed evaluator's first trusted-script review correctly caught the budget ceiling failing OPEN (0/negative = uncapped) and an unescaped workflow_dispatch input interpolated into shell.
- Fixed: 0/negative/garbage caps now fail closed at every channel (argparse type, CLI resolution, env var, apply_source_ceiling ValueError — defense in depth, all tested); workflow input reaches the shell only via env and is validated as a positive integer before anything runs; replay-log artifact absence is an error on success (audit trail guaranteed) and a warning after failure; tighter type hints.

## 2026-07-13 (later) — PR #12 round 2: remaining fail-open crack sealed
- Evaluator round 2: set-but-EMPTY `ONELIVE_MAX_SOURCES_PER_RUN` now fails closed (CI forwards unset vars as empty — same class as the PR #11 model bug); cap validation moved BEFORE any DB/provider access so misconfig can never hide behind "no sources found"; empty-string added to the bad-env test matrix; workflow input validated as a whole string via [[ =~ ]] (newline-proof) and never echoed into annotations; _run_real typed.

## 2026-07-13 (later) — Founder communication rules added to the charter
- Founder directive incorporated into CLAUDE.md as a standing section: plain language; why-this-not-that with alternatives; honest tradeoffs; direct links; make-it-easy (numbered, phone-friendly, one consolidated ask). Binding on every founder-facing report/PR description, every session.

## 2026-07-13 (later) — "Brain" research delivered (G-BRAIN, PROPOSAL)
- Founder ask: persistent memory so the build agent and the platform never forget. Researched agent-memory landscape (Mem0/Zep/Graphiti/Letta/Anthropic memory tool/pgvector patterns) + platform memory.
- New artifact docs/strategy/ONE_LIVE_BRAIN_OPTIONS_v1.md: Build brain options 1A file-brain sharpening / 1B pgvector-in-existing-Supabase (RECOMMENDED fused with 1A) / 1C hosted (Zep $125+/mo, best LongMemEval 63.8%) / 1D self-hosted graph (Graphiti+Neo4j). Platform brain: audit/replay/provenance already = never-forgets; 2A pgvector semantic layer at Step 7; 2B Emotion Graph stays P3.
- Awaiting founder one-liner (G-BRAIN). No build until ratified.

## 2026-07-13 (later) — Cost discipline chartered; model-cost routing shipped (closes the last 2026-07-11 harness gap)
- Founder directive: least costly method per task, balanced against urgency/criticality, world-class always, maximum margin. Researched routing state of the art (FrugalGPT/RouteLLM cascades: 40–85% cost cuts at ~95% quality) + authoritative Anthropic pricing/caching/batch numbers.
- CLAUDE.md gains a "Cost discipline" section (cheapest-capable first; deliberate logged escalation; quality gates never relax; measure don't guess).
- New docs/MODEL_ROUTING.md: tier ladder w/ real prices (Haiku $1/$5 · Sonnet $3/$15 · Opus $5/$25 · gpt-5.5 evaluator never downgraded), stage mapping, 4 escalation triggers, techniques (prompt caching ~0.1× reads, Batch API 50% off for descriptor-foundry/embedding jobs, effort levels, context hygiene), ceilings unaffected.
- New tools/model_router.py (+6 tests): stage→model resolver, env-overridable, unknown/empty fails loud. TODOS model-cost-routing item checked off.

## 2026-07-13 (later) — G-BRAIN RATIFIED: "1A+1B, platform at Step 7"; 1D trigger made standing; Brain 1A LIVE
- Founder ratified the brain recommendation verbatim and directed that the 1D condition never be lost: "if it ever needs graph infrastructure, that's the moment option 1D becomes worth it, one investment serving both brains."
- Codified as G-BRAIN-1D, a STANDING trigger with objective fire conditions — T1 Emotion Graph build begins / T2 pgvector temporal-recall failures logged / T3 relationship queries outgrow SQL — recorded in the (now RATIFIED) brain doc, a never-check-off TODOS item, and STATE.md's locked-in decisions. On fire: friction attack → founder (new infra = money).
- Brain 1A shipped: docs/memory/ (README conventions + decisions/ + gotchas/ + entities/) seeded with the G-BRAIN decision record and the CI empty-env fail-closed lesson; wired into CLAUDE.md's harness map.
- Brain 1B (pgvector migration + index/recall tools) queued as a P1 contract-first build; platform 2A gated on Sprint Step 7.

## 2026-07-13 (later) — "Recording" implemented: the no-silent-deferrals Record, mechanically enforced
- Founder directive: every "check later" / "ok for now" / noticing-holding moment must be recorded — ideally none exist, since everything is checked against the documented world-class bar for that item.
- New docs/RECORD.md: the deviations register — each entry names what is deferred, the bar it deviates from (cited), and an OBJECTIVE resolution trigger; rows never deleted, resolved rows flip status. Seeded honestly with 9 currently-live deferrals (Sentry tracing-off R-001, visual-regression skip R-002/D4, SCA baseline R-003, stale ground-truth block R-004, provisional friction attack R-005, unratified extraction threshold R-006, catalog gap R-007, unarmed cron R-008, open PRs #4/#7 R-009).
- New tools/deferral_scan.py (+7 tests, incl. real-repo-clean guard): deferral-language code comments must carry a live [R-###] tag; dangling tags fail; missing register = hard failure. Wired into tools/validate as a BLOCKING check. The three existing "for now" comments (Sentry tracing) tagged [R-001].
- CLAUDE.md gains "The Record" section (same-commit rule, prose covered by evaluator review); SESSION_START close adds step 7: review OPEN rows — a fired-but-unactioned trigger is a defect.

## 2026-07-13 (later) — PR #14 evaluator round 1: evaluator slot hardened, Record enforcement made real
- The gate's REQUEST-CHANGES on PR #14 was correct on all 7 blocking counts. Fixed:
  - `tools/model_router.py` now REJECTS any Claude/Anthropic model id in the evaluator slot from every channel the ROUTER resolves (both env overrides AND the policy default). (Round 2 correctly flagged that the live review path in `tools/adversarial_review.py` was not yet covered — closed in the round-2 entry below.) Whitespace-only overrides fail like empty; values are stripped. Tests prove the invariant (both env names, case-insensitive) and that generator stages still accept Claude overrides.
  - CI wiring actually done: `dependency-hygiene.yml` + `source-backfill.yml` resolve their model via `tools/model_router.py standard` instead of hardcoding — the TODOS "DONE" claim is now true, not deferred-work-hidden-as-completion.
  - `tools/deferral_scan.py` now parses real `| R-### | … |` table rows (prose mentions of an id no longer count), only OPEN rows legitimize a tag (tags on RESOLVED rows fail — fired deferrals can't linger in code), a register with zero parseable rows is a hard failure, and scanning covers SQL `--` comments (supabase/ added to scan dirs) and TS/JS `/* */` block comments.
  - The widened scanner immediately caught a real pre-existing silent deferral: 0006's "revisit before the anon key ships" RLS comment — already resolved by migration 0007 — reworded (comment-only) + retro-recorded as R-011 (RESOLVED).
  - R-010 added: option 1D not-built-now is now a register row (the G-BRAIN-1D standing trigger is its resolution trigger); both prose docs point at it.
  - R-007's trigger made objective (Sprint Step 6 exit gate: backfill-filled or founder-descoped); MODEL_ROUTING.md states ids/prices are verified-live 2026-07-13, and documents the evaluator-slot invariant.
- Suite: 274 passed / 28 skipped (11 new tests); trust_gate, lint, deferral_scan green.

## 2026-07-13 (later) — PR #14 evaluator round 2: separation enforced at the live review path; extraction routing fail-closed
- Round 2 caught that round 1's invariant was real but not WIRED: the non-Claude-evaluator check lived only in `tools/model_router.py`, while the actual review entry point (`tools/adversarial_review.py`) would still accept a Claude id. Fixed at the entry point itself — hard fail (exit 2) before any API call. The check is deliberately duplicated, not imported: CI runs the reviewer as a trusted copy from the base ref and must never import PR-controlled repo modules.
- `extraction` stage now fails closed (overrides included) until the §11.2 hallucination threshold is founder-ratified (R-006) — a trust-critical AI path routes nowhere without its release-blocking gate in force. `EXTRACTION_THRESHOLD_RATIFIED` flips only in the ratification commit. MODEL_ROUTING.md updated to match.
- Model-id allowlist added to the router (letters/digits/._:/- only) — catches newline/space/metacharacter misconfig before it reaches an API or a CI `$GITHUB_OUTPUT` write.
- Round-1 changelog claim corrected (it said "every channel" when only the router was covered — operational records must not overstate enforcement). Brain doc's answered founder-ask marked HISTORICAL.
- Suite: 278 passed / 28 skipped (4 new tests).

## 2026-07-14 — PR #14 evaluator round 3: swallowed router failures + the empty-model fallback itself
- Round 3 caught round 2's own wiring: `echo "model=$(router)"` in the two Actions swallows a router failure (a failing command substitution inside a successful echo doesn't fail the step) — the fail-closed resolver could emit `model=` silently. Fixed: the substitution runs as its own assignment under `bash -e` + a non-empty assertion, so a router rejection fails the step loudly.
- It also correctly turned our own fail-closed rule against the reviewer's oldest line: present-but-empty `OPENAI_REVIEW_MODEL` silently meaning "default" (the PR #11 first-live-run fallback) is fail-open on the trust-critical path. Now: the workflow exports the var only when the repo variable is genuinely non-empty (so "unset" is expressible in CI), and the script HARD-FAILS on set-but-empty model or base URL; unset still means the documented default. The old codifying test replaced with fail-closed tests. Back-compatible with the base-ref trusted copy during this PR's own review.
- Nits: TODOS bold-marker hygiene; P3 TODOS item for a model-id liveness smoke check; deferral_scan contributor note on deliberate false-positive bias (reword/tag, never weaken).
- Suite: 279 passed / 28 skipped.

## 2026-07-14 — PR #14 evaluator round 4: CI reviewer-model override channel removed entirely
- Round 4's single blocker was airtight: GitHub renders an UNSET repo variable and a SET-BUT-EMPTY one identically in `${{ vars.* }}`, so no workflow shell gate can fail closed on the difference — round 3's "export only when non-empty" quietly maps set-but-empty to "default", bypassing the script's hard-fail.
- Resolution: the runtime override channel is REMOVED from CI rather than patched (fewer config channels on a trust-critical path beats a cleverer check). CI always runs the trusted script's `DEFAULT_MODEL`; changing the CI reviewer model is now a PR editing that constant — which the trusted-base-ref mechanism has the OLD model review. Dead-default emergency path: the documented human-review bootstrap exception. `OPENAI_REVIEW_MODEL` remains for local runs with the script's own fail-closed handling.
- Nits: autouse env-isolation fixture in the router tests; MODEL_ROUTING.md now states explicitly that the CI reviewer enforces the evaluator invariant independently of the router (trusted copy must not import PR-controlled modules).
- Suite: 279 passed / 28 skipped.

## 2026-07-13 (later) — RAG investigation folded into the ratified brain plan
- Founder ask: "investigate the use of a RAG System re: our prior 'brain' conversation." Finding: the ratified Brain 1B (pgvector-in-Supabase) IS a RAG system — no direction change; two proven quality upgrades folded into the queued 1B build spec at zero new vendor/spend: hybrid retrieval (vector + Postgres full-text) and a cheap rerank pass (typ. 15–30% retrieval-quality gain). GraphRAG identified as the RAG name for option 1D — already covered by the standing G-BRAIN-1D trigger (T3 = exactly the workload where GraphRAG earns its cost). Addendum in docs/strategy/ONE_LIVE_BRAIN_OPTIONS_v1.md; TODOS 1B item updated.

## 2026-07-14 — PR #14 merged after 5 evaluator rounds; po + Kaizen ratified and built
- PR #14 (brain ratification + cost routing + the Record) APPROVED on round 5 and squash-merged. Round-by-round: trust-design gaps → enforcement wiring → shell failure modes → config-channel closure — recorded as the Kaizen ledger's seed data.
- Founder ratified "All three": (a) po provocation battery, (b) Kaizen measures, (c) maturity levels deferred. Built: `docs/skills/po_provocation.md` (de Bono canon — escape/reversal/exaggeration/distortion/wishful + founder's absurd + random entry + random×operator combos, with mandatory movement techniques; research-cited incl. LLM-era evidence that structured multi-operator prompting beats single-shot ideation) + `tools/po_battery.py` (+8 tests, seedable prompt generator, no API calls) + `docs/KAIZEN.md` (zero ESCAPED defects absolute; internal catches mined by class; measures M1–M6) + `docs/metrics/KAIZEN_LEDGER.md` (append-only, seeded with PRs #11–#14 incl. the empty-env repeat-class watch) + charter "Thinking tools & Kaizen" section + SESSION_START close step 8 + standing TODOS items + R-012 (levels: objective trigger = first real cron week).
- Trust boundary stated everywhere it matters: provocations are stimuli, never facts — po output enters memory/candidate data/user-facing copy only by surviving the normal gates; convergent gates stay purely convergent.

## 2026-07-15 — Certainty Display Stack RATIFIED ("Display stack accepted")
- Founder ratified same day: NO fifth state — epistemic state frozen at 4, composing with freshness and provenance as attributes; event_status its own field. Doc flipped PROPOSAL → RATIFIED with the verbatim anchor; the governance rule stands for any future candidate (decision test + explicit founder decision; no design process or agent may add states). Build unchanged: Step 7.

## 2026-07-15 — Founder closes PRs #4/#7 + confirms 4-state; fifth-state RECOMMENDATION: NO (Certainty Display Stack, PROPOSAL)
- Founder: "Close both and confirmed" — PRs #7 (superseded by #9) and #4 (closed as Step 7 reference draft, closing notes attached) closed; R-009 RESOLVED. 4-state confidence model CONFIRMED as final canon. (PR #24 evaluator round 1 tightened this entry's wording: the fifth-state answer is a PROPOSAL awaiting FOUNDER acceptance (the only ratification path; Step 7 re-presents, never decides), and the non-critical-path founder-decision backlog in TODOS remains open — "no standing blocks" applies to the critical path only.)
- Founder question "do we need a fifth state?" researched (uncertainty-communication trust studies: transparent uncertainty does not erode source trust — van der Bles et al. PNAS 2020; intelligence tradecraft: likelihood and evidence-confidence are deliberately separate elements — Kent/ICD 203). Recommendation recorded as PROPOSAL in docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md: keep the 4 states FROZEN; compose with freshness ("verified 2h ago", from watcher last_verified_at) and provenance class (already ratified); event_status (cancelled/postponed) is its own field, never a confidence state. Decision test codified for any future fifth-state candidate.

## 2026-07-15 — PR #21 MERGED (3 rounds); measurement unit made explicit
- PR #21 merged: 1% bar + one-way ratchet canon, extraction gated at every entry point until the Step 6 golden-set exam ships and passes (R-013).
- Founder precision question ("1% of what?") answered and recorded in KAIZEN §M7: unit = FIELD ASSERTION; numerator = invented-or-wrong asserted fields; denominator = all asserted fields (micro-averaged; correctly-empty fields don't pad; meta excluded; times strict). Recall reported alongside as the anti-gaming pair (going mute is not safety). Event-level "≥1 bad field" rate reported as a secondary, non-gating measure — field-level 1% ≠ 1% of events, and the doc says so plainly.

## 2026-07-15 — PR #21 round 2: explicit model= cannot bypass the gate; records made truthful
- Round 2 caught the leftover door: an explicit `model=` constructor argument skipped the R-013 block entirely — and a test enshrined the bypass. Fixed: the gate is checked FIRST on every construction path (explicit selects WHICH model once permitted, never WHETHER); provider-mechanics tests open the gate via an explicit fixture; a dedicated test proves explicit model= is blocked while the gate is unshipped.
- Ledger row corrected in-branch ("extraction unblocked WITH its gate" was false in the diff's final state — records must describe what EXISTS). enforce_useful_work now counts attempted sources from the report's per-source results, not the input list.

## 2026-07-15 — PR #21 round 1: the ratchet rule enforced against its own author; extraction stays blocked until the exam exists
- The evaluator applied KAIZEN §M7 (merged hours earlier) to this PR itself: an extraction model change may not ship without golden-set exam evidence — and no golden set exists yet. Correct. Resolution: ratification of the NUMBER stands (R-006 RESOLVED), but the router flag returns to False and NEW row R-013 records that extraction stays blocked until Step 6 ships the gate (≥40-example golden set ≈ 320 facts meeting the 1% sample floor, live-exam runner, blocking CI) and the starting model PASSES.
- Invariant-at-entry-point (repeat class from #14): ClaudeProvider now resolves its model THROUGH tools.model_router (tools made a package) — single-sourced id (stale-drift class structurally closed), gate enforced where extraction actually runs; blank explicit model arguments fail closed. Real runs now fail loudly at provider construction until Step 6 — honest state: the pipeline refuses to extract ungated.

## 2026-07-15 — FIRST REAL INGESTION RUN + R-006 RATIFIED (1% + ratchet)
- First real capped run (3 of 266 enabled sources): infrastructure green end-to-end — DB via as-pasted DSN+password splice, budget cap enforced, ANTHROPIC key authenticated, dead-man pinged, replay artifact persisted. Extraction failed loud on a retired model id (claude-3-5-sonnet-latest, 404 ×3) — refusing to silently degrade, exactly as designed. Cost ~$0.
- Two internal catches (ledger M2): stale-model-config, and — caught in log review — the run reported SUCCESS with the dead-man pinging healthy despite 3/3 sources erroring (fail-open class). Fixed: extraction default → claude-haiku-4-5 (routing tier) with fail-closed env resolution (ONELIVE_MODEL_EXTRACTION > legacy ONELIVE_CLAUDE_MODEL; set-but-empty raises); TotalRunFailure RAISES on zero-useful-work runs so deadman pings /fail (partial errors: loud warning, still success).
- Founder ratified R-006: "I'm ok to BEGIN at 1%" — threshold live, router extraction stage unblocked in the same commit, and the ONE-WAY KAIZEN RATCHET codified (docs/KAIZEN.md §M7): golden-set exam pre-ship + production sampling feeding new exam cases; drop to 2× measured after 4 clean half-bar weeks at valid sample size (sample-size table: 1%→~300 facts … 0.001%→~300k); never loosens.

## 2026-07-14 — PR #19 evaluator round 2: scope AND masking (defense in depth), docs made truthful
- Round 2 correctly rejected round 1's "never logged beats masked" stance: the URL-encoded DSN equals NEITHER GitHub secret, so auto-redaction misses it, and the bar cannot rest on every future failure path (traceback, Sentry breadcrumb, env dump) never printing a connection string. Final design keeps BOTH layers: in-step scope (no GITHUB_ENV/outputs; pip install never sees it) + a properly ESCAPED ::add-mask:: registered before deps install ('%'→'%25' first — the exact escaping hole round 1 flagged), via assemble_dsn.py --mask-command (+tests proving the escaped command and escape ordering).
- Changelog claims corrected in place (round-0 "masked" and round-1 "no masking surface" both pointed at this entry) — operational security docs must describe the behavior that EXISTS.
- Nits: outer whitespace on pasted secrets normalized (the most common paste artifact) while interior whitespace/line breaks hard-fail; no-secret-in-errors invariant now also locked on an error path where secret material exists.

## 2026-07-14 — PR #19 evaluator round 1: credential scope tightened, assembly extracted to tested script
- Both blockers were real credential-handling regressions in my round-0 design: GITHUB_ENV persisted the assembled DSN to EVERY later step (pip install included — supply-chain exposure the original per-step scoping never had), and `::add-mask::` lacks workflow-command escaping, so URL-encoded passwords (%xx) could mis-register the mask.
- Fix eliminates both mechanisms: assembly moved into tools/assemble_dsn.py (+7 tests: passthrough, url-encoded splice, fail-closed on placeholder-without-password/empty/line-breaks, stdout-is-only-the-DSN, error-output-carries-no-secret-material) and runs INSIDE the single step that needs the DSN via silent command substitution — never exported to other steps. (Round 2 corrected this entry's original 'no masking needed' stance: scope alone relies on every future failure path never printing the environment — see the round-2 entry for the final both-layers design.)

## 2026-07-14 — Founder ergonomics: DSN placeholder substitution in the ingest workflow
- Founder friction (phone setup): hand-editing [YOUR-PASSWORD] inside a long credential string is the most error-prone step of secrets setup. ingest.yml now supports pasting the Supabase URI AS-IS as ONELIVE_DB_DSN plus the password as its own ONELIVE_DB_PASSWORD secret; the workflow splices them, URL-ENCODING the password (special characters silently corrupt a hand-edited URI). Placeholder-present + no password secret = hard fail; line breaks in the assembled DSN = hard fail. (Masking/scoping mechanism revised twice by evaluator review — the CURRENT behavior is defined by the PR #19 round-2 entry: in-step scope + escaped add-mask.) Fully-edited DSNs still work unchanged.

## 2026-07-14 — PR #17 evaluator round 1 + channel playbook
- The gate held even the po-harvest CANDIDATE ideas to the trust invariants — correctly: "fresher first-party signal wins" would have silently collapsed a dispute (now: newer signal may become PREFERRED, conflict always surfaces per shown-never-hidden); the "confirm your listing" magic link was a link-possession elevation path (now: the link only INITIATES the verified claim/auth flow — single-use, expiring, replay-protected, audited; a forwarded link is worthless). Nits: DMARC-ALIGNMENT required (generic SPF/DKIM pass proves nothing); fast lane explicitly checks existing contradictory evidence before promotion; HIBERNATED = stop polling only, push/manual/contradiction signals still land and wake the record.
- Founder ask "how do we best sign up?" → §2b channel playbook added: open channel taxonomy (type/subscription/validation/trust-class per channel, config not code), priority = cheapest-reliable-first (ICS/RSS → newsletter → website → socials → aggregators → LinkedIn/PR-as-discovery); aggregators are always third-party corroboration+discovery, never the fast lane, and their ToS/data-licensing review is founder-crucial (legal) before scale use.

## 2026-07-14 — Scale-out sensor architecture RATIFIED (watchers, three modes, first-party = confirmed)
- Founder ratified across four messages and said "Record it": entity-scale coverage = cheap watcher RECORDS (not persistent LLM agents; rejected alternative costed at ~$1k+/day idle at 10^5 entities); three engagement modes (proactive pull / responsive push / investigative escalation); provenance-weighted gate — a validated FIRST-PARTY assertion about the entity's OWN event logistics enters at `confirmed`, via verified external channels (DKIM/DMARC domain validation, canonical domain, registered handles) OR the entity's authorized in-product account (claim flow); third-party stays unverified-climbing-via-corroboration. Boundaries: scoped authority (own logistics only, never opinions/other entities), no command authority (injection rule applies to the fast lane), disputed-still-wins. Scout swarm = gated+capped discovery growing from source-backfill.
- Trust invariants UNCHANGED (4-state model, AI never publishes, shown-never-hidden, tastemaker separation). New canon doc: docs/strategy/ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md with build-trigger table (critical path unchanged; watcher records + gate rule at Step 7).
- First chartered po battery run opened the design work (seed 20260714, word "beehive"); harvest of 5 candidate ideas in the doc appendix + M6 ledger row (multi-party authority, burst/hibernation lifecycle, per-source extraction templates, confirm-your-listing magic link, change-rate attention allocation).

## 2026-07-14 — PR #15 merged (round 2 APPROVE); Foundry production-harness review folded into specs
- PR #15 (po battery + Kaizen measures) APPROVED round 2, squash-merged. Ledger M1 for #15: 2 rounds.
- Founder-supplied article (Microsoft Foundry/Core AI production-agent harness) reviewed against our build. Verdict: strong independent convergence — harness-over-model, deterministic-code-where-possible, rubric evaluation, structured-uncertainty, guardrails-as-architecture all already ours. Two adoptables folded into queued specs at zero cost: (1) Brain 1B recall is an AGENTIC LOOP with an explicit `no relevant memory` return (TODOS 1B item); (2) Step 6 golden set must include indirect-prompt-injection cases — fetched text is untrusted input (SPRINT_LIVE_SITE Step 6).

## 2026-07-14 — PR #15 evaluator round 1: the battery must not be trimmable
- The gate correctly held the tool to the founder's own words ("exhaust"): defaulting to 2 of 6 random×operator combos while printing "run EVERY prompt" was partial coverage wearing full-coverage clothes, and `--combos 0/1` was a fail-open knob. Fixed: ALL six P8 combos generated every battery, the knob is REMOVED (a downgrade path is a false-confidence door), doc says coverage is never sampled down, and the tests now fail if any P8.1–P8.6 goes missing (plus a canon-size tripwire).
- Nits: P7 random-word variance test parses the word field directly; citations upgraded to labeled sources (author/venue/date); P3 TODOS item for a ledger append-only CI guard.

## 2026-07-14 — Charter amendment: gate custody (founder-approved)
- Trigger: founder-requested review of Weco AI's "first evidence of recursive self-improvement" post. Its transferable lesson — a self-improving agent's evaluation must be held out from the loop it optimizes — exposed a charter-prose gap: the Generator maintains its own harness, but changes to the gate tooling itself were not named in the evaluator-MANDATORY list, and nothing made a gate relaxation a founder interrupt.
- Amendment (CLAUDE.md, two lines): (1) **gate custody** added to the evaluator-MANDATORY list — any change to verification tooling/thresholds (`tools/validate`, `trust_gate.py`, `deferral_scan.py`, `lint.py`, `adversarial_review.py`, `eval_harness`, CI gate workflows) requires independent non-Claude review; (2) **gate-threshold relaxations** added to founder-crucial escalations — loosening any gate is never an agent decision.
- Honesty note recorded in the same breath: the evaluator half was ALREADY mechanically enforced — `adversarial-review.yml` runs on every PR with no path filter (deliberate, PR #11 rounds 1–2). The charter now states the intent so it doesn't depend on one workflow file; the genuinely new rule is the relaxation interrupt. Decision record: `docs/memory/decisions/2026-07-14_gate-custody.md`.
- Boundary stated: stricter gates and false-pass bugfixes are normal evaluator-reviewed work; only loosening interrupts the founder.

## 2026-07-14 — Research note: po battery on global sensing + Peirce semiotics (PROPOSAL)
- Founder research note executed (Session Contract #6): full chartered po battery (seed 20260715, random word "anchor", all P1–P8.6 with movement) against "share all the entertainment happening all the time — hundreds of thousands of sites/feeds globally, starting from central Texas." Harvest: 12 candidates (H1–H12) recorded with per-candidate trust screens in `docs/strategy/ONE_LIVE_GLOBAL_SENSING_PO_AND_PEIRCE_NOTE_v1.md`; M6 ledger row added; disposition = design-time inputs for the queued Step-7+ sensor-architecture items, converging through the normal gates. Two provocations logged as dead ends (honesty over padding).
- Peirce analysis verdict: useful in exactly two places — (1) icon/index/symbol as evidence-typology VOCABULARY (indexical connection is why first-party = confirmed is principled; symbolic evidence needs corroboration), adopt in the Step-7 evidence-schema docs; (2) po = engineered abduction, and the existing loop already completes Peirce's inquiry cycle (po=abduce, friction=deduce, gates=induce) — cite in the po skill doc at next touch. Six-hats mapping judged decorative; no semiotic formalism/ontology/tooling adopted (least-costly-method-first). Founder's "Proc" reference unresolvable — flagged for a one-line correction.
- Trust boundary restated: nothing po-generated entered memory, candidate data, or user-facing copy; the note is PROPOSAL; plan of record remains the ratified scale-out sensor architecture.
