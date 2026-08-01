# ONE LIVE — Web Harvest & Subscribe Ingestion — Spec v1

**Status:** PROPOSAL — the *passive* half is buildable now (free, no founder decision);
the *active-subscription* half is **founder-crucial** (new service · a receiving domain · a
public subscribing identity · legal posture). Founder directive 2026-08-01: *"get really good
at searching and finding and pulling data from websites, Linktree, etc. … a serious plan and
capability to sign up for newsletters, blogs, fan clubs, etc."*

**Why this matters (the moat):** the differentiated, long-tail announcements — a neighborhood
lecture, a local band's one-off, a venue's recurring night — often **never hit a public
calendar or a big platform.** They live on the entity's own pages and go out through its own
**newsletter/blog/socials.** Getting them is the "how are they even getting this?" advantage.

**The invariant that makes it safe:** every signal here is a **weak sensor feeding the
corroboration gate** — it becomes a candidate with provenance + confidence and passes the
normal extraction → gate → promote path. **AI never publishes directly**, and this capability
does not change that.

---

## §1 · Two halves, very different risk

| Half | What | Risk | Founder decision? |
|---|---|---|---|
| **A. Passive extraction** | Read what entities *publish for machines* on their own pages — JSON-LD, `sameAs`, feeds, oEmbed, site-hosted embeds, Linktree/bio-hub links | **Low** (public, first-party) | **No** — build now |
| **B. Active subscription** | *Subscribe* to newsletters/blogs to catch announcements not on any calendar | **Low legally, but needs infra + identity** | **Yes** — §5 |

Explicitly **out of scope** (legal/ethics — §4): creating accounts, paying for fan clubs,
scraping Instagram/TikTok beyond the single public bio link, and scraping Discord/Patreon
(ToS-banned, enforced). We **subscribe transparently as OneLive** and **honor every
unsubscribe.**

---

## §2 · Passive extraction (Half A — buildable now, free)

Preferred over scraping wherever a machine-readable path exists:

1. **First-party structured data** — `worker/enrich/first_party.py` (built): JSON-LD
   (`Event`/`MusicGroup`/`Person`/`VideoObject`), `sameAs` official channels, own-domain
   `og:image`, RSS/Atom/JSON-feed + oEmbed + WebSub-hub autodiscovery, site-hosted
   YouTube/Spotify/Vimeo embeds.
2. **Link-hub resolver** — Linktree/Beacons/Substack bio pages: the outbound links are in the
   page's own HTML/JSON; `classify_link()` sorts them into pathway kinds
   (`link_hub`/`newsletter`/`streaming`/`ticketing`/`social`/`own_site`), resolving an entity
   to its **own calendar + newsletter + socials** — the highest-authority targets.
3. **RSS / Atom / JSON Feed + WebSub** — the clean, ToS-friendly path for blogs/Substack.
   Autodiscover the feed; where a `<link rel="hub">` is advertised, **subscribe for push**
   (WebSub) instead of polling. Free; near-zero legal risk (feeds exist *for* machines).
4. **schema.org `Event` JSON-LD** on venue/first-party pages — deterministic event facts
   (name/date/venue/offers), no LLM, no hallucination surface.

**Legal policy (all of Half A):** public no-login pages only; obey `robots.txt` per host; send
a **truthful identifying User-Agent with a contact URL**; self-rate-limit + cache; honor
`429`/`Retry-After` and machine-readable opt-outs; never defeat auth/anti-bot (a CAPTCHA/paywall
is a "no"); extract **facts** (dates/venues — not copyrightable), never republish prose bodies.
Grounded in *hiQ v. LinkedIn* (public data ≠ CFAA breach; **fake accounts + ToS breach are the
losing side**) and RFC 9309.

---

## §3 · Active subscription (Half B — the new capability)

### Inbound email pipeline (recommended: Cloudflare Email Routing — free)
Register a receiving subdomain (e.g. `ingest.1live.co`), point its MX at the inbound service,
use a **catch-all / plus-addressing** so each subscription gets a unique address
(`signups+<source-id>@ingest.1live.co`) for clean provenance + per-source unsubscribe. Each
inbound message is **parsed at the first hop** (MIME/HTML → text via PostalMime) and POSTed to a
webhook that runs the event extractor.

Service options: **Cloudflare Email Routing + Email Workers — FREE, catch-all, programmable**
(recommended); **AWS SES inbound** ($0.10/1k) at scale; SendGrid/Postmark/Mailgun (turnkey but
paid). Deliverability note: parse at the first hop (don't forward into Gmail — breaks SPF/DMARC
and gets silently spam-filed); publish SPF/DKIM/DMARC on the ingest domain; **handle
double-opt-in** by clicking the confirmation link legitimately.

### Subscribing — legality & ethics
- Signing up to *receive* email is legal for the recipient (**CAN-SPAM binds senders, not
  subscribers**; you gain the *right* to unsubscribe, which senders must honor).
- **Subscribe with a real, disclosed identity** — never impersonate a fan, never fake names;
  obey CAPTCHAs/anti-bot as a "no"; **honor every unsubscribe immediately**, including
  auto-unsubscribing dropped sources; store minimal PII.
- **Blogs → RSS/WebSub** (above) is the clean path; email is for newsletter-only announcements.

### Fan clubs / gated communities
Only the **free/public tier** or an **admin-invited official bot** (e.g. a venue adds a Discord
bot). **No** account creation, **no** pay-to-extract, **no** self-bots (Discord/Patreon ToS ban
scraping and enforce it).

---

## §4 · Extracting events from prose (newsletter/blog/social text)

1. **Structured signals first** — a schema.org `Event` or clean RSS item is parsed
   deterministically; the LLM is used only on genuine free prose.
2. **Schema-constrained output** — every event is a typed object (act/date/venue/city/ticket/
   price), format-validated.
3. **Span-grounded provenance (the core hallucination guard)** — each extracted field must cite
   the **verbatim source span** it came from; a field the model can't ground is **dropped, not
   guessed.**
4. **Per-field confidence → the 4-state model** — a single uncorroborated newsletter mention →
   `unverified`; matched against a second source (venue calendar / ticketing) →
   `likely`/`confirmed`; conflicting → `disputed` (shown, never hidden).
5. **Relative dates** ("this Friday") are resolved against the message's received-date passed in
   as an explicit anchor — the model never invents a calendar date.
6. Everything lands as a **candidate with full provenance** (source URL/message-id, quoted
   spans, model + prompt_version) and passes the corroboration gate. Routed cheap-tier-first per
   `docs/MODEL_ROUTING.md`; governed by the existing extraction spend cap.

---

## §5 · Guardrails (hard rules — non-negotiable)

1. First-party preferred; resolve to and prefer the entity's own property.
2. Public, no-login only — never create accounts, never defeat auth/anti-bot.
3. `robots.txt` + honest identifying User-Agent + contact URL; self-rate-limit; cache; honor opt-outs.
4. ToS-respecting — no scraping where ToS bans it and the platform enforces (IG/TikTok beyond the
   one bio link, Discord, Patreon gated). Prefer official APIs / admin-invited bots / RSS.
5. **Transparent subscriber identity**; never impersonate; real monitored reply-to.
6. **Honor unsubscribe** always and immediately; double-opt-in clicked legitimately.
7. No payment misrepresentation; no pay-to-extract; free/public tiers only.
8. PII-minimal — extract event facts, not personal data; never republish copyrighted prose.
9. **Provenance on everything; gate everything.** AI never publishes.
10. EU-aware if EU personal data is ever touched (legitimate-interest basis + EDPB guidelines).

---

## §6 · Founder decisions (the consolidated ask)

Everything in Half A the agent builds and gates. Half B needs, per the charter's escalation
list (new service / spend / legal / identity):

1. **The inbound-email service + a receiving domain.** Recommend **Cloudflare Email Routing
   (free)** on a subdomain like **`ingest.1live.co`**. → *You point that subdomain's mail at
   Cloudflare; the agent wires the parser + candidate extractor.*
2. **The disclosed subscribing identity** — the address/name OneLive subscribes *as* (e.g.
   `announcements@1live.co`), a short public **"who we are / opt your newsletter out"** page, and
   a **real inbox a human watches** for replies. A trust/legal-posture decision, not the agent's.
3. **Confirm out-of-scope** — no automated account creation, no paid fan clubs (recommended;
   revisit only as a deliberate later escalation).

**Recommendation:** approve (1) with Cloudflare + an `ingest.` subdomain and (2) with a
`1live.co` identity + a one-paragraph public opt-out page; hold (3) as out-of-scope. That stands
up the newsletter capability at **zero marginal cost** and full legal/ethical cover.

---

## §7 · Build sequence

- **Phase H1 (free, no decision):** first-party extractor (`worker/enrich/first_party.py`,
  built) → RSS/Atom/JSON-feed ingestion + autodiscovery + WebSub push → link-hub resolver wired
  into source discovery. All feed the gate.
- **Phase H2 (after §6 decisions):** inbound-email pipeline (catch-all domain → parse → webhook
  → candidate extractor), transparent subscribe flow (disclosed identity, double-opt-in click,
  unsubscribe hygiene).
- **Phase H3:** the span-grounded LLM prose extractor for genuine free text (metered, gated).
- Every phase: robots/ToS-respecting, provenance + per-field confidence, no pay-to-rank,
  measured by the analytics canon's coverage/depth metrics.

---

## Appendix · Method sources (research 2026-08-01)
hiQ v. LinkedIn / CFAA (public data ≠ breach; fake-accounts + ToS = liability); RFC 9309
robots.txt; EDPB web-scraping guidelines (EU); Cloudflare Email Routing + Email Workers +
PostalMime (free inbound); AWS SES inbound pricing; CAN-SPAM (binds senders, not recipients) +
double-opt-in; RSS/Atom autodiscovery + WebSub (W3C); Discord/Patreon anti-scraping ToS;
span-grounded provenance as the hallucination guard for prose extraction; schema.org `Event`.
Grounds on OneLive assets: `worker/enrich/first_party.py`, the source pathway kinds
(`link_hub`/`social`/`email_opt_in`), the `email_opt_in` anchor class, and the 4-state
confidence model.
