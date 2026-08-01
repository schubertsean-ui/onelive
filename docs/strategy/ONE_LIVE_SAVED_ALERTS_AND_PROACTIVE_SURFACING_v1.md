# ONE LIVE — Saved Alerts & Proactive Surfacing — Spec v1

**Status:** PROPOSAL (founder-directed, 2026-08-01). PROPOSAL ≠ license to build. Founder directive
(verbatim, distilled from the 2026-08-01 thread): people should be able to *save* "searches or
listings or events or genres or categories or subgenre/category and be auto-texted when a new event
shows up," and this proactive surfacing "would be world class in terms of helping us grow fast."

**One-line thesis.** The app **proactively brings the right _verified_ thing to the user** — instead
of the user hunting for it. A user saves *any* axis; when a **gate-verified** event later matches, we
notify them. It is simultaneously our **retention engine** and our **demand-sensing engine**.

**Why it's differentiated (not "just another undifferentiated ticketing alert").** The payoff is
**verified**. "Follow this and we'll surface the next one" is a commodity when the next one is
unfiltered noise; it's a moat when the next one passed the trust gate. Same loop, trust-first.

---

## §1 · What you can save (save-any-axis)

A saved alert is a **standing query** over any one — or a combination — of these axes:

| Axis | Example saved alert |
|---|---|
| **Free-text search** | "cumbia in South Austin" |
| **Venue / space** | Antone's · the Paramount · a specific gallery |
| **Artist / series / organizer** | a band · a recurring lecture series · a comedy night |
| **Genre → subgenre** | Live music → Tejano; Ideas → philosophy talks |
| **Category → subcategory** | Comedy → improv; Literary → poetry readings |
| **Area / geo** | a neighborhood, a city, "near me tonight" |
| **Vibe / feel** | (via the Emotion/Vibe layer) "high-energy," "quiet & intimate" |
| **Price / access** | free events; all-ages; wheelchair-accessible |

Saving is **frictionless by design** (the automagical-nav principle, PR #112): a saved alert is
created from *whatever the user is already looking at* — a one-tap "save this search / follow this
venue / notify me for this genre" on the surface itself, never a separate form to fill in.

---

## §2 · The trigger: verified-only notification

1. A new candidate flows through the normal pipeline (extraction → gate → promote).
2. **Only when it PROMOTES to a verified/canonical event** does it become eligible to fire a saved
   alert. An `unverified` candidate never fires an alert — proactive push is a **stronger** claim than
   passive display, so it holds to the stronger bar.
3. A **`disputed`** event MAY fire (disputed is shown-never-hidden), but the notification **says so
   honestly** ("reported, not confirmed — check with the venue"), never dressed as an ordinary
   confirmed show.
4. Match = the promoted event satisfies the saved query's axes. Matching is a **lens, never a gate**:
   it changes *who is told*, never *what is true or ranked*.

**Invariant:** a saved alert is **match-triggered, never pay-to-rank.** An alert fires because the
event matches the user's saved query — never because an organizer paid to reach that user. There is
no promoted-placement path into the alert stream, ever.

---

## §3 · The demand-sensing dividend (the clever half)

Saved alerts are not just retention — **what people save tells us what to source.**

- **Aggregate saved demand** (privacy-safe, counts not identities) ranks what locals actually want:
  "412 people saved Tejano in the Eastside" is a sourcing priority, not a guess.
- **A saved search that returns _nothing_ is the coverage-gap queue.** Zero-result saves are the
  highest-signal input to "where do we expand supply next" — the direct, demand-weighted answer to the
  venue-coverage question (event-level coverage, `ONE_LIVE_SOURCE_EXPANSION_PLAN_v1.md`; the H5
  "zero-result coverage-gap queue" po-harvest candidate).
- **The loop closes and compounds:** user demand → tells us where to grow supply → we onboard those
  venues/sources (Owned Agent, gov registries, harvest) → the once-empty saved search now matches →
  we notify → the user returns. Demand pulls supply; supply pays back the demand.

This feeds the **Heartbeat analytics** canon (depth/breadth/coverage) and is reported as a real
measured signal, never a vanity number.

---

## §4 · Notification channels & consent (the SMS rule, baked in)

Proactive value with zero legal exposure. Channels, in order of default:

1. **Push (PWA) and Email — ON by default** for any saved alert. Full proactive value, low legal risk.
2. **SMS / text — a SEPARATE, EXPLICIT, REVOCABLE opt-in.** Because SMS is regulated harder than
   email/push (**TCPA**), text alerts follow three hard rules:
   - **Its own toggle** — "text me when a saved search matches" is a distinct opt-in, **never bundled**
     into the general signup / Terms checkbox, with a one-line disclosure of exactly what fires a text.
   - **Never a condition of using OneLive** — a user who declines SMS still gets full push/email value.
   - **STOP works instantly and forever** — the standard "reply STOP to end" footer; opt-out is honored
     permanently and a dropped/again-added source never resurrects a revoked consent.

**Notification hygiene (all channels):** user controls frequency (instant / daily digest / weekly),
per-alert mute, and a global quiet-hours setting; digests batch to prevent fatigue; every message
links straight to the verified event and carries a one-tap "manage this alert."

**Privacy:** saved preferences are the **user's own personal data** — minimal, user-owned, never sold
(Texas **TDPSA**; the personalization-is-a-lens-never-a-gate rule from
`ONE_LIVE_MEMBER_PREFERENCES_v1.md`). We store the query and the consent, not a behavioral dossier.

---

## §5 · Where this fits (reconciliation, not a new silo)

This spec **unifies threads already in flight** rather than inventing a sixth overlapping idea:

| Existing work | Relationship |
|---|---|
| `ONE_LIVE_MEMBER_PREFERENCES_v1.md` | Saved alerts ARE the "account favorites / saved preferences" surface, made proactive. This spec is its notification + demand-signal half. |
| Growth loop **#3** (`ONE_LIVE_COMMUNITY_PLATFORMS_GROWTH_v1.md`) | "Follow-a-venue / subscribe + notify me" — this spec is that loop's full design. |
| Automagical-nav spec (PR #112) | Saving is created inline from the current view (one tap), per that spec's frictionless principle. |
| Emotion/Vibe layer (`ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1`) | Supplies the "vibe/feel" save axis; alerts fire on consented/aggregate vibe signals only (never scraped individual posts). |
| Owned Agent | Supplies fresh first-party verified events that *fire* these alerts — the supply side of the loop. |
| Heartbeat analytics + Source Expansion plan | Consume the aggregate/zero-result demand signal as the coverage-gap sourcing queue. |

---

## §6 · Trust invariants (hard rules)

1. **Verified-only fires.** Proactive push holds to the promote-gate bar; `unverified` never fires;
   `disputed` fires only with an honest caveat. AI never publishes — and never *pushes* — unverified.
2. **Match-triggered, never pay-to-rank.** No paid placement into the alert stream, ever.
3. **SMS is a separate, explicit, revocable opt-in** (TCPA); push/email default; STOP honored forever.
4. **Preferences are user-owned, minimal, never sold** (TDPSA); personalization is a lens, never a gate.
5. **Demand signals are aggregate/anonymized** — counts of what's wanted, never a surveillance profile.
6. **Frictionless creation** — a saved alert is one tap from the current view, never a form.

---

## §7 · Build sequence (all gated on founder ratification)

- **SA-1 (data):** a `saved_alert` record (user · query-axes · channels · consent flags · created_at)
  + RLS fail-closed (a user reads only their own). Trust-critical (SQL/RLS) → evaluator mandatory.
- **SA-2 (match):** on promote, evaluate promoted events against saved queries (a lens over the
  existing promote event); enqueue matches. No new trust decision — matching never changes truth/rank.
- **SA-3 (notify):** push/email delivery + the digest/hygiene controls; SMS behind the §4 opt-in with
  STOP handling. Outward-facing → evaluator mandatory; SMS provider = a new service (founder-crucial).
- **SA-4 (demand signal):** aggregate saved-demand + the zero-result coverage-gap queue wired into the
  Heartbeat coverage metrics and the sourcing backlog.
- Every phase: verified-only, match-not-pay, consent-clean, measured by the analytics canon.

---

## Appendix · Founder decisions this needs
1. **Ratify this spec** (PROPOSAL ≠ license to build).
2. **SMS provider** = a new service + spend → founder-crucial (Twilio/others; caps set first). Push +
   email need no new vendor relationship, so SA-1→SA-2→push/email can ship before any SMS decision.
3. Confirm the save-axis list (§1) against the ratified genre taxonomy and member-preferences phasing.
