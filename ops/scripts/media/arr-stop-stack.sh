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
if [ -z "${COLIMA:-}" ]; then
  echo "Colima nao encontrado."
  exit 1
fi

if ! "$COLIMA" status >/dev/null 2>&1; then
  echo "Colima nao esta rodando."
  exit 0
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

for c in lingarr lingarr-db whisper-asr bazarr prowlarr radarr sonarr sabnzbd qbittorrent; do
  engine stop "$c" >/dev/null 2>&1 || true
  echo "stopped:$c"
done
