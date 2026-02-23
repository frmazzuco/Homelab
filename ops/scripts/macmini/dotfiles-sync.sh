#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOTFILES_DIR="$REPO_ROOT/hosts/macmini/dotfiles"

mkdir -p "$DOTFILES_DIR"
for f in .zshrc .zprofile; do
  if [ -f "$HOME/$f" ]; then
    cp -f "$HOME/$f" "$DOTFILES_DIR/$f"
    echo "synced $f"
  fi
done
