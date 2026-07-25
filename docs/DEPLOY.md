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
   Vercel Deployment Protection; ops (`/ops`) stays denied regardless. Setting
   `NEXT_PUBLIC_AUTH_DISABLED=1` still works but is no longer required.
2. **Stealth gate (before public launch):** `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   + Clerk secret + `ONELIVE_ALLOWLIST` (+ optionally override the Supabase vars
   for a different project). PRODUCTION never auto-opens — with no provider and
   no explicit disable it FAILS CLOSED (denies), so a real gate is required.

Note: the two Supabase values are committed as PUBLIC defaults (publishable key
+ URL — safe by design, RLS is the boundary), so data works with no config;
any env var overrides them. A real secret is never committed.

## Verify without guessing — `/api/health`

`GET /api/health` is **always reachable** (even in the fail-closed state) and
returns the resolved config WITHOUT any secret value:

```
{ ok, auth:{mode, disabledBy}, supabase:{configured, source, reachable, eventCount}, vercelEnv }
```

- `auth.mode:"unconfigured"` → the gate flag isn't being read → fix per row 1.
- `supabase.reachable:false` → the DB vars aren't resolving → fix per rows 2–3.
- `ok:true` and `eventCount>0` → the whole path works; the feed will render.

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
