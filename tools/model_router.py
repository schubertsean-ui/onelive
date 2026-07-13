#!/usr/bin/env python3
"""Resolve a loop-stage label to the cheapest-capable model id (docs/MODEL_ROUTING.md).

Greppable summary: mechanical stage→model resolver for the cost-routing
policy — `python tools/model_router.py <stage>` prints the model id for
`mechanical` / `standard` / `critical` / `extraction` / `evaluator`. Each
stage is env-overridable via ONELIVE_MODEL_<STAGE> (evaluator also honors
the pre-existing OPENAI_REVIEW_MODEL); unknown stages fail loud (a typo must
never silently route to an expensive or incapable tier). Exit codes per
tools/README.md: 0 resolved / 2 unknown stage or empty override.
"""
from __future__ import annotations

import argparse
import os
import sys

# Cheapest-capable defaults, ratified via docs/MODEL_ROUTING.md. Change them
# THERE first — this table implements the doc, not the other way around.
STAGE_MODELS = {
    "mechanical": "claude-haiku-4-5",
    "standard": "claude-sonnet-4-6",
    "critical": "claude-opus-4-8",
    # Provisional cheap tier, governed by eval-harness thresholds (§11.2):
    # keeps its slot while golden-set gates pass, escalates when they fail.
    "extraction": "claude-haiku-4-5",
    # Non-Claude by charter (§0.2) — cost never downgrades the grader.
    "evaluator": "gpt-5.5",
}

# Extra env names honored per stage, after ONELIVE_MODEL_<STAGE>, for
# compatibility with wiring that predates this router.
_LEGACY_ENV = {"evaluator": "OPENAI_REVIEW_MODEL"}


def resolve_model(stage: str) -> str:
    """Return the model id for a stage. Unknown stage or empty override raises.

    Precedence: ONELIVE_MODEL_<STAGE> > legacy env (evaluator:
    OPENAI_REVIEW_MODEL) > policy default. A present-but-empty override is a
    misconfiguration and fails loud (the PR #11/#12 empty-env lesson).
    """
    if stage not in STAGE_MODELS:
        raise KeyError(
            f"unknown routing stage {stage!r} — valid stages: "
            f"{', '.join(sorted(STAGE_MODELS))} (docs/MODEL_ROUTING.md)"
        )
    for env_name in (f"ONELIVE_MODEL_{stage.upper()}", _LEGACY_ENV.get(stage, "")):
        if not env_name:
            continue
        value = os.environ.get(env_name)
        if value is None:
            continue
        if value == "":
            raise ValueError(
                f"{env_name} is set but empty — set a model id or unset it "
                "entirely; empty must never silently mean 'default'."
            )
        return value
    return STAGE_MODELS[stage]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the cheapest-capable model id for a loop stage "
                    "(policy: docs/MODEL_ROUTING.md)."
    )
    parser.add_argument("stage", help=f"one of: {', '.join(sorted(STAGE_MODELS))}")
    args = parser.parse_args(argv)
    try:
        print(resolve_model(args.stage))
    except (KeyError, ValueError) as exc:
        print(f"model_router: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
