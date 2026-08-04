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
| `CLERK_SECRET_KEY` | With the stealth gate | Middleware (server) | plain | Yes — Sensitive is fine | Clerk's server secret (`sk_…`); the SDK reads this name by default. Verifies the session server-side. |
| `ONELIVE_ALLOWLIST` | With the stealth gate | Edge **middleware** (build-inlined) | plain | **NO — must be non-Sensitive** | Comma-separated tester emails (lowercased/trimmed, case-insensitive; empty ⇒ denies everyone, fail-closed — `web/lib/allowlist.ts`). Read by the edge gate, so like row 1 it must be build-visible; **redeploy to apply a change**. |
| `ONELIVE_CONSUMER_PUBLIC` | For deployment 3 below | Edge **middleware** (build-inlined) | plain (or `NEXT_PUBLIC_` form) | **NO — must be non-Sensitive** | Declares the CONSUMER surface public while `/ops` keeps the full Clerk + allowlist gate. Honored **only** when the Clerk key is also set — without a provider the flag changes nothing (`web/lib/auth.ts` `consumerSurfacePublic`). |

Fallbacks the code accepts (so old setups keep working): auth also reads plain
`AUTH_DISABLED`; Supabase also reads `NEXT_PUBLIC_SUPABASE_URL` /
`NEXT_PUBLIC_SUPABASE_ANON_KEY`. **Prefer the table above** — the fallbacks are
compatibility only.

## The rule of thumb

- **Reaches the edge gate (middleware) → `NEXT_PUBLIC_`, never Sensitive.**
- **Read server-side at request time (the feed) → plain name, Sensitive is fine.**

## Three supported deployments

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
3. **Public site + gated ops (the live posture, 2026-08-04):** everything from
   deployment 2 **plus** `ONELIVE_CONSUMER_PUBLIC=1`. The consumer surface
   (feed, detail, API) is public with no sign-in; `/ops` runs the full Clerk
   sign-in → allowlist gate. Why this exists: the go-live "declared public"
   posture (plain `NEXT_PUBLIC_AUTH_DISABLED`, no provider) hides `/ops` behind
   a 404 by design — no provider exists to gate it — which locked the founder
   out of the promote console on the live site (founder-caught 2026-08-04).
   Set ALL FOUR variables in the same change, then redeploy ONCE: adding the
   Clerk key without the declaration flips the whole site behind sign-in
   (deployment 2's behavior), and the declaration without the key is inert.
   `NEXT_PUBLIC_AUTH_DISABLED` becomes irrelevant once the Clerk key is present
   (a provider always beats the disable flag) — remove it to avoid confusion.

Note: the two Supabase values are committed as PUBLIC defaults (publishable key
+ URL — safe by design, RLS is the boundary), so data works with no config;
any env var overrides them. A real secret is never committed.

## Custom domain

The founder owns **`1live.co`** (registered at **GoDaddy**). It is the intended
public address, pointed at the Vercel **Production** deployment.

- Add `1live.co` + `www.1live.co` in Vercel → Settings → Domains; put the exact
  DNS records Vercel shows into GoDaddy DNS (A record for the apex, CNAME for
  `www`). Canonical: `1live.co`, with `www` redirecting to it.
- Because it maps to **Production**, the domain shows the **stealth gate** (the
  fail-closed default), NOT the open preview — so the Clerk gate + allowlist must
  be configured before testers visit, or they hit `/access`. Full ordered
  runbook: `docs/ops/GO_LIVE_TESTERS_CHECKLIST.md`.

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
