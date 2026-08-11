# RTSS (RivaTuner Statistics Server) D3D11 present-hook stalls — full case

## Resolution (Aug 10, 2026, G14 GA403 — Harbor embedded libmpv)

User-reported: periodic ~1s PICTURE freeze during playback, audio continues,
nothing in the mpv log at freeze moments. Survived every Harbor config,
both Harbor versions, fresh reinstall, VRR off, hwdec on/off, HDR-to-SDR off,
seek-preview off, cache-on-disk=no, unembed (claimed), and `d3d11-flip=no`.
Standalone bundled `mpv.exe --no-config` on the same stream was smooth.
HTML5 engine was smooth.

FINAL CAUSE: **RivaTuner Statistics Server (RTSS, ships with MSI Afterburner)
hooked the D3D11 Present() call of the embedded libmpv swapchain** (to draw
its overlay / enforce frame limits). Its hook blocked Present 100–554ms in a
mechanical ~1.04s-period pattern. Killing RTSS eliminated the stalls.

## The proof chain (log evidence)

1. `--dump-stats=C:\...\mpvstats.txt` in mpvExtraOptions → per-frame
   `video-flip` (Present) timing:
   - normal flips: **393µs median** (max 1.8ms)
   - **47 flips took 100–554ms** = the freezes
2. DURING a stall: `render`/`video-draw`/`hwdec-map` events CONTINUE,
   `audio-diff` stays ±1ms → decode+render+audio healthy; ONLY the Present
   call is blocked. Fault is between mpv and the screen.
3. Inter-stall gaps were exact multiples of 25 frames (~1.04s) — a
   mechanical external timer, not content/network/decode.
4. Event-counting killed competing theories:
   - CW-snapshot grab loop: 47 stalls vs 4 grabs in the window (a 12s loop
     cannot cause 18 stalls/40s). Grab loop is a REAL separate Harbor bug
     (ungated render-API readback every 12s) but not this freeze.
   - `d3d11-flip=no` (blit model): TESTED, did NOT fix — still 19 stalls/50s,
     max 513ms. Swapchain model exonerated.
   - audio/underrun, network, hwdec, HDR churn: all ruled out earlier.
5. Decisive A/B (same session, same stream, same config — only RTSS removed):
   BEFORE (RTSS active): 19 stalls in 50s, max 513ms
   AFTER  (RTSS gone):    0 stalls in 38s, max 8ms

## Why standalone mpv was smooth

RTSS hooks per-process via its profiles/global injection; Harbor.exe (the
process hosting libmpv) was hooked, while the standalone `mpv.exe` sessions
were not (RTSS ships an mpv.exe template that disables hooking — see below).

## Permanent fix: RTSS per-app ignore rule

RTSS already ships templates that disable hooking for video players:
`ProfileTemplates\mpv.exe.cfg`, `VLC.exe.cfg`, `mpc-hc64.exe.cfg` all contain:
```
[Hooking]
EnableHooking		= 0
```
Create the same for Harbor: `C:\Program Files (x86)\RivaTuner Statistics
Server\Profiles\Harbor.exe.cfg` with that content (tab-separated, ASCII).

- Program Files write needs admin: elevated PowerShell
  (`Set-Content ... -Encoding ASCII`) or Notepad-as-admin. UAC from WSL
  `Start-Process -Verb RunAs` may be declined — give the user the manual
  steps instead of fighting it.
- RTSS reads per-app profiles when the process LAUNCHES → **restart Harbor**
  after creating the file; an already-hooked process stays hooked.
- After an RTSS/Afterburner reinstall the Profiles folder may reset — re-create.

## Cleanup after diagnosis (test scaffolding to remove)

`mpvExtraOptions` should be left as just `cache-on-disk=no` (optional hygiene
fix for the cache-dir -3 bug):
- REMOVE `d3d11-flip=no` — tested, not the cause, AND it costs HDR10
  passthrough (flip model is required for proper HDR metadata on Windows).
- REMOVE `dump-stats=...` — diagnostic only; writes a multi-MB file to Temp.

## Recurring lesson (hit 3x this session)

User-reported test results were NOT applied twice (hwdec=no, playerMpvEmbed
toggle) — settings.json/mpv-log ground truth showed the change never landed.
Before accepting "I tried that": grep settings.json for the key AND the mpv
log for the applied `Set property:` line. A Harbor reinstall/update resets
settings to defaults, silently undoing applied fixes (cwSnapshotRetentionDays
0→7, mpvExtraOptions→empty) — re-verify after ANY reinstall before re-debugging.
