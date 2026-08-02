# 1LIVE — The Standing-Authorization Boundary v1 (plain-language explainer)

**Status: PROPOSAL — the tier lists below need founder ratification
(commissioned 2026-08-02, "Explain the auth boundary"; decision record
`docs/memory/decisions/2026-08-02_songkick-hold-reader-guides.md`).
Until ratified, the interim rule is absolute: EVERYTHING outbound requires
the owner's tap (`ONE_LIVE_ENGAGEMENT_HYPOTHESES_v1.md`, invariant 7).**

## The question, in one paragraph

When a business owner connects 1Live, they approve things. The question
is what ONE approval can cover. If every tiny correction — a typo, an
expired event coming down, a time fixed on their own website — needs its
own tap, the agent recreates the labor burden it exists to remove, and
owners learn to tap "yes" without reading (approval fatigue — the external
review's §3.8, which we adopted as a real problem). If one approval covers
too much, the owner has silently authorized things they'd want to see —
and trust, our whole product, erodes. The boundary is the line between
those two failure modes.

## The proposed split (needs your ratification)

**Standing authorization MAY cover — "keep my facts right" (set once,
revocable anytime):**
1. Factual changes the owner already made in their own calendar (the
   calendar is the source of truth; the agent is propagating THEIR edit).
2. Removing events that have already passed.
3. Updates to the owned website widget and the 1Live record.
4. Typo and formatting corrections that change no fact.
5. Factual changes inside explicit rules the owner wrote (e.g. "always
   correct my hours from the calendar").

**Explicit per-item approval ALWAYS required — "speak or spend for me":**
promotional messaging of any kind · paid media and budget changes ·
discounts, offers, and price claims · legal or health claims · anything
touching a DISPUTED fact · connecting a new account or channel · sends to
their private email/SMS list · use of new media or music rights.

The principle underneath: **standing authorization propagates facts the
owner already authored; the tap covers everything that speaks in their
voice, spends their money, or touches their audience.** Nothing in either
tier changes the charter physics — the AI still never publishes to
1Live's consumer feed (gate-custodied), disputed stays shown, and every
action is logged and reversible.

## What ratifying this changes

Today (interim): a stale Tuesday listing waits for a tap before the
agent's correction goes anywhere — safe, but it makes the agent a
notification machine. After ratification: the owner chooses their level at
CONNECT time (the six-step flow's step 3), defaulting to
everything-needs-a-tap; "keep my facts right" is an opt-in they can revoke
in one place. Grants are content-bound and expire on drift — the same
custody mechanics already built for the carousel engine (allowlisted
approvers, signed grants, fail-closed) apply here.

## Open items for the founder (the actual decision)

1. Ratify, edit, or reject the two lists above (any move of an item from
   "always ask" to "standing" is the decision that matters).
2. Default level at onboarding (proposed: everything-needs-a-tap).
3. Whether "factual sync" grants expire and re-confirm on a cadence
   (proposed: re-confirm every 90 days).
