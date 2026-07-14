# PO — the provocation battery (founder-ratified 2026-07-14)

Greppable summary: de Bono's "po" (provocative operation) made mechanical for
this repo's agents. Critical thinking (evaluator, friction attack, personas)
finds what is wrong with an existing idea; po GENERATES ideas criticism never
reaches, by asserting something deliberately wrong and "moving" from it.
Founder direction: run MANY operators, standalone and in combination, to
near-exhaust the option space before converging. Prompt generator:
`python tools/po_battery.py "<statement>"`. Fires at DIVERGENT moments only
(planning, architecture, design directions, Descriptor Foundry ideation, the
Friction pre-work's opening move) — never inside verification gates, and
NEVER into memory/trust surfaces: provocations are stimuli, not facts; no
provocation output enters docs/memory/, candidate data, or user-facing copy
except by surviving the normal gates as an ordinary, evidenced change.

## Why po, in one paragraph (the research)

De Bono's provocation tool ("po" from hypothesis/suppose/possible) makes a
statement known to be wrong or impossible, not as a proposal but as a stimulus
to force thinking off its established track ([Wikipedia, "Po (lateral thinking)" — de Bono, 1972/1992 canon](https://en.wikipedia.org/wiki/Po_(lateral_thinking));
[deBono.com, "Serious Creativity" article — de Bono's own summary](https://www.debono.com/serious-creativity-article)).
The canonical operator set is escape / reversal / exaggeration / distortion /
wishful thinking, plus random entry (juxtapose a random noun), and the value
is extracted by explicit MOVEMENT techniques, not judgement
([Mycoted creativity wiki, "Provocation" — practitioner reference](https://www.mycoted.com/Provocation);
[Peak Performance Center, "Lateral Thinking Techniques" — movement: extract-principle/difference/moment-to-moment/positive/circumstances](https://thepeakperformancecenter.com/educational-learning/thinking/types-of-thinking-2/lateral-thinking/lateral-thinking-techniques/);
[verrocchio Institute Innovation Wiki, "Random Input Technique" — de Bono 1968, publ. Serious Creativity 1992](https://www.innovation.wiki/en/method/random-input-technique/)).
Modern LLM-creativity research supports exactly the founder's "run many"
instruction: models under-diversify by default, and structured multi-operator
prompting with diverse roles measurably outperforms single-shot ideation
([arXiv 2511.07448, "LLMs for Scientific Idea Generation: A Creativity-Centered Survey", 2025](https://arxiv.org/html/2511.07448v2);
[arXiv 2602.20408, "Examining and Addressing Barriers to Diversity in LLM-Generated Ideas", 2026](https://arxiv.org/pdf/2602.20408v1);
[ACM Collective Intelligence 2025, "Can LLM-Powered Multi-Agent Systems Augment Human Creativity?"](https://dl.acm.org/doi/10.1145/3715928.3737479)).

## The operator battery (founder-directed: standalone AND combinations)

Given a target statement S (a plan step, an architecture choice, a design
assumption), first list S's taken-for-granted assumptions, then run EVERY
operator; each yields ≥1 provocation ("Po: ..."):

| # | Operator | How it provokes | Example on "venues publish their own events" |
|---|---|---|---|
| P1 | ESCAPE | Negate a taken-for-granted assumption | Po: venues do not know their own schedules |
| P2 | REVERSAL / INVERT / OPPOSITE | Swap subject↔object, or state the opposite relationship (the founder's invert/opposite/reverse family — do both directions when they differ) | Po: events publish their venues; Po: audiences schedule the venue |
| P3 | EXAGGERATION | Push any quantity absurdly up AND down | Po: a venue hosts 10,000 events tonight; Po: Austin has one event a year |
| P4 | DISTORTION | Scramble the time-order or the relationship structure | Po: the review happens before the event is extracted |
| P5 | WISHFUL | "Wouldn't it be nice if…" impossible fantasy | Po: every event verifies itself the moment it's spoken aloud |
| P6 | ABSURD | Founder's addition — the flat-out ridiculous version, past exaggeration into category error | Po: the events attend the people |
| P7 | RANDOM ENTRY | Juxtapose a random noun with S and force associations | Po: event trust + "lighthouse" |
| P8 | RANDOM + <operator> | Founder-directed combo: apply EACH of P1–P6 to the random word's associations (e.g. random "lighthouse" + REVERSAL: the ships warn the lighthouse) | ALL six combos, P8.1–P8.6, every battery — coverage is never sampled down |

Rules: (1) operators run cheap — this is Mechanical/Standard-tier work per
docs/MODEL_ROUTING.md; (2) every provocation gets written down BEFORE any
judging (judging mid-generation kills the tool); (3) a provocation is never
"answered" — it is MOVED from.

## Movement (how value is extracted — never skip this half)

For each provocation, apply at least two of de Bono's movement techniques:
- **Extract a principle** — what abstract principle would make this true? Can
  that principle be implemented sanely?
- **Focus on the difference** — what does the provoked world do differently
  from ours? Is any difference adoptable?
- **Moment to moment** — simulate the provoked world minute-by-minute; the
  operational details often contain the idea.
- **Positive aspects** — what is genuinely good in it, taken straight?
- **Special circumstances** — under what real conditions would this actually
  be the right design?

Harvest = a list of CANDIDATE ideas (each traceable to its provocation), which
then converge through the NORMAL machinery: friction attack, evaluator review,
trust gates, cost discipline. Po widens the funnel's mouth; it never touches
the funnel's filters.

## When it fires (and when it must not)

FIRES (mandatory): Friction pre-work opening move before irreversible actions
(deploy/migration/spend/prompt bump — battery first, attack second); sprint &
architecture planning; design-direction selection; Descriptor Foundry
candidate generation (P7/P8 especially).
MUST NOT fire: inside validate/trust_gate/evaluator verdicts (convergent
gates stay convergent); into docs/memory/ or any factual record (facts never
— a provocation recorded as a fact is a poisoning bug); on trivial mechanical
tasks (cost discipline — ritual is not insight).

## Session integration

- Generate the battery: `python tools/po_battery.py "<statement S>"` (prints
  all operator prompts incl. a random-entry word and combos; `--seed` for
  reproducibility in tests).
- Log: a po run on a founder-crucial decision appends its harvest (ideas kept
  + provocations that produced them) to the decision record / FRICTION_LOG
  entry, so the Kaizen ledger can count po-sourced ideas that survived gates
  (docs/KAIZEN.md measure M6).
