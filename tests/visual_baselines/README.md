# Visual baselines — how they're captured, compared, and updated

Greppable summary: baseline PNGs for the /tonight visual-regression gate
(R-002, resolved 2026-08-03) live here as `NAME.png`. They are captured by
`tools/visual_check.sh` from a local production boot in SYNTHETIC QA fixture
mode and pixel-diffed by `tools/visual_regression.py`. CI enforces them on
every web-touching PR via `.github/workflows/visual-regression.yml`.

## The determinism contract (why these baselines never flake)

A pixel gate over LIVE data would cry wolf — real events change nightly and
the feed is clock-driven. So capture runs against a state that cannot drift:

1. **Data + clock** — `ONELIVE_QA_FIXTURES=1` renders committed SYNTHETIC
   fixtures (`web/qa/fixtures.ts`: fictional acts/venues, all four confidence
   states incl. disputed, both Spark Line registers, all three density tiers)
   with the clock frozen at `QA_FROZEN_NOW_MS`. The mode is fail-closed off
   everywhere else and renders a visible "SYNTHETIC QA FIXTURES" banner.
2. **Timezone** — `TZ=America/Chicago` on both the server and the browser
   (day-bucket boundaries use local time; labels format in CT).
3. **Renderer** — Chromium build **1194** (= Playwright **1.56.0**) on Linux.
   CI installs exactly that build; recapture baselines only with it. Bump the
   pin ONLY together with freshly captured baselines in the same PR.
4. **Network** — fixtures carry no external URLs, and the capture browser
   maps every non-localhost host to a dead address, so online and offline
   environments render identically.

Proven at capture time: an independent boot + fresh capture compared
0/329160 pixels different against these baselines.

## The pages

Defined in `tools/visual_check.sh` (`PAGES=`): the mobile feed (390×844),
the desktop feed (1280×900), the disputed-event detail (its disclosure opens
by default — that behavior is part of the pinned pixels), and the
cancelled-event detail (the status-note surface).

## Running it

```bash
# Compare current rendering against the committed baselines (what CI does):
bash tools/visual_check.sh

# After an APPROVED visual change: recapture + commit in the SAME PR,
# so the reviewer sees the pixel change alongside the code change:
bash tools/visual_check.sh --update
```

Requires `web/node_modules` (npm ci) and a Chromium (`ONELIVE_CHROMIUM=` to
point at one; defaults to the sandbox's `/opt/pw-browsers/chromium`).
`tools/validate` runs the compare automatically when the environment has
both; a browserless environment SKIPs loud, bound to record row R-068.

## Tolerance model

A pixel counts as "differing" only if any RGB channel differs by more than
`pixel_tolerance` (default 8/255) — this absorbs harmless anti-aliasing
noise without masking a real regression. `--threshold` then caps what
*fraction* of pixels may differ before the comparison fails (default 1%).

## On a CI failure

The workflow uploads `NAME.CANDIDATE.png` artifacts next to each diverged
baseline so the reviewer can SEE the change. Either fix the regression, or —
if the change is intended — recapture with `--update` and commit the new
PNGs in the same PR with a message saying what changed and why.

## The low-level engine

`tools/visual_regression.py` (pure-stdlib PNG decode + diff; 13 unit tests)
also supports direct use: `compare A.png B.png` or `capture-and-compare NAME
--url URL --capture-cmd 'CMD {url} {out}'`, and fails loud (exit 2) when the
capture binary is missing — never a faked screenshot.
