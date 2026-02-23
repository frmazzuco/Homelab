#!/bin/bash
set -euo pipefail

export PATH="$HOME/Tools/lima/bin:$PATH"
COLIMA="$HOME/Tools/colima/colima"
UIDN=$(id -u)
GIDN=$(id -g)
TZV="America/Sao_Paulo"

mkdir -p \
  "$HOME/arr/config/sabnzbd" \
  "$HOME/arr/config/sonarr" \
  "$HOME/arr/config/radarr" \
  "$HOME/arr/config/prowlarr" \
  "$HOME/arr/config/bazarr" \
  "$HOME/arr/config/lingarr" \
  "$HOME/arr/config/lingarr-mysql" \
  "$HOME/Media/Entrada/incomplete" \
  "$HOME/Media/Entrada/complete" \
  "$HOME/Media/Filmes" \
  "$HOME/Media/Series"

MYSQL_PASS_FILE="$HOME/arr/config/lingarr/.mysql-pass"
if [ ! -s "$MYSQL_PASS_FILE" ]; then
  LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24 > "$MYSQL_PASS_FILE"
fi
chmod 600 "$MYSQL_PASS_FILE"
MYSQL_PASS=$(cat "$MYSQL_PASS_FILE")

if ! "$COLIMA" status >/dev/null 2>&1; then
  "$COLIMA" start --runtime containerd --vm-type vz
fi

for i in {1..30}; do
  if "$COLIMA" ssh -- sudo nerdctl version >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

run_or_start() {
  local name="$1"
  shift
  if "$COLIMA" ssh -- sudo nerdctl ps -a --format '{{.Names}}' | grep -qx "$name"; then
    "$COLIMA" ssh -- sudo nerdctl start "$name" >/dev/null || true
    echo "started:$name"
  else
    "$COLIMA" ssh -- sudo nerdctl run -d --name "$name" --restart unless-stopped "$@" >/dev/null
    echo "created:$name"
  fi
}

# if old sqlite Lingarr exists, force recreate into mysql-backed mode
if "$COLIMA" ssh -- sudo nerdctl ps -a --format '{{.Names}}' | grep -qx 'lingarr'; then
  CUR_DB=$(
    "$COLIMA" ssh -- sudo nerdctl inspect lingarr --format '{{range .Config.Env}}{{println .}}{{end}}' \
      | awk -F= '/^DB_CONNECTION=/{print $2; exit}'
  )
  if [ "${CUR_DB:-}" != "mysql" ]; then
    "$COLIMA" ssh -- sudo nerdctl rm -f lingarr >/dev/null 2>&1 || true
    echo "recreated:lingarr (sqlite->mysql)"
  fi
fi

run_or_start lingarr-db \
  -e MARIADB_ROOT_PASSWORD="$MYSQL_PASS" \
  -e MARIADB_DATABASE=lingarr \
  -e MARIADB_USER=lingarr \
  -e MARIADB_PASSWORD="$MYSQL_PASS" \
  -p 3307:3306 \
  -v "$HOME/arr/config/lingarr-mysql:/var/lib/mysql" \
  docker.io/mariadb:11 \
  --sql-mode=''

run_or_start sabnzbd \
  -e PUID="$UIDN" \
  -e PGID="$GIDN" \
  -e TZ="$TZV" \
  -p 8086:8080 \
  -v "$HOME/arr/config/sabnzbd:/config" \
  -v "$HOME/Media/Entrada:/downloads" \
  -v "$HOME/Media/Entrada/incomplete:/incomplete-downloads" \
  lscr.io/linuxserver/sabnzbd:latest

run_or_start sonarr \
  -e PUID="$UIDN" \
  -e PGID="$GIDN" \
  -e TZ="$TZV" \
  -p 8989:8989 \
  -v "$HOME/arr/config/sonarr:/config" \
  -v "$HOME/Media:/media" \
  -v "$HOME/Media/Entrada:/downloads" \
  lscr.io/linuxserver/sonarr:latest

run_or_start radarr \
  -e PUID="$UIDN" \
  -e PGID="$GIDN" \
  -e TZ="$TZV" \
  -p 7878:7878 \
  -v "$HOME/arr/config/radarr:/config" \
  -v "$HOME/Media:/media" \
  -v "$HOME/Media/Entrada:/downloads" \
  lscr.io/linuxserver/radarr:latest

run_or_start prowlarr \
  -e PUID="$UIDN" \
  -e PGID="$GIDN" \
  -e TZ="$TZV" \
  -p 9696:9696 \
  -v "$HOME/arr/config/prowlarr:/config" \
  lscr.io/linuxserver/prowlarr:latest

run_or_start bazarr \
  -e PUID="$UIDN" \
  -e PGID="$GIDN" \
  -e TZ="$TZV" \
  -p 6767:6767 \
  -v "$HOME/arr/config/bazarr:/config" \
  -v "$HOME/Media/Filmes:/movies" \
  -v "$HOME/Media/Series:/tv" \
  lscr.io/linuxserver/bazarr:latest

run_or_start whisper-asr \
  -e ASR_MODEL=small \
  -e ASR_ENGINE=faster_whisper \
  -p 9000:9000 \
  onerahmet/openai-whisper-asr-webservice:latest

run_or_start lingarr \
  -e ASPNETCORE_URLS=http://+:9876 \
  -e DB_CONNECTION=mysql \
  -e DB_HOST=host.lima.internal \
  -e DB_PORT=3307 \
  -e DB_DATABASE=lingarr \
  -e DB_USERNAME=lingarr \
  -e DB_PASSWORD="$MYSQL_PASS" \
  -e AUTH_ENABLED=false \
  -e SERVICE_TYPE=localai \
  -e LOCAL_AI_ENDPOINT=http://host.lima.internal:11434/api/generate \
  -e LOCAL_AI_MODEL=gemma3:12b \
  -e LOCAL_AI_API_KEY=ollama \
  -e MAX_CONCURRENT_JOBS=2 \
  -p 9876:9876 \
  -v "$HOME/arr/config/lingarr:/app/config" \
  -v "$HOME/Media/Filmes:/movies" \
  -v "$HOME/Media/Series:/tv" \
  docker.io/lingarr/lingarr:latest

echo "ARR_STACK_DONE"
