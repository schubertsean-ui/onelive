Founder-ratified 2026-07-29: gates ADVISE, the founder DECIDES. No AI gate or reviewer may ever veto an authenticated founder directive; it may only refuse to FORGE one. This corrects the reviewer discipline that read "gate-custody weakening MUST block regardless of founder rationale" — that wording put the machine above the founder, which is backwards.

## The principle (canon — do not weaken)

1. **The founder is the final authority.** Every gate, threshold, check, and
   reviewer in this repo exists to protect the founder's own goals (the
   user-facing trust invariants) from mistakes by the *generator* (the AI that
   writes code). None of them exists to constrain the founder.

2. **AI flags; the founder decides.** An AI reviewer's verdict is ADVICE. On a
   founder-directed change — including a change to the gates, thresholds, or the
   reviewer itself — the reviewer's job is to (a) confirm the user-facing trust
   invariants still hold and (b) surface anything the founder should know. It is
   NOT to block the change on the ground that "the founder should not be allowed
   to." A founder-directed gate/process change, absent a real user-facing
   defect, is APPROVE.

3. **The one guard that stays — and it protects the founder, not the machine:**
   the AI must never FORGE the founder's authority. The generator claiming "the
   founder approved this" with no authenticated founder signal is the one thing
   a reviewer still refuses. This is anti-forgery, not anti-founder. The AI
   declining to *self-merge* a gate change is the AI refusing to impersonate the
   founder — the opposite of vetoing the founder.

4. **The authenticator is the founder's own identity.** The founder merging or
   approving from their own account is the authenticated signal the AI cannot
   fake. A red advisory check does not disable that button (a gate change PR is
   `mergeable_state: unstable`, not `blocked`); the founder's merge is final.

## Why the old wording existed (honest)

The "MUST block regardless of founder rationale" rule was written to stop the
*generator* from talking its way past a safety gate by claiming founder backing.
Legitimate goal (anti-forgery), wrong implementation — it threw out the
founder's real authority in order to stop the AI forging it. The fix keeps the
anti-forgery guard and restores founder supremacy: real founder approval is
final; a mere *claim* of it is not.

## Mechanics now live

- `tools/adversarial_review.py` SYSTEM_PROMPT: a "FOUNDER AUTHORITY IS FINAL"
  clause — the reviewer advises, never vetoes an authenticated founder directive,
  and refuses only a forged one.
- The 2026-07-29 scale-back already removed the gate-custody-veto discipline
  (decision record `2026-07-29_process-scaleback-ship-capcog.md`).

## The bootstrap note (why the PR that installs this is red once)

The reviewer is base-owned: a PR is judged by `master`'s copy of the reviewer,
not its own. So the PR that FIXES the reviewer is still judged by the OLD
reviewer, which will block it. That red is unavoidable and is the charter's
documented one-time bootstrap ("merged with this check red, once"); the founder's
merge — their authenticated authority — is what lands it. Every PR after gets the
corrected, founder-deferring reviewer.
