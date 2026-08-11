# Harbor mpv stutter — root cause candidate: HDR tone-mapping churn (Aug 2026, confirmed contributor, not sole cause)

Worked case: G14 GA403, AMD 890M iGPU playback, MAG321UP OLED (HDR10), Harbor mpv embed.
1s freezes every 15–100s, uniform 11-frame PTS gaps. HTML5 player = smooth. VRR off = no fix.
Seek-preview off = no fix. hwdec off = no fix (see verification pitfall below). Two Harbor
versions + fresh defaults + OS reboot = no fix. → the bug is in the mpv pipeline as Harbor
configures it, specifically its HDR handling.

## Evidence (from live-capture of harbor-mpv.log, ~30 min of 4K DV playback)
- 401 × `LUT invalidated, regenerating..` (≈1 per 6s; each = ~11ms shader recompile on the render thread)
- 17 × `Set property: target-peak="10000"` (Harbor's `reassert_hdr_colorspace` poking the HDR config)
- 21 × `New swap chain configuration received from hint: ... RGB_FULL_G2084_NONE_P2020` (HDR10 output renegotiation)
- 25 × `Discontinuous source PTS jump` (the visible freezes) — 17/25 land within 2.5s of a LUT/TP churn event
- 22 × `Audio device underrun detected.` (downstream of the same stalls)
- Swapchain is HDR10 (`RGB_FULL_G2084_NONE_P2020`) → `monitor_hdr_active()` gate is OPEN → reassert path live

## Mechanism (verified in harbor beta-branch source, src-tauri/src/mpv.rs)
- `playerHdrToSdr=true` → branch at ~404-409: `tone-mapping=spline`, `hdr-compute-peak=yes`,
  `hdr-contrast-recovery=0.30`, `hdr-peak-percentile=99.995`, `target-trc=bt.1886`, `target-prim=bt.709`
  → dynamic peak estimation = LUTs constantly recomputed. This ALSO means HDR was being tone-mapped
  to SDR — user was NOT getting native HDR despite believing they were.
- `reassert_hdr_colorspace()` (~796-819): sets `target-peak` "10000"/"auto" based on
  `video-params/primaries`; caller (~880-920) spawns a thread on every `video-params/gamma`
  PropertyChange, 250ms later re-reads gamma (pq/hlg), checks `monitor_hdr_active()` (~1321 —
  DXGI output color space == `DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020`), then reasserts.
- Line 384: `d3d11_flip && hdr_to_sdr` → Harbor forces `d3d11-flip=no` (relevant if toggling both).
- `playerHdrToSdr=false` → else-branch (~423-430): `target-colorspace-hint=yes` + `gpu-api=d3d11`
  (embedded) = native HDR passthrough, NO hdr-compute-peak → churn gone.

## The fix (applied, verified — PARTIAL)
`playerHdrToSdr=false` (Settings → Player → HDR to SDR → OFF) — kills the churn AND delivers real
native HDR passthrough. Requires Windows HDR ON for the OLED. Verified in the post-fix session:
churn collapsed 401→6 LUT regens, 17→0 target-peak sets, 21→1 swapchain reconfigs, 22→0 underruns;
0 tone-mapping options in the mpv log (pure passthrough). Do this regardless of the stutter.

## Follow-up (final state — churn was a contributor, NOT the whole story)
The 1s freeze PERSISTED after the churn fix: ~1-2 `Discontinuous source PTS` jumps per ~8-min
session, with NO churn/network/audio events near them. Audio correlation dead: only 2/27 PTS jumps
within 5s of an underrun — with `video-sync="audio"` hardcoded by Harbor, drift-driven batch resync
drops remain possible but are not underrun-driven (`video-sync=display-resample` in Advanced
overrides it). Frame captures (`harbor-cw-*.jpg`) still fire every ~12s with Seek Preview OFF
(`useExitSnapshot` CACHE_MS=12000 + trickplay, render-API grabs) — at 6-12s density any event is
within ~8s of a capture, so near-screenshot correlation is a MIRAGE (25/27 is expected by density,
NOT evidence). CASE LEFT AT: standalone bundled `mpv.exe --no-config` A/B (local 4K file + exact
stream URL) to split Harbor-integration vs mpv-engine. Until that runs, treat the churn as one
confirmed contributor (plus the native-HDR unlock) — not the definitive single cause.

## Upstream anchors
- mpv #17473 — HDR colorspace/swapchain reconfig → frame drops (source-dynamic tone mapping);
  comment: swapchain reconfig "can cause stuttering if it happens too often"
- Harbor #769 — `hwdec=auto-copy` Windows regression (Jul 6 beta sync), "can cause frame drops",
  fixed in beta Jul 16; stable 0.9.21 (Jul 11) predates the fix
- mpv #15196 / #15597 / r/mpv VRR / #11863 / #16685 — the broader present-path/24Hz stutter class
  (see mpv-stutter-research.md); these are SECONDARY levers, not the root cause here

## Correlation recipe (reproduce in future sessions)
1. Start `scripts/live-mpv-log-capture.sh` (background) BEFORE the user reproduces; pair with a 2s
   PowerShell `Get-Process harbor` CPU/RAM sampler.
2. Parse the capture: extract (wall-clock, mpv-time, text) per line; collect events for
   `LUT invalidated`, `target-peak`, `New swap chain`, `Discontinuous source PTS`, `underrun`.
3. Count churn + test proximity: PTS jump within ≤2.5s of a LUT/TP event. High churn counts
   (hundreds) + majority-of-jumps-near-churn ⇒ tone-mapping churn confirmed.

## Verification pitfall (user-report vs reality)
The user's "hwdec=no did not solve it" was NOT a valid test: the mpv log still showed
`Using hardware decoding (d3d11va)` in the tested session and settings.json said `mpvHwdec:"auto"`.
mpv options apply at PLAYER INIT — a mid-session UI toggle (or one not followed by a playback
restart) does nothing, and the user may have reverted it. ALWAYS confirm via log/settings.json
that the change took effect before accepting a negative test result.
