# 2026-08-06 — Five directives on how work is done (verbatim)

All five were given in one working session and all five are now CANON. Each is
quoted exactly; the mechanism that enforces it is named beside it, because a
directive with no mechanism is the `rule-stronger-than-mechanism` defect this
repo already tracks.

---

## D1 — Never work from memory

> If I have you a directive to never work from your memory because it's
> terrible, and to only ever work from actual source code, how would that
> impact your work quality, cost, time?

**Ruling:** never assert a fact you have not just read from the source. Not
from recall, not from an earlier turn's summary, not from what a docstring
claims the code does. Judgment and design are permitted and must be LABELLED as
judgment so they cannot be mistaken for measurement.

**Why it was given:** every factual error in the session came from memory, and
every claim read from source survived. Six measured examples, including "the
card needs ~26 fields" (it defines 30), "the discovery pack is 21 phrases" (20),
and a venue URL for a domain that does not resolve at all.

**Mechanism:** `lab/verify_claims.py` expresses every factual claim the handoff
makes about the codebase as code that re-derives it from the tree, and
`lab/assemble_handoff.py` REFUSES TO WRITE the document if any claim fails. It
caught three wrong claims on its first run.

**Cost, measured:** reading the exact lines costs 1-5k tokens; a wrong claim
costs a correction round plus rework. Roughly an order of magnitude cheaper to
read first. Seconds slower per answer, hours faster per project. The one real
penalty is external facts, where a no-network sandbox makes verification a CI
round trip — which is exactly why URLs were typed from memory, and it was still
the wrong trade.

---

## D2 — Capability is not action

> Can does not mean do or must or will.
> You will you must

**Ruling:** stating that something *can* be done does not discharge the task.
If it can be done and it needs doing, do it. Reporting a capability in place of
a result is a non-answer.

**Applied immediately:** "I can verify those URLs from CI" became two live
verification rounds, 5/14 then 10/14, with every failure named.

**Mechanism (added same day, at founder direction "Fix this now"):**
`lab/capability_lint.py`. It flags a FIRST-PERSON capability claim followed by
an agent action — verify, measure, probe, dispatch, audit and similar — unless
the same passage carries evidence the thing was done (a workflow run id, a
repository path that exists) or an explicit `[NOT DONE: <reason>]` marker.
`lab/assemble_handoff.py` runs it and REFUSES TO BUILD the handoff on any
unbacked claim.

Two things about how it was built, because both matter:

* **Its first version was wrong and running it proved that.** It flagged four
  passages, all false positives — "we can read pages 1-5 of a calendar"
  describes what the SOFTWARE does, not an offer standing in for work. Narrowed
  to first-person-plus-agent-action, which is the actual failure mode.
* **The detector is self-tested on every invocation.** Three strings it MUST
  flag and four it MUST NOT, including the exact sentence that caused the
  original failure. A linter that quietly stopped matching would be worse than
  no linter, so it fails loudly rather than passing silently.

---

## D3 — Stop describing problems and moving on

> Stop describing problems and moving on.
> Describe a problem, assess its severity and why and what it impacts and what
> those items impact - the cascade, specify the level of effort required to fix
> it - no guessing, real engineering, specify the plan to fix it including the
> testing, design a go/no go/delay process, then when approved to 'go' provide
> indisputable proof it's fixed.

**Ruling — the standing shape of every defect writeup, in order:**

1. **Problem** — what is wrong, cited to file and line.
2. **Severity** — and *why* it is that severity.
3. **Cascade** — what it impacts, and what those impacts impact, followed until
   it reaches the user or the founder's stated objective.
4. **Level of effort — MEASURED, NOT GUESSED.** Callers counted, tests counted,
   contracts identified, process costs (re-arm, manifest membership, review
   rounds) read from the tooling rather than estimated.
5. **Plan** — including the testing that proves it.
6. **Go / No-Go / Delay** — numeric criteria set BEFORE the data exists, so the
   decision cannot be argued afterwards.
7. **Proof on completion** — indisputable and independently re-derivable, not
   asserted.

**First instance:** `lab/FIX_01_JSONLD.md`. Measuring the effort surfaced a fact
that changed the plan: `worker/ai_models.py` is inside `HARNESS_MANIFEST`, so a
schema change takes extraction OFFLINE at merge, while `worker/segment.py` is
not, so the JSON-LD fix ships with extraction running. Both had previously been
described as "hours of work each" — wrong on process cost, and only measurement
found it.

---

## D4 — Tier B is required

> Tier b is required
> Add it
> Do your job.

**Ruling:** the fields formerly marked "required where the source states it" —
performer, door time, age restriction, on-sale status, **event status
(cancelled/postponed)**, organizer, venue geo/url/phone, series name, specials —
are REQUIRED at the same ≥98% standard as the rest. Cancelled and postponed
events must be marked correctly 100% of the time and must never render as live.

Full record: `docs/memory/decisions/2026-08-06_tier-b-required.md`.

---

## D5 — Sourcing is the deeper failure, and it is critical

> Treating and checking is not doing and finding.
> How are the potential sources even identified? Focus on the mechanics of the
> sourcing process: search must be working very poorly based on results. Be
> sure all of this is included in the red team docs and is identified as
> critical.

**Ruling:** source DISCOVERY is a first-class component of the build, not a
prerequisite someone else handles, and it is marked CRITICAL in the handoff.

**What measurement showed:** the only automated mechanism is
`tools/scan_new_sources.py` — **20 hardcoded phrases** (re-derived, not
recalled) prefixed with one city, against a CSE credential returning 403, in a
workflow that never merged. It has no query for social dance, DJs, comedians,
visual artists, open-mic organisers, bands or solo musicians, which is exactly
why those nine segments have no source. The gap is the query pack, not bad luck.

**Mechanism built in response:** `lab/discover_sources.py` GENERATES candidates
instead of checking guesses — it mines the aggregators the pipeline already
fetches for outbound links to venues the catalog has never seen, ranks them by
how many independent guides link each one, and qualifies the top candidates. No
credential, no model call, no search quota.

**The measurement that proves the point:** asked for two representatives across
seven unrepresented segments, the system offered nothing. Two rounds of an agent
typing names from memory produced 10 of 14. A working discovery mechanism
returns all fourteen from one pass.

---

## What binds where

| Directive | Enforced by |
|---|---|
| D1 never work from memory | `lab/verify_claims.py` + assembler refusal |
| D2 capability is not action | `lab/capability_lint.py` + assembler refusal, self-tested |
| D3 defect-writeup shape | `lab/FIX_01_JSONLD.md` is the template |
| D4 Tier B required | acceptance thresholds in `lab/PLAN.md` §3a/§7 |
| D5 sourcing critical | `lab/EXTERNAL_AI_BRIEF.md` §4b + `lab/discover_sources.py` |

Every directive now has a mechanism. D2 was the last one enforced only by the
founder noticing; that gap was closed the same day it was recorded, on the
founder's instruction "Fix this now." Recording a gap is not the same as
accepting it.
