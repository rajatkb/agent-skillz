# TorBox CDN stall — worked diagnosis (Aug 2026)

Symptom reported: "video gets stuck ~1s every few minutes, then resumes; started suddenly in the evening; I changed nothing; the seekbar shows the video is already buffered."

## Verdict
Feed starvation on a direct TorBox CDN link, made hard-freeze (instead of smooth rebuffer) by `torrentFullDownload=True`. Evening onset = TorBox CDN peak-hour throttling, not a local change.

## Evidence trail (in order gathered)
1. Harbor RAM 295MB WS, 18.2GB free → NOT the 4K RAM trap.
2. `settings.json` (Roaming\app.harbor): `torrentFullDownload=True`, `mpvHwdec=auto`, `mpvExtraOptions=''`, `directTorrentStream=True`, `tbKey` set, rd/ad/pm/dl keys empty.
3. mpv log showed the toggle's caps applied to a debrid stream:
   ```
   Set property: demuxer-max-bytes="48GiB" -> 1
   Set property: demuxer-max-back-bytes="48GiB" -> 1
   Set property: demuxer-readahead-secs="100000" -> 1
   Set property: cache-secs="100000" -> 1
   ```
4. Disk cache broken: `Set property: cache-dir="C:\...\mpv-cache" -> -3` (init-only option at runtime) then `[e][mkv] Failed to create file cache` (×13 in one session). `mpv-cache\` dir exists but stays empty.
5. Stall signature (the freeze itself):
   ```
   [vo/gpu-next/libplacebo] Discontinuous source PTS jump 30.781000 -> 31.240000   (~0.46s video gap)
   [w][cplayer] Audio device underrun detected.
   [v][cplayer] restarting audio after underrun
   [v][cplayer] Set property: pause="yes" -> 1                                          (visible ~1s freeze)
   ```
   Audio underrun ⇒ demuxer stopped receiving data ⇒ feed stall, NOT decode/GPU/RAM.
6. Stream source: `Opening https://nexus-008.indi.tb-cdn.pw/dld/...` — direct TorBox CDN (India node), not Harbor's local proxy. The first URL (`torrentsdb.com/.../torbox/...`) failed: `Opening failed or was aborted` → Harbor fell back to the raw CDN link. Both = TorBox-side degradation.
7. "Changed nothing" check: Harbor.exe 0.9.118 LastWriteTime Aug 4, mpv v0.41.0-604 built May 5, ffmpeg N-124399 — no app update. System event log: no nvlddmkm / event 4101 (no GPU TDR); Windows Update + Kernel-Power churn only at 22:46–23:25, after the evening stalls.

## Commands used
```bash
# Harbor RAM + system free
powershell.exe -NoProfile -Command 'Get-Process -Name "Harbor*" | Select-Object Id,ProcessName,@{n="WS_MB";e={[math]::Round($_.WorkingSet64/1MB)}} | Format-Table -AutoSize; $os=Get-CimInstance Win32_OperatingSystem; "{0:N1} GB free" -f ($os.FreePhysicalMemory/1MB)'
# WSL→PowerShell gotcha: single-quote the whole -Command or bash eats $_

# settings keys (single-line JSON → parse with python)
python3 -c "import json;d=json.load(open('/mnt/c/Users/<user>/AppData/Roaming/app.harbor/settings.json'));[print(k,'=',repr(v)[:300]) for k,v in d.items() if any(s in k.lower() for s in ['hwdec','cache','full','download','mpv','stream'])]"

# stall counts + applied caps + source URLs (log rewrites per mpv instance — re-grep after restarts)
LOG=/mnt/c/Users/<user>/AppData/Roaming/app.harbor/harbor-mpv.log
grep -E "demuxer-max|readahead" $LOG | sort -u
grep -cE "underrun|Discontinuous source PTS" $LOG
grep -E "Opening https?://" $LOG
grep -E "cache-dir|Failed to create file cache" $LOG

# TDR / driver check (System log, last 14h)
powershell.exe -NoProfile -Command 'Get-WinEvent -FilterHashtable @{LogName="System"; StartTime=(Get-Date).AddHours(-14)} -ErrorAction SilentlyContinue | Where-Object { $_.ProviderName -match "nvlddmkm|NVIDIA|Kernel-PnP|Kernel-Power|WindowsUpdateClient" -or $_.Id -in 4101,14 } | Select-Object -First 25 TimeCreated,Id,ProviderName | Format-Table -AutoSize'
```

## External corroboration (TorBox CDN throttling is known/ongoing)
- TorBox help center, "My Torrent Is Slow Or Won't Load" (Aug 2025): *"This is an ongoing issue which we're working to rectify with our own upcoming CDN being setup in America."*
- r/TorBoxApp (May 2026): "Constant buffering on cached files played through Stremio" — top fix: change the CDN in the TorBox dashboard, or switch player.
- r/TorBoxApp + r/StremioAddons (days before this session): "Buffering SO MUCH since this new update", "TORBOX BUFFERING ISSUE" — widespread.
- Community fix order: (1) change CDN node in TorBox dashboard, (2) different player, (3) different debrid (RD).

## Related Harbor issues (GitHub search)
- #1170 [Bug]: Cached Debrid Player! (open)
- #785 Bug: seek bar glitching (closed)
- #664 New Beta player not working (closed; touched cache-dir)

## Fixes delivered
1. Toggle OFF "Download the whole file while streaming" (Settings → Player → Play Mode) — primary; restores ~600MB caps + graceful rebuffer.
2. If keeping the toggle: `demuxer-max-bytes=1GiB` + `demuxer-max-back-bytes=128MiB` in Settings → MPV → Advanced.
3. Decisive test for "it's buffered, so not the network": press `i` during playback; if cache buffering % collapses to ~0 at each freeze → feed starved, seekbar was showing target not headroom.

## REVISED verdict (same session, second pass — overlay disproved feed starvation)
User pressed `i` during a 4K HEVC + TrueHD playback; the overlay read:
```
Cache buffering: 100%      Dropped (decode / vo): 40 / 0
Engine: libmpv  Resolution: 3840x1608  hwdec: d3d11va  TrueHD 8ch 48kHz 20.24Mbps
```
Cache 100% + decode drops > 0 + vo 0 ⇒ feed healthy; the DECODER/present path is stalling and audio underruns are DOWNSTREAM. Lesson: the log signature (PTS jump + underrun + pause) alone does NOT prove feed starvation — check the overlay cache % first. Event ordering is unreliable (observed underrun BEFORE the PTS jump in one instance).
Additional findings:
- wasapi device buffer = 1056 frames @ 48kHz = 22ms (`Buffer frame count: 1056 (22000 us)`); audio underruns on any ≥20ms delay → audio is the canary, not the root cause. Fixes: `audio-exclusive=yes` / `audio-buffer=2` (Settings → MPV → Advanced).
- `OnPropertyValueChanged` fired on a DIFFERENT endpoint ({58145ff9...} = MAG321UP OLED display audio) — noise, not the cause.
- GPU: playback runs on the AMD iGPU (d3d11va = AMD); `nvidia-smi` P4/15W was the idle dGPU (user: "ignore NVIDIA, running on AMD").
- audiodg 76 CPU-s in ~30min uptime — shared-mode 7.1-float mixing working overtime.
- GitHub: #1176 (0.9.118 direct-play freezes — different symptom, open), #837 (freezes, closed — maintainer: "might be debrid related"); NO player/mpv fixes on beta-branch after 0.9.118 (commits atom feed, Aug 4–9) → updating won't help. Fresh boot ~23:14 + Kernel-Power churn before onset → boot-state suspect; reboot is the zero-cost A/B.
- Decode A/B test offered: `hwdec=no` — freezes gone = GPU decode/present path; remain = audio/demuxer side.
