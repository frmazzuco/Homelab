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

# Log full output locally
echo "$OUTPUT" | tail -10
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Exit: $EXIT_CODE (${DURATION}s)"

# Build notification
if [ $EXIT_CODE -eq 0 ]; then
    TYPE="success"
    TITLE="✅ Datalake: $JOB_NAME"
    BODY="Concluído em ${DURATION}s"
else
    TYPE="failure"
    TITLE="❌ Datalake: $JOB_NAME"
    # Get last meaningful error line
    ERR=$(echo "$OUTPUT" | grep -iE "error|falha|exception|errno" | tail -1 | head -c 200)
    [ -z "$ERR" ] && ERR=$(echo "$OUTPUT" | tail -1 | head -c 200)
    BODY="Falhou em ${DURATION}s — $ERR"
fi

# Send via Apprise default config
if [ $EXIT_CODE -ne 0 ] || [ "${NOTIFY_ON_SUCCESS}" = "true" ]; then
    # Use Python for clean JSON encoding
    python3 -c "
import json, urllib.request
data = json.dumps({
    'title': '''$TITLE''',
    'body': '''$BODY''',
    'type': '$TYPE'
}).encode()
req = urllib.request.Request('${APPRISE_URL}/notify/', data=data, headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(req, timeout=10)
except Exception as e:
    print(f'Warning: Apprise failed: {e}')
" 2>&1
fi

exit $EXIT_CODE
