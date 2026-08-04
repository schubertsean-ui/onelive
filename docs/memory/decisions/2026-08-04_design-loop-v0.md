# Decision: the design loop moves to v0 — founder-directed (2026-08-04)

**Founder, verbatim:**
> "Go v0"
with the constraint, same message:
> "I don't want our code at 1live.co exposed to others who may want to download it."

Earlier the same day (on the UI mismatch): *"You have got to find the codified
UI/UX doc and reshare it with me. Let's bring in Figma or the other in lieu of
using Google - it's not working"* — Google Stitch is out; of the two candidates
the agent recommended v0 (v0.app, by Vercel) and the founder ratified it.

**The loop (one-way, code-private by construction):**
1. Agent packages the ratified design canon (ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4 +
   ONE_LIVE_TONIGHT_UI_CANON_v1) into a v0 prompt — design language only:
   copy rules, trust display rules, card anatomy, tokens. REPO CODE NEVER GOES
   IN. No pipeline, no gates, no app source is ever pasted into v0.
2. Founder runs the three-direction pass in v0 (signs in at v0.app with the
   existing Vercel account) and does NOT use v0's "Share" button (shared chats
   are public links; unshared chats are not).
3. Only v0's OUTPUT (exports/screens) comes back — dropped into design/inbox/
   like the old Stitch flow; the Generator translates the chosen direction into
   apps/web under the existing rules (verbatim copy strings, trust display
   rules, WCAG 2.2 AA, CWV budgets), with the evaluator pass against the
   brief's rubric.

**Code-exposure posture (answered to the founder, recorded here):** the GitHub
repo is private; 1live.co serves only compiled, minified client bundles like
any production site — server/pipeline/trust code runs server-side and never
leaves the deployment. The CLAUDE.md "Working with the designer AI" section's
Stitch references remain historical; this record governs the current loop.

**Tradeoff, stated.** v0 outputs Next.js/Tailwind-shaped components, which fits
our stack but can tempt direct code-paste; the standing rule stays translate,
never transplant — every design-derived change still goes through the normal
review gates.
