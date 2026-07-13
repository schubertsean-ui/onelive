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
