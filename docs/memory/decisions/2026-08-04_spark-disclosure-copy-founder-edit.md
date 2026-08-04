# Decision: ✳ disclosure copy shortened — founder-directed (2026-08-04)

**Founder, verbatim:** "Remove this: [Artist] can make it theirs anytime.""

**What changed.** The Spark Line tier-C tap-to-dismiss disclosure sheet now reads
**"Drafted from [artist]'s own materials."** — the second sentence is removed from every
LIVING surface: the product copy (`web/app/(public)/tonight/FeedApp.tsx`, card + lens via
the shared `SparkLineView`), its pinning test (`sparksheet.test.tsx`, which now also
asserts the removed sentence's ABSENCE), UI canon §4
(`docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md`), and the master design brief §4
(`docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`). Historical records (changelog
entries, session arcs, prior PR bodies, STATE contract text as written) keep the original
sentence — append-only records of what the copy was when shipped.

**Authority.** The disclosure copy is founder-ratified canon text; this edit is
founder-directed in writing (quoted above), following the 2026-08-03 invariant-rewording
pattern: edit the living canon at the founder's written direction, record the verbatim
instruction, sweep every living surface in the same change, leave history untouched.

**What did NOT change.** The disclosure mechanism (native `<details>`, one tap in / one
tap gone, no modal, no history entry), the ✳ mark, the tier waterfall, and the
creator-words-replace-ours behavior (canon §4's "the moment a creator claims, their words
replace ours" remains canon — only the sheet's second SENTENCE is removed, not the claim
behavior it described).
