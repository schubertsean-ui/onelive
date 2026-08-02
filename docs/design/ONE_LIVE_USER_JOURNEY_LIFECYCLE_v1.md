# 1LIVE — User Journey & Lifecycle Model (v1)

**Status:** RATIFIED-in-capture (founder directive, 2026-08-02). This is the **spine** the whole
UX hangs on — the staged, "automagical," background process a person moves through, from a very
first visit to a saved, personalized, returning relationship. It connects and integrates the
pieces that were specced separately (effortless-UX metrics, choice architecture, card design,
saved alerts, on-device personalization, Heartbeat analytics) into **one journey**.

**Founder's framing (verbatim anchors, 2026-08-02):**
- *"Separate the entire process, in the background, because it's automagical."*
- *"There is a very first time and a next first time and then maybe a next or several next first
  times before it is a saved site with some saved or preferred results or interests or packages."*
- *"Arrive on the page, first impression must be wow and awesome and I want to find what I want,
  and then the initiation to find something or to pursue an interest, to seeing results, to
  evaluating those results and eliminating some and keeping 1 or more, to deciding — do I have
  enough info and insight to know what I am going to do, or do I want to continue exploring the
  specific items I've selected, or spin out into another area and start the process again."*
- *"I may want to start with prepackaged searches upon first opening the site or perhaps see my
  past saved."*
- *"All of these various use cases and related personas need to be thoughtfully considered and
  connected and integrated and ultimately learn and respond appropriately based on my usage — all
  on device, but with the actions being saved and plug into DB for real-time and post-hoc and
  standard analysis as part of the Heartbeat Analytics."*

The whole model obeys the core principles (UI Canon §1): calm over clutter · curiosity over
completeness · speed · beauty-is-trust · trust-by-construction · nothing hidden/for-sale · honest
gaps · accessibility. It is **automagical**: the person feels flow, the machinery is invisible.

---

## §1 · The lifecycle — first time → next first times → saved relationship

A person's relationship with 1Live matures across visits. The app **stages this in the
background** and meets them where they are — never making a returning person start from zero, never
overwhelming a newcomer with personalization they haven't earned.

| Stage | Who | What the app does | Feels like |
|---|---|---|---|
| **The very first time** | Brand-new, no history | A **wow** first impression + **prepackaged entry points** (curated "what's on," intent starters). Zero setup. Everything works with no account. | "Whoa — and I already see something for me." |
| **The next first time(s)** | Been once or a few times, lightly known | The app **remembers on-device** what they explored/kept and **gently pre-composes** the arrival toward it — still offering the wide world, just warmer. Repeats until enough signal accrues. | "It's starting to know me, without me doing work." |
| **The saved relationship** | Returning, with saved results/interests/packages | Arrival can **lead with their saved** (searches, interests, "packages") *or* the fresh edition — their choice. Alerts (opt-in) bring the verified new match to them. | "This is *my* 1Live." |

**Rules for the lifecycle (non-negotiable):**
- **Automagical, never demanding.** Personalization accrues from *use*, never from a setup wizard.
  A newcomer is never asked to configure; a regular is never made to re-declare.
- **On-device first.** The maturing model (tastes, history, saved) lives on the person's device
  (see §4). Nothing about "who they are" is hoarded server-side.
- **Personalization is a lens, never a gate** (member-preferences canon). The full edition is always
  one tap away; the app narrows *for* you, never *from* you.

---

## §2 · The exploration loop (the core in-session journey)

Within any visit, a person moves through a loop. The app makes each step **fast, calm, and
reversible**, and lets them exit or re-enter at any point. This is the founder's model, made
explicit:

1. **ARRIVE — the wow.** In <10s, no login, a beautiful, trustworthy answer to "what's happening?"
   First impression is the product's promise kept. (UI Canon §0 North Star.)
2. **INITIATE — find something / pursue an interest.** Either a **prepackaged search** (a curated
   intent: "Free tonight," "Live music near me," "Date night"), a **saved** interest, or a fresh
   search/filter. The app pre-composes a sensible default so *no query assembly is required* to get
   going (choice-architecture: don't make them build the query).
3. **SEE RESULTS.** A calm, scannable set of slightly-open-door cards — enough scent to decide, not
   a wall (curiosity over completeness).
4. **EVALUATE.** Open a card (the smooth lens), read enough to judge; the trust display is felt, not
   advertised.
5. **ELIMINATE / KEEP.** Discard what's not it; **keep 1 or more** (save / shortlist / add to a
   plan). Keeping is one tap and reversible.
6. **DECIDE — three honest exits, all first-class:**
   - **Enough** — "I know what I'm going to do." (Success = a confident decision; a *satisfied
     browse* with no click-out is also success.)
   - **Continue** — keep exploring the specific items already selected (go deeper on the shortlist).
   - **Spin out** — jump to another area/interest and **start the loop again** — a welcomed, tracked
     move, never a dead end.

**Design consequence:** the loop must be **frictionless and non-linear** — a person can eliminate,
re-add, deepen, or spin out in any order, and the app keeps their place. This is why the interaction
model is *forward-expanding lenses over one river* (never separate tabs or page loads that lose
context, UI Canon §6/§9).

---

## §3 · Entry modes (how a visit begins)

The **first screen adapts to the lifecycle stage** (§1) and the person's choice:

- **Prepackaged searches / intent starters** — a small, curated set of one-tap entries that each
  encode a whole multi-facet query ("Free tonight," "Live music near me," "Something for the
  family," "Ideas & talks"). The newcomer's front door; also always available to regulars.
- **Past saved** — a returning person can lead with their **saved searches / interests / packages**
  (a "package" = a saved bundle: e.g. "my Friday jazz + patio + under-$20"). Their choice whether
  arrival opens on saved or on the fresh edition.
- **The open river** — the full chronological edition, always one tap away regardless of the above.

No entry mode is a gate; each is a *lens* over the same trusted river.

---

## §4 · On-device + the DB / Heartbeat split (the automagical machinery)

The magic ("it knows me") comes from the device; the intelligence-for-the-business comes from
**aggregate** signals — never a server-side dossier.

**On the device (the personal layer):**
- The maturing taste/interest model, exploration history, shortlist, saved searches/interests/
  **packages**, and the "which stage am I in" state (§1). The feed re-composes locally.

**Saved to the DB (as actions/events, for analysis):**
- The **actions** a person takes — searched X, kept Y, eliminated Z, decided/continued/spun-out —
  are recorded as **events** (with consent, minimal, the person's own), and plugged into the DB for:
  - **Real-time** response (e.g. an opt-in saved-alert fires when a verified match appears),
  - **Post-hoc** and **standard analysis** as part of **Heartbeat Analytics** (aggregate demand,
    the coverage-gap queue, effort-to-decision, curiosity depth — the effortless-UX metric set).
- **Aggregate/anonymized only** for analysis (counts, not identities); the demand signal is a
  **mirror shared as neutral intelligence** (we sense demand, never drive it), never a surveillance
  profile. Consent, minimality, TDPSA, and "no pay-to-rank" bind everything here.

**The learn-and-respond loop:** on-device usage → the app responds appropriately (warmer defaults,
better prepackaged starters, timely verified alerts) → the *actions* feed Heartbeat in aggregate →
the aggregate tells us where to sharpen coverage and which starters land → the newcomer's very-first
experience gets better. The person feels a product that flows; the machinery stays invisible.

---

## §5 · Personas × use-cases (to be considered, connected, integrated)

The journey is one model, but people enter it as different **personas** with different **use-cases**;
the app must serve each *through the same loop* and learn which fits. Seed set (extends the
domain-expert lenses; not exhaustive — grows with evidence):

| Persona | Dominant use-case | What arrival + loop should favor |
|---|---|---|
| **Tonight-restless** | "What's on *right now / tonight*?" | Fresh edition, on-now, near me; fast decide |
| **The planner** | "Build my Friday / weekend" | Plan mode, packages, save + shortlist |
| **The interest-follower** | "Keep me on cumbia / lectures / comedy" | Saved interests + verified alerts |
| **New-in-town explorer** | "Show me the city" | Prepackaged starters, breadth, map/nearby |
| **The date/group organizer** | "Something for us" | Curated intents, shareable plan/package |
| **The returning regular** | "My 1Live" | Lead with saved; warm defaults |

**Discipline:** personas are **inferred gently from usage, never asked**; each is a lens, never a
gate; and each person may be several personas across visits (the "spin out and start again" move).
The system **learns which** fits and responds — on-device — and the *aggregate* of these fits is a
Heartbeat signal, never a label sold or exposed.

---

## §6 · How this integrates with the rest of the canon (nothing new-siloed)

| This model's element | Where it already lives |
|---|---|
| Arrive / results / evaluate → success-states (decide/act/share/satisfied-browse) | `ONE_LIVE_EFFORTLESS_UX_METRICS_v1.md` §4 |
| Initiate without assembling a query; prepackaged starters; calm top | Effortless-UX choice-architecture §1; UI Canon §1/§9 |
| Keep / save / packages / alerts; verified-only notify; on-device + SMS-consent | `ONE_LIVE_SAVED_ALERTS_AND_PROACTIVE_SURFACING_v1.md` |
| Card evaluate (glanceable → lens → detail) | `ONE_LIVE_CARD_DESIGN_v1.md`; UI Canon §2/§6 |
| On-device personal layer; aggregate-only analysis | Effortless-UX §7 guardrails; member-preferences (lens-not-gate, never sold) |
| Actions → Heartbeat (real-time + post-hoc); demand as a shared mirror | `ONE_LIVE_ANALYTICS_METRICS_v1.md` (Heartbeat) |
| Prove it's easy/loved (effort-to-decision, curiosity depth, trust-comprehension) | The Discovery Exam (persona×query gate), Effortless-UX §6 |

The redesign build (UI Canon §13 / the world-class UI/UX plan) **implements this journey** — the
loop's steps map onto arrival, cards, lenses, filters, save/plan, and alerts.

---

## §7 · Process canon (founder directive, 2026-08-02): ALWAYS start with a plan

Codified rule (to be mirrored into `docs/OPERATING_RULES.md` and the Construction Loop): **no
substantive build begins without a plan that states — for the work — WHAT, HOW, WHY, WHY IT
MATTERS, and the EXPECTED OUTCOMES/RESULTS.** The plan is presented and approved before building;
the build then runs the loop (plan → small-batch build → validate → independent evaluator →
preview for the founder → approval → merge → measure). "World-class" is never unplanned or
unreviewed.

---

## §8 · Status

Captured 2026-08-02 as the design spine. It does not itself build anything — it **directs** the
world-class UI/UX build (the plan) so the journey, personas, on-device learning, and Heartbeat
integration are served coherently rather than as disconnected features. Each element ships only when
real and validated (honest gaps beat filler); none feeds ranking; each is measured.
