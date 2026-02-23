#!/bin/bash
set -euo pipefail
export PATH="$HOME/Tools/lima/bin:$PATH"
COLIMA="$HOME/Tools/colima/colima"
IP=$(ipconfig getifaddr en1 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || echo 'IP_NAO_ENCONTRADO')
"$COLIMA" ssh -- sudo nerdctl ps --format '{{.Names}} {{.Status}} {{.Ports}}' | egrep 'sabnzbd|sonarr|radarr|prowlarr|bazarr|whisper-asr|lingarr|lingarr-db|jellyfin' || true
echo "SABnzbd:    http://$IP:8086"
echo "Sonarr:     http://$IP:8989"
echo "Radarr:     http://$IP:7878"
echo "Prowlarr:   http://$IP:9696"
echo "Bazarr:     http://$IP:6767"
echo "Whisper ASR:http://$IP:9000"
echo "Lingarr:    http://$IP:9876"
echo "Lingarr DB: mysql://$IP:3307"
echo "Jellyfin:   http://$IP:8096"
