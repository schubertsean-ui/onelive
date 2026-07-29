# Reviewer rule: arming-gated findings are not merge blockers (2026-07-29)

## Retrieval token
**"Dormant + fail-closed → arming-time finding, not a blocker."** When a review
finding's harm can only occur once a founder-provisioned capability (credential,
secret, service, flag) that is ABSENT from the tree is armed, and the code fails
closed without it, the finding is routed to the capability's arming record
(R-###) and does NOT block the merge. It is moved to the gate where it bites,
never dropped.

## Verbatim directive
Founder, 2026-07-29 (after PR #106): "I'll merge - provide the link. And prevent
this 'kind' of issue from reoccurring in the future."

## The issue being prevented
PR #106 (the dormant Meta posting client — see R-061, R-026) drew **six**
adversarial-review rounds. Both Gemini seats and the OpenAI absence-only seat
APPROVED throughout, confirming "no user-facing defects." One OpenAI lens kept
finding the next-deeper "once this is armed, a user could see X" refinement on
code that is **fail-closed and cannot post anything** until the founder mints
`META_ACCESS_TOKEN`, `ONELIVE_APPROVAL_KEY`, `ONELIVE_CARD_IMAGE_HOSTS`, and the
R-061 infrastructure is built. Each refinement was real-ish but blocked nothing
real, because the harm is impossible until arming — which is itself
founder-custodied. The review scope-back (2026-07-29, `adversarial_review.py`)
narrowed to "user-facing harm" but left this hole: harm reachable ONLY after a
not-yet-existent, founder-gated capability is armed was still treated as a
present blocker.

## The rule (the mechanism, shipped in the same commit)
`tools/adversarial_review.py` — both `SYSTEM_PROMPT` and the panel
`V2_DISCIPLINE` now carry: a finding whose harm cannot reach any user until a
NAMED capability absent from the merged tree is armed, AND where the code fails
closed without it, is an ARMING-TIME item — recorded in NOTE/NITS as
"ARMING: … — clear before <capability>" citing the open RECORD id, never a
REQUEST-CHANGES. Plus: a refined restatement of a finding already fixed or
already routed to an arming item is not a new blocker.

## Why this does NOT fail open (the two hard limits, in the prompt)
1. It applies ONLY to harm a user CANNOT experience from the tree as-merged
   today. Anything reachable now is a normal blocker — unchanged.
2. The reviewer must CONFIRM the fail-closed property from the diff or its
   tests; if it cannot, the finding stays a blocker.
Net scrutiny is unchanged: the arming record is founder-custodied and arming is
gated on clearing its items, so every arming-gated finding is still enforced —
at the moment it can actually cause harm, not before. This is scope PRECISION,
not a relaxation of user-facing protection.

## Custody note
This edits the reviewer's mandate = gate custody = founder-crucial. It is
founder-directed, so it is founder-ratified, but by the same bootstrap as the
2026-07-29 scale-back the base-owned reviewer on the PR carrying THIS change may
flag a reviewer-scope change — resolution is the FOUNDER merges (gate tuning is
the founder's call by charter). The tamed rule takes effect for every PR after
this lands. Reversal = revert this commit.
