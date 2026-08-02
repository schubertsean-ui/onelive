# 2026-08-02 — Songkick held-not-lost; reader's guides required; auth-boundary explainer commissioned

**Founder, verbatim (2026-08-02):** "Put an explanation of what is in each
document up front so a reader understands what they are about to see. Plain
language. / Provide a brief plain language description for each page as
well. / Put Songkick on hold but don't lose it. / Explain the auth
boundary. / What out do you need on pricing? / When complete commit these
new docs and decisions to the repo and canon."

## Decisions

1. **Songkick: ON HOLD, RETAINED (decided).** The open hold from the
   external review is now a founder decision, with a retention clause: the
   connector stays in the registry and the surfaces inventory, marked ON
   HOLD — it is not deleted, and its value case (artist/venue event
   database, concert-discovery alerts) is preserved in place. Nothing may
   use Songkick in product until a legal review of its API terms clears it
   (legal posture — founder-crucial, unchanged). Reopen trigger: that legal
   review, whenever the founder commissions it.

2. **Reader's guides are now part of the deliverable standard.** Every
   founder-/customer-facing document opens with a plain-language "what
   you're about to see" page, and every page carries a one-line
   plain-language description. Implemented in `build_customer.py` and
   `build_model.py` this session; applies to future deliverables (joins
   the deliverable visual-QA standard in TODOS).

3. **Standing-authorization boundary: explainer written, decision still
   open.** `docs/strategy/ONE_LIVE_STANDING_AUTHORIZATION_v1.md` (PROPOSAL)
   explains the boundary in plain language and carries the proposed
   two-tier split. Until the founder ratifies the tier lists, the interim
   rule holds: EVERYTHING outbound requires the owner's tap
   (ONE_LIVE_ENGAGEMENT_HYPOTHESES_v1.md, invariant 7).

4. **Pricing:** the founder asked what input is needed. Answered
   in-conversation and recorded on the TODOS pricing item: the only
   decision needed NOW is whether percentage-of-ad-spend is permanently
   ruled out (both our research and the external reviewer flag it as the
   misaligned agency pattern). Everything else in the Tier-2 pricing packet
   waits for pilot usage data by design.


## Addendum (2026-08-02, later the same day) — copy directive

**Founder, verbatim:** "Remove this language: ' Leave anytime and keep
everything.' ' 1Live's answer: - we do the repetitive time consuming
maintenance work across marketing channels for you - we create the
marketing content that helps you improve what matters - we do the work of
getting that marketing content placed in the right marketing channel for
you You remain in control and approve every decision with a tap'"

Executed as: (1) the exit-promise formula ("leave anytime, keep
everything") REMOVED from all copy — Customer Story rail, Model
standing-rules rail, the data-model figure's physics strip, and the
surfaces-inventory standing rules (which now note the removal applies to
LANGUAGE; no data-portability behavior change was directed). (2) The
Customer Story problem page's one-line "OneLive's answer" replaced by the
founder's dictated three-bullet answer, closing on "You remain in control
and approve every decision with a tap." Read as dictation of the second
block, not deletion (it matched no existing copy). Normalizations applied
and disclosed: "1Live's" → "OneLive's" (brand consistency),
"time consuming" → "time-consuming". Near-identical phrases deliberately
LEFT in place pending founder direction: the "Your exit" control tile,
the "no lock-in by design" line, and the six-step "stop after any step"
framing — these state progressive adoption/portability, not the removed
exit slogan.
