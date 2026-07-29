Founder-ratified 2026-07-29 ("make it green, not red-compensated"): the golden-exam classifier now recognizes the image/vision extraction path as a SEPARATE, deliberately-uncertified harness and does NOT refuse changes confined to it. This removes a chronic "red-but-compensated" check without weakening protection of the certified text extractor.

## The principle (canon)

A gate that is permanently red-and-explained-away is a broken gate: it trains
everyone to scroll past red, which is how a real red eventually hides in the
noise. Same disease as ceremony. Every gate should either block for a real
reason or be green — never "red, but the charter compensates it elsewhere."

## What was wrong

`tools/classify_extraction_surface.py::on_surface` flagged **anything** under
`ai/` as certified-extraction surface. The golden-exam exists to protect the
attended-exam-**certified text extractor**; that catch-all also swept up
`ai/vision_provider.py`, a genuinely separate module the text exam never runs
and the certified extractor never imports. So every vision PR got a designed
refusal that the charter then patched as "NOT-manifest-bound, compensated by
the adversarial review" — a standing red with no real cause.

## The fix

`SEPARATE_UNCERTIFIED_HARNESS = {"ai/vision_provider.py"}` is excluded from
`on_surface` before the `ai/` catch-all. A vision-only change now classifies
clean (green). The list is explicit and narrow: adding a new vision-path file
is a deliberate gate-scoping change (founder-crucial).

## Why this is safe (protection unchanged)

- The certified text harness (`ai/prompts.py`, `ai/claude_provider.py`,
  `ai/golden_exam.py`, `ai/provider.py`, `worker/ai_models.py`, the runner,
  the workflows, …) is UNCHANGED — any change to it still refuses and still
  demands a fresh attended exam. `test_vision_exclusion_is_no_smuggle_path`
  proves a diff touching the vision file AND a certified file still refuses.
- The vision path keeps its OWN compensating controls: fail-closed OFF by
  default, the human promote gate (AI never publishes), the ops-visible
  `extractor="vision"` provenance marker, and the mandatory adversarial review
  (no path filter). Its trust story is those controls, not the text exam.
- If vision extraction is ever certified in its own right (its own attended
  exam), that is a separate, additive step; nothing here presumes it.

## Note

The PR that installs this edits the classifier (`tools/classify_extraction_surface.py`),
which is itself extraction surface (but NOT manifest-bound), so golden-exam
shows its one-time compensated refusal on that PR — the usual bootstrap for a
gate change. After it merges, vision-only PRs are green.
