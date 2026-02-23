#!/bin/bash
set -euo pipefail

export PATH="$HOME/Tools/lima/bin:$PATH"
COLIMA="$HOME/Tools/colima/colima"

if [ ! -x "$COLIMA" ]; then
  echo "Colima não encontrado em $COLIMA"
  exit 1
fi

# Sobe o Colima (containerd) se necessário
if ! "$COLIMA" status >/dev/null 2>&1; then
  "$COLIMA" start --runtime containerd --vm-type vz
fi

# Aguarda o runtime responder
for i in {1..30}; do
  if "$COLIMA" ssh -- sudo nerdctl version >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if "$COLIMA" ssh -- sudo nerdctl ps -a --format '{{.Names}}' | grep -qx jellyfin; then
  "$COLIMA" ssh -- sudo nerdctl start jellyfin >/dev/null || true
else
  "$COLIMA" ssh -- sudo nerdctl run -d \
    --name jellyfin \
    --restart unless-stopped \
    -p 8096:8096 \
    -v "$HOME/jellyfin/config:/config" \
    -v "$HOME/jellyfin/cache:/cache" \
    -v "$HOME/Media:/media" \
    jellyfin/jellyfin:latest >/dev/null
fi

open "http://localhost:8096"
