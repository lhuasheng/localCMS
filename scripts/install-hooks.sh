#!/usr/bin/env bash
# install-hooks.sh — installs the pre-commit hook into .git/hooks/.
# Usage:  bash scripts/install-hooks.sh
#         Run once from the repo root after cloning.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
HOOK_SOURCE="$REPO_ROOT/scripts/hooks/pre-commit"
if [ ! -f "$HOOK_SOURCE" ]; then
    HOOK_SOURCE="$REPO_ROOT/scripts/pre-commit"
fi
HOOK_DEST="$HOOKS_DIR/pre-commit"

if [ ! -f "$HOOK_SOURCE" ]; then
    echo "Error: hook source not found at $HOOK_SOURCE" >&2
    exit 1
fi

cp "$HOOK_SOURCE" "$HOOK_DEST"
chmod +x "$HOOK_DEST"

echo "Installed pre-commit hook at $HOOK_DEST"
echo "Run 'git commit --no-verify' to bypass the hook if needed."
