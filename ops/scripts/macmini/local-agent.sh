#!/bin/bash
set -euo pipefail

export PATH="$HOME/Tools/lima/bin:$PATH"
COLIMA="$HOME/Tools/colima/colima"
OLLAMA="$HOME/Tools/ollama/ollama"
ARRCTL="$HOME/Scripts/arrctl"
MODEL="gemma3:12b"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JELLYFIN_START_SCRIPT="$SCRIPT_DIR/../media/jellyfin-start-server.sh"

usage() {
  cat <<USAGE
Uso:
  local-agent "seu pedido"

Exemplos:
  local-agent "status do jellyfin"
  local-agent "abrir jellyfin"
  local-agent "iniciar jellyfin"
  local-agent "parar jellyfin"
  local-agent "qual meu ip local"
  local-agent "uso de disco"
  local-agent "listar filmes"
  local-agent "listar séries"
  local-agent "buscar filme night of the living dead"
  local-agent "baixar filme tmdb 10331"
USAGE
}

if [ $# -eq 0 ]; then
  usage
  exit 1
fi

TASK="$*"

# garante ollama server
if ! curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  nohup "$OLLAMA" serve > "$HOME/Library/Logs/ollama-serve.log" 2>&1 &
  sleep 2
fi

PROMPT=$(cat <<P
Você é um roteador de automação local no macOS.
Converta o pedido para APENAS este JSON:
{"action":"...","query":"...","id":0}

Ações permitidas:
- jellyfin_status
- jellyfin_open
- jellyfin_start
- jellyfin_stop
- ip_local
- disk_usage
- media_folders
- arr_status
- arr_list_movies
- arr_list_series
- arr_search_movie
- arr_search_series
- arr_download_movie
- arr_download_series
- help
- none

Regras:
- Responda SOMENTE JSON válido.
- Não invente ação fora da lista.
- Para buscas, preencha query.
- Para download por id, preencha id numérico.
- Se não tiver certeza, use "none".

Pedido: $TASK
P
)

RAW=$("$OLLAMA" run "$MODEL" --format json --hidethinking "$PROMPT" 2>/dev/null || echo '{"action":"none"}')

PARSED=$(printf "%s" "$RAW" | python3 -c 'import json,re,sys
raw=sys.stdin.read().strip()
m=re.search(r"\{[\s\S]*\}", raw)
if not m:
    print("none\n\n")
    raise SystemExit
try:
    j=json.loads(m.group(0))
except Exception:
    print("none\n\n")
    raise SystemExit
a=str(j.get("action","none") or "none")
q=j.get("query","")
if q is None: q=""
i=j.get("id","")
if i is None: i=""
print(a)
print(str(q))
print(str(i))')

ACTION=$(printf "%s" "$PARSED" | sed -n '1p')
QUERY=$(printf "%s" "$PARSED" | sed -n '2p')
IDVAL=$(printf "%s" "$PARSED" | sed -n '3p')

case "$ACTION" in
  jellyfin_status)
    if "$COLIMA" status >/dev/null 2>&1; then
      OUT=$("$COLIMA" ssh -- sudo nerdctl ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep '^jellyfin ' || true)
      if [ -n "$OUT" ]; then
        echo "✅ Jellyfin: $OUT"
        curl -fsS --max-time 3 http://127.0.0.1:8096/system/info/public >/dev/null 2>&1 && echo "✅ API local respondendo em http://localhost:8096" || echo "⚠️ Porta 8096 sem resposta HTTP"
      else
        echo "⚠️ Jellyfin não está rodando"
      fi
    else
      echo "⚠️ Colima não está rodando"
    fi
    ;;

  jellyfin_open)
    open "http://localhost:8096"
    echo "✅ Abri o Jellyfin no navegador"
    ;;

  jellyfin_start)
    "$JELLYFIN_START_SCRIPT" >/dev/null 2>&1 || true
    echo "✅ Comando de start enviado para Jellyfin"
    ;;

  jellyfin_stop)
    "$COLIMA" ssh -- sudo nerdctl stop jellyfin >/dev/null 2>&1 || true
    echo "✅ Comando de stop enviado para Jellyfin"
    ;;

  ip_local)
    IP=$(ipconfig getifaddr en1 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || true)
    [ -n "$IP" ] && echo "🌐 IP local: $IP" || echo "⚠️ Não consegui identificar IP local"
    ;;

  disk_usage)
    echo "💾 Uso de disco (/):"
    df -h / | tail -n 1
    ;;

  media_folders)
    echo "🎬 Pastas de mídia:"
    find "$HOME/Media" -maxdepth 2 -type d 2>/dev/null | sed "s|$HOME/||" | sort
    ;;

  arr_status)
    "$ARRCTL" status
    ;;

  arr_list_movies)
    "$ARRCTL" filmes
    ;;

  arr_list_series)
    "$ARRCTL" series
    ;;

  arr_search_movie)
    if [ -z "$QUERY" ]; then
      echo "⚠️ Falta termo para buscar filme"
    else
      "$ARRCTL" buscar-filme "$QUERY"
    fi
    ;;

  arr_search_series)
    if [ -z "$QUERY" ]; then
      echo "⚠️ Falta termo para buscar série"
    else
      "$ARRCTL" buscar-serie "$QUERY"
    fi
    ;;

  arr_download_movie)
    if [[ "$IDVAL" =~ ^[0-9]+$ ]]; then
      "$ARRCTL" baixar-filme "$IDVAL"
    elif [ -n "$QUERY" ]; then
      "$ARRCTL" baixar-filme-termo "$QUERY"
    else
      echo "⚠️ Envie tmdbId ou termo do filme"
    fi
    ;;

  arr_download_series)
    if [[ "$IDVAL" =~ ^[0-9]+$ ]]; then
      "$ARRCTL" baixar-serie "$IDVAL"
    elif [ -n "$QUERY" ]; then
      "$ARRCTL" baixar-serie-termo "$QUERY"
    else
      echo "⚠️ Envie tvdbId ou termo da série"
    fi
    ;;

  help)
    usage
    ;;

  *)
    echo "🤖 Não entendi o pedido para automação simples."
    echo "Tenta: status jellyfin, listar filmes/séries, buscar/baixar por termo ou id."
    ;;
esac
