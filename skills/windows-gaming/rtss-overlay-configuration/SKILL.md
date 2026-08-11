---
name: rtss-overlay-configuration
description: Configure RivaTuner Statistics Server (RTSS) / MSI Afterburner on-screen displays — loading OverlayEditor .ovl layout files, selecting the active layout, and the dual-OSD gotcha where the old/default stats text keeps rendering alongside (or instead of) a loaded OVL because the classic client-driven OSD is a separate rendering path. Load for any RTSS/Afterburner overlay question — OVL won't show, default layout persists, layout switching, disabling the classic OSD.
---

# RTSS / Afterburner Overlay Configuration

## The core model — TWO independent OSD paths (learn this first)

1. **Classic OSD** — text stats rendered by the CLIENT (MSI Afterburner, HWiNFO, CapFrameX) through the RTSS API. Each monitored entry is individually enabled with **"Show in On-Screen Display"** in the client's settings. Position/format come from RTSS main window ("Show On-Screen Display" toggle + Framerate position dropdown) or the client's OSD settings.
2. **OverlayEditor layouts (.ovl)** — plugin-rendered custom layouts via `OverlayEditor.dll`.

**Loading an .ovl ONLY touches path 2. It never disables path 1.** The old/default stats text keeps rendering because it's the classic OSD, not an OverlayEditor layout. This is the #1 answer to "I loaded my OVL but the previous default layout still shows up." Both paths render simultaneously — disabling one does not affect the other.

## Steps

### Load an OVL
1. RTSS main window → **Setup** → **Plugins** tab → check `OverlayEditor.dll` → double-click to launch the editor.
2. OverlayEditor → switch to **Layouts** → **Load** → pick the `.ovl` (RTSS ships sample layouts in `RTSS install dir\Plugins\Client\Overlays`).
3. Select the imported layout as the active one and restart RTSS if it doesn't take effect immediately.

### Remove the persistent default overlay
- **With MSI Afterburner** (most common): Afterburner → Settings (gear) → **Monitoring** tab → for EVERY entry with a checkmark in the **"Show in On-Screen Display"** column, uncheck it. Monitoring itself can stay enabled — only the OSD flag matters. After this, the .ovl layout is the only thing drawn.
- **RTSS standalone** (no Afterburner): the "default" is RTSS's own framerate counter — the classic OSD controlled by **"Show On-Screen Display"** + the **Framerate position** dropdown in the main window. Disable it; the OverlayEditor layout is unaffected.

## Pitfalls

- **Name collision:** an OVL containing a layout with the same name as an existing one silently keeps the old version. Rename the layout to something unique and re-load.
- **Version mismatch:** an OVL saved by a newer RTSS than the installed one can be rejected silently → RTSS falls back to whatever layout was active before.
- **12-core CPUs** (e.g. Ryzen AI 9 HX 370): BreadPitch's per-core grid auto-picks 8/16/32-core layouts — a 12-core chip shows the 16-core grid with empty slots. Cosmetic only.
- While OverlayEditor is open, RTSS main-window zoom settings can't be adjusted (editor blocks them — MSI Afterburner blog).
- The capture indicator (screenshots/video recording marker) ALWAYS renders in the topmost layer regardless of layout.
- RTSS/Afterburner reinstalls or updates reset Profiles, plugin state, and per-app hook configs — re-apply after any reinstall.
- If the "default overlay" appears ONLY in one app and the user wants it gone there: per-app hook disable via `Profiles\<App>.exe.cfg` with `EnableHooking=0` (see Related).

## OVL file format (INI-style, NOT XML — inspect without RTSS)

Sections: `[Master]` (FontFace, FontHeight, ZoomRatio), `[Settings]` (Name, RefreshPeriod, EmbeddedImage), `[General]` (Sources=N, Layers=N, Tables=N), then `[SourceN]` / `[LayerN]` / `[TableN]` blocks.

Source block keys: `Name`, `Units`, `Format`, `Formula`, `Provider` (`HAL` | `HwInfo` | `PerfCounter`), plus `ID` (HAL) or `SensorInst`/`ReadingType`/`ReadingName` (HwInfo).

Layer/table bindings are inline, not separate fields: `VisibilitySource=SourceName`, text tags `<G=SourceName,min,max,...>` (bars/graphs) and `<TT=Table Name>`, and table rows `LineNCell4Source=SourceName`. Dump any .ovl with `scripts/inspect_ovl.py`.

### Provider semantics (what populates on which hardware)

- **HAL** — RTSS built-in: `GPU1 clock/temp/usage/power/memory usage/voltage/fan tachometer`, `CPU1-32 clock/usage`, `CPU temperature/power/usage`, `RAM usage`, `Framerate/Frametime`. GPU1* names work on NVIDIA via NVAPI — no HWiNFO/AB needed.
- **HwInfo** — deep sensors via HWiNFO shared memory (free version re-arms every 24h): Ryzen PPT/TDC/EDC + limits, SVI2 voltages, CCD temps, FCLK/UCLK; NVIDIA hot spot, memory junction, TGP. RDNA-only names (GPU PPT, SoC voltage, VR temps) stay empty on NVIDIA.
- **PerfCounter** — NIC DL/UL rates.

## Finding good OVLs (curated, verified)

- **BreadPitch THE-RTSS-Overlay** (github.com/BreadPitch/THE-RTSS-Overlay) — richest; dynamic color bars + history graphs, vendor-logo auto-detect, WHEA counter, ping, 10 variants (100%/80% font, vertical/horizontal). **For NVIDIA GPUs use `BreadPitCh-Size100-RTSS-Compact4all.ovl`** (HAL-based, works out of the box). Install: close RTSS → copy zip contents into `C:\Program Files (x86)\RivaTuner Statistics Server\` → install Lato-Regular.ttf → OverlayEditor → Load. Deep sensors light up automatically if HWiNFO runs with shared memory.
- **PeterKelemen2 RTSS-Overlay** (github.com/PeterKelemen2/RTSS-Overlay) — single plain-text OVL for AMD CPU + NVIDIA GPU (`PeterKelemen2-AMD-NVIDIA.ovl`, 53 sources/36 layers: CPU temp/power/per-core, RAM, GPU temp/fan/usage/power/VRAM, net, disk, FPS, clocks, voltage); needs AB or HWiNFO feeding it.
- Verified source lists + install details: `references/ovl-repos.md`.

## Web research notes for RTSS topics

- guru3d forums: Cloudflare-walled for direct curl AND r.jina.ai — use search snippets or cached mirrors.
- GitHub API + raw.githubusercontent.com work fine via curl — inspect repo contents, READMEs, even download and parse .ovl files directly (verified workflow).
- wccftech's RTSS guide is reachable via r.jina.ai.

## Related

- RTSS D3D11 present-hook stalls (video freezes in mpv/Harbor, audio continues) + per-app `EnableHooking=0` ignore rules: `windows-debugging` skill Chapter 1 and `harbor-stremio-client` → `references/rtss-present-stall.md`. Note: OVL overlay rendering itself doesn't involve `Present` hooking — overlay use alone won't reintroduce the Harbor stutter, but `EnableHooking=0` also kills overlay rendering in that process.
- Researched sources with quotes: `references/ovl-sources.md`.
