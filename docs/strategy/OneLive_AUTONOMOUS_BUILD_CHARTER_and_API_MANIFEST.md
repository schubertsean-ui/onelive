# OneLive — Autonomous Build Charter & API/Credentials Manifest (v1)

**Compiled 2026-07-12 · Status: PROPOSAL pending founder ratification (§0.3 contract-first). Nothing below spends money or mints keys — only the founder does that, by design.**

---

## §1 — CREDENTIALS NEEDED *NOW* FOR INDEPENDENT VERIFICATION (blocking)

Live probe results this session: GitHub repo = private (404 unauthenticated); Supabase project = live, 401 without key; sandbox env = zero stored credentials. Exactly two items unblock verification:

### 1A. GitHub fine-grained PAT (read-only, single repo)
1. GitHub → Settings → Developer settings → **Fine-grained personal access tokens** → Generate new token. (Docs: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
2. Resource owner: `schubertsean-ui`. Repository access: **Only select repositories → onelive**.
3. Permissions: **Contents: Read-only · Pull requests: Read-only · Metadata: Read-only.** Nothing else.
4. Expiration: 7 days (verification is a bounded task; re-mint if needed).
5. Env var name when provided: `ONELIVE_GH_RO_TOKEN`.
**Why fine-grained over classic PAT:** classic tokens grant all-repo scope; fine-grained tokens are repo- and permission-scoped — least privilege per OWASP authorization guidance already in your bar (§4.4) and GitHub's own recommendation (https://github.blog/security/application-security/introducing-fine-grained-personal-access-tokens-for-github/).

### 1B. Supabase read credential (choose one tier)
- **Tier 1 (counts on public-read tables only):** the **anon key** — Dashboard → Project Settings → API → `anon` `public` key. Verifies `event`/`venue`/`artist` through RLS exactly as a future public client would. (Docs: https://supabase.com/docs/guides/api/api-keys)
- **Tier 2 (full verification: 14 tables, migrations, source counts per county):** create a **read-only Postgres role** and hand me its pooler DSN — SQL editor:
  `create role onelive_ro login password '<generate>'; grant usage on schema public to onelive_ro; grant select on all tables in schema public to onelive_ro;`
  DSN format from Dashboard → Project Settings → Database → Connection pooler. (Docs: https://supabase.com/docs/guides/database/postgres/roles · https://supabase.com/docs/guides/database/connecting-to-postgres)
- **Never** the service-role key to a chat agent — it bypasses RLS entirely (your own Part 4 posture; https://supabase.com/docs/guides/api/api-keys#the-servicerole-key).
- Env var names: `ONELIVE_SB_ANON` / `ONELIVE_RO_DSN`.

---

## §2 — THE AUTONOMOUS BUILD ORG (loops, harnesses, second brain)

Design goal: **founder input only at crucial decision points; everything else runs as standing loops with disk-backed state** (Karpathy LOOPS §I/§IV — already your §0.1/§0.4).

### The agents
| Agent | Runs where | Loop | Writes to |
|---|---|---|---|
| **1. Generator** | Claude Code session | Understand → implement → self-review → verify (Part 5 inner loop) | branches, PRs, STATE.md |
| **2. Independent Evaluator** | GPT-5.5 via API (+ Gemini as second lens per defect D5) | Reads raw diff + test logs on every auth/pipeline/SQL/data-trust PR; APPROVE/REQUEST-CHANGES | review records in PR |
| **3. Friction Agent** (new — see §3) | Non-Claude model, pre-work | Challenges plans *before* code: attacks the contract, names blast radius, forces the bottleneck statement, decides "founder-crucial or not" | `docs/FRICTION_LOG.md` |
| **4. Sentinel (ops)** | Scheduled job | Watches Sentry, healthchecks dead-man switch, spend meters; opens issues; pages founder only on trust-invariant or budget breach | `audit_log`, issues |
| **5. Librarian (second brain)** | Claude, session bookends | Maintains STATE.md, session arcs, TODOS.md, evidence base (`onelive_worldclass_sources.md`), change log; reconciles at session start (your `tools/session_reconcile.py`) | all docs/ state files |
| **6. Ingestion Orchestrator** | Scheduled worker (§4 comparison) | fetch → sensor → extract → gate per source; structurally cannot promote | candidate store, audit_log |

### The founder-crucial escalation protocol (the ONLY times you're pinged)
1. **Money** — any new paid service, any spend-cap change, any contract.
2. **Legal posture** — §10 ratifications, ToS/privacy publication, restricted-data edge cases.
3. **Trust invariants** — any proposed change to Part 4 invariants (default answer is no).
4. **Go-live pushes & allowlist changes** (already Step 10 of your critical path).
5. **Credential minting/rotation** — only you create keys; agents never self-provision.
Everything else proceeds autonomously with a decision record; you get a **weekly digest** from the Librarian instead of interrupts. This mirrors LOOPS §V: insert a human only when the contract is wrong, not when the build is.

---

## §3 — THE FRICTION AGENT (framed per gap protocol: issue → options → recommendation → reasoning)

**Issue:** "friction agent" is ambiguous; three defensible readings:
- **Option A — Adversarial challenger (pre-work):** attacks every plan/contract before the Generator writes code: "what breaks, who's harmed, what's the cheaper path, is this founder-crucial?" Extends §0.2 role-separation *upstream* from code review to planning.
- **Option B — Deliberate speed-bump gate:** mechanically slows a defined class of irreversible actions (deploys, schema migrations, spend, prompt changes) behind a checklist that must be answered in writing before the action executes.
- **Option C — Product-friction hunter:** finds UX friction in the product itself (onboarding drop-off, slow flows) — a growth function, not a build-safety function.

**Recommendation: A + B fused into one agent; C is a Phase-2 duty of the same agent once real users exist.**
**Reasoning:** A without B produces critiques nobody must answer; B without A is a dumb checklist. Fused, the Friction Agent is the *only* gate between "autonomous" and "reckless": it is what makes minimal-founder-input safe, because it owns the crucial/not-crucial classification (§2 protocol) and logs every waved-through decision to `FRICTION_LOG.md` for your weekly digest. It must run on a **non-Claude model** so the Generator never negotiates with its own family (§0.2 logic). Charter rule: **the Friction Agent can block but never write code** — pure evaluator, zero generator privileges.

---

## §4 — COMPLETE API MANIFEST (every key, who uses it, why this tool, how to obtain)

Legend: **When** = must exist before that critical-path step. Costs: see linked pricing pages — no numbers invented here; each is a founder-crucial approval anyway (§2 rule 1).

| # | API / Service | Used by (agent) | Why this over alternatives | How to obtain the key | Env var | When |
|---|---|---|---|---|---|---|
| 1 | **GitHub fine-grained PAT (read-only)** | Me, this verification | Least-privilege vs classic PAT (all-repo scope) | §1A steps | `ONELIVE_GH_RO_TOKEN` | **Now** |
| 2 | **Supabase anon key / RO DSN** | Me, verification; later the PWA (anon) | RLS-respecting; never service-role to agents | §1B steps | `ONELIVE_SB_ANON` / `ONELIVE_RO_DSN` | **Now** |
| 3 | **Anthropic API** | Ingestion Orchestrator (extraction only) | Stack-fixed by ratified contract (Part 0); extraction-only role is a trust invariant | console.anthropic.com → API Keys → Create key; set a **monthly spend limit in the console before first scheduled run** (§14.3). Docs: https://docs.claude.com | `ANTHROPIC_API_KEY` | Step 6 |
| 4 | **OpenAI API (GPT-5.5)** | Independent Evaluator + Friction Agent | Contract requires a *non-Claude* grader (§0.2); already the reviewer of record for PR #9 | platform.openai.com → Settings → API keys → Create; set usage limit. Docs: https://platform.openai.com/docs | `OPENAI_API_KEY` | Before next trust-critical PR |
| 5 | **Google Gemini API** | Second evaluator lens (defect D5) | Third independent model family; free tier exists for review-sized workloads | aistudio.google.com → Get API key. Docs: https://ai.google.dev/gemini-api/docs | `GEMINI_API_KEY` | Optional, D5 |
| 6 | **Clerk (secret + publishable keys)** | Web + FastAPI auth layers | Already shipped & adversarially reviewed (PR #9: RS256 pinned, azp validated); switching auth now would reopen GAP 1 | dashboard.clerk.com → your app → API Keys (`pk_…`, `sk_…`); JWKS URL is public per instance. Docs: https://clerk.com/docs/backend-requests/manual-jwt | `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Step 8 |
| 7 | **Vercel token** | Deploy pipeline | First-party Next.js 15 App Router support; your monitoring Q2 baseline already assumes Vercel Analytics | vercel.com → Account Settings → Tokens → Create (scope: the project). Docs: https://vercel.com/docs/rest-api#authentication | `VERCEL_TOKEN` | Step 9 |
| 8 | **Sentry DSN** | Sentinel; web + API + worker SDKs | Open Q2 recommendation: wire now, not "before public launch" — the recurring loop (Step 5) is when silent failures begin; Next.js/FastAPI/Python SDKs first-party | sentry.io → Create project (one per surface) → DSN shown on setup. Docs: https://docs.sentry.io | `SENTRY_DSN` | Step 5 |
| 9 | **Healthchecks.io ping URL** | Sentinel dead-man switch on the scheduled orchestrator | A cron that dies silently violates the no-silent-degradation invariant; a ping-based dead-man switch is the standard fix; generous free tier | healthchecks.io → New check → copy ping URL. Docs: https://healthchecks.io/docs/ | `ORCHESTRATOR_PING_URL` | Step 5 |
| 10 | **markdown.new (Cloudflare)** | Ingestion Orchestrator, JS-heavy sources only | Your own pre-append directive: browser-render method for JS-heavy pages; keyless HTTP endpoint per your provided usage | None required per your provided invocation (`{"url":…, "method":"browser"}`) | — | Step 5/6 |
| 11 | **AWS IAM (S3)** | Tastemaker photo storage | Stack-fixed (Part 3); Phase 2 — do not mint yet | AWS Console → IAM → user with single-bucket policy → access key pair. Docs: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html | `AWS_ACCESS_KEY_ID`/`SECRET` | Phase 2 |
| 12 | **Stripe Connect** | Payments | Stack-fixed, Phase 3, and Open Q3 pending | dashboard.stripe.com → Developers → API keys | `STRIPE_SECRET_KEY` | Phase 3 |

**Key-handling rules (apply to all 12):** secrets live only in env (12-Factor Config: https://12factor.net/config, your §2.3/§4.13); never in repo, never in logs (§8.3); every key has a named owner-agent and a rotation note in `docs/KEYS.md`; agents never mint keys (§2 rule 5).

### Required comparison — scheduler hosting for the recurring orchestrator (Step 5)

| Dimension | A: GitHub Actions cron | B: Fly.io / Railway worker | C: Vercel Cron |
|---|---|---|---|
| **Speed** | Ships today (workflow file in repo) | Days (Dockerize, deploy, secrets) | Fast, but invokes HTTP functions, not the Python worker |
| **Accuracy** | Cron drift minutes-level; fine for hourly ingestion | Precise, long-running, resumable | Timeout-bounded serverless — wrong shape for a long pipeline |
| **Cost** | Free tier likely sufficient at 268 sources/day cadence (verify: https://docs.github.com/en/billing) | Small monthly fee (see https://fly.io/docs/about/pricing/) | Included with Vercel, but see accuracy |
| **Complexity** | Lowest — repo-native, secrets in Actions | Medium — new platform | Low, but forces a Python→HTTP refactor |
| **Maintenance** | Low; logs in Actions UI | Medium; another prod surface | Low |

**Recommendation: A now, revisit B when runs exceed job time limits or need mid-run resumability.** Reasoning: fastest path to Step 5 with zero new spend (founder-crucial rule 1 stays untriggered), and the dead-man switch (#9) covers Actions' silent-failure mode.

---

## §5 — 3 WAYS THIS COULD BE WRONG → VERIFIED → UPDATED
1. **"Anon key is safe to share" could be wrong.** Verified: the anon key is designed to be public *but* it exposes whatever RLS allows — your migration 0007 narrowed `event` public-read, and 11 tables are default-deny, so exposure = the three public tables only (https://supabase.com/docs/guides/api/api-keys). *Update:* Tier 1/Tier 2 split added in §1B so you choose exposure consciously.
2. **"GitHub Actions cron is sufficient" could be wrong** — job time limits and cron unreliability could break multi-hour ingestion over 268 sources. Verified: risk is real for long runs; *update:* the comparison names the promotion trigger to Fly.io (time-limit or resumability breach) instead of pretending A is permanent.
3. **"Friction Agent = adversarial gate" could be a misread of your intent** — you may have meant product-UX friction hunting (Option C). Verified: unresolvable from the message alone; *update:* framed as a formal gap with options per your protocol — confirmation is question G-F below, and I did not build further assumptions on top of it.

---

## §6 — LIMITATIONS
- Live verification remains blocked pending §1 credentials; all repo/DB facts are still MASTER-doc claims (§0.7).
- Pricing figures deliberately omitted — pointed at official pricing pages; every paid activation is founder-crucial anyway.
- Tool-choice rationales cite official docs; a per-tool full alternatives bake-off (e.g., Sentry vs. 4 rivals across 5 dimensions) can be produced on request, one table per tool.
