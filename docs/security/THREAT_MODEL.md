# OneLive threat model — the "world model" the red team attacks

Greppable summary: the explicit, living model of the system a security review
reasons against — assets, actors, trust boundaries, invariants, and the
attacks already closed. Founder question (2026-07-17): "Is there a world model
that may be useful?" Answer, made concrete: not a learned simulator (Genie /
JEPA-style world models are for visual/embodied agents and buy CI security
nothing), but THIS — a maintained description of the world the system operates
in, so a red team attacks a stated model instead of guessing at one, and every
finding updates the model rather than evaporating. The product-domain world
model is separate and already ratified: the Step-7 entity graph
(venue/artist/event lifecycle, `docs/strategy/ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md`).

This file is the red team's target of record (`docs/security/RED_TEAM_CHARTER.md`).
Keep it current: a review against a stale model reviews a system that no longer
exists.

## 1. Assets (what an attacker wants, ranked)

| Asset | Why it matters | Where it lives |
|---|---|---|
| **The trust surface** (`/tonight` shown events) | The product IS "which shows are really happening"; a single confidently-wrong or planted event is the whole-company failure | canonical `event` rows → `/tonight` API |
| **ANTHROPIC_API_KEY_EXAM** | Spend + a foothold in the exam channel | `extraction-exam` GitHub environment only |
| **ANTHROPIC_API_KEY** (extraction) | Spend | worker runtime env |
| **OPENAI_API_KEY / _ATTENDED** | Spend + could let PR-controlled code self-approve | repo secret (base-owned review job) + `attended-review` env |
| **The gate itself** | Whoever weakens validate/trust_gate/evaluator/eval-harness disables every other protection | `tools/`, `.github/workflows/` |
| **DB (Supabase)** | Private-event columns, source catalog, future PII | Postgres 15, RLS fail-closed |
| **Clerk allowlist** | The stealth-gate boundary before go-live | Clerk + `apps/web` middleware |

## 2. Actors / trust zones (who can do what)

- **Anonymous internet** — untrusted. Reaches raw-fetched source text (attacker-authorable: a venue page, a social post) and, post-launch, the public `/tonight` read surface.
- **Fetched source text** — UNTRUSTED DATA that the AI reads. The prompt-injection surface (see §4). Never code, never authority.
- **The Generator (this Claude)** — trusted to write, NOT to self-certify. Cannot publish, cannot merge its own examiners unreviewed, cannot mint keys.
- **The Independent Evaluator (GPT-5.5) / Friction (non-Claude)** — the adversarial gate. Different vendor by charter; still an LLM (the bias §6 addresses).
- **Maintainer (founder)** — the only actor who dispatches secret-bearing exams, merges through documented reds, and holds Red-hat go/no-go.
- **CI runners** — semi-trusted; the whole PR-#31/#32 design exists because a PR-controlled workflow copy is attacker-influenced.

## 3. Trust boundaries (the lines attacks try to cross)

1. **Untrusted text → extraction.** AI reads attacker-authorable text. Boundary: the AI's output is a *candidate*, never a publish.
2. **Extraction → publish.** The gate. AI physically cannot import the promote path — enforced by `tools/trust_gate.py::check_ai_never_promotes` (+ `check_promote_import_allowlist`), covered by `tests/test_trust_gate.py::test_catches_ai_promoting` and `::test_promote_allowlist_blocks_new_importer`; every event crosses via evidence → gate → human review.
3. **PR-controlled code → secrets.** No PR code shares a runner with any key: extraction exam runs default-branch harness only (subject = pure data); reviewer key isolated into a base-owned job (PR #32 r13).
4. **Candidate data → confidence.** No hat, model, expertise, or enthusiasm raises confidence — only source corroboration. The one-way valve.
5. **Anon key → private data.** RLS fail-closed; migration 0007 narrowed the `event` public-read policy.

## 4. Attack surfaces & the standing invariants that cover them

- **Prompt injection** (planted text tells the extractor to output a marker / fake event): golden set carries `injection` traps with `forbidden` markers; ANY marker in output fails the exam regardless of rate math. Invariant: extracted facts are candidates; corroboration + human review are the second wall.
- **Pay-to-rank / paid placement:** structurally forbidden — no ranking input is purchasable; ads cannot import gating/promote (`trust_gate.py` invariant 2).
- **Gate tampering / self-certification:** evaluator mandatory + path-filterless on every PR; the Generator never merges its own examiners; gate-threshold relaxation is founder-crucial.
- **Evidence forgery / reuse:** exam evidence binds subject SHA + prompt hash + model + golden hash + harness-manifest hash + full dependency lock; verdict re-derived from raw metrics, never trusted as `passed:true`.
- **Secret exfiltration via CI:** §3.3 boundaries, all mechanical (pull_request_target base-owned execution; environment deployment-branch policies proven in-run).
- **Disputed-event suppression:** disputed shown-never-hidden (charter invariant); deletion is not a state.

## 5. Closed-attack log (what those adversarial-review histories already killed)

The evaluator review histories on PR #25 (exam harness) and PR #32 (reviewer
evidence) are the durable adversarial record — see those PRs' adversarial-review
check runs for the exact rounds; each closed attack is a test or a mechanical
boundary today. Load-bearing examples — the red team should try to
REOPEN these, not re-derive them:

- filename/stack-string exam-channel spoofing → process-entrypoint boundary (r8)
- forged/`passed:true` reports → re-derived verdict + evidence bound on all six: subject SHA, prompt sha256, model id, golden-set sha256, harness-manifest sha256, and the full dependency lock (r10, r22–r26)
- truthy-string ratification flag (`"False"` opens the gate) → exact-boolean `is True`, both production reads (r26 + merge-land)
- incomplete evidence binding (golden set, scorer, deps) → computed import-closure test; full transitive dependency lock (r22–r26)
- PR-workflow-copy secret exfiltration → base-owned job isolation, key never shares a runner with PR code (PR #32 r13)
- self-consistent-but-wrong answer key (g007 gates-time) → convention lint + this doc's §6 human check

## 6. The residual this model cannot close by itself (why the red team exists)

Every reviewer above is an LLM. Cross-*vendor* (Claude vs GPT-5.5) is not
cross-*paradigm*: a flaw-class that AI systems systematically miss — in security
reasoning, in what counts as a "fact," in the shape of the whole design — is
plausibly shared, not caught. And the Generator authored the exam key, the
"correct"-defining conventions, and the tools that assemble what the reviewer
sees; the reviewer audits fiercely but inside a Generator-built frame.

Mitigation status — stated by what EXISTS today, never by what is planned
(crediting a future control as current is exactly the residual-laundering this
section must avoid):

- **Exists now:** the §4 mechanical invariants (code + tests — the live
  protection); the human golden-key audit SHEET
  (`GOLDEN_HUMAN_AUDIT_2026-07-17.md`) is generated, though the human reading
  is still pending; this doc + the red-team charter exist as target and
  procedure, but no red-team run has occurred yet.
- **Planned, NOT yet active (do not count as present protection):** production
  ground truth (item 1 — gated on Step 7, no real rows yet); the Gemini third
  family (item 4 — waits on `GEMINI_API_KEY`); the cross-family red team's
  first run (BLOCKED until that key AND its enforcement tooling exist — one
  fail-closed mode, no degraded GPT-5.5 substitution).
- **The honest ceiling (R-020, OPEN):** a one-time HUMAN security review
  before go-live — the AI red team informs it but does not replace it. Default
  is fail-closed: this review is REQUIRED before the allowlist opens (R-020
  blocks go-live sign-off); any decision to launch without it is a new,
  dated, founder-crucial risk-acceptance recorded at that time — never
  pre-authorized. No silent launch.

This §6 NAMES a residual the §4 invariants do not cover; it adds no protection
by describing one.

## Change rule

Every red-team finding, every new attack surface, every closed attack updates
this file in the same change (the Record's no-silent-deferral rule applies). A
finding with no model update is a finding half-recorded.
