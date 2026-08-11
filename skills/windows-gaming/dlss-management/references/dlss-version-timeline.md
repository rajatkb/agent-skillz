# DLSS Version Timeline & Preset System

Sources: TechPowerUp DLSS DLL / FG DLL / RR DLL tracker pages, NVIDIA DLSS 4.5 announcement (nvidia.com/geforce/news, Jan 6 2026), NVIDIA developer blog (CES 2026), XDA "360p with DLSS 4.5" article (Feb 13 2026).

## Super Resolution DLL (nvngx_dlss.dll) — TechPowerUp dated history

| Version | Date | Notes |
|---|---|---|
| 2.5.0 | 2023 | DLSS 2 era, SR only, no FG |
| 3.x | 2023–2024 | DLSS 3 / 3.5 (CNN model) |
| 310.1.0 | Jan 31, 2025 | DLSS 4 / 1st-gen transformer, MFG |
| 310.2.0 | Feb 1, 2025 | |
| 310.2.1 | Feb 10, 2025 | common in early DLSS 4 games |
| 310.3.0 | Jun 24, 2025 | |
| 310.4.0 | Aug 27, 2025 | |
| **310.5.0** | **Jan 6, 2026** | **DLSS 4.5 launch — 2nd-gen transformer SR, 6x MFG** |
| 310.5.2 | Jan 29, 2026 | |
| 310.5.3 | Jan 30, 2026 | |
| 310.6.0 | Mar 31, 2026 | Dynamic MFG (real-time FG multiplier adjustment, RTX 50 only) |
| 310.7.0 | Jun 24, 2026 | latest at time of writing |

## Frame Generation DLL (nvngx_dlssg.dll) — same numbering

310.0.0 / 310.1.0 / 310.2.0 (Jan 31–Feb 2025), 310.2.1 (Mar 26 2025), 310.3.0 (Jun 24 2025), 310.4.0 (Aug 27 2025), 310.5.0 (Jan 6 2026), 310.5.2 (Jan 29 2026), 310.5.3 (Jan 30 2026), 310.6.0 (Mar 31 2026). FG before 310.x = 3.x (DLSS 3 FG).

## Quick classification rule

- **2.x** → DLSS 2 (no FG capability — engine-level, DLL swap cannot add FG)
- **3.x** → DLSS 3 / 3.5 (pre-transformer)
- **310.0–310.4** → DLSS 4 (1st-gen transformer)
- **310.5.0+** → DLSS 4.5 (2nd-gen transformer; 310.6.0+ = Dynamic MFG)

## DLSS 4.5 preset system (auto-selected by quality mode)

| Preset | Model | Default modes |
|---|---|---|
| K | 1st-gen transformer | DLAA, Quality, Balanced |
| M | 2nd-gen transformer | Performance |
| L | 2nd-gen transformer | Ultra Performance — NVIDIA recommends for UHD output to minimize detail loss |

L/M are only available if game DLL ≥ 310.5.0; DLSSTweaks config can force them per-mode. Preset L at 4K Ultra Performance is the big win over 1st-gen: near-native static clarity + far better temporal stability at extreme upscale ratios. Still not "free" — foliage/wires/HUD shimmer in motion at 720p internal.

## Ultra Performance render scales

- 33.3% linear render scale
- 4K → 720p internal (9x pixel upscale)
- 1440p → 480p internal
- 1080p → 360p internal

## Observed inventory example (Aug 2026 scan, RTX 5070 Ti laptop user)

21-game library: 5 on DLSS 4.5 (007 First Light 310.6.0, Death Stranding 2 310.5.2, Forza Horizon 6 310.6.0, Dying Light The Beast 310.5.0, God of War Ragnarök 310.5.0), 8 on DLSS 4.0-era (310.1–310.3), 3 on DLSS 3.7, 1 on DLSS 2.5 (Dead Space 2023 — no FG, engine limitation). Repack games often ship with `bakup/` folders holding the original 3.x DLLs swapped out by the repacker.
