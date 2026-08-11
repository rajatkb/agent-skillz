# mpv-embed present-stall: final mechanism + causal proof protocol (Aug 2026)

Resolution of the G14 GA403 "1s picture freeze, audio continues" saga. The evidence chain that
convinced (and the mistakes along the way).

## The mechanism (why the grab = picture freeze + audio continues)

- mpv's player core (`cplayer` thread) is a SINGLE-threaded maestro: it sequences decode,
  A/V sync, and frame-present scheduling. Audio runs on its own wasapi thread with its own buffer.
- Harbor queues `screenshot-to-file` (with `screenshot-sw=no` = GPU readback) onto the core
  thread's command queue every 12s. The core thread must stop and execute it synchronously:
  1. D3D11 readback of the rendered 4K HDR frame (~50MB RGBA16F) — `Map()` on the immediate
     context stalls the GPU pipeline
  2. JPEG encode via zimg on CPU (log: "using 12 threads for scaling", "Spent 53ms generating shader LUT")
  3. Rust busy-waits up to 1500ms for the temp file (mpv.rs:1766-1777)
- While blocked, the core cannot schedule the next present → the last frame stays on screen =
  the freeze. The audio thread's buffer keeps playing = audio continues. On resume the picture
  jumps forward. **No frames are dropped, nothing logs** — present stall, not frame drop.

## Why intermittent + content-independent

- Readback duration varies with iGPU power state: 41ms (awake) → 348ms (asleep, clock/power ramp
  first). Frame budget at 23.976fps = 41.7ms. ≤40ms = one frame, invisible; ≥80ms = multi-frame, visible.
- Content-independent: the block is the same regardless of resolution (verified: 1080p SDR also
  freezes — the "cost scales with content" theory is WRONG).
- "Sudden Aug 9 onset": no system delta found (PMF driver theory retracted — pnputil shows
  amdpmf.sys package dated 05/08/2026, months before). The mechanism holds regardless of the trigger.

## Why standalone mpv + HTML5 are smooth (the clean A/B)

- Standalone `mpv.exe --no-config`: same binary/GPU/stream, but NOTHING injects commands into the
  core thread → never blocks → smooth. The ONLY difference is the 12s command injection.
- HTML5: snapshot path draws the `<video>` element to a canvas — Chromium compositor, fully async,
  no playback thread touched → smooth.
- Unembedded mpv via Harbor (`playerMpvEmbed=false`): STILL freezes — the grab is a core-thread
  command, window-independent. Don't waste a test on it.

## Causal proof protocol (live, while the user plays)

Everything before this is correlation (12s cadence, drops near grabs). To PROVE causation live:

1. Run a wall-clock-timestamped capture (scripts/live-mpv-log-capture.sh variant) that stamps
   `screenshot-to-file`, `Screenshot: ...harbor-cw`, PTS jumps, LUT regens with `date +%H:%M:%S.%N`.
2. User watches; at EVERY freeze they note the wall-clock second (taskbar clock/phone).
3. Correlate freeze-times vs grab-command times. Chance of a random freeze landing within ±2s of a
   grab ≈ 4s/12s ≈ 33%; 5 consecutive coincidences ≈ 0.4% — statistically conclusive.
4. Bonus discriminator during a freeze: if the `i` stats overlay freezes WITH the picture → core/
   render thread blocked (grab confirmed). Overlay alive while picture frozen → present/swapchain
   level (D3D11/DWM), different mechanism.

## Git-history technique ("was it ever guarded?")

- File history: `GET /repos/harborstremio/harbor/commits?path=<file>&per_page=100` → creation +
  every change (dates, shas, messages).
- Old versions: `https://raw.githubusercontent.com/harborstremio/harbor/<sha>/<file>` — diff old vs
  current to answer "was there ever a guard?" (Answer here: use-exit-snapshot.ts added 2026-06-04
  v0.8.5 commit a062c96e7, NEVER guarded, 4 commits total, current main still ungated at :115).

## Mistakes to not repeat (all cost real hours)

- Tracking PTS jumps as "the freeze" while the user's symptom was a present stall (invisible).
  The audio question ("does audio keep playing?") discriminates in seconds — ask it FIRST.
- Calling a session "clean" from log metrics when the user says it froze.
- Believing a reported test ran: hwdec=no was never applied (log still showed d3d11va), the unembed
  toggle was never changed (`playerMpvEmbed` stayed true), fixes were silently wiped by a reinstall.
  Ground truth = settings.json grep + mpv log `Set property:` lines, not the user's report.
- Theorizing about driver installs from file dates — pnputil is ground truth.
- Recommending retention=0 as "the fix" — it gates only persistence, not the grab.
- The final honest state: NO user-side off switch exists; HTML5 engine is the only relief; the
  fix is upstream (gate grab on snapshotsDisabled() or skip while playing).
