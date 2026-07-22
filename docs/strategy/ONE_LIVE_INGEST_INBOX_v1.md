# ONE LIVE — Ingest Inbox v1: newsletters, fan clubs, and direct feeds at scale (PROPOSAL)

Greppable summary: founder-directed 2026-07-22 ("Spec all 3… Provide the
world class options in terms of how best to have email inbox(s) set up to
manage the potentially massive volume of artists, venues, and the like").
Design for a founder-owned email ingestion channel: how agents subscribe,
how mail becomes pipeline input, and how the system stays governable at
10 subscriptions or 100,000. STATUS: PROPOSAL. Po battery run seed
20260723 word "windmill" (harvest H1–H10 in
ONE_LIVE_SIGNAL_ACQUISITION_PO_NOTES; H1/H3/H4 land here). New service +
domain custody = founder-crucial at build.

## The shape of the problem

Venue and artist newsletters are the densest willingly-given event signal
that exists — a weekly email IS a structured lineup announcement. But
email at scale is not a mailbox problem; it is a ROUTING problem. A
folder full of 40,000 newsletters is a liability; 40,000 messages that
each arrive pre-bound to a known source and flow into the same
fetch→extract→gate path as a web page is an asset.

## Options considered (why-this-not-that)

### Option A — a plain hosted mailbox (Google Workspace + Gmail API)
One `sources@onelive.___` inbox, agents poll the Gmail API.
- For: 30-minute setup; familiar; ~$7/mo.
- Against: one address means every subscription lands unbound — sender
  classification becomes an inference problem we created for ourselves;
  API quotas and label gymnastics at volume; mailbox retention becomes an
  accidental database. Fine for a 20-newsletter pilot, wrong at scale.

### Option B — inbound email routing to code (RECOMMENDED)
Email Routing on a founder-owned domain (Cloudflare Email Routing +
Workers is the reference implementation — routing is free; alternatives
with the same shape: Postmark Inbound, Mailgun Routes, SendGrid Inbound
Parse). Every message arrives as an HTTPS event to our code; no mailbox
exists at all.

The world-class detail is **one address per subscription**
(plus-addressing or subdomain catch-all):

    sub+<source_id>@in.onelive.___

- Every newsletter self-identifies by the address it was SENT TO — the
  binding to a catalog source is by envelope, not by guessing from
  sender fields a spammer can forge.
- A leaked/sold address is instantly attributable AND instantly
  revocable (kill one address, not the channel).
- Volume is a queue-depth number, not a mailbox size: receive → verify
  SPF/DKIM/DMARC results → strip to text/HTML → store as a raw_fetch row
  (source_id from the address, content-hash dedup) → the EXISTING
  extraction→gate3→candidate path takes over unchanged. The pipeline
  cannot tell a newsletter from a fetched web page, which is the point.
- Cost: ~$0 at pilot; pennies per 10k messages at scale.

### Option C — self-hosted mail server
Discarded: deliverability and ops burden are a full-time job that buys
nothing over Option B.

## Governance (the part that makes it OneLive)

1. **Founder owns the identity surface**: the domain, the routing
   account, and the decision to stand them up (new service =
   founder-crucial). Agents never mint any of it.
2. **Subscription registry, auditable**: every signup an agent performs
   is a row — source_id, address minted, form URL, timestamp, consent
   text seen. Nothing is subscribed to silently. The registry IS the
   subscription lifecycle: per-sender yield tracking (events produced
   per message) feeds the same least-recently-attempted /
   yield-weighted rotation logic as web sources; a subscription that
   never yields gets unsubscribed, logged (po H1).
3. **Receive-only, forever**: ingest addresses never send (no replies,
   no auto-responses beyond list-unsubscribe handling). One narrow
   future exception, separately gated: reply-to-claim (po H3) — a venue
   replying "this is us" to bootstrap the claimed channel — is a P2
   product feature with its own consent design, not part of this spec.
4. **Same trust physics**: an email is raw text with provenance
   (source_id + verified sender domain + received_at). It earns
   candidate status through the same gate as everything else; a
   newsletter making a claim is one source, not truth.
5. **Legal hygiene**: subscriptions are to PUBLIC lists using our own
   address; we honor unsubscribe; CAN-SPAM/GDPR obligations sit on the
   SENDER for their list — our obligations are storage minimization
   (strip tracking pixels, don't store remote assets) and honoring our
   own data map (§13).

## Build shape (when ratified)

Phase 1 (pilot, ~1 day of build): domain + routing + one Worker → queue
→ `worker/email_ingest.py` adapter emitting raw_fetch rows; registry
table + migration; subscribe the top ~25 Austin venue newsletters by
hand-curated list; watch yield for two weeks.
Phase 2: agent-performed signups from the source catalog (logged), the
yield lifecycle, sender-reputation dashboard in /ops.
Phase 3: fan clubs / artist mailing lists (higher churn, lower density —
earn their place by pilot data), reply-to-claim design.

## Founder decisions this spec needs

1. Ratify Option B and name the domain (subdomain `in.` of the product
   domain, or a dedicated utility domain).
2. Stand up the routing account (Cloudflare account you own; ~15 min).
3. Approve the pilot list scope (top ~25 Austin venue newsletters).
