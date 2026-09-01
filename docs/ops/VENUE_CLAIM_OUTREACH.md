# Venue claim outreach — the message a human sends a closed door

Coverage Law calls a login, paywall, or bot wall a **class D** source and gives
exactly one lawful response: *do not fetch; open a claim/submit path instead.*
`docs/CLASS_D_CLAIM_QUEUE.md` is the list of doors. This file is what a person
says when they knock, and `/ops/claim` is where the answer gets recorded.

No tool in this repo sends this. A human sends it, from their own mailbox, to a
person. That is the point: the door opens because someone was asked, not because
something got around it.

---

## The message

> **Subject: Your listings on 1Live — a feed, a spreadsheet, or a forwarded email**
>
> Hi — I'm building 1Live, a listings guide that shows people what's happening
> tonight and says plainly where each listing came from.
>
> We only read sources that are open to read. Yours sits behind a login or a
> partner agreement, so we don't touch it — no scraping, no account, no
> workaround. That means the only way your events show up is if you hand them
> to us, and it's your call whether you do.
>
> If you want in, any one of these works, whichever is least effort for you:
>
> 1. **Send a calendar feed link** — the .ics or public calendar address you
>    already publish. Nothing to maintain; we read it as you update it.
> 2. **Send a spreadsheet** — a CSV with columns `title` and `start` (optional:
>    `end`, `venue`, `city`, `url`). Good for a one-off season or a run of dates.
> 3. **Forward the listings** — just email them to **events@1live.co** the way
>    you'd send them to anyone else.
>
> What happens on our end: your listings are recorded as **unverified** until we
> confirm you're the one who sent them, and nothing about you is published on
> your say-so alone. You can ask us to stop at any time and we'll drop the feed.
> We never charge for placement and there's no way to pay for a better spot.
>
> If you'd rather we didn't list you at all, say so and we won't.
>
> — [name], 1Live

Keep it to that. Do not promise traffic, ranking, a launch date, or a feature
they haven't seen — copy asserts only what the product already does.

---

## Three doors to use it on

Straight from `docs/CLASS_D_CLAIM_QUEUE.md` — one of each shape, so the message
gets tested against all three reasons a door is shut:

| source | why it's class D | what to ask for |
| --- | --- | --- |
| **DICE** (<https://dice.fm/>) | `access_method 'partner_preferred'` — a partnership or nothing; no public URL to read | Ask specifically whether they can expose a **public ICS or a nightly CSV drop**. That needs no partnership at all, so it routes around the slowest part of their process rather than joining the queue for it. |
| **Eventbrite API** (<https://www.eventbrite.com/platform/api>) | `access_method 'oauth_api'` — needs a credential we will not mint on our own | Same ask, aimed past the API: an organizer's **public event page feed or an ICS export**. Minting an API credential is founder-crucial; an exported feed is not. |
| **Bing Search (Benchmark Only)** (<https://www.bing.com/>) | `explicitly_disallowed` contains `automated_ingest` — the source forbids it in writing | Ask **in writing** for explicit feed permission or a first-party export. If they decline, the source stays out of the catalog and that is the end of it. A written "no" is a fine outcome; the unacceptable one is reading it anyway. |

---

## Recording the answer

When they reply, an operator opens **`/ops/claim`** and records it:

1. **Venue / organizer name** — what the listings attach to.
2. **Who is handing this over** — the organizer themselves → **class E**;
   someone reporting on their behalf → **class F**. Nothing else picks the class.
3. **How the listings reach us** — feed URL, CSV, or the email address.
4. Submit. The receipt names the class, the confidence, and how many listings
   landed.

What the form will not let anyone do, by construction (`worker/claim/intake.py`):

- **Set the confidence.** Every claim is recorded `unverified`. A claim is an
  assertion of ownership, not proof of one.
- **Reach the anchor tier.** Claims are written in classes `worker/gating.py`
  names third-party, so the listings HOLD at the existing gate until a person
  verifies the claimant. The verified classes (`claimed_upload`, `email_opt_in`)
  promote on one source; an unverified claim must never inherit that, or the
  form becomes a way to publish as any venue.
- **Carry a login through the door.** A pasted sign-in URL is refused, and so is
  a URL with `user:password@` in it. A private-but-unguessable feed address the
  owner chose to give us is fine — that is a handover, not a bypass.
- **Half-record a calendar.** One unreadable CSV row refuses the whole file. A
  venue believing their listings are in when half of them are is worse than a
  clean rejection.
