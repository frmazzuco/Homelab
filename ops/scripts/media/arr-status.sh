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
  exit 1
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

IP=$(ipconfig getifaddr en1 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || echo 'IP_NAO_ENCONTRADO')
STACK_STATUS="$(engine ps --format '{{.Names}} {{.Status}} {{.Ports}}' | egrep 'sabnzbd|sonarr|radarr|prowlarr|bazarr|whisper-asr|lingarr|lingarr-db|jellyfin' || true)"
if [ -n "$STACK_STATUS" ]; then
  printf "%s\n" "$STACK_STATUS"
else
  echo "Nenhum container da stack ARR/Jellyfin encontrado em execucao."
fi
echo "SABnzbd:    http://$IP:8086"
echo "Sonarr:     http://$IP:8989"
echo "Radarr:     http://$IP:7878"
echo "Prowlarr:   http://$IP:9696"
echo "Bazarr:     http://$IP:6767"
echo "Whisper ASR:http://$IP:9000"
echo "Lingarr:    http://$IP:9876"
echo "Lingarr DB: mysql://$IP:3307"
echo "Jellyfin:   http://$IP:8096"
