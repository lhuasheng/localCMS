#!/usr/bin/env bash
# Install git hooks from the scripts/ directory into .git/hooks/.
# Usage: bash scripts/install-hooks.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

install_hook() {
    local name="$1"
    local src="$REPO_ROOT/scripts/$name"
    local dst="$HOOKS_DIR/$name"

    if [ ! -f "$src" ]; then
        echo "Hook source not found: $src" >&2
        return 1
    fi

    cp "$src" "$dst"
    chmod +x "$dst"
    echo "Installed $name -> $dst"
}

install_hook pre-commit

echo "Done. Hooks installed in $HOOKS_DIR"
