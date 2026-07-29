#!/usr/bin/env python3
"""Resolve a loop-stage label to the cheapest-capable model id (docs/MODEL_ROUTING.md).

Greppable summary: mechanical stage→model resolver for the cost-routing
policy — `python tools/model_router.py <stage>` prints the model id for
`mechanical` / `standard` / `critical` / `extraction` / `evaluator`. Each
stage is env-overridable via KERNEL_MODEL_<STAGE> (evaluator also honors
the pre-existing OPENAI_REVIEW_MODEL); unknown stages fail loud (a typo must
never silently route to an expensive or incapable tier). Exit codes per
tools/README.md: 0 resolved / 2 unknown stage or empty override.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

# Routing VALUES + the ratification flag live in tools/routing_data.py — a
# PURE DATA module (docstring + constant assignments only) so a release gate
# can certify routing changes as AST-extracted data without executing subject
# code (evaluator r13). Re-exported here so every existing import path keeps
# working; the flag is read via this module's global so test monkeypatching
# stays effective.
try:
    from tools.routing_data import (  # noqa: F401  (re-exports)
        EXTRACTION_THRESHOLD_RATIFIED,
        STAGE_MODELS,
    )
except ImportError:
    # Direct-script invocation (`python tools/model_router.py <stage>`) puts
    # tools/ — not the repo root — on sys.path, so the package import above
    # cannot resolve. Add the repo root and retry ONCE. A second failure is a
    # HARD error (the traceback propagates): the resolver must never fall back
    # to a locally-guessed table, because a drifting duplicate of the routing
    # values is exactly the failure this split exists to prevent.
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from tools.routing_data import (  # noqa: F401  (re-exports)
        EXTRACTION_THRESHOLD_RATIFIED,
        STAGE_MODELS,
    )

# Model ids across vendors are ASCII: letters/digits/dot/underscore/colon/
# slash/hyphen. Anything else (newlines, spaces, shell metacharacters) is a
# misconfiguration caught HERE, not later at an API or inside a CI $GITHUB_OUTPUT
# write where a newline could smuggle extra output lines.
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")

# Extra env names honored per stage, after KERNEL_MODEL_<STAGE>, for
# compatibility with wiring that predates this router. Vendor-owned names
# (OPENAI_*) keep their vendor spelling; project-owned ones carry the KERNEL_
# prefix.
_LEGACY_ENV = {
    "evaluator": "OPENAI_REVIEW_MODEL",
    "extraction": "KERNEL_CLAUDE_MODEL",
}

# The charter (CLAUDE.md): the evaluator grades the generator's work, so it
# must never
# be the generator's model family — a Claude evaluator would be self-grading.
# Enforced here (fail-closed), not by operator discipline.
_GENERATOR_FAMILY_MARKERS = ("claude", "anthropic")


def _check_evaluator_separation(stage: str, model: str, source: str) -> None:
    if stage == "evaluator" and any(m in model.lower() for m in _GENERATOR_FAMILY_MARKERS):
        raise ValueError(
            f"{source} resolves the evaluator stage to {model!r} — a "
            "generator-family (Claude/Anthropic) model must never grade its "
            "own work (write/grade separation, CLAUDE.md). Use a non-Claude "
            "model id."
        )


def resolve_model(stage: str) -> str:
    """Return the model id for a stage. Unknown stage or bad override raises.

    Precedence: KERNEL_MODEL_<STAGE> > legacy env (evaluator:
    OPENAI_REVIEW_MODEL) > policy default. A present-but-empty (or
    whitespace-only) override is a misconfiguration and fails loud (the
    PR #11/#12 empty-env lesson). The evaluator stage additionally rejects
    Claude/Anthropic model ids regardless of source — write/grade separation
    is an invariant, not a default.
    """
    if stage not in STAGE_MODELS:
        raise KeyError(
            f"unknown routing stage {stage!r} — valid stages: "
            f"{', '.join(sorted(STAGE_MODELS))} (docs/MODEL_ROUTING.md)"
        )
    if stage == "extraction" and EXTRACTION_THRESHOLD_RATIFIED is not True:
        # Fail-closed on the EXACT boolean, never truthiness (mirrors the r26
        # provider-level invariant): a misconfigured truthy non-bool such as
        # "False", "yes", or 1 must keep extraction CLOSED, not open it. This is
        # an auth/fail-closed gate — only the literal `True` unlocks extraction.
        # Fail-closed regardless of overrides: the block is about the missing
        # quality gate, not about which model would run. The kernel ships this
        # flag False on purpose — a template has never sat an exam, and an
        # uncertified stage must route nowhere.
        raise ValueError(
            "extraction routing is fail-closed until this project's own "
            "release-blocking quality gate for the extraction stage ships "
            "and the routed model PASSES it. Flip "
            "EXTRACTION_THRESHOLD_RATIFIED to the literal True in "
            "tools/routing_data.py only as the record of a passed attended "
            "exam — never to unblock a run."
        )
    for env_name in (f"KERNEL_MODEL_{stage.upper()}", _LEGACY_ENV.get(stage, "")):
        if not env_name:
            continue
        value = os.environ.get(env_name)
        if value is None:
            continue
        if value.strip() == "":
            raise ValueError(
                f"{env_name} is set but empty/whitespace — set a model id or "
                "unset it entirely; empty must never silently mean 'default'."
            )
        value = value.strip()
        if not _MODEL_ID_RE.fullmatch(value):
            raise ValueError(
                f"{env_name} value {value!r} is not a plausible model id "
                "(letters/digits/._:/- only) — refusing to pass it downstream."
            )
        _check_evaluator_separation(stage, value, env_name)
        return value
    default = STAGE_MODELS[stage]
    _check_evaluator_separation(stage, default, "STAGE_MODELS default")
    return default


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the cheapest-capable model id for a loop stage "
                    "(policy: the project's docs/MODEL_ROUTING.md)."
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
