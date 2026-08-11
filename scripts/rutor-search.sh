#!/bin/bash
# WSL wrapper for rutor-search.ps1
# Usage: rutor-search "game name" [filter]
#   rutor-search "cyberpunk 2077"
#   rutor-search "elden ring" FitGirl

SCRIPT="C:\Users\RAJAT\.hermes\rutor-search.ps1"
ARGS="-Q \"$1\""
if [ -n "$2" ]; then
    ARGS="$ARGS -F \"$2\""
fi

exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$SCRIPT" $ARGS
