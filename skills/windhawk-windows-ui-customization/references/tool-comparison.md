# Windows Taskbar System Monitoring — Tool Comparison

When a user asks for macOS StatsD-like system stats in the Windows taskbar, the best option depends on how much they want and how they want it delivered.

## Quick Decision

| If user wants... | Recommend |
|---|---|
| Stats embedded in existing taskbar via Windhawk, zero extra processes | **Windhawk Taskbar Clock Customization** mod |
| Native taskbar widget with CPU/GPU/temps + signed installer | **NetSpeedTray** (erez-c137/NetSpeedTray) — `winget install` |
| Lightweight standalone taskbar widget with temps | **TrafficMonitor** (zhongyang219/TrafficMonitor) |
| Full macOS-style menu bar replacement, CSS-themable | **YASB** (amnweb/yasb) |
| Minimal text-based in tray area | **XMeters** (entropy6.com/xmeters) |
| Nothing fits → build custom Windhawk mod | `references/custom-mod-development.md` |

## Detailed Breakdown

### Windhawk Taskbar Clock Customization (⭐ Best for Windhawk users)
- Hooks into `explorer.exe` via Windhawk — no separate process, no widget framework that can break
- Shows: CPU%, CPU temp, RAM%, GPU%, VRAM, network up/down, disk I/O, battery, media player, weather, RSS
- Mature (v1.8, m417z, actively maintained)
- Limit: Lives in clock area only — can't be placed elsewhere on the taskbar
- **No GPU temp pattern** available — use `%gpu%` for usage only

### NetSpeedTray (⭐ Best standalone; most polished)
- **GitHub**: [erez-c137/NetSpeedTray](https://github.com/erez-c137/NetSpeedTray) — 647★, 745 commits, v2.1.2 (updated weekly, actively maintained)
- **Install**: `winget install --id erez-c137.NetSpeedTray` or signed installer from GitHub releases (SignPath Foundation signed — no SmartScreen warnings)
- Native taskbar widget — embeds directly in taskbar layer, never vanishes behind Start menu or system flyouts
- Shows: Network up/down with mini-graph, CPU%, GPU%, RAM, VRAM, **temps**, **power draw (Watts)**
- Double-click opens Monitor window with history charts, per-app connections, exportable stats (CSV/JSON)
- Open source (GPLv3), no ads, no telemetry, ~50 MB RAM idle, ~0.1% CPU between polls
- Full feature list: data caps + alerts, network latency probe, daily/weekly/monthly totals, custom thresholds, light/dark auto-theming, per-process CPU/GPU/RAM list

#### Temperature & Power Sensor Matrix (NetSpeedTray)

| Reading | Works Natively (no admin/helper) | Needs LibreHardwareMonitor v0.9.4 (run as admin) |
|---|---|---|
| CPU / GPU / RAM / VRAM usage % | ✅ Always | — |
| GPU temperature | ✅ NVIDIA (via nvidia-smi) | AMD & Intel discrete GPUs |
| GPU power | ✅ NVIDIA + Intel iGPU | AMD GPUs |
| CPU temperature | ⚠️ Only if board exposes ACPI thermal zones | AMD Ryzen, boards without usable zones |
| CPU power | ✅ Intel (RAPL) | AMD CPUs |

**Bottom line**: NVIDIA + Intel PC = most temps/power work out of the box. AMD CPU needs LibreHardwareMonitor v0.9.4 specifically (v0.9.5+ removed the WMI interface NetSpeedTray reads). The widget itself never runs as admin.

### TrafficMonitor (zhongyang219)
- Open-source, lightweight, embeds in native taskbar notification area
- Shows: Net speed (up/down), CPU%, RAM%, disk activity, GPU/CPU temps (standard version)
- Very stable, skinnable, portable (no install needed)
- Less customizable than YASB or Windhawk clock mod

### YASB (Yet Another Status Bar)
- Full custom status bar — top, bottom, per-monitor
- Shows: CPU, RAM, disk, network, clock, weather, battery, active window, systray icons
- CSS-themable — can match macOS menu bar exactly
- Trade-off: Python process running constantly; replaces rather than extends native taskbar

### XMeters
- Classic, minimal, least intrusive — CPU, RAM, disk, network as compact text/bar in notification area
- Free = basic metrics. Pro (~$5) adds GPU, custom labels
- Mature but less actively updated

### kil0bit System Monitor
- **GitHub**: [kil0bit-kb/kil0bit-system-monitor](https://github.com/kil0bit-kb/kil0bit-system-monitor) — 161★, WPF + Win32
- v3.0, lightweight (~2.71 MB), modern glassmorphism design
- Sits inside taskbar, CPU/GPU/RAM/network/disk, multi-disk monitoring
- Less mature than NetSpeedTray or TrafficMonitor

### WidBar / System Metrics (❌ Avoid for now)
- Beta widget platform with only 2 widgets. System Metrics widget kept breaking (user report)
- Low community traction (developer: 3 followers, 5 repos)
- Check back in 6+ months

## Common User Flow

1. User says "I want macOS StatsD on Windows taskbar"
2. Probe: "Already on Windhawk?" If yes → Windhawk Clock Mod (most integrated)
3. If no Windhawk → NetSpeedTray first (winget install, best features, signed), then TrafficMonitor
4. If they want full macOS aesthetic → YASB with CSS theming
5. If they tried WidBar and it broke → steer to NetSpeedTray or Windhawk
6. If nothing satisfies → offer to build a custom Windhawk mod
