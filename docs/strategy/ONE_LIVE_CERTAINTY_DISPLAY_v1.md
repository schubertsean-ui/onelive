# ONE LIVE — Certainty, Trust & the Fifth-State Question (v1)

**Compiled 2026-07-15 · Status: PROPOSAL (founder question: "Do we need a fifth state?"). The 4-state model itself is CONFIRMED canon (founder, 2026-07-15: "confirmed") — this doc addresses whether to EXTEND it.**

Greppable summary: researched recommendation — **NO fifth state.** The
things a fifth state would try to express (freshness, event status,
provenance, volatility) are DIFFERENT AXES that human-trust research says
should compose with the 4 epistemic states, not multiply them. Proposal:
the **Certainty Display Stack** — state (4, fixed) × freshness (continuous,
"last verified…") × provenance (first-/third-party, already ratified) —
with event STATUS (cancelled/postponed) as its own field, never a
confidence state. Habit research argument: 4 learned meanings build user
trust through consistency; a 5th erodes the schema for marginal precision.

## What the research says (per clause)

1. **Transparent uncertainty does not cost source trust.** The landmark
   field + lab experiments ([van der Bles et al., PNAS 2020](https://www.pnas.org/doi/abs/10.1073/pnas.1913678117);
   [summary](https://pmc.ncbi.nlm.nih.gov/articles/PMC7149229/)) found
   communicating uncertainty (numerically or as ranges) slightly reduces
   confidence in the specific number but does NOT erode trust in the
   source. Implication: OneLive showing `unverified`/`likely` honestly is
   trust-BUILDING, not trust-costing — the 4-state display is an asset,
   and the design brief's quiet markers ("Info may change") are the right
   register. Hedging everything, however, numbs users; states must stay
   few and meaningful.
2. **Likelihood and confidence are two different judgments.** Intelligence
   tradecraft ([Kent's words of estimative probability](https://en.wikipedia.org/wiki/Words_of_estimative_probability);
   [ICD 203 analytic standards](https://factually.co/fact-checks/politics/how-icd-203-intelligence-analytic-standards-confidence-levels-work-why-they-matter-1d3959);
   [analytic confidence](https://en.wikipedia.org/wiki/Analytic_confidence))
   deliberately separates "how likely is X" from "how good is the
   evidence behind that judgment." Our 4 states are the likelihood-facing
   surface; evidence quality (source count, provenance class, recency)
   is the second element and should be EXPRESSED AS ATTRIBUTES, exactly
   as the IC pairs a probability word with an evidence explanation —
   never fused into one enum.
3. **Freshness is the most habit-forming trust signal in mass products.**
   Weather ("updated 5 min ago"), package tracking, transit ETAs — the
   dominant consumer pattern for time-sensitive data is a LIVE RECENCY
   cue beside a stable state vocabulary. Users re-check habitually
   because the recency cue visibly moves; the state vocabulary stays
   small and learnable. Our watcher records already carry
   `last_verified_at` (sensor architecture §1) — surfacing it is free.
4. **Habit and reuse favor a frozen vocabulary.** Trust through habituation
   comes from consistent, predictable signals (design brief behavioral
   architecture); each added state multiplies gate logic, tests, ops
   training, AND user learning cost. A state earns its place only if
   users must DECIDE differently because of it.

## The decision test a fifth state must pass
Would a user, seeing the new state, act differently than they would under
one of the existing four *plus the attributes below*? Candidates examined:

| Candidate 5th state | Verdict | Why |
|---|---|---|
| `stale` / `expired` | **Attribute, not state** | It's `confirmed` + old `last_verified_at`. Freshness is continuous — binning it into a state loses information. Display: "confirmed · verified 2h ago" (+ staleness de-emphasis rules). |
| `cancelled` / `postponed` | **Different axis entirely** | That's EVENT STATUS (what is true), not confidence (how sure we are). A cancellation can itself be confirmed/disputed. Own field: `event_status`. |
| `changed` / `volatile` | **Attribute** | Change-frequency signal on the watcher record (ratchet/attention allocation already uses it); display as "updated 3× this week" if ever user-facing. |
| `pending` / `in-review` | **Internal only** | Ops-pipeline position, not user-facing epistemics; the ops console already sees it. |
| `verified-by-attendance` | **Provenance grade, not state** | Post-hoc ground truth strengthens `confirmed`'s evidence attributes; feeds the Kaizen golden set. |

## Proposal — the Certainty Display Stack (no new states)
- **Axis 1 — Epistemic state (FROZEN at 4):** unverified · likely ·
  confirmed · disputed. Confirmed canon; gates, tests, and user habit all
  build on exactly these.
- **Axis 2 — Freshness (continuous):** surface `last_verified_at` as the
  quiet recency cue ("verified 2h ago"); staleness thresholds per event
  proximity (day-of events demand fresher verification) — thresholds
  live with watcher freshness SLOs (sensor architecture §1). Build: Step 7
  with watcher records.
- **Axis 3 — Provenance class (already ratified):** first-party vs
  corroborated vs single-third-party — the sensor architecture's
  provenance-weighted gate; display per the design brief's quiet-marker
  rules (no badges, dismissible sheet).
- **Separate field — `event_status`:** scheduled · cancelled · postponed
  · moved (each carrying its own confidence state). Design at Step 7.

## Founder ask
None required to proceed — this proposal keeps the confirmed 4-state canon
intact and adds no build-now work (Axis 2/3 + `event_status` ride Step 7's
existing triggers). If the fifth-state question resurfaces, the decision
test above is the bar a candidate must pass, with a founder decision
record either way.
