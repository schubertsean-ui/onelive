# Decision: earned-confidence auto-publish FLIPPED ON — founder-directed (2026-08-04)

**Founder, verbatim (live-site review, on being told promotion was human-custodied):**
> "Change this so I am not the blocker. I thought I changed this long ago. I cannot
> personally and individually approve hundreds of entries. If the logic of our
> verification is solid - you tell me if it isn't - and our checks and balances are
> working properly - you tell me if they are not - then publish without my personal
> and individual approvals."

This is the founder-flipped switch the ratified design has waited for since
2026-07-25 ("prep to enable AI to post without human approval except for
exceptions or sources we have graded as often unreliable" — decision record
2026-07-25_auto-publish-earned-confidence-ratification.md, which built the
machinery fail-closed OFF and named the flip founder-crucial). Per-item human
approval was REJECTED as a design then; today's directive activates the
replacement.

**The honest audit the founder conditioned the flip on (delivered in chat,
summarized here).** SOLID: the publish decision is a pure, exhaustively-tested
policy (worker/publish_policy.py + worker/autopromote.py, 28 tests; full suite
green) — PASS (anchor or ≥2 independent sources) publishes at confirmed/likely;
a single trustworthy source publishes at 'unverified' WITH the quiet uncertainty
marker; ESCALATE (contradictory times, private-RSVP, dedupe ambiguity,
validation errors), sources graded below the 0.35 reliability threshold, and any
fabrication-risk shell go to HUMAN REVIEW, never published; the orchestrator
remains structurally unable to import the promote path (tests +
trust_gate); extraction itself re-certified today (attended exam run
30935638738: hallucination 0.0063 ≤ 0.01, recall 0.9751 ≥ 0.8, zero injections).
CHECKS AND BALANCES LIVE: trust_gate green; adversarial review on every PR;
Sentry DSN live on web + worker as of today; spend hard-capped at the console
($500/mo, alert at $280). RESIDUALS, stated not hidden: (1) new sources start at
reliability 0.5 — above the 0.35 review threshold — so a brand-new source's
first events can auto-publish before a track record accumulates (the grade is
outcome-driven and self-corrects; this is the ratified design's choice); (2) the
public feed will now show more 'unverified'-tier events — honestly marked, which
is the design's uncertainty display doing its job; (3) escalations still land in
/ops, but that queue is conflicts-only (dozens, not hundreds).

**What changed.** `.github/workflows/autopromote.yml` (new): hourly bounded pass
running `worker/run_autopromote.py --real --limit 200`, with
`AUTO_PUBLISH_RATIFIED: "1"` as a visible workflow literal (one-line reversible),
Sentry + a DEDICATED dead-man check (AUTOPROMOTE_PING_URL secret → the sentinel's
ORCHESTRATOR_PING_URL binding), fail-closed guards on every secret. No code
changed — the machinery ships exactly as ratified and reviewed on 2026-07-25.

**Custody statement (invariant unchanged).** Publication remains gate-custodied:
extraction → candidate → gate → promote, with promotion now earned-confidence
AUTO behind this founder-flipped, fail-closed flag — exactly the second of the
two custody modes the charter has always named. Disputed stays shown-never-
hidden; fabrication risk still cannot publish; the founder can close the door
again in one line.

**Founder action to arm the alarm (fail-closed until done):** create a
healthchecks.io check named `onelive-autopromote` and add its ping URL as the
`AUTOPROMOTE_PING_URL` repo secret — the workflow refuses to run without it
(Sentinel rule: no scheduled loop without its own dead-man ping).
