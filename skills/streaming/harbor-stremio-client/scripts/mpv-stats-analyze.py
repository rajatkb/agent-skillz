#!/usr/bin/env python3
"""
Analyze mpv --dump-stats output for D3D11 Present() stalls (present-stall diagnosis).

Usage:
  mpv-stats-analyze.py <mpvstats.txt> [cutoff_s]

Detects the "picture freezes ~1s, audio continues, log is clean" bug class:
the video-flip (Present) call itself blocking for 100ms+ while render/draw
events continue. Normal flips are ~400us; anything >100ms is a visible stall.

Worked case (Aug 2026, G14 GA403, Harbor embedded libmpv):
  BEFORE fix (RTSS hooking Present): 19 stalls in 50s, max 513ms, every ~1.04s
  AFTER  fix (RTSS killed):           0 stalls in 38s, max 8ms
Culprit was RivaTuner Statistics Server hooking D3D11 Present; the CW-snapshot
grab loop and d3d11-flip=no were both exonerated by counting events (see
harbor-stremio-client SKILL.md, ACTUAL ROOT CAUSE section).

To capture: add  --dump-stats=C:\Users\<user>\AppData\Local\Temp\mpvstats.txt
to Settings -> MPV -> Advanced (runtime-settable, applies mid-session).
"""
import bisect
import sys


def analyze(path, cutoff=None):
    starts, ends = [], []
    for ln in open(path, encoding="utf-8", errors="replace"):
        p = ln.split()
        if len(p) < 3:
            continue
        ns = int(p[0]) / 1e9
        kind = p[1]
        if kind == "start" and p[2] == "video-flip":
            starts.append(ns)
        elif kind == "end" and p[2] == "video-flip":
            ends.append(ns)
    starts.sort()

    flips = []  # (start_time, duration_s)
    for e in ends:
        j = bisect.bisect_right(starts, e) - 1
        if j >= 0 and e - starts[j] < 2.0:
            flips.append((starts[j], e - starts[j]))
    if not flips:
        print("no video-flip events found (is --dump-stats active? correct file?)")
        return

    if cutoff:
        flips = [(s, d) for s, d in flips if s >= cutoff]
    if not flips:
        print("no flips after cutoff", cutoff)
        return

    durs = sorted(d for _, d in flips)
    slow = [(s, d) for s, d in flips if d > 0.100]
    slow50 = [(s, d) for s, d in flips if d > 0.050]
    print(f"flip range: {flips[0][0]:.1f}s -> {flips[-1][0]:.1f}s  ({len(flips)} flips)")
    print(f"median: {durs[len(durs)//2]*1e6:.0f}us | max: {max(durs)*1000:.0f}ms")
    print(f"flips >100ms (visible stalls): {len(slow)}  ({100*len(slow)/len(flips):.2f}%)")
    print(f"flips >50ms: {len(slow50)}")
    if slow:
        print("\nstall times (seconds into session, duration):")
        for s, d in sorted(slow, key=lambda x: -x[1])[:20]:
            print(f"  {s:9.2f}s  {d*1000:6.0f} ms")
        # cadence check: inter-stall gaps
        st = sorted(s for s, _ in slow)
        gaps = [round(st[i + 1] - st[i], 3) for i in range(len(st) - 1)]
        print(f"\ninter-stall gaps: {gaps}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    analyze(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
