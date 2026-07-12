# Visual baselines — how they're captured, compared, and updated

Greppable summary: baseline PNGs for `tools/visual_regression.py`'s pixel-diff
checks live here as `NAME.png`. Capture requires a real headless browser
(Playwright/Chromium or similar) — **not installed in the agent sandbox**;
the diff/compare engine itself is pure stdlib and fully tested without one.

## What's real vs. what's environment-dependent

- `tools/visual_regression.py`'s PNG decode + pixel-diff engine is pure
  stdlib (`zlib` + `struct`, no Pillow/browser dependency) and is fully
  exercised by `tests/test_visual_regression.py` (13 tests, all pass in any
  environment — decode round-trip, identical/different/noisy/dimension-
  mismatch comparisons, CLI exit codes).
- Actually *capturing* a fresh screenshot from a running OneLive web app
  requires a headless browser binary on `PATH` (e.g. `playwright screenshot`,
  or any CLI you template into `--capture-cmd`). **This sandbox has none
  installed**, and `tools/visual_regression.py` deliberately does not fall
  back to faking a screenshot when the binary is missing — it raises a loud
  `RuntimeError` naming the missing binary instead (covered by
  `test_capture_screenshot_fails_loudly_when_binary_missing`). This is the
  one piece of item 15 that cannot be exercised end-to-end inside this
  sandbox; running it for real requires an environment with `web/` actually
  booted (`npm run dev` in `web/`) plus a headless browser installed.

## Creating a new baseline

```bash
# One-time, in an environment with the web app running and a browser CLI
# installed (example uses a hypothetical `playwright screenshot` CLI):
tools/visual_regression.py capture-and-compare tonight-page \
  --url http://localhost:3000/tonight \
  --capture-cmd 'playwright screenshot {url} {out} --viewport-size=1280,800' \
  --update-baseline
```

This writes `tests/visual_baselines/tonight-page.png`. Commit that PNG.

## Checking against an existing baseline

```bash
tools/visual_regression.py capture-and-compare tonight-page \
  --url http://localhost:3000/tonight \
  --capture-cmd 'playwright screenshot {url} {out} --viewport-size=1280,800'
```

Exits 0 on match (within `--threshold`, default 1% of pixels), 1 on a real
diff, 2 on a hard failure (missing binary, capture command error, missing
baseline without `--update-baseline`).

## Comparing two PNGs directly (no capture step)

```bash
tools/visual_regression.py compare BASELINE.png CANDIDATE.png --threshold 0.01
```

## Tolerance model

A pixel counts as "differing" only if any RGB channel differs by more than
`pixel_tolerance` (default 8/255) — this absorbs harmless
compression/anti-aliasing noise between runs without masking a real visual
regression. The `--threshold` flag then caps what *fraction* of pixels may
differ before the whole comparison fails (default 1%).

## Updating a baseline intentionally (after an approved UI change)

Re-run the `capture-and-compare ... --update-baseline` command above and
commit the new PNG with a message explaining what changed and why (e.g.
"Update tonight-page baseline after redesigning the RSVP button").
