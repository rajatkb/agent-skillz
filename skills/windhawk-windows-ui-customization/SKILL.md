---
name: windhawk-windows-ui-customization
description: Configure Windows UI via Windhawk mods — taskbar styling, clock customization with system metrics (CPU/RAM/temps/network/GPU/media), translucent/acrylic themes, and taskbar repositioning on Windows 10/11.
category: devops
triggers:
  - windhawk
  - taskbar clock
  - transluscent taskbar
  - transluscent theme
  - taskbar customization
  - windows UI mod
  - context menu
  - show more options
  - nilesoft
---

# Windhawk Windows UI Customization

## Overview

Windhawk is a Windows UI modding tool. This skill covers configuring the most useful mods for a translucent, information-rich taskbar experience — clock customization with live system metrics, taskbar/notification center theming, and taskbar repositioning.

## Key Mods

| Mod | Purpose | Install in Windhawk |
|---|---|---|
| **Taskbar Clock Customization** | Custom date/time, CPU/RAM/GPU/temps/network, media player info, weather, RSS on the clock | Search "Taskbar Clock Customization" |
| **Windows 11 Taskbar Styler** | Translucent/acrylic/mica taskbar themes | Search "Windows 11 Taskbar Styler" |
| **Windows 11 Notification Center Styler** | Match notification center to your taskbar theme | Search "Windows 11 Notification Center Styler" |
| **Dynamic Taskbar Transparency** | Per-state transparency (desktop, Start open, search, maximized windows) | Search "Dynamic Taskbar Transparency" |
| **Translucent Flyouts Controller** | Makes context menus/flyouts translucent (needs TranslucentFlyouts app too) | Search "Translucent Flyouts Controller" |
| **Taskbar on top for Windows 11** | Move taskbar to top of screen | Search "Taskbar on top" |
| **Taskbar Background Helper** | Set taskbar background color for transparent parts (pairs with Taskbar Styler) | Search "Taskbar Background Helper" |

Native Win11 setting for left-aligned icons: Settings → Personalization → Taskbar → Taskbar behaviors → Taskbar alignment → **Left**

## Taskbar Clock Customization — Configuration

### Structure

Paste YAML into Windhawk → Mod Details → Settings → Textual Mode.

```yaml
TopLine: '<content>'        # Upper tile (always shown)
BottomLine: '<content>'     # Lower tile (shown if taskbar is tall enough)
MiddleLine: '<content>'     # Windows 10 only
TooltipLine: '<content>'    # Tooltip text
TooltipLineMode: append|replace

Width: 180       # Win10 clock width
Height: 60       # Win10 clock height
MaxWidth: 0      # Win11 max width (0 = no limit)
TextSpacing: 0   # Line spacing

ShowSeconds: 0
TimeFormat: HH':'mm
DateFormat: dd MMM yyyy
WeekdayFormat: ddd

TimeStyle:       # Win11 22H2+ only
  TextColor: '#FFFFFF'
  TextAlignment: center
  FontSize: 12
  FontWeight: semibold
  FontFamily: Segoe UI Variable

DateStyle:       # Win11 22H2+ only (applies to BottomLine/MiddleLine as well)
  TextColor: '#AAAAAA'
  TextAlignment: center
  FontSize: 11
```

### Available Patterns

**Time/Date/Weekday:**
- `%time%` — time per TimeFormat setting. `%time2%`, `%time3%` for additional formats
- `%time_tz1%`, `%time_tz2%` — time in custom time zones
- `%date%` — date per DateFormat setting. `%date2%`, `%date3%` for additional
- `%weekday%` — weekday name. `%weekday_num%` (1-7), `%weeknum%`, `%weeknum_iso%`
- `%dayofyear%` — day of year
- `%timezone%` — timezone in ISO 8601

**System Performance:**
- `%cpu%` — CPU usage %
- `%cpu_temp%` / `%cpu_temp_f%` — CPU temp °C/°F
- `%ram%` — RAM usage %. `%ram_used%` (GB), `%ram_total%` (GB)
- `%ram_committed%` — committed RAM %. `%ram_committed_used%`/`%ram_committed_total%` (GB)
- `%gpu%` — GPU usage % (NOTE: no GPU temp pattern exists)
- `%vram%` / `%vram_used%` / `%vram_total%` — VRAM metrics
- `%upload_speed%` / `%download_speed%` / `%total_speed%` — network transfer rates
- `%disk_read%` / `%disk_write%` / `%disk_total%` — disk I/O
- `%battery%` — battery level. `%battery_time%` (remaining), `%power%` (watts)

**Media Player (GSMTC-compatible players):**
- `%media_title%` / `%media_artist%` / `%media_album%`
- `%media_status%` — text icon (⏯ ⏸ ⏹)
- `%media_info%` — combined "Artist — Title", auto-truncated. Best for taskbar line

**Other:**
- `%weather%` — weather from wttr.in (configure location in mod settings)
- `%web1%` / `%web1_full%` — web content/RSS items
- `%n%` or `%newline%` — line break (for multi-line tooltips)
- `↓`/`↑` — Unicode arrows for download/upload labels

### Sample Configs

**Clean — date/time top, CPU/RAM bottom:**
```yaml
TopLine: '%weekday%, %date% | %time%'
BottomLine: CPU %cpu% | RAM %ram%
```

**With network speeds and CPU temp:**
```yaml
TopLine: '%date%  %time%'
BottomLine: ↓%download_speed%  ↑%upload_speed%  %cpu_temp%°C
```

**StatsD-like — dense system metrics:**
```yaml
TopLine: 'CPU %cpu% · RAM %ram% · %gpu% GPU'
BottomLine: ↓%download_speed% ↑%upload_speed% · %cpu_temp%°C
```

**Media player + metrics (two-line bottom using %n%):**
```yaml
TopLine: '%time%  %date%'
BottomLine: %media_info%%n%↓%download_speed%  ↑%upload_speed%
```

## Windows 11 Taskbar Styler — Translucent Theme

1. Install **Windows 11 Taskbar Styler** in Windhawk
2. Click Details → Settings → pick a theme:

| Theme | Effect |
|---|---|
| **TranslucentTaskbar** | Acrylic/blur taskbar with dark tint |
| **SimplyTransparent** | Fully transparent taskbar background |
| **Lucent** | Accented colored acrylic bar |
| **WindowGlass** | Glass-like aero effect |
| **Aeris** | Light acrylic with rounded taskbar |

For custom translucency, the theme uses XAML brushes:
```
<WindhawkBlur BlurAmount="18" TintColor="#25323232"/>
```

To match the notification center, install **Windows 11 Notification Center Styler** and pick the corresponding theme.

## Tool Selection — What to Recommend

When someone asks for system stats on the Windows taskbar, use the reference at `references/tool-comparison.md` to pick the right tool. Key decision factors:
- **Already on Windhawk** → Taskbar Clock Customization mod (most integrated, zero extra processes)
- **Want native taskbar widget + signed installer** → NetSpeedTray (`winget install --id erez-c137.NetSpeedTray`)
- **Don't use Windhawk / want lightweight standalone** → TrafficMonitor (open-source, portable, taskbar-embedded)
- **Want full macOS menu bar replacement** → YASB (Python, CSS-themable, per-monitor bars)
- **WidBar/System Metrics** = beta, unreliable — steer away
- **Nothing fits** → consider building a custom Windhawk mod (see `references/custom-mod-development.md`)

## Context Menus — What Actually Exists

**Key fact: no Windhawk mod expands the Win11 modern menu to show all items.** The only mod that removes "Show more options" is **Classic context menu on Windows 11** (m417z) — but it reverts to the legacy Win10-style menu, the opposite direction. Everything else is styling or removal. The feature is a long-open request (windhawk-mods discussions #1915, #1836); the modern menu's item set is fixed by Explorer's CommandStore, which is what hides classic shell extensions — a mod would have to re-implement menu building.

When someone wants "all items in a modern-style menu":
- **Nilesoft Shell** (nilesoft.org, free/open-source) — replaces the menu with its own fluent-styled menu with ALL items (legacy + modern) merged; shell-extension DLL inside explorer.exe, no separate process
- **StartAllBack's "full context menus" option is ALSO the classic menu** — not modern-menu expansion
- Registry route = per-item manual work, no blanket "show all" switch

Full mod catalog, discussion links, and verified non-answers: `references/context-menu-solutions.md`

## Custom Windhawk Mod Development

When no existing tool satisfies — create a custom Windhawk mod for a StatsD-like taskbar monitor. This is a substantial C++ project, not a quick script.

### What's Involved

A Windhawk mod is a **single `.wh.cpp` file** compiled to a DLL, injected into `explorer.exe`. It needs:
- **PDH API** — read CPU%, RAM, disk I/O, network traffic via Performance Counters
- **GPU APIs** — NvAPI (NVIDIA), ADL (AMD), or PDH GPU Engine counters for GPU%/VRAM
- **Temperature sources** — ACPI thermal zones or LibreHardwareMonitor WMI
- **Custom HWND** — a window positioned in the taskbar notification area, painted with GDI/D2D
- **Worker thread** — poll data every 1-2s, PostMessage results to UI thread
- **Windhawk settings** — configurable metrics, colors, refresh rate

### Reference

Full architecture, API table, skeleton code, compilation workflow, and gotchas: `references/custom-mod-development.md`

### Key Reference Mods

- [taskbar-clock-customization.wh.cpp](https://github.com/m417z/my-windhawk-mods/blob/main/mods/taskbar-clock-customization.wh.cpp) — best PDH data-collection pipeline (6K lines, mature)
- [desktop-live-overlay.wh.cpp](https://github.com/m417z/my-windhawk-mods/blob/main/mods/desktop-live-overlay.wh.cpp) — custom overlay window creation
- [Windhawk wiki: Creating a new mod](https://github.com/ramensoftware/windhawk/wiki/Creating-a-new-mod)

## Pitfalls

- **No GPU temp pattern** in Taskbar Clock Customization. Use `%gpu%` for usage %. Workaround: run LibreHardwareMonitor with its web server enabled, then pull GPU temp via a web content item (`%web1%`) pointed at `http://localhost:8085/data.json` — parse the JSON with ContentMode=json and a SearchReplace pattern to extract the GPU temp value
- **Media info is text-only** — no clickable play/pause/next buttons in the clock. Use a dedicated media controller mod for controls
- **Taskbar on top mod** is Windows 11 only. Win10 taskbar positioning is native (registry tweak or ExplorerPatcher)
- **Windows 11 Taskbar Styler** and **Dynamic Taskbar Transparency** can conflict on some XAML elements — if the taskbar looks wrong, try disabling one
- **Mod config is YAML** — watch indentation. Paste errors silently disappear
