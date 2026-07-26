#!/usr/bin/env bash
# bootstrap_dev.sh — one command, fresh clone to a runnable gate.
#
# v1 done-criterion 3 / BAR G5 / R-058. Before this, a new environment turned four
# gate rows red for reasons that were not code, and nothing on disk said which
# packages were needed or that the clone had to be un-shallowed.
#
# Idempotent: safe to re-run. Does NOT install anything globally — everything lands
# in ./.venv, which is gitignored.
#
# Usage:
#   bash tools/bootstrap_dev.sh          # venv + deps + full history
#   bash tools/bootstrap_dev.sh --no-git # skip the unshallow (offline)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DO_GIT=1
for arg in "$@"; do
  case "$arg" in
    --no-git) DO_GIT=0 ;;
    -h|--help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "bootstrap_dev: unknown argument '$arg' (see --help)" >&2; exit 1 ;;
  esac
done

PY="${PYTHON:-python3}"
VENV="$REPO_ROOT/.venv"

echo "== 1/3 virtualenv =="
# HERMETIC, deliberately. This used --system-site-packages, justified in a comment
# as "so a distro-provided cryptography/psycopg2 is reused rather than rebuilt from
# source, which fails on images without a compiler". That justification was simply
# WRONG — both ship manylinux wheels, so a clean venv needs no compiler (verified
# 2026-07-26: every requirement installed from a cached wheel).
#
# And the flag actively broke the gate. With system site-packages visible, pip
# considers a DECLARED requirement already satisfied by the system copy and skips
# it — so a BROKEN system package silently wins. That is what happened: the image's
# `cryptography` panics in its Rust extension for a missing `_cffi_backend`, pip
# never installed a good one, and `import jwt` died. Three of the gate's rows went
# red (pytest, blocking_failure_check, perf) for one environment cause, in the very
# environment this script exists to make sound.
#
# Inheriting the system's packages is inheriting the system's faults. A dependency
# worth running the gate against is worth declaring in requirements-dev.txt.
_rebuild_reason=""
if [ ! -x "$VENV/bin/python" ]; then
  _rebuild_reason="absent"
elif grep -qi '^include-system-site-packages *= *true' "$VENV/pyvenv.cfg" 2>/dev/null; then
  # A venv built by the old flawed recipe. Reusing it would silently keep the fault,
  # so it is rebuilt rather than reported — the founder's manual work is the scarcest
  # resource and "your venv is wrong, recreate it" is manual work.
  _rebuild_reason="built with --system-site-packages (the fault described above)"
fi

if [ -n "$_rebuild_reason" ]; then
  if [ -d "$VENV" ]; then
    echo "rebuilding $VENV — $_rebuild_reason"
    rm -rf "$VENV"
  fi
  "$PY" -m venv "$VENV" || {
    echo "bootstrap_dev: could not create $VENV — is python3-venv installed?" >&2
    exit 1
  }
  echo "created $VENV (hermetic — no system site-packages)"
else
  echo "$VENV already exists and is hermetic — reusing"
fi

echo "== 2/3 dependencies =="
"$VENV/bin/python" -m pip install --upgrade pip --quiet || {
  echo "bootstrap_dev: pip self-upgrade failed" >&2; exit 1; }
"$VENV/bin/python" -m pip install -r requirements-dev.txt --quiet || {
  echo "bootstrap_dev: dependency install failed — the error above is the reason" >&2
  exit 1
}
echo "installed from requirements-dev.txt"

echo "== 3/3 full git history =="
if [ "$DO_GIT" -eq 1 ]; then
  if [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
    # The arming-evidence binding cannot be proven without history (R-036); it
    # fails CLOSED, which is correct but reads as a defect to a newcomer.
    git fetch --unshallow || echo "bootstrap_dev: unshallow failed (offline?) — \
tests/test_arming_smoke_binding.py will report UNPROVABLE-HERE until it succeeds" >&2
  else
    echo "history already complete"
  fi
else
  echo "skipped (--no-git)"
fi

echo
echo "== verifying =="
"$VENV/bin/python" tools/env_preflight.py
echo
echo "Now run the gate with this interpreter:"
echo "  PATH=\"$VENV/bin:\$PATH\" bash tools/validate"
