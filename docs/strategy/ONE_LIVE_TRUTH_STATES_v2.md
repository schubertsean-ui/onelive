# ONE LIVE — Truth States v2 (six-state model + evidence dependency + outcome truth)

**Status: FOUNDER-RATIFIED 2026-08-01** ("Adopt Truth-state additions
(OWNER-CONFIRMED, STALE)" — decision record
`docs/memory/decisions/2026-08-01_truth-states-v2-and-hypothesis-split.md`).
Adopted from the external review (§3.5, §3.6, §3.9), which correctly found
the deliverable's truth model internally ambiguous ("drift" used as if it
were a state; owner assertion conflated with independent corroboration).
Supersedes the 4-state model of 2026-07-15 **additively** — no state is
removed or redefined; two are added and observations become flags.
Implementation in the running pipeline is pending (R-026); this doc is the
spec it implements.

## 1 · The six truth states

| state | meaning | derivation |
|---|---|---|
| `confirmed` | Supported by sufficient **independent** authoritative evidence | corroboration across independent origin groups (§3) |
| `owner-confirmed` | Explicitly asserted by a **verified owner or authorized operator** | owner assertion through an authenticated channel — labeled as such, never silently merged into `confirmed` |
| `likely` | Supported by one credible source, or by multiple **dependent** sources | single-origin evidence, however many pages echo it |
| `unverified` | Insufficient evidence | default entry state |
| `disputed` | Material independent sources conflict | conflict detection across origin groups |
| `stale` | Previously supported, now outside the applicable freshness window | freshness windows per field class (event time: days; hours: weeks; identity: months) |

Rules carried over unchanged (charter physics):
- **Disputed is shown as disputed, never hidden, never deleted.** The
  reviewer's suggestion to soften this for the consumer feed was REJECTED —
  the invariant stands. Its compatible operational half is adopted: a
  disputed fact is never *promoted as settled*, the owner is asked, and the
  public display says what is unconfirmed rather than pretending.
- **Confidence is derived from corroboration, never asserted.**
  `owner-confirmed` does not weaken this: it is a distinct, labeled
  provenance class with its own display, not a shortcut to `confirmed`.
  Independent corroboration can upgrade an owner-confirmed fact to
  `confirmed`; an owner assertion alone never can.
- **AI never publishes.** States gate what may be promoted; promotion
  remains human-custodied.

## 2 · Issue flags (observations, not states)

A fact carries exactly one truth state and any number of flags:
`drift-detected` · `missing-date` · `source-dependency` ·
`authorization-expired` · `suspicious-change` · `duplicate-candidate` ·
`rights-unknown`. Flags route work (ask the owner, re-read the source,
hold promotion); they never substitute for a state transition. "Drift" in
every earlier doc reads as the flag, not a fifth state.

## 3 · Evidence dependency graph (review §3.6 — catch #7)

Four websites echoing one upstream feed are ONE origin, not four
confirmations. Every evidence record carries:

`source_id · source_type · source_authority · source_origin_group ·
observed_at · published_at · valid_from · valid_to · field · raw_value ·
normalized_value · extraction_method`

- **Corroboration weights independent origin groups, not page count.**
  Example from our own Continental run: an official venue calendar, an
  Eventbrite listing the venue created, a Songkick record syndicated from
  Eventbrite, and a city calendar copied from Songkick may be only one or
  two independent origins.
- **Field-specific authority:** date/time — organizer or ticket seller can
  outrank a venue directory; address/hours — verified venue account or
  official site outranks the performer; performer identity — verified
  artist source outranks the venue's shortened listing; availability —
  ticketing system outranks old promotional copy; cancellation —
  organizer/venue/ticket seller by provenance and recency.

## 4 · Outcome truth — measurement classification (review §3.9 — catch #8)

Attribution is not causal proof. Every reported outcome carries one class:

| class | example |
|---|---|
| **Directly tracked** | campaign-specific code redeemed at the door |
| **Attributed** | clicked a tagged link, later purchased |
| **Assisted** | engaged, converted through another path |
| **Self-reported** | "how did you hear about us?" |
| **Modeled** | estimated from historical relationships |
| **Incremental** | measured against a valid control or holdout |

Comparative claims ("X beat Y 3-to-1") require identical denominators,
defined metrics, comparable exposure, sufficient sample, treatment
assignment, and stated confounders — otherwise they ship as HYPOTHESIS
(claim ledger C-11 already enforces this for the worked examples). For
low-volume venues: alternating treatment weeks, staggered rollouts,
matched-event comparisons, uncertainty intervals — never one small event
dressed up as an A/B result. Optimize on attendance, signups,
reservations, revenue — not views or taps.

## 5 · Where this binds

- `docs/strategy/CLAIM_LEDGER.md` — outcome classes join the standing
  rules; comparative claims must name their class.
- `docs/review_personas/domain-truth-and-trust.md` — persona updated: the
  guarded invariant is now "six states, founder-ratified 2026-08-01;
  further additions/removals remain founder-crucial."
- `docs/strategy/ONE_LIVE_AGENT_SURFACES_v1.md`,
  `docs/strategy/marketing_model/` builders — references updated;
  `check_artifacts.py` forbids stray "4-state" wording in deliverable
  sources.
- **R-026** — pipeline implementation trigger (enum, gating, tests,
  display, CLAUDE.md charter text) in the next code-armed session.
