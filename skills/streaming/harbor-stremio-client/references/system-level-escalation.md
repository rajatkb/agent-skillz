# System-level escalation: stutter that survives a Harbor reinstall (worked case, Aug 2026)

When a Harbor 1s-freeze complaint survives a FULL app reinstall (stable over beta) with fresh
default settings, every app-level variable is eliminated. The problem is below the app layer:
OS boot state, the decode path, the audio engine, or drivers. This is the escalation path used
when the user has already ruled out everything on their side.

## The key insight: Harbor reinstall ≠ OS reboot

A Tauri app reinstall only restarts the app process. Kernel/driver state that a fresh boot
would clear is untouched. Before assuming anything about "did the machine restart", check:
`(Get-CimInstance Win32_OperatingSystem).LastBootUpTime` — correlates "sudden onset" with a boot.

Case fact pattern: afternoon playback fine → machine powered off (no sleep/resume events 42/107;
only Kernel-General 1 boot events) → cold boot at 23:14 → Harbor launched → stutter from that
boot onward, persisting through a Harbor reinstall 45 min later. The OS never rebooted in between.

## Elimination matrix (what got ruled out and how)

| Suspect | Evidence it's not the cause |
|---|---|
| Harbor version (beta 0.9.118 → stable 0.9.21) | both stutter; reinstall kept same libmpv-2.dll build |
| Settings | fresh defaults still stutter |
| Source/CDN | keys removed (no TorBox/addons) still stutter |
| Power source | `Win32_Battery` BatteryStatus=2 (AC), 100% |
| Windows Update drivers that week | COM UpdateSearcher history: only Defender defs, WindowsAppRuntime, one "AMD System Driver Update (1.0.19.4)" = DRTM boot driver (irrelevant) |
| MPO/DWM | `HKLM:\SOFTWARE\Microsoft\Windows\Dwm` OverlayTestMode=0, OverlayMinFPS=0 (fix intact) |
| NVIDIA | playback runs on AMD iGPU (d3d11va); nvidia-smi P4/15W = idle dGPU |
| **OS boot (no reboot since onset)** | **never tested at diagnosis time — first action** |

## System-level commands (from WSL, via powershell.exe)

```powershell
# boot time / uptime
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime

# sleep (42) / resume (107) / boot (Kernel-General 1) events
Get-WinEvent -FilterHashtable @{LogName="System"; StartTime=(Get-Date).AddHours(-24); Id=42,107,1}

# GPU TDR / driver crash (absent = no driver crash)
Get-WinEvent -FilterHashtable @{LogName="System"} | ? { $_.ProviderName -match "nvlddmkm" -or $_.Id -eq 4101 }

# driver ages — look for generation mismatch (case: Radeon 890M June 2025 vs AMD PMF Aug 5 2026)
Get-CimInstance Win32_PnPSignedDriver | ? { $_.DeviceName -match "AMD|Radeon|Realtek" } | select DeviceName,DriverVersion,DriverDate

# DEFINITIVE Windows Update history incl. driver titles (Get-WinEvent WU messages come back EMPTY)
$s = (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher()
$h = $s.QueryHistory(0, 60)   # iterate; filter .Date > threshold; print .Title, .ResultCode

# audio engine load (elevated CPU-seconds = shared-mode mixer working overtime)
Get-Process audiodg | select CPU, @{n="RAM_MB";e={[math]::Round($_.WorkingSet64/1MB)}}

# which GPU drives which display
Get-CimInstance Win32_VideoController | select Name,CurrentRefreshRate,CurrentHorizontalResolution,CurrentVerticalResolution
```

## Discriminating tests (in order)

1. **Reboot the OS** → retest. Clears boot-state issues — the one variable a reinstall doesn't touch.
2. **Cross-app test**: same stutter in YouTube/browser video = system-wide (display/driver/audio
   stack); only-Harbor = mpv-specific.
3. **mpv A/B levers** (Settings → MPV → Advanced): `hwdec=no` (decode path — use when overlay
   shows "Dropped (decode) > 0, vo 0"), `audio-exclusive=yes` (audio engine — use when audiodg
   is busy / shared-mode underruns). Restart playback to apply.

## GitHub landscape (checked Aug 2026)

- #1176 (open): "Direct Play video playback not consistent/freezes" — 0.9.118, but different
  symptom (0-5s then dies on "Connecting", Plex direct URL).
- #837 (closed): "Playback freezes during streaming" — maintainer: "might be debrid related as
  well… we don't wanna regress anybody."
- beta-branch commits Aug 4→9 (atom feed): calendar, settings lazy-load, xray, subtitle-remember —
  NO player/mpv/cache fixes. Updating Harbor won't help a system-level cause.

## Reinstall side effects to warn the user about

- settings.json reverts to defaults: tmdbKey/tbKey/rdKey emptied, torrentFullDownload reset to
  false, custom stream filters gone. Keys must be re-entered (TMDB key survives only if re-saved).
- The mpv log is deleted on session end — reinstall churn can make it vanish mid-diagnosis;
  capture while live.
- Two settings stores can diverge after reinstall: Roaming settings.json (API keys) vs WebView2
  localStorage `harbor.settings` (EBWebView\Default\Local Storage\leveldb — binary; `strings`
  the .log file; values are length-prefixed so the value may sit on a separate line from the key).
