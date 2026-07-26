#!/usr/bin/env bash
# install_hooks.sh — install a real git pre-commit hook, no framework needed.
# SUMMARY: fallback for when the `pre-commit` framework (.pre-commit-config.yaml)
# isn't installed. Writes .git/hooks/pre-commit that runs `lint.py --fix` and
# BLOCKS the commit (non-zero exit) if violations remain after fixing what's
# safely fixable, then runs the PROJECT's trust gate if one is registered.
# Run once per clone: `bash tools/install_hooks.sh`.
#
# The kernel ships no trust gate of its own — trust invariants are per-project.
# The hook therefore DISCOVERS one, in this order:
#   1. $KERNEL_TRUST_GATE_CMD (if set, run it verbatim via the shell)
#   2. tools/trust_gate.py    (the conventional location)
# If neither exists the hook prints a LOUD banner saying the commit was NOT
# trust-verified, and does not block. That non-blocking choice is deliberate
# and narrow: the BLOCKING authority for "this repo has no project gate" is
# tools/validate, which records it as a Record-bound SKIP and refuses to go
# green. A pre-commit hook that blocked every commit in a repo whose gate is
# not written yet would simply be deleted — fail-open by abandonment, which is
# worse than a loud warning plus a hard gate at validate time.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [ ! -d "$REPO_ROOT/.git" ]; then
  echo "install_hooks.sh: FAIL — $REPO_ROOT/.git not found. Run this from inside the repo." >&2
  exit 1
fi

mkdir -p "$HOOKS_DIR"
HOOK_FILE="$HOOKS_DIR/pre-commit"

cat > "$HOOK_FILE" <<'HOOK'
#!/usr/bin/env bash
# Installed by tools/install_hooks.sh — do not hand-edit, re-run that script instead.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "[pre-commit] python tools/lint.py --fix"
if ! python3 tools/lint.py --fix; then
  echo "[pre-commit] BLOCKED: tools/lint.py found violations that --fix could not "
  echo "             auto-resolve. Fix them (see messages above) and re-commit."
  exit 1
fi

# Project trust gate — discovered, never assumed. A missing gate is announced
# LOUDLY (never silently treated as verified); tools/validate is the blocking
# authority for its absence.
TRUST_GATE_RAN=0
if [ -n "${KERNEL_TRUST_GATE_CMD:-}" ]; then
  echo "[pre-commit] project trust gate: \$KERNEL_TRUST_GATE_CMD"
  if ! bash -c "$KERNEL_TRUST_GATE_CMD"; then
    echo "[pre-commit] BLOCKED: the project trust gate found an invariant violation."
    echo "             These are non-negotiable (see CLAUDE.md / OVERLAY.md)."
    exit 1
  fi
  TRUST_GATE_RAN=1
elif [ -f tools/trust_gate.py ]; then
  echo "[pre-commit] python tools/trust_gate.py"
  if ! python3 tools/trust_gate.py; then
    echo "[pre-commit] BLOCKED: tools/trust_gate.py found a trust-invariant violation."
    echo "             These are non-negotiable (see CLAUDE.md / OVERLAY.md)."
    exit 1
  fi
  TRUST_GATE_RAN=1
fi

if [ "$TRUST_GATE_RAN" -eq 0 ]; then
  echo "[pre-commit] ############################################################" >&2
  echo "[pre-commit] # NO PROJECT TRUST GATE FOUND — THIS COMMIT IS NOT         #" >&2
  echo "[pre-commit] # TRUST-VERIFIED. Lint passed; invariants were NOT checked.#" >&2
  echo "[pre-commit] # Add tools/trust_gate.py (or set KERNEL_TRUST_GATE_CMD)   #" >&2
  echo "[pre-commit] # and register it in tools/project_checks.d/ so            #" >&2
  echo "[pre-commit] # tools/validate can go green.                             #" >&2
  echo "[pre-commit] ############################################################" >&2
fi

# --fix may have modified files in place; re-stage anything it touched so the
# commit actually contains the fixed version instead of silently committing
# the pre-fix content. NUL-delimited + `--` so filenames with spaces/newlines
# or leading-dash names are handled safely and never parsed as options.
git diff --name-only -z --diff-filter=M -- '*.py' | xargs -0 -r git add --

if [ "$TRUST_GATE_RAN" -eq 1 ]; then
  echo "[pre-commit] OK — lint + project trust gate clean."
else
  echo "[pre-commit] OK — lint clean; trust invariants UNVERIFIED (see banner above)."
fi
exit 0
HOOK

chmod +x "$HOOK_FILE"
echo "install_hooks.sh: OK — installed $HOOK_FILE"
echo "It runs on every 'git commit': lint.py --fix, then the project trust gate if one is registered."
echo "Non-zero exit blocks the commit. A missing project trust gate warns LOUDLY and is a"
echo "Record-bound SKIP in tools/validate — it is never treated as verified."
