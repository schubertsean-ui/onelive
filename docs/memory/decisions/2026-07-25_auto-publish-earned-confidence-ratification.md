# Decision — Auto-publish at earned confidence (founder ratification, 2026-07-25)

**Status:** RATIFIED by the founder (the only authority for a trust-invariant
change; CLAUDE.md Prime Directive 1). Mechanism built; the switch flips ON once
the safeguards below are live.

## The founder's directive (verbatim, 2026-07-25)

> "Even a passing candidate waits for a human click. Good lord I can't approve
> every one of thousands of events! I told you to prep to enable AI to post
> without human approval except for exceptions or sources we have graded as
> often unreliable."

And, on single non-anchor sources (radio/TV/press):

> "they are great sources of data and have been for decades. Use the data. If we
> can verify with 2 sources then that's fine we can still have in the background
> our source list and rules for what we show."

## What changes

The pipeline no longer stops at "candidate awaiting a human click." Every
fetched, extracted, **non-fabricated** candidate is **published at its earned
confidence**, with honest uncertainty display, **without a human click** — except
the exceptions below. This is a deliberate relaxation of the operational rule
"a human promotes every event," ratified by the founder. It is NOT a relaxation
of "never fabricate an event" — that invariant is preserved and is what keeps
auto-published data trustworthy.

## The rules (mechanical — worker/publish_policy.py, pure + unit-tested)

Given a candidate's gate decision, its sources, and its source-reliability grade:

| Situation | Action | Confidence shown |
|---|---|---|
| Fabrication risk (schema-invalid extraction / sensor-rejected shell) | **Human review** | — (never published) |
| Gate ESCALATE (contradictory time / private-RSVP / dedupe ambiguity) | **Human review** | — |
| Source graded often-unreliable (reliability < threshold, default 0.35) | **Human review** | — |
| Gate PASS, anchor source | **Auto-publish** | `confirmed` |
| Gate PASS, ≥2 independent sources | **Auto-publish** | `likely` |
| Gate HOLD, a single trustworthy non-anchor source (radio/TV/press/one venue) | **Auto-publish** | `unverified` (quiet uncertainty marker) |
| Moderation flags a contradiction | (separate) | `disputed` — ALWAYS shown, never hidden |

The single-source HOLD → `unverified`-published rule is the change the founder
demanded: a single good source is USED and shown honestly; a second source
agreeing raises it to `likely`. The background source list + show-rules
(source_reliability, the catalog) govern what surfaces and how.

## The safeguards that must be LIVE before the switch flips

Auto-publish is gated by one mechanical, fail-closed flag
(`AUTO_PUBLISH_RATIFIED`, default OFF — reversible in one line). The founder's
ratification is recorded here; the flag flips to ON only when all of:

1. **Reliability grading is real** — source_reliability scores are being updated
   from outcomes so "graded unreliable" actually gates (worker/source_reliability.py
   exists; the update loop must run).
2. **Honest uncertainty display is live** — the feed already renders the quiet
   caution marker + "How we know" sheet for `unverified`/`likely`/`disputed`
   (web/lib/trust.ts, shipped). Confirmed once promoted events flow through it.
3. **No fabrication** — the sensor + schema-validation guards stay in force
   (they do); auto-publish only ever publishes candidates that passed them.

Until the flag is ON, `decide_publish` returns `human_review` for everything —
identical to today's behavior. So this change is inert and safe until deliberately
enabled.

## Why this is safe / what did NOT change

- **The only new promoter WILL BE worker/autopromote.py** — it is NOT yet in the
  tree; it lands with the DB wiring in a future change (pending), added to the
  promote-import allowlist in that same change (the deliberate, reviewed pattern
  the guard requires). Until then the orchestrator still never imports
  `worker.promote`, and `decide_publish` is inert (fail-closed → human review).
- **The independent (non-Claude) evaluator reviews this on the PR** — gate custody.
- **"Never fabricate" is untouched.** disputed-shown-never-hidden is untouched.
  RLS/privacy is untouched.
- **Reversible:** flip the flag OFF and the pipeline returns to human-promote.

## Trigger to flip ON

Founder confirms (or the deploy sets `AUTO_PUBLISH_RATIFIED=1`) after safeguards
1–3 are verified live on a preview. Recorded as a live item so the flip is
deliberate, not a default.
