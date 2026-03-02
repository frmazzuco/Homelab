#!/bin/sh
# run-job.sh <job_name> <command>
# Runs a job and notifies Apprise on success/failure

JOB_NAME="$1"
shift
COMMAND="$@"

APPRISE_URL="${APPRISE_URL:-http://apprise-api:8000}"

START=$(date +%s)
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting: $JOB_NAME"

# Run the job, capture output and exit code
OUTPUT=$(eval "$COMMAND" 2>&1)
EXIT_CODE=$?

END=$(date +%s)
DURATION=$((END - START))

if [ $EXIT_CODE -eq 0 ]; then
    STATUS="✅"
    TITLE="Datalake: $JOB_NAME OK"
    TYPE="success"
else
    STATUS="❌"
    TITLE="Datalake: $JOB_NAME FALHOU"
    TYPE="failure"
fi

# Log
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $STATUS $JOB_NAME (${DURATION}s, exit $EXIT_CODE)"
echo "$OUTPUT" | tail -5

# Notify via Apprise default config (uses apprise.yml)
if [ $EXIT_CODE -ne 0 ] || [ "${NOTIFY_ON_SUCCESS}" = "true" ]; then
    BODY=$(printf "%s **%s** — %ss\n\n%s" "$STATUS" "$JOB_NAME" "$DURATION" "$(echo "$OUTPUT" | tail -10 | head -c 400)")
    
    curl -s -X POST "${APPRISE_URL}/notify/" \
        -H "Content-Type: application/json" \
        --data-binary "$(printf '{"title":"%s","body":"%s","type":"%s"}' "$TITLE" "$(echo "$BODY" | sed 's/"/\\"/g' | tr '\n' ' ')" "$TYPE")" \
        > /dev/null 2>&1 || echo "Warning: Apprise notification failed"
fi

exit $EXIT_CODE
