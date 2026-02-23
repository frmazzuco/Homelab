#!/bin/bash
set -euo pipefail

export PATH="$HOME/Tools/lima/bin:/opt/homebrew/bin:$PATH"

resolve_colima_bin() {
  if [ -n "${COLIMA_BIN:-}" ] && [ -x "${COLIMA_BIN:-}" ]; then
    printf "%s\n" "$COLIMA_BIN"
    return
  fi
  if [ -x "$HOME/Tools/colima/colima" ]; then
    printf "%s\n" "$HOME/Tools/colima/colima"
    return
  fi
  if command -v colima >/dev/null 2>&1; then
    command -v colima
    return
  fi
}

COLIMA="$(resolve_colima_bin || true)"

if [ ! -x "$COLIMA" ]; then
  echo "Colima nao encontrado."
  exit 1
fi

# Sobe o Colima (containerd) se necessário
if ! "$COLIMA" status >/dev/null 2>&1; then
  "$COLIMA" start --runtime containerd --vm-type vz
fi

ENGINE=()
if "$COLIMA" ssh -- sudo nerdctl version >/dev/null 2>&1; then
  ENGINE=(sudo nerdctl)
elif "$COLIMA" ssh -- docker version >/dev/null 2>&1; then
  ENGINE=(docker)
else
  echo "Nao consegui detectar runtime dentro da VM Colima (nerdctl/docker)."
  exit 1
fi

engine() {
  "$COLIMA" ssh -- "${ENGINE[@]}" "$@"
}

# Aguarda o runtime responder
for i in {1..30}; do
  if engine version >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if engine ps -a --format '{{.Names}}' | grep -qx jellyfin; then
  engine start jellyfin >/dev/null || true
else
  engine run -d \
    --name jellyfin \
    --restart unless-stopped \
    -p 8096:8096 \
    -v "$HOME/jellyfin/config:/config" \
    -v "$HOME/jellyfin/cache:/cache" \
    -v "$HOME/Media:/media" \
    jellyfin/jellyfin:latest >/dev/null
fi

open "http://localhost:8096"
