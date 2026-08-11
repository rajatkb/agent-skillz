---
name: windows-debugging
description: Windows debugging knowledge base — esoteric bugs and proven fixes collected over time. Current chapters — (1) video present stalls from overlay/frame-limiter hooks (RTSS/RivaTuner blocking D3D11 Present in embedded/libmpv players, picture freezes while audio continues and logs stay clean), and (2) Windows 11 25H2 DWM/MPO corruption after virtual-display use (fullscreen game flickering and green line, fixed via OverlayTestMode registry). Load when diagnosing Windows video stutter or freezes, DWM/MPO flicker, or any of the specific symptoms below. Add new chapters as more esoteric bugs get solved.
---

# Windows Debugging

Umbrella skill for esoteric Windows bugs and their proven fixes. Each chapter is a self-contained playbook. Add new chapters as they're solved.

---

## Chapter 1 — Video Present Stalls (overlay/frame-limiter hooks)

**Trigger:** periodic ~1s picture freeze while **audio continues**; embedded/libmpv players stutter but standalone players and HTML5 are smooth; logs show nothing at the freeze moments.

### The core distinction (learn this first)

**Frame drop** = frames lost between decoder and renderer → shows in logs (`Discontinuous source PTS jump` in mpv), `i`-overlay decode counter climbs. Cause is usually decode/network/CPU.

**Present stall** = the picture freezes on screen while playback continues internally → **audio continues, NO log events, no drops counted**. The fault is between the renderer and the display: the D3D11 `Present()`/flip call itself blocks. This is the sneaky class — logs look "clean" at the exact freeze moments.

Discriminating question for the user: **does audio keep playing during the freeze?**
- Audio continues + picture only → present stall (this chapter's territory)
- Everything stops → core/decode issue

### Step 1 — Isolate with the fork matrix

Test in order (each takes 2 min):
1. **Standalone player** (same binary! e.g. Harbor bundles mpv.exe): `mpv.exe --no-config "<url>"` → smooth?
2. **HTML5/browser player** of the same content → smooth?
3. Embedded player in the app → stutters?

Interpretation:
- Standalone smooth + embedded stutters → the app's integration or a hook on that process (check Step 2 BEFORE blaming the app!)
- HTML5 smooth + standalone smooth → the D3D11/present path of the native player is the only victim → **external hook or driver**, not the app's config

### Step 2 — CHECK OVERLAY/FRAME-LIMITER TOOLS FIRST (the silent killer)

RTSS (RivaTuner Statistics Server, ships with MSI Afterburner), MSI Center/Afterburner overlays, Discord overlay, GeForce Experience overlay — these **hook D3D11 Present()** to draw overlays/enforce frame limits. A hooked Present can block 100–550ms in a periodic pattern (their ~1s timer cadence).

Check:
```powershell
Get-Process | Where-Object { $_.ProcessName -match "rtss|afterburner|encoder" }
```
Test: kill RTSS (and EncoderServer) → play → stalls gone = confirmed. RTSS auto-starts at boot — explains "suddenly started after a reboot" with no user changes.

**Fix (per-app ignore rule):** RTSS reads per-app profiles from `C:\Program Files (x86)\RivaTuner Statistics Server\Profiles\<AppName>.exe.cfg` (note: `Profiles\Global` is the all-app config). Create `<App>.exe.cfg` with:
```
[Hooking]
EnableHooking		= 0
```
RTSS ships these templates for video players (mpv.exe.cfg, VLC.exe.cfg, mpc-hc64.exe.cfg — all `EnableHooking=0`). **Restart the app** after creating it — RTSS reads profiles at process launch. For in-process libmpv (e.g. Harbor.exe), the profile targets the HOST process.

### Step 3 — Measure the present path (mpv): `--dump-stats`

The decisive tool. Add to mpv's extra options (Harbor: Settings → MPV → Advanced):
```
--dump-stats=C:\Users\<user>\AppData\Local\Temp\mpvstats.txt
```
Then run `scripts/analyze_flips.py <mpvstats.txt>` from this skill. Healthy flips ~400µs; flips of 100–550ms = present stalls = the freezes. **During a stall, render/hwdec-map/audio events continue** — that isolates the fault to the Present call itself.

### Step 4 — Correlation discipline (avoid the traps)

- **Dense periodic events ≠ cause.** Harbor's CW-snapshot loop fires screenshot commands every 12.0s — looked guilty, but dump-stats showed 47 stalls vs 4 grabs in the window. Count events before blaming.
- **Test must actually apply.** Harbor rewrites settings.json and reinstalls wipe mpvExtraOptions — twice a "fix" was reported tested but never applied (hwdec=no, playerMpvEmbed). ALWAYS verify the setting in settings.json/log after the user changes it (`Set property: X -> 1` lines).
- **Reinstall/update wipes fixes** — re-check settings after any user reinstall.
- **Present stalls produce zero log lines** — never conclude "no problem" from a clean log when audio-continues freezes are reported.

### Pitfalls

- `d3d11-flip=yes` (Harbor default) blocks when the swapchain queue is full — but blit mode (`d3d11-flip=no`) stalled identically here, so flip-model is usually NOT the cause; don't burn time on it. (Also: flip model is required for HDR passthrough — don't leave it disabled.)
- Writing to `C:\Program Files (x86)\...` from WSL needs elevation. Pattern that works: stage file in `%TEMP%`, then
  `powershell.exe -Command 'Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File","C:\...\script.ps1" -Wait'`
  — the UAC prompt MUST be approved by the user; if it exits with "operation canceled by the user", the prompt was dismissed.
- AMD driver version matters for present-path bugs (mpv #15597 fixed only by driver update) — check driver age when RTSS isn't present.

---

## Chapter 2 — Windows 11 25H2 DWM/MPO Corruption (after virtual display use)

**Trigger:** after using Apollo/Moonlight (or any virtual display driver — SudoVDA/IddSampleDriver), games flicker in FULLSCREEN as if alt-tabbing rapidly; a green line at the top of the screen; works fine windowed/borderless; works at non-native resolutions (e.g. 900p vs 1080p); affects BOTH GPUs (hybrid laptops); persists across reboots, driver reinstalls, GPU switching. Full writeup saved at `~/Work/apollo-moonlight-25h2-dwm-fix/README.md`.

### Root cause

Windows 11 **25H2 (build 26200)** has a known DWM **Multiplane Overlay (MPO)** bug: the MPO plane allocation table gets corrupted when the display topology changes — exactly what virtual-display drivers do when they connect/disconnect. After corruption, fullscreen games request planes from the broken table → misaligned planes (green line) + plane swapping (flickering).

Sources: Microsoft GitHub `Windows-Dev-Performance` issue #129 (24H2/25H2 display flicker & game crash); Microsoft Q&A 5749171 (flicker = DWM/MPO conflict); SmoothFPS MPO guide (OverlayMinFPS companion); NVIDIA driver 581.08 notes bug 5434811 (power-cycling monitor + NVIDIA App flicker).

### The fix (three registry keys, reboot required)

```powershell
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayTestMode" /t REG_DWORD /d "0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayMinFPS" /t REG_DWORD /d "0" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v "DisableOverlays" /t REG_DWORD /d "1" /f
```

| Key | Before | After | Effect |
|-----|--------|-------|--------|
| `OverlayTestMode` | 5 (default) | 0 | **The critical one.** Disables MPO compatibility-testing mode → DWM falls back to software composition, bypassing the corrupted plane table |
| `OverlayMinFPS` | unset | 0 | Prevents 25H2's dynamic MPO plane reallocation on framerate changes (which re-triggers the corruption) |
| `DisableOverlays` | 1 (default) | 1 | Kernel-level overlay disable (already default; included for completeness) |

### Notes

- The corrupted state lives in **DWM's runtime memory** — no file/log to inspect or repair; the only cure is the registry workaround.
- **Leave the keys as-is.** Reverting `OverlayTestMode` to 5 brings the flicker back (corrupted plane table still in DWM state). Only try reverting on a Windows version that Microsoft claims fixed MPO (e.g. 26H1+).
- Trade-off is negligible extra GPU bandwidth for desktop composition — imperceptible on modern GPUs.

### What did NOT fix it (don't re-try)

Deleting GraphicsDrivers registry cache (Configuration/Connectivity/ScaleFactors); CRU EDID reset; uninstalling the virtual display driver; reverting FSO/GameDVR keys; switching dGPU-only mode; changing color format (RGB→YCbCr422); removing NVIDIA App/overlay; RTSS OSD off; latest NVIDIA driver; sfc /scannow.

---

## Related

- `harbor-stremio-client` skill: Harbor-specific logs (harbor-mpv.log at `Roaming/app.harbor/`), settings, and the CW-snapshot grab loop (real but minor contributor, ungated 12s render-API readback — harmless with RTSS gone).
- mpv GitHub #15196 (Windows 11 D3D11 present stutter class, closed unfixed — often actually external hooks/driver).
