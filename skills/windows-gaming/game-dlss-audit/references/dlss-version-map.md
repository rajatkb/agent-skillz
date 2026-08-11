# DLSS Version Map (verified Aug 2026)

## Ground truth sources
- TechPowerUp DLSS SR tracker: https://www.techpowerup.com/download/nvidia-dlss-dll/
- TechPowerUp DLSS FG tracker: https://www.techpowerup.com/download/nvidia-dlss-3-frame-generation-dll/
- NVIDIA DLSS 4.5 announcements (nvidia.com/geforce/news, developer.nvidia.com/blog)

Fetch pattern when web_extract is unavailable (search-only backend):
```bash
curl -sL "<tracker-url>" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" | python3 -c "
import sys, re, html
t = sys.stdin.read()
t = re.sub(r'<script.*?</script>', '', t, flags=re.S)
t = re.sub(r'<style.*?</style>', '', t, flags=re.S)
t = re.sub(r'<[^>]+>', ' ', t)
t = html.unescape(t); t = re.sub(r'\s+', ' ', t)
seen=set()
for m in re.finditer(r'(310\.\d+(?:\.\d+)?)\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})', t):
    k=m.group(0)[:45]
    if k not in seen: seen.add(k); print(k)
"
```

## SR DLL (nvngx_dlss.dll) — version → generation
| Version | Date | Generation |
|---|---|---|
| 310.7.0 | Jun 24, 2026 | DLSS 4.5 (latest) |
| 310.6.0 | Mar 31, 2026 | DLSS 4.5 (added Dynamic MFG) |
| 310.5.3 | Jan 30, 2026 | DLSS 4.5 |
| 310.5.2 | Jan 29, 2026 | DLSS 4.5 |
| 310.5.0 | Jan 6, 2026 | **DLSS 4.5 launch** (2nd-gen transformer SR, 6x MFG) |
| 310.4.0 | Aug 27, 2025 | DLSS 4 |
| 310.3.0 | Jun 24, 2025 | DLSS 4 |
| 310.2.1 | Feb 10, 2025 | DLSS 4 |
| 310.2.0 | Feb 1, 2025 | DLSS 4 |
| 3.7.x | 2024 | DLSS 3.7 (CNN) |
| 3.1.x | 2023 | DLSS 3.1 |
| 2.5.x | 2022 | DLSS 2.5 (no FG era) |

## FG DLL (nvngx_dlssg.dll)
Same 310.x timeline: 310.0–310.4 = DLSS 4 MFG; **≥310.5.0 = DLSS 4.5** (6x MFG / Dynamic MFG). 3.x = DLSS 3 FG (single frame). Note: DLSS 4.5's 6x/Dynamic MFG requires RTX 50-series GPU + matching driver.

## Reading rules
- Version is the FileVersion string dotted (FileVer=310,6,0,0 → 310.6.0.0).
- Judge SR and FG independently — mixed kits exist (e.g. Wukong: SR 3.1.30 + FG 310.1.0).
- `bakup/` folders in repacks = original pre-swap DLLs; active files are what the game loads.
- RR (`nvngx_dlssd.dll`) can be newer than SR/FG in the same game (TLoU2: SR/FG 310.1.0, RR 310.5.0).

## Aug 2026 audit baseline (this machine)
DLSS 4.5 (≥310.5.0, both SR+FG): 007 First Light (310.6.0), Death Stranding 2 (310.5.2), Forza Horizon 6 (310.6.0), Dying Light The Beast (310.5.0), GoW Ragnarök (310.5.0).
DLSS 4 (310.1–310.4): Halo Campaign Evolved, PRAGMATA, Avatar FoP, RE Requiem, Cyberpunk 2077, TLoU2 (SR/FG), KCD2 (no FG DLL), GoT, HFW.
Older: Black Myth Wukong (SR 3.1.30), STALKER 2 (3.7.20), RDR (3.7.0), Dead Space 2023 (2.5.0, no FG).
