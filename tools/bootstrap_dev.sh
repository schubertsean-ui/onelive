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
if [ ! -x "$VENV/bin/python" ]; then
  # --system-site-packages so a distro-provided cryptography/psycopg2 is reused
  # rather than rebuilt from source, which fails on images without a compiler.
  "$PY" -m venv --system-site-packages "$VENV" || {
    echo "bootstrap_dev: could not create $VENV — is python3-venv installed?" >&2
    exit 1
  }
  echo "created $VENV"
else
  echo "$VENV already exists — reusing"
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
