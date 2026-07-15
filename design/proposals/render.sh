#!/usr/bin/env bash
# Reproducible render script for the committed evidence in renders/
# (evaluator round 7: screenshots must not be trust-me artifacts).
# Usage: bash render.sh   — requires headless Chromium on PATH or $CHROMIUM.
set -euo pipefail
if [ -z "${CHROMIUM:-}" ]; then
  for c in /opt/pw-browsers/chromium chromium chromium-browser google-chrome; do
    if command -v "$c" >/dev/null 2>&1; then CHROMIUM="$c"; break; fi
  done
fi
[ -n "${CHROMIUM:-}" ] || { echo "FATAL: no Chromium found — set \$CHROMIUM" >&2; exit 1; }
cd "$(dirname "$0")"
for f in direction-1-marquee direction-2-current direction-3-setlist; do
  "$CHROMIUM" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --window-size=1240,1500 --screenshot="renders/$f-dark.png" "file://$PWD/$f.html"
  tmp="$(mktemp --suffix=.html)"
  sed 's|<html lang="en">|<html lang="en" class="light">|' "$f.html" > "$tmp"
  "$CHROMIUM" --headless --disable-gpu --no-sandbox --hide-scrollbars \
    --window-size=1240,1500 --screenshot="renders/$f-light.png" "file://$tmp"
  rm -f "$tmp"
  echo "$f: dark + light rendered"
done
