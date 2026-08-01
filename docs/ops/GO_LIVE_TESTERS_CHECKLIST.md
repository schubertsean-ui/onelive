# GO-LIVE (testers) — one-sitting checklist

**Goal:** put OneLive behind a controlled allowlist at **www.1live.co / 1live.co**
so named testers can sign in and give feedback, and no one else gets in.

This is a founder runbook. Env-var details defer to **`docs/DEPLOY.md`** (the
single source of truth); this file is the ordered click-path. Do the steps in
order — the gate must exist **before** the domain points at it, or an early
visitor hits the "access denied" screen.

Order: **Clerk keys → Vercel env → allowlist → domain → verify.**

---

## A. Clerk keys (sign-in provider)

1. Go to https://dashboard.clerk.com → **Create application** (name it `OneLive`).
2. Under **sign-in methods**, the simplest for testers is **Email verification
   code / magic link** (passwordless — no password to manage).
3. Open **API keys** and copy the two values:
   - **Publishable key** — starts `pk_…`
   - **Secret key** — starts `sk_…`
4. *(Only if you'll run the gate on the custom domain with a Clerk **Production**
   instance):* Clerk will show a short list of **DNS records** (e.g.
   `clerk.1live.co`, `accounts.1live.co`). You'll add those in GoDaddy in step D
   alongside the Vercel records. For a first tester round you can skip this and
   use Clerk's default keys.

## B. Vercel environment variables

In Vercel → project **onelive** → **Settings → Environment Variables**
(https://vercel.com/sss-projects-e4775771/onelive/settings/environment-variables),
add these to **Production** (and Preview if you want the same gate there):

| Name | Value | Sensitive? |
|---|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | your `pk_…` | **No** (must be build-visible) |
| `CLERK_SECRET_KEY` | your `sk_…` | Yes is fine |
| `ONELIVE_ALLOWLIST` | tester emails, comma-separated (see C) | **No** (read by the edge gate) |

> Why the Sensitive flags matter: the gate runs in **edge middleware**, whose env
> is resolved at **build**. A value marked "Sensitive" is hidden from the build,
> so a Sensitive `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`/`ONELIVE_ALLOWLIST` would
> make the gate misbehave. Keep those two **non-Sensitive**. (DEPLOY.md, rows 1
> & the gate rows.)

## C. The allowlist

`ONELIVE_ALLOWLIST` is a **comma-separated list of the exact tester email
addresses** — for example:

```
alice@example.com, bob@work.com, carol@gmail.com
```

- Matching is **case-insensitive**, whitespace-trimmed. A person must sign in
  with an email **on this list** to get past the gate.
- **Fail-closed:** an empty/unset allowlist matches **nobody** (a misconfigured
  gate denies everyone rather than opening to all — by design).
- **To add/remove a tester later:** edit this value, then **Redeploy** (the gate
  reads it at build, so a redeploy makes the change take effect).

## D. Point the domain (GoDaddy → Vercel)

1. Vercel → onelive → **Settings → Domains**
   (https://vercel.com/sss-projects-e4775771/onelive/settings/domains). Add
   **`1live.co`** and **`www.1live.co`**. Pick which is canonical — recommend
   **`1live.co`** with `www` redirecting to it.
2. Vercel shows the **exact DNS records** to create — copy them, don't guess.
   Typically: an **A record** for `1live.co` → the IP Vercel shows, and a
   **CNAME** for `www` → the value Vercel shows.
3. In **GoDaddy → your domain → DNS / Manage DNS**, add those records exactly.
   *(If you set up a Clerk Production instance in A.4, add Clerk's CNAMEs here
   too.)*
4. Back in Vercel, wait for it to verify; HTTPS is issued automatically.

## E. Verify (no guessing)

1. Open **https://1live.co/api/health** — you want:
   - `auth.mode: "clerk"` (the gate is on),
   - `supabase.reachable: true` and `eventCount > 0` (real data flows).
   If `auth.mode` is `"unconfigured"`, the Clerk key isn't being read → recheck B.
2. Open **https://1live.co** in a private window:
   - An **allowlisted** email → signs in → sees the feed. ✅
   - A **non-allowlisted** email → lands on the branded **/access** screen. ✅
3. Tell me when it's live and I'll confirm the whole path end-to-end via
   `/api/health` and a gate check.

---

## Rollback / safety notes

- The gate is **fail-closed**: if anything is misconfigured, it denies — it never
  accidentally opens to the public. That's the safe failure direction.
- To pause access entirely: clear `ONELIVE_ALLOWLIST` (or remove the Clerk keys)
  and redeploy — everyone is denied until you restore it.
- `GET /api/health` is always reachable and never returns a secret value — use it
  to diagnose, per DEPLOY.md.
