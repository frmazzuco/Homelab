#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LAUNCHAGENTS_DIR="$REPO_ROOT/hosts/macmini/launchagents"
CURRENT_USER="$(id -un)"

if [ ! -d "$LAUNCHAGENTS_DIR" ]; then
  echo "Diretorio nao encontrado: $LAUNCHAGENTS_DIR"
  exit 1
fi

if ! command -v plutil >/dev/null 2>&1; then
  echo "plutil nao encontrado (necessario para auditar plists no macOS)."
  exit 1
fi

warn_count=0
checked=0

echo "Auditando LaunchAgents em: $LAUNCHAGENTS_DIR"
echo "Usuario atual: $CURRENT_USER"
echo

for plist in "$LAUNCHAGENTS_DIR"/*.plist; do
  [ -f "$plist" ] || continue
  checked=$((checked + 1))
  base="$(basename "$plist")"

  all_paths="$(
    plutil -convert json -o - "$plist" 2>/dev/null | python3 -c '
import json,sys
def walk(value):
    if isinstance(value, str):
        if value.startswith("/") and ":" not in value:
            print(value)
    elif isinstance(value, dict):
        for v in value.values():
            walk(v)
    elif isinstance(value, list):
        for v in value:
            walk(v)
obj=json.load(sys.stdin)
walk(obj)
' | sort -u
  )"

  exec_paths="$(
    plutil -convert json -o - "$plist" 2>/dev/null | python3 -c '
import json,sys,os
obj=json.load(sys.stdin)
for arg in obj.get("ProgramArguments", []):
    if isinstance(arg, str) and arg.startswith("/"):
        print(arg)
' | sort -u
  )"

  file_warns=0
  IFS=$'\n'
  for p in $all_paths; do
    [ -n "$p" ] || continue
    case "$p" in
      /Users/*)
        owner="$(printf "%s" "$p" | cut -d/ -f3)"
        if [ "$owner" != "$CURRENT_USER" ]; then
          echo "[WARN] $base: caminho com usuario hardcoded '$owner': $p"
          warn_count=$((warn_count + 1))
          file_warns=$((file_warns + 1))
        fi
        ;;
    esac
  done

  for p in $exec_paths; do
    [ -n "$p" ] || continue
    case "$p" in
      *.sh|*.py|*.js|*/node|*/ollama|*/tailscaled)
        if [ ! -e "$p" ]; then
          echo "[WARN] $base: executavel/script nao encontrado localmente: $p"
          warn_count=$((warn_count + 1))
          file_warns=$((file_warns + 1))
        fi
        ;;
    esac
  done
  unset IFS

  if [ "$file_warns" -eq 0 ]; then
    echo "[OK] $base"
  fi
done

echo
echo "Arquivos analisados: $checked"
echo "Avisos encontrados: $warn_count"

if [ "$warn_count" -gt 0 ]; then
  echo
  echo "Sugestao:"
  echo "- Converter os plists para template com \$HOME e caminhos parametrizados."
  echo "- Ver runbook: docs/runbooks/macmini-baseline-checklist.md"
fi
