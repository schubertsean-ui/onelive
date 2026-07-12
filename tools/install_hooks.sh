#!/usr/bin/env bash
# install_hooks.sh — install a real git pre-commit hook, no framework needed.
# SUMMARY: fallback for when the `pre-commit` framework (.pre-commit-config.yaml)
# isn't installed. Writes .git/hooks/pre-commit that runs `lint.py --fix` then
# `trust_gate.py` and BLOCKS the commit (non-zero exit) if either fails after
# fixing what's safely fixable. Run once per clone: `bash tools/install_hooks.sh`.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [ ! -d "$REPO_ROOT/.git" ]; then
  echo "install_hooks.sh: FAIL — $REPO_ROOT/.git not found. Run this from inside the onelive repo." >&2
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

echo "[pre-commit] python tools/trust_gate.py"
if ! python3 tools/trust_gate.py; then
  echo "[pre-commit] BLOCKED: tools/trust_gate.py found a trust-invariant violation."
  echo "             These are non-negotiable (see docs/OPERATING_RULES.md SS1/SS3)."
  exit 1
fi

# --fix may have modified files in place; re-stage anything it touched so the
# commit actually contains the fixed version instead of silently committing
# the pre-fix content.
git diff --name-only --diff-filter=M | grep -E '\.py$' | xargs -r git add

echo "[pre-commit] OK — lint + trust_gate clean."
exit 0
HOOK

chmod +x "$HOOK_FILE"
echo "install_hooks.sh: OK — installed $HOOK_FILE"
echo "It runs on every 'git commit': lint.py --fix, then trust_gate.py. Non-zero exit blocks the commit."
