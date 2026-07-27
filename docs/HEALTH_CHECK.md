# HEALTH_CHECK — the recurring whole-system checkup

**Status: CANON.** Founder-directed 2026-07-26: *"make this a recurring action as
part of a world class health check up of the entire system."* The mechanism is
`tools/health_check.py`; the snapshots live in `docs/health/`; the first one is the
before/after accounting of the 2026-07-26 revamp.

---

## Read this first: what is grounded, and what is not

This document is built on **primary sources already fetched, quoted and ratified in
`docs/WORLD_CLASS.md`** (40 distinct primary URLs with quoted passages). Every
clause below that claims authority names the on-disk citation it rests on.

**It is NOT built on fresh research, and it cannot be, from this environment.** The
founder's primary-source gate is explicit (`docs/OPERATING_RULES.md` §1, ratified
2026-07-24): *"the research does NOT proceed on excerpts, mirrors, search
summaries, or memory — however heavily caveated."* Every attempt to fetch a primary
from this sandbox returns **HTTP 403** — `dora.dev`, `sre.google` and
`google.github.io` were each tried on 2026-07-26 and each refused at the proxy.
Web *search* works and returns summaries; using them here would be exactly the
defect the gate names, so they are not used.

The blocker report and the smallest founder action are in the final section. What
follows is therefore **the checkup this project can honestly justify today**, not
a survey of industry practice — and that distinction is stated rather than blurred.

---

## Why a recurring checkup at all — the on-disk warrant

Two clauses of the ratified bar mandate it, and both were written down and then
never performed until 2026-07-26:

> **§0.8** *"The harness that grows monotonically is a harness that has stopped
> reading. Re-read your harness against each new release and delete anything the
> model now does for free."*
> — Karpathy, LOOPS §VIII, via `docs/WORLD_CLASS.md` §0.8

> **§0.9** *"When coding stops being the bottleneck, planning becomes the
> bottleneck. When planning is solved, verification becomes the bottleneck… If
> everything is going smoothly, you are not looking carefully enough."*
> — Karpathy, LOOPS §IX, via `docs/WORLD_CLASS.md` §0.9

§0.8 is a **pruning** obligation and §0.9 is a **re-diagnosis** obligation. Neither
can be discharged by a passing test suite, because both ask a question no gate
asks: *is the system as a whole getting better, and is the thing limiting us still
the thing we think it is?* That is what this checkup answers.

The 2026-07-26 audit is the evidence that intent alone does not discharge them.
§0.8 had been canon since 2026-07-12 and the audit was its **first** execution —
which the audit found by reading §0.8's own self-assessment, where the project had
written *"0.8 harness-pruning never done."*

## Why a tool and not a written ritual

Because the audit's own numbers rotted within hours. Three of its figures were
wrong by the time its independent reviewer read them — a test count, a word-count
reduction, and a check count — and the reviewer correctly classified the stale
copies as *the false-confidence class recurring inside the fix for that class*.

A metric a human retypes is a metric that lies eventually. So the checkup is a
command, its output is committed, and the numbers are never transcribed by hand:

```bash
python tools/health_check.py --baseline <last-snapshot-sha> \
  --out docs/health/$(date +%F)_snapshot.md
```

No network, no database, no model. Anyone running it on the same commit gets the
same answer, which is the property that makes a trend meaningful.

---

## What it measures, and why each number earns its place

| Metric | Why it matters | Warrant |
|---|---|---|
| **Code lines by category** — product · tests · harness · brain · off-mission | The audit's central finding was a ratio, not a defect: harness code at 3.0× the product it serves. A build optimising itself shows up here first and nowhere else. | §1.10 Ousterhout — complexity as *"change amplification, cognitive load, unknown unknowns"* |
| **Prose words, all Markdown** | The founder's original complaint. It also catches this session's own uncomfortable fact: total prose went **up** 10%. A metric that only flatters the last change is not a metric. | §0.8 (pruning) |
| **Read-before-code words and document count** | The surface a builder must hold before writing a line. Measured against the set that was *actually binding* at each ref, never today's list against a past that lacked it. | §1.3 *"'Too complex' usually means 'can't be understood quickly by code readers'"* |
| **BAR rows by status** — MET / NOT MET / UNMEASURED / NOT BUILT, with section P counted separately | The definition of done, graded. The P split is load-bearing: it is what exposed that the machine is in better shape than the experience. | `docs/BAR.md` §0 |
| **RECORD rows open vs resolved** | Declared deviations. Rising is not automatically bad — an undeclared gap is invisible — but rising *while nothing resolves* is debt accumulating. | §F7, and `tools/deferral_scan.py` |
| **Red classes indexed** | Ways this project has actually been wrong. Growth is learning; growth without trigger specificity is an index that fires on everything and discriminates nothing (already an open follow-up). | §J6 |
| **Escaped defects (M3)** | Counted the way `docs/KAIZEN.md` defines them, so the checkup and the Kaizen gate cannot disagree about whether a defect escaped. | §G4, absolute-zero goal |
| **Unwired modules** — first-party modules imported by nothing but tests | The mechanical form of *"wire it or delete it."* Previously discoverable only by hand; **16 found** on first run, including two the audit had found manually. | §F5; §1.9 Beck's *"fewest elements"* |
| **validate check count** | A gate inventory. A check silently disappearing is the worst possible regression and nothing else would notice. | §J5 |
| **Gate/threshold files changed vs baseline** | Turns *"no gate was weakened"* from a claim into a command. `0` is the proof. | Charter: gate-threshold relaxations are founder-crucial |

### What it deliberately does **not** do

**It does not pass or fail.** It is a thermometer, not a gate. Wiring it into
`tools/validate` as a blocking check would be a gate change, which is
founder-crucial — and it would also be wrong: these numbers need *judgement*, not
a threshold. "Prose went up 10%" is sometimes correct and sometimes rot, and only a
reader can tell which.

**It never reports a number it did not compute.** Any metric it cannot measure
prints as `UNVERIFIED` with the reason, in both columns, never as a zero. That is
the founding anti-pattern applied to measurement: *"we could not measure" must
never look identical to "the number is fine."* Pinned by
`tests/test_health_check.py`.

---

## The cadence

Derived from existing canon, not invented: `docs/OPERATING_RULES.md` §2b already
establishes a **weekly Kaizen loop** as the moment to *"step back from feature work
and improve the system that builds the system."* The checkup attaches to it rather
than creating a competing ritual.

| When | Depth | What happens |
|---|---|---|
| **Every session close** | Snapshot only | Run the tool; if any number moved sharply, say so in the session record. Costs seconds. |
| **Weekly**, with the Kaizen loop | Read the trend | Compare against last week's snapshot. Name what moved and why. Triage any *new* unwired module before it becomes furniture. |
| **Monthly** | Full checkup | Re-grade every `docs/BAR.md` row against reality, refresh statuses, execute the §0.8 pruning pass (delete harness that stopped earning its place), and **name the current bottleneck explicitly** per §0.9. Write the verdict into the snapshot. |
| **Before any launch or go-live** | Full checkup, blocking by judgement | The founder reads it before the irreversible action. |

**The monthly one has teeth by convention, not by gate:** a full checkup that names
no bottleneck has not been done. §0.9's warning is that smooth-looking is a
looking problem, not a health signal.

## What a bad checkup looks like

These are the shapes to act on, written down now so they are recognised later
rather than rationalised:

1. **Harness/product ratio rising while product code is flat** — the build is
   optimising itself. This is the 2026-07-26 finding and the reason the ratio is
   the first row.
2. **Unwired modules rising** — work is being completed and not connected. Each new
   one is a subsystem that will be defended later because it is "already built".
3. **UNMEASURED rows flat over months** — the bar is decorative in that area.
   Twelve rows are unmeasured today; five of them are the experience users get.
4. **RECORD open rising while resolved is flat** — deviations are being declared
   instead of fixed. Declaring is better than hiding and worse than closing.
5. **Prose rising faster than product code** — the failure mode the founder named
   in the first place.
6. **A check disappearing from `validate`** — treat as an incident, not a diff.

## What it cannot see, stated so nobody trusts it too far

- **Runtime behaviour.** It reads the repository, not production. Core Web Vitals,
  feed freshness and the ten-second answer (`BAR` P1, P2, C1) are invisible to it
  and must be measured against the deployed site.
- **Whether the product is any good.** No structural metric can grade §0. That is
  the brief's 8-criterion rubric and `docs/V1.md` criteria 6–7, both human.
- **Live delivery facts** — open PR ages, cron delivery rates, database row counts.
  All need network or credentials this environment lacks; they belong in the
  reconciler's remit, and when absent must be reported `UNVERIFIED`.

---

## BLOCKER REPORT — the research half, and what unblocks it

Per the primary-source gate, this thread is **stopped**, not caveated. Naming
exactly what was inaccessible:

| Primary needed | Why | Status from this sandbox |
|---|---|---|
| `dora.dev` four-keys guidance | `docs/WORLD_CLASS.md` §7.5–7.8 records the four keys but marks the **elite/high/medium/low numeric thresholds as `n.a.` — "not on fetched page"**. Without them the DORA rows cannot become numbers, which is exactly what a bar requires. | **403 at the proxy**, 2026-07-26 |
| `sre.google` SRE book — production readiness review | The nearest established analogue to a recurring whole-system checkup; would tell us what a mature version of this document contains. | **403** |
| `google.github.io/eng-practices` | Already quoted in `WORLD_CLASS.md` from a prior session, but a re-read would confirm nothing has moved. | **403** |
| ISO/IEC 25010 product-quality model | The standard taxonomy for "quality attributes"; would test whether the bar's A–J sections have a gap. | Paywalled — not fetchable at any price from here |
| SEI **ATAM** architecture evaluation method | The recognised method for *architecture* review specifically, which this checkup does not attempt. | Not fetched |

**Smallest founder action, cheapest first:**

1. **Paste the DORA thresholds table** (or the page text) into a message. That alone
   converts `WORLD_CLASS.md` §7.5–7.8 from `n.a.` to four real numbers and lets the
   checkup grade delivery performance. Highest value per second of your time.
2. If you want the wider survey, **allow egress to `dora.dev`, `sre.google` and
   `google.github.io`** in the environment's network policy, and I will fetch the
   primaries and revise this document with proper citations.
3. ISO 25010 needs a purchased copy; I would not spend on it before v1.

Until then this document is honest about its own footing: **grounded in on-disk
ratified primaries, engineering judgement where it says so, and explicitly not a
literature review.** Recorded as R-065.
