#!/bin/bash
set -euo pipefail
export PATH="$HOME/Tools/lima/bin:$PATH"
COLIMA="$HOME/Tools/colima/colima"
for c in lingarr lingarr-db whisper-asr bazarr prowlarr radarr sonarr sabnzbd qbittorrent; do
  "$COLIMA" ssh -- sudo nerdctl stop "$c" >/dev/null 2>&1 || true
  echo "stopped:$c"
done
