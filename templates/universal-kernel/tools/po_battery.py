#!/usr/bin/env python3
"""Po provocation-battery prompt generator (docs/skills/po_provocation.md).

Greppable summary: given a target statement, print the FULL de Bono
operator battery (escape, reversal, exaggeration,
distortion, wishful, absurd, random entry, random+operator combos) as
ready-to-run provocation prompts, each paired with the movement techniques
that extract value. Pure stdlib, no API calls — the agent (or founder) runs
the prompts; this tool guarantees no operator is forgotten and the random
entry is genuinely random (seedable for tests). Exit codes: 0 printed /
2 empty statement.
"""
from __future__ import annotations

import argparse
import random
import sys

# Curated random-entry nouns: concrete, image-rich, deliberately far from
# software and from this project's own domain, so the juxtaposition forces a
# real jump (random input works BECAUSE the word is unrelated — never pick a
# topical word).
RANDOM_WORDS = (
    "lighthouse", "glacier", "beehive", "anchor", "compass", "orchard",
    "volcano", "loom", "tide", "scaffold", "prism", "quarry",
    "carousel", "furnace", "riverbed", "telescope", "hourglass", "kite",
    "reef", "windmill", "lantern", "avalanche", "greenhouse", "pendulum",
)

MOVEMENT = (
    "extract a principle (what abstract rule would make this true — is that "
    "rule implementable sanely?)",
    "focus on the difference (what does the provoked world do differently — "
    "is any difference adoptable?)",
    "moment to moment (simulate the provoked world minute-by-minute; the "
    "operational detail often contains the idea)",
    "positive aspects (what is genuinely good in it, taken straight?)",
    "special circumstances (under what real conditions would this be the "
    "right design?)",
)

# (key, title, instruction) — the standalone operator battery. P8 combos are
# generated against these same instructions with the random word as substrate.
OPERATORS = (
    ("escape", "P1 ESCAPE",
     "List the taken-for-granted assumptions in the statement, then NEGATE "
     "each one: 'Po: <assumption is false>'."),
    ("reversal", "P2 REVERSAL / INVERT / OPPOSITE",
     "Swap subject and object, AND separately state the opposite "
     "relationship — produce both directions when they differ: "
     "'Po: <reversed statement>'."),
    ("exaggeration", "P3 EXAGGERATION",
     "Take every quantity or frequency in the statement and push it "
     "absurdly UP, then absurdly DOWN: 'Po: <10000x version>' and "
     "'Po: <1/10000th version>'."),
    ("distortion", "P4 DISTORTION",
     "Scramble the time-order or the relationship structure (who acts "
     "first, who depends on whom): 'Po: <distorted sequence>'."),
    ("wishful", "P5 WISHFUL",
     "Complete the fantasy 'Wouldn't it be nice if…' with something you "
     "know cannot occur: 'Po: <impossible wish>'."),
    ("absurd", "P6 ABSURD",
     "Go past exaggeration into category error — the flat-out ridiculous "
     "version where roles/objects do things they categorically cannot: "
     "'Po: <absurdity>'."),
)


def build_battery(statement: str, seed: int | None = None) -> str:
    """Return the FULL battery as printable text. Deterministic under seed.

    Deliberately not configurable downward (evaluator finding, PR #15 r1):
    the founder's contract is near-exhaustive coverage — every standalone
    operator AND every random×operator combo, every time. A knob that trims
    the battery is a fail-open door to false confidence.
    """
    statement = statement.strip()
    if not statement:
        raise ValueError("statement must be non-empty — po needs a target.")
    rng = random.Random(seed)
    word = rng.choice(RANDOM_WORDS)
    combo_ops = OPERATORS  # ALL of them — P8.1 through P8.6, no sampling

    lines = [
        "PO BATTERY (docs/skills/po_provocation.md) — run EVERY prompt, write",
        "every provocation down before judging any, then apply >=2 movement",
        "techniques per provocation. Provocations are stimuli, never facts.",
        "",
        f"TARGET STATEMENT: {statement}",
        "",
        "STEP 0 — ASSUMPTIONS: list everything the statement takes for granted.",
        "",
    ]
    for _, title, instruction in OPERATORS:
        lines += [f"{title}: {instruction}", ""]
    lines += [
        f"P7 RANDOM ENTRY (word: {word!r}): free-associate on {word!r} (its "
        "properties, behaviors, ecosystem), then force each association "
        f"against the statement: 'Po: <statement> + {word}'.",
        "",
    ]
    for i, (_, title, instruction) in enumerate(combo_ops, 1):
        lines += [
            f"P8.{i} RANDOM + {title.split(' ', 1)[1]}: apply the operator to "
            f"the {word!r} associations themselves, then map back to the "
            f"statement. Operator: {instruction}",
            "",
        ]
    lines += ["MOVEMENT (apply >=2 per provocation):"]
    lines += [f"  - {m}" for m in MOVEMENT]
    lines += [
        "",
        "HARVEST: candidate ideas, each traceable to its provocation. Converge",
        "through the normal gates (friction, evaluator, trust, cost) — po",
        "widens the funnel's mouth, never bypasses its filters.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the full po provocation battery for a statement."
    )
    parser.add_argument("statement", help="the target statement/plan/assumption")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed the random-entry word (tests/reproducibility)")
    args = parser.parse_args(argv)
    try:
        print(build_battery(args.statement, seed=args.seed))
    except ValueError as exc:
        print(f"po_battery: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
