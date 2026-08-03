# Decision — all handoffs are world-class; currency is proven, not asserted

One-line: founder-directed — codify a WORLD-CLASS HANDOFF standard (with an explicit definition) and the PROOF discipline (currency/completeness claims must show re-runnable evidence, never be asserted). Canon: `docs/ops/HANDOFF_STANDARD.md`; rule pointer: `docs/OPERATING_RULES.md` §6a.5.

**Date:** 2026-08-03. **Authority:** founder-directed, verbatim: *"Save to canon and repo and arc that all handoffs are to be world class with clarity about what that means. Ensure the proof piece is also codified and saved."* Follows the same day's *"confirm all is current - I mean everything and you must prove it."*

## What is codified

1. **World-class handoff (definition, not a vibe).** `docs/ops/HANDOFF_STANDARD.md` §1 defines it as eight required properties: self-contained · disk-is-truth · current-AND-proven · prioritized actionable remaining work · failure memory · interaction contract · decisions separated by ownership (founder HOLDS vs founder-crucial vs agent-decidable) · plain/honest/linked. Missing any one is a defect. The live artifact `docs/ops/NEXT_SESSION_KICKOFF_PROMPT.md` must meet it and is rewritten to it at every session close.

2. **Proof discipline.** `HANDOFF_STANDARD.md` §2 + OPERATING_RULES §6a.5: a claim of currency/completeness/done/green is never asserted — it SHOWS the evidence a reader can re-run. This generalizes §1 ("findings are claims until verified") to every such claim. The standing, saved proofs: `tools/staleness_check.py` (blocking); marker == `git rev-parse origin/master`; `tests/test_live_state_consistency.py`; `bash tools/validate` RESULT with no gate FAILED; PR/DB facts via connectors (UNVERIFIED when absent, never guessed).

## Why

Handoffs are how work survives ephemeral sessions and containers; a weak one silently loses context and forces re-discovery. And "everything is current" asserted from memory is exactly how STATE.md rotted ~50 PRs — the fix is to make currency a shown, re-runnable fact, not a sentence. The founder had to demand proof; from now the proof is the default.

## The transferable rule

Before you hand off or claim done: run the proofs, paste the evidence, and check the receiver could act from the handoff alone. If a property is missing or a proof won't run, the handoff/claim is not finished.
