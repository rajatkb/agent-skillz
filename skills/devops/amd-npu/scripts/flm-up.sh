#!/usr/bin/env bash
# Start FLM server on demand, idempotently.
# Usage: bash flm-up.sh [model_name]
#   model_name overrides FLM_MODEL env var (default: gemma4-it:e2b)
#   FLM_PORT env var sets port (default: 50001)

set -uo pipefail

FLM_PORT="${FLM_PORT:-50001}"
FLM_MODEL="${1:-${FLM_MODEL:-gemma4-it:e2b}}"
FLM_BIN='C:\Program Files\flm\flm.exe'

exec </dev/null

# Check if already serving
if powershell.exe -NoProfile -Command "netstat -ano | findstr ':$FLM_PORT' | findstr LISTENING" 2>/dev/null | grep -q .; then
    echo "FLM already running on port $FLM_PORT with model $FLM_MODEL"
    exit 0
fi

# Check for existing process (might be binding a different port)
if powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue" 2>/dev/null | grep -q .; then
    echo "FLM process exists but not on port $FLM_PORT — might be serving a different model"
fi

# Start FLM
echo "Starting FLM server with model $FLM_MODEL on port $FLM_PORT..."
powershell.exe -NoProfile -Command "
    Start-Process -WindowStyle Hidden -FilePath '$FLM_BIN' -ArgumentList 'serve $FLM_MODEL --host 0.0.0.0 --port $FLM_PORT'
" 2>/dev/null

# Wait for the server to be ready
echo -n "Waiting for server"
for i in $(seq 1 30); do
    if curl -s --max-time 1 "http://localhost:$FLM_PORT/v1/models" >/dev/null 2>&1; then
        echo " READY"
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo " TIMEOUT — server did not respond within 30s"
echo "Check: powershell.exe Get-Process flm"
exit 1
