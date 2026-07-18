# de Bono fidelity map — evidence for the practitioner's review

Greppable summary: a claim-by-claim mapping of this repo's hats + po
(`docs/hats/*`, `docs/skills/po_provocation.md`, `tools/po_battery.py`)
against de Bono's actual method, with citations. Built 2026-07-17 at founder
direction ("verify these are world class… not ad hoc or interpreted… or 'some
of'"). **This is Layer-A evidence, NOT a self-certification** — the Generator
authored the implementation and cannot grade its own fidelity. The reviewer is
the founder acting as the de Bono practitioner (Layer C — the human who *is*
the standard, independent of the author); the GPT-5.5 evaluator adjudicates it
on the PR (interim independent AI); the cross-family red team re-checks it once
a third-family key lands. Each row is here so a practitioner can confirm or
correct it — not take the author's word.

**How to review (founder = practitioner):** read the "de Bono canon" column,
then "our implementation," then mark the verdict — ✅ faithful, ✏️ correct me,
or ⚠️ this adaptation is not acceptable. Your marks are the sign-off.

## Part 1 — the six hats

| Hat | de Bono canon (cited) | Our implementation | Verdict to confirm |
|---|---|---|---|
| **White** | Information: what you have, need, and how to get it; neutral facts ([deBono summary][1], [Wikipedia][2]) | `white.md`: verifiable facts + unknowns named as loudly as knowns; IS deterministic tooling (reconciler, eval-harness, trust-gate); LLM only narrates | Faithful; arguably stricter (facts are machine-verified, not opined) |
| **Red** | Feelings, intuition, hunches — expressed WITHOUT justification ([Wikipedia][2], [NHS][3]) | `red.md`: the founder, permanently; "I don't like it is a complete verdict"; never an agent | Faithful to the no-justification rule; **adaptation:** Red = founder-only (stricter than de Bono, who lets anyone wear Red) |
| **Black** | Caution, critical judgment, risks — must give the LOGICAL reasons ([deBono summary][1], [NHS][3]) | `black.md`: the adversarial evaluator + friction attack; `file:line — issue — why it blocks`; findings only tighten | Faithful; de Bono calls it most valuable/most overused — our counter-measure (overrule-rate tracking) guards the overuse |
| **Yellow** | Positive view: benefits and values, logical-positive ([deBono summary][1], [Wikipedia][2]) | `yellow.md`: strongest honest case FOR; every benefit must NAME its mechanism; conditions forwarded, never risk-scored | Faithful; **enrichment candidate:** adopt de Bono's *Six Value Medals* (2005) taxonomy for structured value ([Six Value Medals][6]) |
| **Green** | Creativity, alternatives, new concepts, provocation ([deBono summary][1]) | `green.md` = the po battery; full operator set + movement; provocations are stimuli | Faithful (see Part 2) |
| **Blue** | Control: sets the agenda, focus, AND SEQUENCE; asks for summaries and next steps; thinking about thinking ([deBono summary][1], [Wikipedia][2]) | `blue.md`: process loop + the conflict-preserving merge + **sequence selection** + frame pre-registration | Faithful — de Bono's Blue explicitly owns the sequence, which our 2026-07-17 fix restored |

## Part 2 — po (the Green-hat engine)

| Element | de Bono canon (cited) | Our implementation | Verdict |
|---|---|---|---|
| **Operators** | Escape, reversal, exaggeration, distortion, wishful thinking, + random entry ([Lateral thinking — Wikipedia][4], [Peak Performance][5]) | `po_battery.py`: all five + random entry + random×operator combos; sampling MECHANICALLY refused | Faithful and COMPLETE — not "some of" |
| **"absurd" (P6)** | NOT in de Bono's five — a founder addition | Labelled a founder addition in `po_provocation.md` | Adaptation, transparently named |
| **Movement (harvest)** | Extract principle, focus on difference, moment-to-moment, positive aspects, special circumstances ([Peak Performance][5]) | All five present; "≥2 per provocation" | Faithful — de Bono's movement is a toolkit, ≥2 is a floor not a "some of" |
| **Provocation ≠ judgement** | Value is MOVEMENT value, not truth value; you move from a po, never evaluate it ([Lateral thinking — Wikipedia][4]) | Enforced: write before judging; "never answered, only moved from"; one-way valve | Faithful — the core discipline is intact |
| **"po" signalling** | The prefix "po" marks a statement as stimulus, not proposal ([Lateral thinking — Wikipedia][4]) | Every generated line is `Po: …` | Faithful |

## Part 3 — the disciplines (where fidelity is subtlest)

1. **Parallel thinking.** *Six Thinking Hats* (1985): everyone wears the SAME
   hat at the SAME time. *Parallel Thinking* (1994) expands to "several
   parallel tracks (preferably more than two), all contributing in parallel"
   ([Parallel Thinking][7]). — **Our sequential mode = the 1985 form
   exactly. Our dedicated-parallel mode (independent agents, merged) is an
   AI-specific extension of the 1994 direction, motivated by LLM-conformity
   research — an adaptation, named.**
2. **Sequences are purpose-fitted, not one fixed order.** Blue chooses the
   sequence; Yellow-before-Black nurtures fragile ideas; evaluation has its
   own order (one authoritative variant: Blue-Red-White-Yellow-Black-Green
   ([NHS][3])). — **Our 2026-07-17 fix has Blue SELECT the sequence per
   decision type. The specific orders we list are "faithful pending your
   confirmation" — sources give several, so no single one is THE canon.**
3. **One hat at a time / separation.** — **Faithful in sequential mode.**
4. **No hat output is evidence (our addition).** de Bono doesn't need this
   rule; we do, because a hat feeding the trust surface would poison it. —
   **A trust-invariant guard layered ON de Bono, not a change to his method.**

## Part 4 — the questions only the practitioner can rule on

These are the judgment calls I explicitly do NOT self-certify — your ruling
closes each:
1. Is the **independent-agents adaptation** of parallel thinking acceptable,
   or should dedicated-parallel mode run de Bono's literal same-hat form?
2. Is **Red = founder-only** the right stricter-than-de-Bono call?
3. Should **Yellow adopt the Six Value Medals** taxonomy, or stay generic?
4. Are the **sequence orders** we listed faithful, or do you correct them?
5. Is the **"absurd" operator** a keeper or a distraction from the canonical five?

## Sign-off

- [ ] Practitioner (founder) reviewed — marks recorded in the decision record.
- [ ] GPT-5.5 evaluator adjudicated (rides the PR).
- [ ] Cross-family red-team re-check (queued; blocked on a third-family key).

Until Part 4 is ruled and the boxes are checked, `README.md`'s fidelity section
stays "faithful pending verification." This map is the evidence; the ruling is
yours.

---
[1]: https://www.debono.com/six-thinking-hats-summary "Six Thinking Hats Summary — deBono.com"
[2]: https://en.wikipedia.org/wiki/Six_Thinking_Hats "Six Thinking Hats — Wikipedia"
[3]: https://library.hee.nhs.uk/patient-information/patient-information-resources/patient-information-resources/six-thinking-hats "Six Thinking Hats — NHS England"
[4]: https://en.wikipedia.org/wiki/Lateral_thinking "Lateral thinking — Wikipedia"
[5]: https://thepeakperformancecenter.com/educational-learning/thinking/types-of-thinking-2/lateral-thinking/lateral-thinking-techniques/ "Lateral Thinking Techniques — Peak Performance Center"
[6]: https://www.debono.com/Books/six-value-medals "The Six Value Medals — deBono.com"
[7]: https://www.goodreads.com/en/book/show/1594773 "Parallel Thinking (1994) — de Bono"
