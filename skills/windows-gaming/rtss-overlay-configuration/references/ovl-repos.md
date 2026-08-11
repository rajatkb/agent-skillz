# Curated OVL repositories (verified Aug 2026)

Both verified by downloading and parsing the .ovl files directly (INI format, see scripts/inspect_ovl.py).

## BreadPitch THE-RTSS-Overlay — recommended

- Repo: https://github.com/BreadPitch/THE-RTSS-Overlay (29 stars, active: v1.4 Jul 2026)
- 10 OVL variants in `Plugins/Client/Overlays/`: 100%/80% font × {Full-RDNA-Ryzen (HWiNFO), RDNA-CPUall (HWiNFO), Ryzen-GPUall (HWiNFO), Compact4all (RTSS HAL), Compact4all-horizontal}
- **Compact4all is the right pick for NVIDIA GPUs** (README: "If you do not use HWiNFO, or have an nVidia GPU or Intel CPU, stick to Compact4all").
- Compact4all internals (verified): 144 sources (76 HAL, 64 HwInfo, 4 PerfCounter), 95 layers, 7 tables. Sections: FPS/frametime (min/max/avg/1%/0.1% lows + bars/history), GPU (HAL: clock/mem clock/temp/temp2/usage/power/voltage/fan/VRAM/mem-ctrl-usage; HwInfo extras: hot spot, mem junction, VR temps — RDNA-only ones empty on NVIDIA), CPU (temp/usage/power/PPT/TDC/EDC + limits, per-core usage+eff clock 16/32-core grids, DRAM usage+bandwidth+FCLK/UCLK), RAM, network (NIC 0/1 DL/UL), ping, WHEA error count, vendor-logo auto-detect (AMD CPU + nVidia GPU on user's rig).
- Install (README): close RTSS → copy zip contents into `C:\Program Files (x86)\RivaTuner Statistics Server\` (pre-enables all settings + loads Compact4all by default) → install `Fonts/Lato-Regular.ttf` manually → load preferred .ovl in OverlayEditor. Optional: HWiNFO portable into RTSS folder + its HWiNFO64.INI, enable Shared Memory Support (free re-arms every 24h).
- 50% transparency default (color codes `80FFFFFF`); edit in notepad++: `=80FFFFFF` → `=CCFFFFFF` (80%) or `=99FFFFFF` (60%).
- DesktopOverlayHost.exe ships for 2nd-screen overlay; disable via right-click → Start with Windows if unwanted.

## PeterKelemen2 RTSS-Overlay — minimal alternative

- Repo: https://github.com/PeterKelemen2/RTSS-Overlay (7 stars)
- Single OVL per CPU/GPU combo: `PeterKelemen2-AMD-NVIDIA.ovl` = 53 sources / 36 layers (verified): CPU temp/power ×3, per-core usage CPU1-8, CPU usage + max, RAM usage (+percent, +process variants), ping, GPU1 temp/fan/usage/power/memory usage (+percent), net DL/UL ×2, HDD usage/read/write, core/mem clock, voltage, framerate. Plain text layout, no graphs/colors.
- Data sources: README says add e.g. MSI Afterburner in OverlayEditor → Data Sources tab. Source names are HWiNFO-style (`GPU1 ...`, `NET1 ...`, `HDD1 ...`) — HWiNFO bridge fills them all.
- Install: copy .ovl to `C:\Program Files (x86)\RivaTuner Statistics Server\Plugins\Client\Overlays\` → Load in OverlayEditor.

## Other

- RTSS built-in sample OVLs: `<RTSS install>\Plugins\Client\Overlays\` — baseline templates.
- wccftech guide (reachable via r.jina.ai): https://wccftech.com/how-to-set-up-high-quality-performance-overlays-with-rtss/ — has a mediafire "Custom Afterburner-RTSS Overlay.ovl" (unverified, mediafire).
