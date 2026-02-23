#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOTFILES_DIR="$REPO_ROOT/hosts/macmini/dotfiles"

STAMP="$(date +%Y%m%d-%H%M%S)"
for f in .zshrc .zprofile; do
  src="$DOTFILES_DIR/$f"
  dst="$HOME/$f"
  if [ -f "$src" ]; then
    if [ -f "$dst" ]; then
      cp -f "$dst" "$dst.bak.$STAMP"
      echo "backup $dst -> $dst.bak.$STAMP"
    fi
    cp -f "$src" "$dst"
    echo "applied $f"
  fi
done
