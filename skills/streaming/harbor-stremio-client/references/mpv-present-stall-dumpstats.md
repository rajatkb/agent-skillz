# Diagnosing Harbor mpv present stalls with --dump-stats (Aug 2026, G14 GA403)

Worked case that ended a multi-theory hunt: "picture freezes ~1s, audio continues" (present stall) that
survived every Harbor config, was invisible in harbor-mpv.log, but was finally measured at the source:
the D3D11 Present() call blocking 100–554ms.

## When to use this
User reports picture freezes with audio continuing (present stall) and the mpv log is CLEAN
(no PTS jumps / underruns / cache lines at the freeze). Log forensics cannot see present stalls —
measure the present path directly.

## Setup
Settings → MPV → Advanced → `--dump-stats=C:\Users\<user>\AppData\Local\Temp\mpvstats.txt`
(runtime-settable; applied via Harbor's extra-options layer; no restart of the app needed, player restart applies it).
The file fills with per-frame events at ns timestamps on mpv's clock (divide by 1e9 = mpv-seconds,
same clock as the log's `[  12.345]` stamps → direct overlay with screenshot/grab times).

## The analysis (python, run on the stats file)
Key events:
- `start/end video-flip` — the D3D11 Present call. duration = present blocking time.
- `start/end video-draw`, `render`, `hwdec-map` — render-thread work. NOTE: hwdec-map fires EVERY
  frame (~849 maps ≈ 843 flips) — it is the normal decode-surface map, NOT a screenshot/readback marker.
- `value <x> audio-diff` — A/V sync drift.

```python
import re, bisect
from collections import Counter
stats = open('mpvstats.txt', encoding='utf-8', errors='replace').read().splitlines()
starts, ends = {}, []
for ln in stats:
    p = ln.split()
    if len(p) < 3: continue
    ns = int(p[0])/1e9
    if p[1] == 'start' and p[2] == 'video-flip': starts[ns] = ns
    elif p[1] == 'end' and p[2] == 'video-flip': ends.append(ns)
ss = sorted(starts); durs = []
for e in ends:
    j = bisect.bisect_right(ss, e) - 1
    if j >= 0: durs.append(e - ss[j])
buckets = Counter('>100ms STALL' if d > .1 else ('20-100ms' if d > .02 else ('2-20ms' if d > .002 else '<2ms normal')) for d in durs)
print(dict(buckets))                      # expect: hundreds normal @ ~0.4ms, tens of >100ms
print([(round(d*1000), round(t,1)) for d, t in sorted(zip(durs, ends), reverse=True)[:15]])
```

## What the worked case showed (numbers to quote in a bug report)
- 2151 normal flips, median **393µs**; **47 flips 100–554ms** → the Present call itself is the freeze.
- During a stall: video-draw/render/hwdec-map keep firing (rendering works), audio-diff ±1ms
  (A/V sync fine) — only video-flip hangs until the stall ends → swapchain Present blocks
  (flip-model queue-full / DWM not consuming).
- Stall gaps = exact multiples of 25 frames (~1.04s) → periodic ~1s contention, matching the
  WebView2 UI's ~1s update churn against the embedded child window (mpv #15196 class).
- Grab-loop exoneration: 47 stalls vs 4 `screenshot-to-file` grabs in the same window → a 12s
  grab loop cannot cause 18 stalls in 40s. COUNT events before correlating.

## Levers (in order, both untested at session end)
1. `playerMpvEmbed=false` (Settings → Player → "Embed mpv inside Harbor window") — mpv own window,
   out of the WebView2 composition path. VERIFY in settings.json — the user claimed this twice while
   `playerMpvEmbed` stayed `true`.
2. `d3d11-flip=no` (mpvExtraOptions) — blit-model Present doesn't queue-block (classic #15196 workaround).
3. HTML5 engine (known smooth on this machine).

## Pitfalls that cost hours
- Present stalls produce NO log events — never call a session "clean" from harbor-mpv.log when the
  symptom is picture-freeze+audio-continues. Measure the present path (dump-stats) or trust the user.
- PTS-jump forensics (uniform 11-frame gaps) are a DIFFERENT bug class (frame drops); matching them to a
  present-stall symptom sends you down the wrong path.
- Dense-schedule correlation is a mirage: at a 12s grab cadence any event is "near" a grab; a clean test
  is event COUNT (stalls vs grabs) or user-timestamped freezes (±2s, 33%/sample chance → 5 samples = 0.4%).
- Verify settings actually applied (settings.json + mpv log `Set property:` lines) before accepting
  "I tried that" — twice this session a test never ran (hwdec=no, playerMpvEmbed=false).
