#!/bin/bash
set -euo pipefail

LABEL="ai.openclaw.node"
UIDN="$(id -u)"
ERR_LOG="$HOME/.openclaw/logs/node.err.log"
WD_LOG="$HOME/.openclaw/logs/node-watchdog.log"
STATE_FILE="$HOME/.openclaw/logs/node-watchdog.state"

NOW="$(date +%s)"
WINDOW_SEC=300
COOLDOWN_SEC=180

mkdir -p "$HOME/.openclaw/logs"

last_restart=0
if [[ -f "$STATE_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$STATE_FILE" || true
fi

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$WD_LOG"
}

needs_restart=0
reason=""

if ! launchctl print "gui/$UIDN/$LABEL" >/dev/null 2>&1; then
  needs_restart=1
  reason="job_missing"
elif ! launchctl print "gui/$UIDN/$LABEL" | grep -q 'state = running'; then
  needs_restart=1
  reason="job_not_running"
fi

if [[ "$needs_restart" -eq 0 && -f "$ERR_LOG" ]]; then
  mtime="$(stat -f %m "$ERR_LOG" 2>/dev/null || echo 0)"
  age=$((NOW - mtime))
  if (( age <= WINDOW_SEC )); then
    if tail -n 80 "$ERR_LOG" | grep -Eiq 'tick timeout|device nonce required|gateway connect failed'; then
      needs_restart=1
      reason="recent_gateway_errors"
    fi
  fi
fi

if [[ "$needs_restart" -eq 1 ]]; then
  delta=$((NOW - ${last_restart:-0}))
  if (( delta < COOLDOWN_SEC )); then
    log "SKIP cooldown=${delta}s reason=${reason}"
    exit 0
  fi

  if launchctl kickstart -k "gui/$UIDN/$LABEL" >/dev/null 2>&1; then
    log "RESTARTED reason=${reason}"
    {
      echo "last_restart=$NOW"
      echo "last_reason=$reason"
    } > "$STATE_FILE"
  else
    log "RESTART_FAILED reason=${reason}"
  fi
else
  log "OK no_action"
fi
