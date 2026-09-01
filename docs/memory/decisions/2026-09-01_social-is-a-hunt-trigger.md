# Founder ruling — social is a hunt trigger, not a ban and not a publish

**Date:** 2026-09-01 · **Status:** RATIFIED, in force · **Scope:** what one
unofficial social mention licenses, and what clears the consumer site.

## The ruling, verbatim

> Social is a hunt trigger, not a ban and not a publish.
>
> One unofficial social mention (not the venue/artist/rep) = lead only.
> Do not show it on 1Live.co.
>
> Engine must then check: official venue/artist/group page or calendar,
> ticket/aggregator pages, and other public mentions.
>
> Publish on the consumer site only if:
> (a) the named venue/artist/group (or known rep) corroborates, or
> (b) at least two additional apparently independent people mention
>     the same who/where/when (best effort, no formal affiliation).
>
> If neither: do not post. Keep the lead. Do not delete.
>
> Do not treat this as "never show social."
> Do not treat this as "one Facebook post is enough."

## What it settles

It closes both wrong readings at once, and the pairing is the point:

- **Not a ban.** A social mention is a legitimate REASON TO GO LOOK. Refusing to
  act on one is a coverage defect, not caution.
- **Not a publish.** One unofficial mention never reaches a reader by itself.
- **Not a delete.** An uncorroborated lead is KEPT — unpromoted means "not in the
  default view", never "thrown away" (Coverage Law, Confidence).

The hunt the ruling mandates, in its own order: the official venue/artist/group
page or calendar → ticket/aggregator pages → other public mentions. Only after
that does either publish condition get evaluated.

## Two units, deliberately different

Condition (b) counts **apparently independent people**, "best effort, no formal
affiliation" — not source *categories*, and not a formal independence proof.
That is a looser evidentiary standard than a legal one and a stricter counting
rule than "two rows": two posts from one person, or one person under two
handles, are one mention on a best-effort read.

## Interaction with the running gate — NOT yet implemented

`worker/gating.py`'s `multi_confirm_gate` does not implement this rule, in two
distinct ways, and the divergence is recorded as **R-083** rather than papered
over:

1. **Count.** The gate clears a non-anchor event at `min_sources = 2` distinct
   source classes. The ruling requires the originating mention **plus two
   additional** — three. The running gate is one short.
2. **Unit.** The gate counts distinct source CLASSES; the ruling counts distinct
   PEOPLE. Two independent Instagram posts are both class `social`, so today
   they count as one — the gate is simultaneously too permissive on (1) and too
   strict on (2).

Neither is fixed here: `gating.py` sits inside the armed ingest cron's runtime
closure (R-081/R-082), and this session is under a founder "no code" instruction
for this ruling. Nothing in the product currently claims to implement it.

## What is already consistent

The class-D → E/F claim path built this session (PR #203) does not violate the
ruling. A class-F human report is written `unverified` in a class
`is_first_party()` answers False for, so it HOLDS at the gate and never reaches
1Live.co on its own — "lead only, do not show", kept and not deleted. The claim
path is how a lead becomes condition (a): when the named venue or a known rep
hands the listing over and a human verifies them, that IS the corroboration.

## Follow-on ruling, same day — how each path DISPLAYS

The founder's second message settles what a reader sees, and adds a verbatim
string. Quoted exactly:

> Social publish rule (founder):
> - Official corroboration (a): list it. No extra warning.
> - Two+ independent unofficial mentions only (b): list it WITH
>   "We have not confirmed this with the venue, artist, or group.
>   Double-check before you go."
> - One unofficial mention: lead / hunt only. Not on 1Live.co.
>
> Priority remains A/B/E feeds and public pages. Path (b) is rare.

**The warning string is canon and must not be paraphrased**, exactly as the
existing verbatim copy strings are. Reproduced here as the single source:

```
We have not confirmed this with the venue, artist, or group. Double-check before you go.
```

Three display states, one per path:

| path | evidence | on 1Live.co | warning |
| --- | --- | --- | --- |
| (a) | named venue/artist/group, or a known rep, corroborates | listed | none — no extra warning, and no positive badge either |
| (b) | two or more additional apparently independent people | listed | the verbatim string above, WITH the row |
| lead | one unofficial mention | **not listed** | n/a — it is kept, hunted, never shown |

### Where this sits against the ratified design canon

The Master Design Brief's trust display rules are "NO badges / 'confirmed'
text; low-confidence = quiet icon → dismissible sheet + venue link". This
ruling does not overturn that — it is narrower and points the other way:

- Path (a) still gets **no badge**. "List it. No extra warning" is not a licence
  to add a positive trust marker; the brief's ban on "confirmed" text stands.
- Path (b) gets an explicit CAUTION SENTENCE, which is stronger than the brief's
  quiet-icon-plus-sheet treatment for a low-confidence row. That is the founder
  deliberately raising the floor for this one class of row, and where the two
  disagree on a path-(b) row, this ruling governs.

**Placement — ANSWERED by the founder, same day:**

> only the rare 'b' should have the note on both - that way people know at a
> glance it is not verified

So the warning goes on **both the card face and the detail page**, and on path
(b) ONLY. The reason is stated in the ruling itself and is the acceptance test
for any implementation: *at a glance*. A reader must be able to tell an
unconfirmed row from a confirmed one while scrolling, without opening anything —
which rules out putting the sentence only behind the "How we know" sheet, and
rules out a quiet icon standing in for it on the card.

Path (a) rows get nothing extra on either surface. Path (a) is the common case,
so the note stays rare by construction: if it starts appearing everywhere, that
is a signal the gate is mis-routing rows into (b), not that the copy needs
softening.

### The presumption for everything else, founder, same day

> the presumption for all other records is they are verified so there is no need
> for a card face or detail page 'verification' statement. We can retain the
> verification process on the platform as designed for audit and other purposes.

Two separate things, and the split is the whole point:

- **The reader's view.** A row that is not path (b) is presented as trustworthy
  by DEFAULT. No per-row verification statement on the card face or the detail
  page — no "verified", no "confirmed", and equally no hedge. Silence IS the
  statement. This agrees with the Master Design Brief's existing ban on badges
  and "confirmed" text rather than overriding it: the brief forbade the positive
  marker, and this forbids the negative one too, everywhere except path (b).
- **The platform's records.** The verification process stays exactly as
  designed — confidence states, the gate, the claim receipt, the audit trail.
  Retained for audit and internal purposes; simply not surfaced per row.

So the only per-row trust copy a reader ever sees is the path-(b) note. That is
what makes it work: a note that appears on one row in a hundred is read; a
qualifier on every row is wallpaper.

### One thing this does NOT settle — flagged, not assumed

Two live behaviours sit next to this and are deliberately NOT changed by it:

1. **`disputed` is untouched.** "Disputed shown-never-hidden" is a standing
   trust invariant (Coverage Law; CLAUDE.md prime directive 1). A disputed row
   is a CONTRADICTION warning, not a "verification statement", so this ruling
   does not reach it. Changing that is founder-crucial and would need saying
   outright.
2. **The existing `unverified` treatment on live /tonight is an open question.**
   `/tonight` today gives a low-confidence row a quiet icon leading to a
   dismissible sheet (Brief §trust display; shipped). Under this presumption an
   ordinary `unverified` row arguably should not carry that either — but that is
   a change to a LIVE consumer surface, so it is asked rather than assumed. See
   R-083.

### Priority, stated so nobody inverts it

"Priority remains A/B/E feeds and public pages. Path (b) is rare." The
social-hunt path is a completeness backstop, not a sourcing strategy: the
structured-open (A), public-HTML (B) and first-party (E) lanes come first, and
work on the hunt engine must not displace them.

## Related

- `ONE-LIVE-COVERAGE-LAW.md` — catalog greedy / views picky; "disputed shown-
  never-hidden"; unpromoted ≠ deleted.
- `docs/ops/VENUE_CLAIM_OUTREACH.md` — the 2026-09-01 copy rule (what we may SAY
  about a public page we read). This ruling governs what we may PUBLISH; the two
  are complementary and neither implies the other.
- `docs/RECORD.md` R-083 — the ratified-vs-running divergence and its trigger.
