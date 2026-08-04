#!/usr/bin/env bash
# Visual regression, end to end (R-002): boot /tonight in SYNTHETIC QA fixture
# mode (web/qa/fixtures.ts — frozen clock, fictional data, visible banner),
# screenshot the named pages with headless Chromium, and pixel-diff each against
# its committed baseline via tools/visual_regression.py.
#
# Determinism contract (all three pinned, or pixels drift):
#   1. DATA+CLOCK — ONELIVE_QA_FIXTURES=1 (fixtures + frozen QA_FROZEN_NOW_MS).
#   2. TIMEZONE   — TZ=America/Chicago on BOTH the server and the browser
#                   (day-bucket boundaries use local time; labels format in CT).
#   3. RENDERER   — Chromium build 1194 (= Playwright 1.56.0) on Linux; CI
#                   installs exactly that. A different build may antialias
#                   differently — recapture baselines only with this build.
#   4. FONTS      — repo-owned fontconfig (tests/visual_baselines/fonts.conf)
#                   pins every CSS-reachable family to Liberation, exported as
#                   FONTCONFIG_FILE below; without it, uninstalled families
#                   (Georgia, Space Grotesk) resolve to machine-dependent
#                   physical fonts and feed pages diverge across venues.
#   Plus: fixtures carry no external URLs the renderer would fetch, and
#   --host-resolver-rules forces any accidental external request to fail fast,
#   so online and offline environments render identically.
#
# Usage:
#   tools/visual_check.sh            # compare against committed baselines
#   tools/visual_check.sh --update   # (re)capture and OVERWRITE baselines
#
# Exit codes: 0 clean · 1 a page diverged from its baseline · 2 hard failure
# (missing browser/build/boot). Never silently passes: every skip/exit is loud.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$REPO/web"
BASELINES="$REPO/tests/visual_baselines"
UPDATE=0
[ "${1:-}" = "--update" ] && UPDATE=1

# RENDERER pin, part 2 — FONTS (diagnosed 2026-08-04, run 30931…/artifact
# 8898154676): the Chromium build is byte-identical across machines, but the
# app's CSS families (Georgia, Space Grotesk, system-ui…) are installed
# nowhere we run, so fontconfig substitutes a MACHINE-DEPENDENT physical font
# and the two desktop feed pages (the only serif-bearing pages) diverged
# 1.39%/3.28% between this venue and CI while serif-free detail pages matched
# 0.000%. Hinting flags alone could not fix different glyph OUTLINES. The
# repo-owned fontconfig below pins every reachable family to the Liberation
# set, present in both venues (ships with playwright install --with-deps).
export FONTCONFIG_FILE="$BASELINES/fonts.conf"
if [ ! -f "$FONTCONFIG_FILE" ]; then
  echo "[visual_check] HARD FAIL: $FONTCONFIG_FILE missing — font pin is part of the determinism contract" >&2
  exit 2
fi
# Verify the pin actually RESOLVES (not merely exists): a malformed fonts.conf
# makes fontconfig print an error and silently fall back to system defaults —
# the exact nondeterminism the pin removes. fc-match under the pin must land
# Georgia on Liberation Serif, or nothing here is deterministic. (Proven the
# hard way, 2026-08-04: an XML double-hyphen-in-comment error produced clean
# exit codes and machine-dependent captures.)
if ! command -v fc-match >/dev/null 2>&1; then
  echo "[visual_check] HARD FAIL: fc-match not available — cannot prove the font pin resolves (install fontconfig)" >&2
  exit 2
fi
GEORGIA_RESOLVED="$(fc-match Georgia 2>/dev/null || true)"
if ! printf '%s' "$GEORGIA_RESOLVED" | grep -q "Liberation Serif"; then
  echo "[visual_check] HARD FAIL: font pin not effective — Georgia resolved to '$GEORGIA_RESOLVED' (want Liberation Serif). Check $FONTCONFIG_FILE for XML errors and that fonts-liberation is installed." >&2
  exit 2
fi

# Page manifest: name | path | viewport WxH. Mobile-first (the product's home
# viewport) + one desktop feed + the disputed detail (its disclosure opens by
# default — that behavior is part of the pinned pixels) + the cancelled detail
# (the status note surface).
# 4th field = color scheme (R-071: light is a product surface too). Dark is
# PINNED with --force-dark-mode (proven pixel-neutral on the pre-light CSS:
# 0/329160 vs the committed baselines, 2026-08-04); light relies on headless
# Chromium's default prefers-color-scheme: light — verified by the light
# captures actually rendering the paper palette (a dark-rendering light
# capture would diverge from its committed light baseline and fail loud).
PAGES=(
  "tonight-feed-mobile|/tonight|390,844|dark"
  "tonight-feed-desktop|/tonight|1280,900|dark"
  "tonight-detail-disputed|/tonight/qa-4|390,844|dark"
  "tonight-detail-cancelled|/tonight/qa-9|390,844|dark"
  "tonight-feed-mobile-light|/tonight|390,844|light"
  "tonight-feed-desktop-light|/tonight|1280,900|light"
  "tonight-detail-disputed-light|/tonight/qa-4|390,844|light"
  "tonight-detail-cancelled-light|/tonight/qa-9|390,844|light"
)

CHROMIUM="${ONELIVE_CHROMIUM:-}"
if [ -z "$CHROMIUM" ]; then
  for c in /opt/pw-browsers/chromium chromium chromium-browser google-chrome; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then CHROMIUM="$c"; break; fi
  done
fi
if [ -z "$CHROMIUM" ]; then
  echo "[visual_check] HARD FAIL: no Chromium found (set ONELIVE_CHROMIUM)" >&2
  exit 2
fi

if [ ! -d "$WEB/node_modules" ]; then
  echo "[visual_check] HARD FAIL: web/node_modules absent — run 'npm ci' in web/ first" >&2
  exit 2
fi

# Build (production render is what users get and what CI checks). Reuse an
# existing build only when explicitly asked — a stale build is a wrong gate.
if [ "${ONELIVE_VR_SKIP_BUILD:-}" != "1" ]; then
  echo "[visual_check] building web (production)…"
  (cd "$WEB" && npx next build >/dev/null)
fi

# Port: explicit override, else derived from the PID so parallel/zombie runs
# can't collide on one hardcoded number.
PORT="${ONELIVE_VR_PORT:-$((3100 + $$ % 400))}"
echo "[visual_check] booting next start on :$PORT in QA fixture mode…"
# setsid gives the server its own process group so cleanup kills next's real
# node process, not just the wrapper shell (a leaked server holds the port).
(
  cd "$WEB" &&
  # AUTH_DISABLED=1 is the documented public mode (web/lib/auth.ts) — the same
  # posture as the live public deploy, so baselines reflect production behavior.
  exec setsid env ONELIVE_QA_FIXTURES=1 AUTH_DISABLED=1 TZ=America/Chicago \
    node node_modules/.bin/next start -p "$PORT"
) >"$REPO/.vr-server.log" 2>&1 &
SERVER_PID=$!
cleanup() { kill -- -"$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; }
trap cleanup EXIT

for i in $(seq 1 60); do
  if curl -sf -o /dev/null "http://localhost:$PORT/tonight"; then break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[visual_check] HARD FAIL: server died — $REPO/.vr-server.log:" >&2
    tail -20 "$REPO/.vr-server.log" >&2
    exit 2
  fi
  sleep 1
  if [ "$i" = 60 ]; then echo "[visual_check] HARD FAIL: server never came up" >&2; exit 2; fi
done

TMP="$(mktemp -d)"
FAIL=0
mkdir -p "$BASELINES"

for spec in "${PAGES[@]}"; do
  IFS='|' read -r name path viewport scheme <<<"$spec"
  shot="$TMP/$name.png"
  SCHEME_FLAG=""
  [ "$scheme" = "dark" ] && SCHEME_FLAG="--force-dark-mode"
  # --host-resolver-rules: any non-localhost request resolves to a dead local
  # address, so a stray external fetch fails identically online and offline.
  # --no-sandbox everywhere this runs: required as root (this sandbox) AND on
  # ubuntu-24 GitHub runners, where AppArmor blocks Chromium's unprivileged
  # userns sandbox and the process ABORTS (proven: run 30840138414). Safe for
  # THIS use: a single-use CI/sandbox machine rendering only our own localhost
  # fixture pages with every external host resolver-blocked above.
  # --disable-dev-shm-usage: runners' small /dev/shm crashes the renderer.
  # --font-render-hinting=none + no subpixel positioning: collapse the one
  # cross-machine nondeterminism the Chromium-build pin does not cover — font
  # hinting config. Diagnosed 2026-08-04 (run 30920739324): identical build,
  # identical fonts, but CI's antialiasing diverged up to 1.83% on the light
  # desktop feed (dark-on-paper shows AA deltas > tolerance where dark-on-night
  # hides them). Hinting off renders text geometry identically everywhere.
  TZ=America/Chicago "$CHROMIUM" --no-sandbox --disable-dev-shm-usage \
    --font-render-hinting=none --disable-font-subpixel-positioning \
    --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --host-resolver-rules="MAP * 127.0.0.1, EXCLUDE localhost" \
    --window-size="$viewport" --screenshot="$shot" $SCHEME_FLAG \
    "http://localhost:$PORT$path" >/dev/null 2>&1 || {
      echo "[visual_check] HARD FAIL: capture failed for $name" >&2; exit 2; }
  [ -s "$shot" ] || { echo "[visual_check] HARD FAIL: empty screenshot for $name" >&2; exit 2; }

  if [ "$UPDATE" = 1 ]; then
    cp "$shot" "$BASELINES/$name.png"
    echo "[visual_check] baseline UPDATED: $name.png"
  else
    if [ ! -f "$BASELINES/$name.png" ]; then
      echo "[visual_check] FAIL: no baseline for $name (run with --update to create)" >&2
      FAIL=1
      continue
    fi
    if python3 "$REPO/tools/visual_regression.py" compare \
        "$BASELINES/$name.png" "$shot" --threshold 0.01; then
      echo "[visual_check] PASS: $name"
    else
      cp "$shot" "$BASELINES/$name.CANDIDATE.png"
      echo "[visual_check] FAIL: $name diverged — candidate saved as $name.CANDIDATE.png" >&2
      FAIL=1
    fi
  fi
done

# ── Leg 2: mechanical WCAG 2.2 AA (axe, machine-checkable subset) + lab LCP
# budget, against the SAME deterministic boot (web/qa/audit.mjs). Fail-closed:
# if the audit runner is missing, that's a hard failure, never a silent skip.
if [ ! -f "$WEB/node_modules/playwright-core/package.json" ]; then
  echo "[visual_check] HARD FAIL: playwright-core not installed (npm ci in web/) — the a11y/LCP audit cannot run" >&2
  exit 2
fi
echo "[visual_check] running a11y + lab-LCP audit…"
if (cd "$WEB" && ONELIVE_CHROMIUM="$CHROMIUM" node qa/audit.mjs --base "http://localhost:$PORT"); then
  :
else
  echo "[visual_check] FAIL: a11y/LCP audit reported violations (see above)" >&2
  FAIL=1
fi

exit "$FAIL"
