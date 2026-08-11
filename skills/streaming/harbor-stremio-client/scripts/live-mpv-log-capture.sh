#!/bin/bash
# Live capture of harbor-mpv.log with wall-clock timestamps; detects rotation/deletion.
# Harbor rewrites the log per mpv instance and DELETES it when playback ends, so:
#   - start this BEFORE the user starts the reproducing playback
#   - the first poll dumps the whole existing file (start clean for a full session)
# Usage: bash live-mpv-log-capture.sh [LOG] [OUT]   (defaults below)
# Companion sampler (optional, for process-level stall correlation):
#   while true; do powershell.exe -NoProfile -Command '$p=Get-Process -Name harbor -EA SilentlyContinue; if($p){"{0} cpu_s={1} ram_mb={2}" -f (Get-Date -Format HH:mm:ss),[math]::Round($p.CPU),[math]::Round($p.WorkingSet64/1MB)}'; sleep 2; done > /tmp/harbor_cpu.log
LOG=${1:-/mnt/c/Users/<user>/AppData/Roaming/app.harbor/harbor-mpv.log}
OUT=${2:-/tmp/harbor_live_capture.log}
: > "$OUT"
last_size=0
while true; do
  if [ -f "$LOG" ]; then
    cur=$(stat -c %s "$LOG" 2>/dev/null || echo 0)
    if [ "$cur" -lt "$last_size" ]; then
      echo "[$(date +%H:%M:%S.%3N)] === LOG ROTATED/RESET (new session) ===" >> "$OUT"
      last_size=0
    fi
    if [ "$cur" -gt "$last_size" ]; then
      tail -c +$((last_size+1)) "$LOG" 2>/dev/null | sed "s/^/[$(date +%H:%M:%S)] /" >> "$OUT"
      last_size=$cur
    fi
  else
    echo "[$(date +%H:%M:%S.%3N)] === LOG MISSING ===" >> "$OUT"
    last_size=0
  fi
  sleep 0.3
done
# Parse pattern for analysis (note: NO space after the closing bracket before [v][cplayer]):
#   ^\[(\d{2}:\d{2}:\d{2})\] \[\s*(\d+\.\d+)\](.*)
# Group 1 = wall clock, group 2 = mpv session clock. mpv clock stalls while wall advances
# = player stalled; gap (Y-X)*23.976 = frames skipped in a "Discontinuous source PTS jump".
