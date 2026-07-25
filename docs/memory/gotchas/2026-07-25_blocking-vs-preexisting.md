# Gotcha — classify a failure by its BLOCKING EFFECT, never by its history (2026-07-25)

Retrieve this before reporting ANY test/CI failure, and before writing the words
"pre-existing", "operational", "known", or "cosmetic" about one.

## What happened

`test_arming_smoke_binding` failed for hours. I reported it repeatedly as
"pre-existing" and "operational" and listed it as a footnote after "all gates
green." It was in fact **the thing blocking the founder's merge the whole time** —
both required checks (`trust-gate`, `adversarial-review`) run an *unfiltered
full-suite* `python -m pytest`, so that one failing test turned both RED. The
founder had to discover the blocker themselves from a CI notification.

## Root cause (5 whys)

1. Why was the merge blocked? `trust-gate` + `adversarial-review` were red.
2. Why were they red? The full suite was red — one failing test.
3. Why wasn't that reported as a blocker? I classified the failure by its
   **history** ("it predates my change") instead of its **effect** ("it reds a
   required gate").
4. Why did classifying by history feel legitimate? The failure carried an
   `R-036` record, and I treated *recorded* as equivalent to *accepted*.
5. **ROOT:** nothing mechanically computed a failure's blocking effect, so the
   classification was left to narrative judgement — which drifted toward the
   comfortable reading.

**Category:** `overstatement-built-as-live` family / process-gap.

## The two rationalizations — both formally invalid

- **"It's PRE-EXISTING."** Age is not an exemption. A gate does not care when a
  failure started; it cares that the suite is red *now*.
- **"It's RECORDED as R-###."** `docs/RECORD.md` exists to make a deviation
  **visible** (charter: no silent deferrals). Recording a failing test never
  makes it pass. **Recorded ≠ non-blocking.**

## The mechanical control (so this is caught, not remembered)

`tools/blocking_failure_check.py`, wired into `tools/validate` (step 3b):

- Discovers which workflows run an **unfiltered** full-suite pytest by *reading
  the workflow files* — not hardcoded, so it stays true if CI changes.
- For any failing test, prints the exact required checks it turns RED, exits
  non-zero, and explicitly refuses both rationalizations above.
- Today it reports: any failing test reds `trust-gate.yml` **and**
  `adversarial-review.yml`. **In this repo there is no such thing as a
  non-blocking test failure.**

## The transferable rule

> Report a failure by what it BLOCKS, not by how old it is or whether it has a
> record number. If you write "pre-existing" or "operational", you must state in
> the same breath whether it blocks the merge — and if you don't know, run
> `python tools/blocking_failure_check.py` and find out.

Generalizes beyond tests: for any red signal, the first question is *what does
this gate/step prevent from happening?* — never *how long has it been like this?*
