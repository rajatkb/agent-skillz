# mpv-on-Windows stutter class — upstream research (Aug 2026)

Worked case: Harbor (Tauri + libmpv embed) on G14 GA403 (Ryzen AI 9 HX 370 + RTX 5070 Ti, hybrid mode, AMD iGPU driving playback + MAG321UP OLED 4K). 1s freezes every 15–100s, uniform 11-frame drops, audio underruns. HTML5 player in Harbor = perfectly smooth → system exonerated, bug lives in the mpv embed.

## What "sudden onset" means (the user's core question)
The bug class itself is characterized by sudden onset. mpv #15196 reporter: *"Video is running fine for about 20-60 minutes fine without stutter in fullscreen and then begin to stutter suddenly"* — with vanilla mpv, no config, no shaders. On this machine the catalyst was a power cycle: display link renegotiation (EDID/refresh/VRR state) after the OLED returned from standby landed mpv's present path in the bad state. Nothing the user changed.

## Upstream sources (verified via GitHub API + web search)
| Source | Finding |
|---|---|
| mpv #15196 "Video stuttering on Windows 11" (Oct 2024, 46 comments, CLOSED unfixed) | Stutter with display refresh matched to 23.976Hz; `i` overlay shows no drops but video clearly stutters; sudden onset after 20–60 min; config-independent. Best leads tried: madVR "Direct3D 11 for presentation" + "present several frames in advance" fixed it in MPC-HC (D3D11 present path!); nvdec+vulkan partial; no clean mpv fix |
| mpv #15597 "Stuttering with wayland and 23.976/24Hz refresh" (Dec 2024) | *"The video jumps always happen when TV refresh rate is set to match videos like 23.976Hz or 24Hz"* — AMD iGPU (M780, sibling of 890M); fixed only by kernel/driver update; amdgpu.dcdebugmask=0x400 also cited |
| r/mpv "MPV Randomly Stuttering" (2021, still cited) | VRR on = mpv stutters. Fix: turn Variable Refresh Rate off (Windows Settings → System → Display → Graphics) or enable G-SYNC for mpv |
| mpv #11863 | d3d11va + vo=gpu-next bad interaction, 10x peak frame times vs vo=gpu |
| mpv #16685 (discussion) | Irregular stutter + A/V desync with d3d11va hwdec in every build since ~late Aug 2024 |

## Trigger combo on this machine (all three present)
1. AMD iGPU (Radeon 890M) hwdec d3d11va + gpu-next
2. Refresh matching: Harbor `playerDisplayPanel` (auto/"oled") switches panel to 24Hz for 24fps content — mpv log: `Estimated source FPS: 24.096, display FPS: 24.390`
3. mpv D3D11 flip present (`playerD3d11Flip: true`) + OLED VRR

HTML5/Chromium immune: Chromium's compositor/present path differs from mpv's frame pacing — the decisive A/B that exonerated the whole system.

## Evidence-ranked fix list (test one at a time, restart playback)
NOTE: superseded as PRIMARY cause by the later HDR tone-mapping churn finding — see references/hdr-tone-mapping-churn.md (fix: `playerHdrToSdr=false`). Keep these as secondary levers; VRR-off and seek-preview-off were tested NEGATIVE on the worked case.
1. `playerDisplayPanel` → fixed 120 (stop 24Hz matching) — strongest per #15597/#15196
2. Disable VRR on the OLED: Windows Settings → System → Display → Graphics → Variable refresh rate → off
3. MPV Advanced: `d3d11-flip=no`
4. MPV Advanced: `cache-on-disk=no` (fixes the independently-broken disk-cache layer; see SKILL.md Pitfalls for the `cache-dir -> -3` runtime rejection)

Harbor settings keys touched this session: `playerEngine` (auto/mpv/html5), `playerMpvEmbed`, `seekPreviewEnabled` (false = no harbor-cw-*.jpg core-thread blocks), `mpvExtraOptions`, `mpvHwdec`, `playerD3d11Flip`, `playerDisplayPanel`, `playerHdrToSdr` (true = tone-map gate; false needed for true native-HDR passthrough), `torrentFullDownload`.

## Native-HDR note
User wants mpv back specifically for native HDR/DV passthrough (HTML5 tone-maps). Verify Windows HDR is ON for the OLED and `playerHdrToSdr` is false for true passthrough. If panel/VRR levers don't cure the stutter, HTML5 remains the fallback for non-HDR viewing; #15196 has no clean upstream fix.
