# mpv-embed stutter — RESOLVED (Aug 2026): Continue-Watching snapshot loop

Worked case on G14 GA403 (AMD 890M iGPU, 4K OLED, Win11 25H2). Harbor's embedded libmpv stuttered ~1s every 15–100s; HTML5 player smooth; **bundled standalone mpv smooth** → Harbor-integration bug, not engine/system.

## The fork that ended the guessing
- `& 'C:\Users\RAJAT\AppData\Local\Harbor\mpv.exe' --no-config '<stream-url>'` → SMOOTH (same mpv build, same 4K stream)
- Harbor mpv (embedded) → stutters; HTML5 player → smooth
- Conclusion: run this fork EARLY when a stutter survives config changes — it splits "Harbor integration" vs "mpv engine + system" in 2 minutes and stops theory-cycling.

## Root cause (proven in log, confirmed in code)
Harbor's Continue-Watching snapshot feature grabs a 4K frame during playback **every 12.0 seconds**:
- Log evidence (post cache-on-disk=no session, 187s): `harbor-cw-*.jpg` screenshot-to-file at 27.8, 35.8, 47.8, 59.8, 71.8, 83.8, 95.8... (exactly 12.0s apart) — 8 of 9 `Discontinuous source PTS jump` events sit ON those moments, each with `Spent 40–54 ms generating shader LUT` + `(Re)creating ... texture` + GPU readback → drops 10–13 frames ≈ the visible 1s freeze. Audio also disturbed at capture moments (wasapi property changes, occasional underrun).
- Code anchors (beta-branch):
  - `src/views/player/hooks/use-exit-snapshot.ts` — `CACHE_MS = 12000` (refresh cadence), `WARM_MS = 4000`, `EXIT_GRAB_MS = 700`; `grabFrame()` → `captureMpvFrame()` (render-API grab via `mpv_screenshot_data_url`) or `mpv_save_screenshot`
  - `src/lib/snapshots.ts:67` — `snapshotsDisabled() { return retentionDays() === 0; }`; gates read/write/save paths
  - `src-tauri/src/mpv.rs:1759` — `harbor-cw-{uuid}.jpg` temp path
  - Settings UI: `src/views/settings/library-panel.tsx` "Continue Watching screenshots" section (`RetentionPicker` → `cwSnapshotRetentionDays`)
- **THE FIX**: Settings → Library → Continue Watching screenshots → retention = **0** (key `cwSnapshotRetentionDays`, defaults.ts:406). Retention 0 disables the entire machinery.

## Secondary Harbor mpv-integration bugs found (real, worth reporting upstream)
1. **cache-dir runtime rejection**: `mpv.set_property("cache-dir", ...)` after init returns `-3` (MPV_ERROR_PROPERTY_UNAVAILABLE — init-only option). Code ignores it (`let _ =`), so `cache-on-disk=yes` runs with a NULL dir (log: `cache path: '' -> '-'`, `home path: '' -> '-'` — embedded instance has no config dir) → `[e][mkv]/[e][lavf] Failed to create file cache` every session (10+/session). Workaround: mpvExtraOptions `cache-on-disk=no` (extra options apply AFTER Harbor's — verified: `Set property: cache-on-disk="no" -> 1` follows Harbor's `"yes"`). Kills churn; NOT the freeze cause.
2. **HDR LUT churn**: `playerHdrToSdr=true` → `hdr-compute-peak=yes` + spline tone-mapping (mpv.rs ~404-409) → dynamic peak estimation = constant LUT invalidation (401 in ~30 min). `reassert_hdr_colorspace` (mpv.rs:796, fires on `video-params/gamma` change when `monitor_hdr_active` ~1321 is true) re-sets `target-peak` mid-playback → more LUT/swapchain churn (mpv #17473 mechanism). `playerHdrToSdr=false` kills the churn (401→6) AND unlocks native HDR passthrough (with it true, Harbor tone-maps HDR→SDR: target-trc=bt.1886, target-prim=bt.709). Keep false.
3. **TorBox URL expiry**: direct `tb-cdn.pw/dld/...` URLs 400 out within ~30–60 min — standalone test needs a FRESH URL from a new playback; the token in the URL is the user's TorBox API key. PowerShell invocation gotcha: quoted path needs `&` call operator.

## Ruled out (with evidence)
- VRR off (Reddit fix) — no change
- Seek-preview off — no change (captures are the CW path, not seek preview)
- hwdec on/off — log still showed d3d11va when user reported testing it; verify via log, not user report
- HDR churn alone — eliminated 401→6 LUT regens, freeze persisted
- Disk cache alone — 0 failures after `cache-on-disk=no`, freeze persisted
- 24Hz panel switching — `display-fps: 165.000000` (win32 line) = panel at 165Hz; libplacebo "display FPS: 23.95" is present-rate of 24fps content, NOT panel refresh
- Audio-driven drops — underruns did NOT precede PTS jumps (2/27 within 5s)
- Sucrose wallpaper engine (second libmpv) — running at 500MB+GPU context but CreationDate showed it started the NEXT morning, after the stutter sessions; check Win32_Process CreationDate before blaming it
- Harbor #769 `hwdec=auto-copy` regression — only affects stable < 0.9.21 (pre-Jul-16-2026 fix); user stuttered on the fixed beta too

## Correlation mirage (methodology lesson)
Screenshots fire every 6–12s → ANY event is within ~8s of a screenshot by density alone ("25/27 jumps near a screenshot" is meaningless as-is). Proof requires either: tight deltas (<1s) at the drop moment, or disabling the feature (retention=0) and comparing cadence. Same trap applies to any periodic background work (pollers, timers).

## Reinstall silently reverts both fixes (bite-2x in one session)
After reinstalling beta 0.9.118, settings.json reset to defaults and BOTH fixes vanished: `cwSnapshotRetentionDays` 0→7, `mpvExtraOptions` → "" (cache-on-disk=no gone). Freezes returned while the user believed the fix was still in place — the "still happening" report was stale config, not a failed fix. Ground truth before re-debugging: `grep -oE '"(cwSnapshotRetentionDays|mpvExtraOptions)"[^,}]*' C:\Users\RAJAT\AppData\Roaming\app.harbor\settings.json` → re-apply both, then test. A clean session WITH both fixes = 0 PTS jumps / 0 underruns / 0 cache failures over 7 min.

## Bug report filed upstream (Aug 2026)
Title: "[Bug]: Embedded mpv stutters with periodic ~1s freezes on Windows — standalone mpv.exe is smooth, HTML5 player is smooth". Affected area: Playback/player/mpv.
- Harbor 0.9.118 (beta), also reproduced on stable 0.9.21; Win11 Home 25H2 (build 26200); Ryzen AI 9 HX 370 + Radeon 890M iGPU (hybrid, running on iGPU); MSI MAG321UP OLED 4K@165Hz via USB-C; TorBox debrid streams; mpv v0.41.0-604-gcfd818bca (May 2026 bundled build).
- Body: isolation facts (standalone bundled mpv.exe --no-config smooth on same URL / HTML5 smooth / embedded stutters); log evidence (Discontinuous source PTS jumps with uniform ~0.45s gaps, harbor-cw screenshot-to-file every ~12s with 40–54ms LUT regens, LUT invalidated ×401 in 30min with hdr_to_sdr=true, cache-dir -> -3 + Failed to create file cache ×10/session, audio underruns 22/session uncorrelated 2/27); 12-item tried-list (full reinstall, both versions, hwdec=no, VRR off, seek-preview off, HDR-to-SDR off, retention=0, cache-on-disk=no, OS reboot, Sucrose removal, standalone mpv smooth, HTML5 smooth); untested at filing: playerMpvEmbed=false (unembedded mpv via Harbor).
- POST-FILING CONFIRMATION (same day): user confirmed the isolation once more — "When mpv was launched separately it was fine. Inside harbor its not fine." CW-snapshot grab = the cause, closed. playerMpvEmbed was never actually toggled (settings still `true` — don't trust a claim of "tested unembed" without checking settings.json).

## Git history — never guarded, still live on main (Aug 2026)
- `use-exit-snapshot.ts` added **2026-06-04 (v0.8.5, commit a062c96e7)** with the SAME ungated structure: `CACHE_MS = 12000` + `grabFrame → captureMpvFrame()` unconditional + `setInterval(() => void tick(), CACHE_MS)`.
- Only 4 commits touching the file (Jun 4 → Jul 6, commit 72345cb10) — all feature/param additions (`fullQuality`, `resolvedImdbVerified`), **never a guard** (no retention/snapshotsDisabled/seek check on the grab in any version).
- **Current `main` still ungated** (line 115 interval, line 58 grab) → no upstream fix exists; the bug is live in the current tree. The report is not redundant.
- Git links: history https://github.com/harborstremio/harbor/commits/main/src/views/player/hooks/use-exit-snapshot.ts · introduced https://github.com/harborstremio/harbor/commit/a062c96e7 · current https://github.com/harborstremio/harbor/blob/main/src/views/player/hooks/use-exit-snapshot.ts#L115

## No-user-lever proof (complete list — for "how do I turn this off" questions)
`seekPreviewEnabled` → gates ONLY the trickplay fallback (use-exit-snapshot.ts:59-60), not the mpv grab. `cwSnapshotRetentionDays` → gates ONLY persistence (`snapshotsDisabled()` at snapshots.ts:67, checked at lines 113/145/184 — never in `captureMpvFrame` at 256). `cwSnapshotFullQuality` → image quality only. `playerShellId` → cosmetic UI shells (player-panel/shell-section.tsx), unrelated. Frontend JS compressed inside harbor.exe (`localStorage`/`harbor.settings` = 0 grep hits on the 162MB binary) → no binary patch path. Answer to the user is: cannot be disabled by any setting or patch; HTML5 engine or upstream fix only.

## Log-validation greps (evidence the user pasted into the report)
```bash
grep -n "screenshot-to-file" harbor-mpv.log        # grab command starts — exactly 12.0s apart
grep -n "Screenshot:.*harbor-cw" harbor-mpv.log    # completions — delta = core-thread block (41–348ms measured)
grep -n "Discontinuous source PTS" harbor-mpv.log  # frame drops — land within ~1–5s of grabs
```
Measured session: 20 grabs in 1859s, every 12.0s on the dot (8.0s first gap = WARM_MS offset), each blocking 41–348ms (1–8 frames @ 23.976), 4/4 drops within ~1–5s of a grab. Note: the command→completion delta is the minimum block; the perceived freeze can extend beyond it (readback stalls the GPU pipeline affecting subsequent presents).
