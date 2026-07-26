# Decision — Everything is built toward the vision, and the feeling is part of the spec (founder, 2026-07-26)

**Status:** RATIFIED by the founder as a standing directive. Recorded the same
session it was given, per Prime Directive 2 (disk is truth).

## The directive (verbatim)

> "Everything is to be built toward the vision and goals and objectives and other
> content surrounding this project and how it is supposed to work and make people
> feel. All actions should be in support of all of those things."

## Why it was given, and what it corrects

It arrived immediately after the 2026-07-26 audit (`docs/V1_AUDIT_2026-07-26.md`)
and the canon simplification that followed it. That work defined "world class" per
aspect in `docs/BAR.md` — 66 measurable rows across trust, extraction, coverage,
security, code, testing, reliability, cost and process — and it was **substantially
incomplete in exactly one direction**: it graded the machine and barely graded the
experience. Nine rows touched the web surface. **Zero rows named the vision, the
mission, the promise to the fan, or the feeling the product exists to create.**

That is a real defect, not a matter of emphasis. A bar that measures correctness
without measuring purpose will pass a product that is accurate, fast, well-tested
— and dead. Trust "is earned by delivered value, never by badges" (brief §2); a
bar that never defines the value cannot tell whether trust was earned.

## What changes

1. **`docs/BAR.md` gains section P — Purpose and Felt Experience — placed FIRST**,
   ahead of every engineering section, with the vision, mission and promise stated
   above it. The rest of the bar exists to keep that promise. The ordering is the
   point: whoever opens the file reads *what this is for* before *how it is
   verified*.
2. **`CLAUDE.md` opens with the vision**, not with the rules. A new prime
   directive states that every change must serve it, and that "does this serve the
   fan on the sidewalk at 9:04 PM?" is a legitimate blocking question in review —
   the same standing as a failing test.
3. **`docs/V1.md` gains experience done-criteria.** v1 was defined purely
   mechanically (feeds refresh, candidates publish, master green, deployed,
   measured). Those are necessary and not sufficient. v1 is not done until the
   ten-second answer works, the page loads in under two seconds, no account is
   required, no badge appears, and the design scores against the brief's own
   8-criterion rubric.
4. **The stricter number wins where canon disagrees.** The design brief requires
   the feed to load "in under 2 seconds"; the engineering bar carried Core Web
   Vitals' LCP ≤ 2.5 s. The product bar is now **2.0 s**, with 2.5 s recorded as
   the floor of external acceptability. Tightening a bar is not a relaxation and
   is not founder-crucial, but it is stated rather than silently absorbed.

## Where the vision text lives, and why it is not being rewritten here

The vision, mission, objectives, trust philosophy, emotion/feel/mood, payoff and
behavioural architecture are already written, ratified, and better than anything
this session would produce: `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`
§1–§6, with the 8-criterion rubric in PART C. `docs/BAR.md` **quotes and points
at** that text; it does not restate or paraphrase it. Paraphrasing ratified canon
is how canon drifts.

## The founder ask this directive surfaced — RATIFIED THE SAME DAY

The brief's §3 **had** mandated the tagline **"Less chaos. Real shows."** as verbatim
copy. On 2026-07-22 (FLOW round 6) the founder removed it from product surfaces and
reframed, in the founder's own words:

> "This is about finding and engaging in experiences, helping individuals and the
> culture thrive."

That is a change in the *feeling* the product is built toward — from defensive
(what the app removes) to generative (what a night can give) — which is precisely
what this directive governs. The delta was logged at the time
(`docs/ONE_LIVE_CHANGE_LOG.md`, 2026-07-22) and queued in `TODOS.md`, but the
ratified brief carried the old line for four more days — which is how a founder
instruction and its canon end up pointing in opposite directions.

**Ratified 2026-07-26, verbatim: "Use the new description for the tagline. Remove
the old."** The brief is amended accordingly (§3 + an amendment log at its head, the
filename kept so its ~30 canon references stay valid): **there is no tagline on any
product surface**, the thrive framing is canon, and the old line is struck.

The removal is mechanical rather than a note. `"Less chaos. Real shows."` moved from
`REQUIRED_VERBATIM` to a new `FORBIDDEN_VERBATIM` list in
`tests/test_design_proposals.py` — proven red against the three pre-amendment comps
before being made green — so the retired string cannot reappear in a comp without a
failing test. It was also removed from all three design comps (with their orphaned
`.tagline` CSS, since dead code is a violation), from `design/proposals/README.md`'s
copy list, and from the reference prototype including the render site that would
otherwise have silently rendered nothing.

## What did NOT change

No gate, threshold, check, test or invariant was loosened. No trust invariant was
touched. The new §P rows are marked ENFORCED only where a mechanism already exists
today; everything else is marked PROPOSED with the mechanism that would make it
blocking named, exactly as the rest of the bar does.
