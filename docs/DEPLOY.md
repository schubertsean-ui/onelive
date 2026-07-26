# DEPLOY.md — the deployment configuration contract (single source of truth)

**This file is the ONLY place deployment/env-var guidance comes from.** If any
instruction to the founder about environment variables is not consistent with
this table, the instruction is wrong. (Origin: 2026-07-24 founder-Red catch —
repeated, inconsistent env-var advice made the founder redeploy to test. The
fix is this contract + the observable `/api/health` endpoint, not more chat.)

## The variables (name, where it's read, Sensitive-safe?)

The **runtime context** column is load-bearing: Next.js resolves env vars
DIFFERENTLY depending on where they're read, and Vercel's "Sensitive" flag hides
a value from the **build**. This is the asymmetry that caused the mistakes.

| Variable | Required? | Read in | Prefix | May be "Sensitive"? | Why |
|---|---|---|---|---|---|
| `NEXT_PUBLIC_AUTH_DISABLED` | For a preview: **yes** (or a Clerk key) | Edge **middleware** (build-inlined) | **`NEXT_PUBLIC_`** (required) | **NO — must be non-Sensitive** | Middleware runs on the edge; its env is inlined at BUILD. `NEXT_PUBLIC_` makes it build-visible; "Sensitive" hides it from the build → gate can't see it → 503. |
| `SUPABASE_URL` | **Yes** | **Server component** (runtime) | plain (no prefix) | **Yes — Sensitive is fine** | Read at request time in a server component; runtime env is injected then, so Sensitive is OK and no build-inlining is needed. |
| `SUPABASE_ANON_KEY` | **Yes** | Server component (runtime) | plain (no prefix) | Yes — Sensitive is fine | Same as above. Value = the Supabase **publishable** key (`sb_publishable_…`). |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Only for the real stealth gate | Middleware + client | `NEXT_PUBLIC_` | No (it's a public client id anyway) | Turns on the Clerk allowlist gate instead of the open-preview mode. |

Fallbacks the code accepts (so old setups keep working): auth also reads plain
`AUTH_DISABLED`; Supabase also reads `NEXT_PUBLIC_SUPABASE_URL` /
`NEXT_PUBLIC_SUPABASE_ANON_KEY`. **Prefer the table above** — the fallbacks are
compatibility only.

## The rule of thumb

- **Reaches the edge gate (middleware) → `NEXT_PUBLIC_`, never Sensitive.**
- **Read server-side at request time (the feed) → plain name, Sensitive is fine.**

## Two supported deployments

1. **Private preview (today) — ZERO CONFIG.** A Vercel preview/development
   deployment needs **no environment variables at all**: the auth gate
   auto-opens on `VERCEL_ENV=preview|development` (host-protected by Vercel), and
   the Supabase read uses the committed **public** default. Privacy comes from
   Vercel Deployment Protection; ops (`/ops`) stays denied regardless. **Amended
   2026-07-26, and VERIFIED rather than asserted:** a *Protection Bypass for
   Automation* secret now exists for this project and is stored as the repository
   secret `VERCEL_AUTOMATION_BYPASS`. Evidence — `site-health` run
   <https://github.com/schubertsean-ui/onelive/actions/runs/30217359539> printed
   `protection_bypass_secret: present`, `http_status: 200` and `event_count: 1532`.
   `docs/V1.md` ask 6 is therefore RESOLVED, not open; if any other document still
   says that secret must be created, that document is stale and this line wins (the
   reason this file exists).

   **The boundary of that evidence, because this file is where people come for the
   truth about config.** It proves the secret works in its **header** form and that
   `/api/health` serves with 1,532 events. It does **not** prove the
   query-parameter link form opens `/tonight` — that run predates the
   product-surface and friend-link checks now in `site_health.yml`, which are
   default-branch-only for secret custody and so first run on merge (R-077). Until
   then the friend link is the documented form, not a measured fact.

   Privacy rests on possession of the bypass URL rather
   than on Vercel's login wall. `/ops` is still denied on that code path regardless,
   and the real boundary remains row-level security, never URL secrecy. Setting
   `NEXT_PUBLIC_AUTH_DISABLED=1` still works but is no longer required — and note
   that a Clerk publishable key OVERRIDES it (`/api/health` now says so explicitly
   via `overriddenDisableFlag`).
2. **Stealth gate (before public launch):** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   + Clerk secret + `ONELIVE_ALLOWLIST` (+ optionally override the Supabase vars
   for a different project). PRODUCTION never auto-opens — with no provider and
   no explicit disable it FAILS CLOSED (denies), so a real gate is required.

Note: the two Supabase values are committed as PUBLIC defaults (publishable key
+ URL — safe by design, RLS is the boundary), so data works with no config;
any env var overrides them. A real secret is never committed.

## The console links — never reconstruct these from memory

Founder directive 2026-07-26: *"Always give me specific and accurate and working
links (it gets me where its supposed to)."* Every founder-facing step that involves
a web page carries its URL from this table. **Keep this table current; it is the
reason a session never has to guess a slug.**

| What | Link | Slug confirmed by |
|---|---|---|
| Vercel project | <https://vercel.com/sss-projects-e4775771/onelive> | Vercel's own PR bot comment on #76 |
| **Deployment Protection** (lets friends in) | <https://vercel.com/sss-projects-e4775771/onelive/settings/deployment-protection> | project link above + Vercel's documented settings path |
| Vercel env vars | <https://vercel.com/sss-projects-e4775771/onelive/settings/environment-variables> | same |
| Vercel deployments list | <https://vercel.com/sss-projects-e4775771/onelive/deployments> | same |
| **New GitHub Actions secret** | <https://github.com/schubertsean-ui/onelive/settings/secrets/actions/new> | repo `html_url` from the GitHub API |
| GitHub Actions secrets list | <https://github.com/schubertsean-ui/onelive/settings/secrets/actions> | same |
| `site-health` runs | <https://github.com/schubertsean-ui/onelive/actions/workflows/site_health.yml> | workflow file path |
| `import-licensed` runs | <https://github.com/schubertsean-ui/onelive/actions/workflows/import_licensed.yml> | same |
| `experience-metrics` runs (Lighthouse + axe) | <https://github.com/schubertsean-ui/onelive/actions/workflows/experience_metrics.yml> | workflow file path |
| Anthropic usage cap (ask 2) | <https://console.anthropic.com/settings/limits> | Anthropic console, documented path |
| Supabase project | <https://supabase.com/dashboard/project/vqipjlvzfiwnandjumvx> | project ref in `CLAUDE.md` + `web/lib/licensed.ts` |

**The honest limit on these, stated rather than hidden.** An agent session **cannot
fetch any of them to prove they resolve** — the network policy denies
`vercel.com` outright and returns 403 for `github.com` settings pages and
`console.anthropic.com` (all three verified 2026-07-26). Even with egress, an
unauthenticated request to a private settings page returns 404, so a green
status-code check would prove nothing anyway. So the **slugs** are taken from
authoritative sources — Vercel's own bot comment, the GitHub API's `html_url`, the
project ref in canon — and the **paths** are the providers' documented shapes.
A link that turns out to be wrong is a finding: fix this table in the same change,
because the next session will copy from here.

## Verify without guessing — `/api/health`

`GET /api/health` is **always reachable** (even in the fail-closed state) and
returns the resolved config WITHOUT any secret value:

```
{ ok, auth:{mode, disabledBy, overriddenDisableFlag}, supabase:{configured, source, reachable, eventCount}, vercelEnv }
```

- `auth.mode:"unconfigured"` → the gate flag isn't being read → fix per row 1.
- `supabase.reachable:false` → the DB vars aren't resolving → fix per rows 2–3.
- `ok:true` and `eventCount>0` → the whole path works; the feed will render.
- `auth.disabledBy` is **null unless the gate is actually open**, and names
  `VERCEL_ENV=preview` when a preview opened itself with no flag. It used to report
  any disable flag that was merely *set*, which produced the self-contradicting
  payload `{"mode":"clerk","disabledBy":"NEXT_PUBLIC_AUTH_DISABLED"}` on a live
  deployment (R-071).
- `auth.overriddenDisableFlag` appears **only** when a disable flag is set and a
  Clerk publishable key beat it. If a preview will not open and you set the flag,
  this is the field that tells you why.

**Always check `/api/health` before advising a config change.** Diagnose from
what the app actually resolved, never from how the platform is assumed to behave.

## Agent process rules (binding)

1. **All env/deploy guidance comes from this file.** No ad-hoc instructions.
2. **Never advise removing a fail-safe** (e.g. "you can delete the auth flag")
   unless this file's supported-deployments section says to, in the same breath
   as what replaces it. A revert that re-requires a deleted flag is the exact
   trap that fired on 2026-07-24.
3. **Any change to auth/gate or config resolution updates this file in the same
   commit**, and keeps `/api/health` truthful. Covered by `tests/`/web tests.
