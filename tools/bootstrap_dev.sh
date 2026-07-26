#!/usr/bin/env bash
# bootstrap_dev.sh — one command, fresh clone to a runnable gate.
#
# v1 done-criterion 3 / BAR G5 / R-058. Before this, a new environment turned four
# gate rows red for reasons that were not code, and nothing on disk said which
# packages were needed or that the clone had to be un-shallowed.
#
# Idempotent: safe to re-run. Nothing is installed globally.
#
# THE VENV LIVES OUTSIDE THE REPOSITORY, at $HOME/.venvs/onelive by default
# (override with ONELIVE_VENV). That is deliberate and it is not a style choice.
# It used to be ./.venv, and a virtualenv inside a tree this harness introspects
# breaks the harness: tests/test_golden_exam.py computes the exam's "repo-local
# import closure" as everything under the repo root, so with ./.venv present it
# demanded that pydantic's 48 vendored files be bound into the exam's evidence
# hash. `git add -A` after bootstrapping also staged 874k lines of wheels.
# Both symptoms have the same cause: the venv was somewhere the tooling reads.
# Put it where nothing reads it and neither symptom exists.
#
# Usage:
#   bash tools/bootstrap_dev.sh          # venv + deps + full history
#   bash tools/bootstrap_dev.sh --no-git # skip the unshallow (offline)
#   ONELIVE_VENV=/path bash tools/bootstrap_dev.sh   # somewhere else entirely
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
# OUTSIDE the repo tree — see the header. A venv under REPO_ROOT is read by the
# golden exam's import-closure check and by `git add -A`, and both then report the
# vendored wheels as if they were this project's code.
VENV="${ONELIVE_VENV:-${HOME:-/tmp}/.venvs/onelive}"
case "$VENV" in
  "$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "bootstrap_dev: refusing to create the venv INSIDE the repository ($VENV)." >&2
    echo "  A venv under the repo root is read by tests/test_golden_exam.py's" >&2
    echo "  import-closure check as this project's own code. Pick a path outside" >&2
    echo "  the tree, or unset ONELIVE_VENV to use the default." >&2
    exit 1 ;;
esac
mkdir -p "$(dirname "$VENV")" || {
  echo "bootstrap_dev: could not create $(dirname "$VENV")" >&2; exit 1; }

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

# A venv left in the repo by the PREVIOUS recipe still poisons the import-closure
# check and `git add -A`, so it is removed rather than reported. "Delete your old
# .venv" is founder/dev labour, and automating around labour beats asking for it.
if [ -d "$REPO_ROOT/.venv" ]; then
  echo "removing the stale in-repo $REPO_ROOT/.venv (it breaks the golden exam's closure check)"
  rm -rf "$REPO_ROOT/.venv"
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
