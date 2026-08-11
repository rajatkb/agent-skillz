#!/usr/bin/env python3
"""Analyze mpv --dump-stats output for present stalls (video-flip durations).
Usage: python3 analyze_flips.py <mpvstats.txt>
Healthy: median ~400us, max <10ms. Stalls: flips >100ms = present blocks = freezes.
"""
import bisect
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else (
    "/mnt/c"
    + os.environ.get("USERPROFILE", r"C:\Users\Public")[2:].replace("\\", "/")
    + "/AppData/Local/Temp/mpvstats.txt"
)
starts, ends = [], []
for ln in open(path, encoding='utf-8', errors='replace'):
    p = ln.split()
    if len(p) < 3:
        continue
    ns = int(p[0]) / 1e9
    if p[1] == 'start' and p[2] == 'video-flip':
        starts.append(ns)
    elif p[1] == 'end' and p[2] == 'video-flip':
        ends.append(ns)

starts.sort()
flips = []
for e in ends:
    j = bisect.bisect_right(starts, e) - 1
    if j >= 0 and e - starts[j] < 2.0:
        flips.append((starts[j], e - starts[j]))

if not flips:
    print("no video-flip events found — is dump-stats active and is vo=gpu-next in use?")
    sys.exit(1)

slow50 = [d for _, d in flips if d > 0.050]
slow100 = [d for _, d in flips if d > 0.100]
med = sorted(d for _, d in flips)[len(flips) // 2]
mx = max(d for _, d in flips)
print(f"flips: {len(flips)}  range {flips[0][0]:.1f}s -> {flips[-1][0]:.1f}s")
print(f"median: {med * 1e6:.0f}us | max: {mx * 1000:.0f}ms")
print(f">50ms:  {len(slow50)}  ({100 * len(slow50) / len(flips):.2f}%)")
print(f">100ms: {len(slow100)}  ({100 * len(slow100) / len(flips):.2f}%)  <-- present stalls (freezes)")
if slow100:
    print("\nstall times (seconds into session):")
    for s, d in sorted((s, d) for s, d in flips if d > 0.100):
        print(f"  {s:9.2f}s  {d * 1000:6.0f}ms  ({(d / 0.041667):.0f} frames)")
