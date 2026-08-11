#!/usr/bin/env bash
# Stop the FLM server and unload the NPU model.
# Kills all flm.exe processes on the Windows host.

set -uo pipefail

FLM_PORT="${FLM_PORT:-50001}"

exec </dev/null

# Check if FLM is running
PROC_COUNT=$(powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count" 2>/dev/null | tr -d '\r' || true)

if [ -z "$PROC_COUNT" ] || [ "$PROC_COUNT" -eq 0 ]; then
    echo "No FLM process running — nothing to stop."
    exit 0
fi

echo "Found $PROC_COUNT FLM process(es). Stopping..."

powershell.exe -NoProfile -Command "taskkill /IM flm.exe /F" 2>/dev/null || true

# Verify stopped
sleep 1
REMAINING=$(powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count" 2>/dev/null | tr -d '\r' || true)

if [ -z "$REMAINING" ] || [ "$REMAINING" -eq 0 ]; then
    echo "FLM stopped. NPU model unloaded."
else
    echo "WARNING: $REMAINING FLM process(es) still running — may need manual taskkill."
    exit 1
fi
