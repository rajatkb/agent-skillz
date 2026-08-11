# Building a Custom StatsD-like Taskbar System Monitor (Windhawk Mod)

When no existing tool satisfies the user's need for a macOS StatsD-style taskbar system monitor, a custom Windhawk mod is the right approach. This reference covers what's involved.

## Why a Windhawk Mod?

- **No separate widget framework** — injects directly into `explorer.exe` via Windhawk engine
- **No breaking** — no beta widget platform to depend on, no Electron/Python runtime
- **Full control** — custom layout, metrics, colors, positioning outside the clock area
- **Distribute via Windhawk** — users install it from the built-in mod browser

## Architecture

```
.wh.cpp (single source file)
  ├── Metadata block (id, name, description, target: explorer.exe)
  ├── Wh_ModInit()          — Called when mod loads into process
  │   ├── Create settings UI
  │   ├── Start worker thread for data collection
  │   └── Create/Hook taskbar window
  ├── Wh_ModSettingsChanged() — Called when user changes settings
  ├── Wh_ModUninit()        — Cleanup on mod unload
  ├── Data Collection Thread — Polls PDH counters every 1-2s
  └── UI Rendering           — GDI/Direct2D drawing on custom HWND
```

## Prerequisites

- **C++** — Windhawk mods are native C++ (.wh.cpp)
- **MSVC compiler** — Visual Studio Build Tools (free) or full VS
- **Windhawk SDK** — `compile_mod.py` script (included with Windhawk)
- Study existing mods as reference:
  - [`taskbar-clock-customization.wh.cpp`](https://github.com/m417z/my-windhawk-mods/blob/main/mods/taskbar-clock-customization.wh.cpp) (~6K lines, best data-collection pipeline reference)
  - [`desktop-live-overlay.wh.cpp`](https://github.com/m417z/my-windhawk-mods/blob/main/mods/desktop-live-overlay.wh.cpp) (creates custom overlay windows)
  - [`taskbar-labels.wh.cpp`](https://github.com/m417z/my-windhawk-mods/tree/main/mods) (taskbar window creation)

## Key Win32 APIs for System Monitoring

| Metric | API | Notes |
|---|---|---|
| CPU usage % | `PdhAddCounter` → `PdhCollectQueryData` | Counter: `\Processor(_Total)\% Processor Time` |
| RAM usage % / GB | `PdhAddCounter` or `GlobalMemoryStatusEx` | Counter: `\Memory\Available Bytes` |
| Disk I/O | `PdhAddCounter` | `\PhysicalDisk(_Total)\Disk Read Bytes/sec` |
| Network up/down | `PdhAddCounter` | `\Network Interface(*)\Bytes Sent/sec` (per adapter) |
| GPU usage % | `NvAPI_GPU_GetDynamicPstatesInfoEx` (NVIDIA), `ADL_Main_Control_Create` (AMD), or PDH `\GPU Engine(*)\Utilization Percentage` | PDH GPU engine counters work on Win10+ |
| CPU temperature | `ACPI thermal zone` via PDH or `LibreHardwareMonitor` WMI | `\Thermal Zone Information(*)\Temperature` |
| Battery % | `GetSystemPowerStatus` | Returns AC status + battery percentage |

## Creating a Taskbar Window

The mod needs to create an HWND that sits in the taskbar's notification area or next to the system tray. Approaches:

1. **Subclass an existing taskbar child window** — Find the clock/tray container via `FindWindowEx`, subclass it, draw additional content. Used by taskbar-clock-customization mod.
2. **Create a new owned window** — Create a small window positioned relative to the taskbar using `SetWindowPos` + `HWND_TOPMOST`. Needs to handle taskbar resize/dock changes.
3. **AppBar approach** — Register as a `SHAppBarMessage(ABM_NEW)` appbar. More complex but handles taskbar interactions natively.

## Mod Development Workflow

1. **Clone the windhawk-mods repo** as reference
2. **Create a new `.wh.cpp` file** with metadata header
3. **Implement callbacks** `Wh_ModInit`, `Wh_ModSettingsChanged`, `Wh_ModUninit`
4. **Add settings** via `Wh_SetValue` / `Wh_GetValue` for configurable metrics/colors
5. **Compile locally** using `python compile_mod.py path/to/your-mod.wh.cpp`
6. **Test in Windhawk**: Advanced → Install from file → select the compiled `.whmod` file
7. **Iterate**: Edit → Recompile → Restart explorer.exe or Windhawk

## Compilation

```bash
# In windhawk-mods repo root
python scripts/compile_mod.py mods/your-mod.wh.cpp
# Output: mods/your-mod.whmod (ready to install in Windhawk)
```

## Skeleton Structure

```cpp
// ==WindhawkMod==
// @id              taskbar-system-monitor
// @name            Taskbar System Monitor
// @description     macOS StatsD-like system monitor for the Windows taskbar
// @version         0.1
// @author          You
// @include         explorer.exe
// ==/WindhawkMod==

// Core Win32 headers
#include <windows.h>
#include <pdh.h>
#include <vector>
#include <string>
#include <thread>
#include <atomic>

// Windhawk API
#include "windhawk_api.h"

// Settings keys
constexpr auto SETTING_COLORS = L"Colors";
constexpr auto SETTING_METRICS = L"Metrics";

// Data collected each tick
struct SystemMetrics {
    double cpuUsage;
    double ramUsage;
    double uploadSpeed;
    double downloadSpeed;
    double gpuUsage;
    // ...
};

// Window procedure for the taskbar widget
LRESULT CALLBACK WidgetWndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    // Handle WM_PAINT — draw metrics using GDI
    // Handle WM_DESTROY — cleanup
}

BOOL Wh_ModInit() {
    // 1. Read settings
    // 2. Initialize PDH query
    // 3. Create worker thread
    // 4. Find taskbar HWND, create child window
    return TRUE;
}

void Wh_ModUninit() {
    // Stop thread, destroy window, close PDH handles
}

void Wh_ModSettingsChanged() {
    // Re-read settings, update UI
}
```

## Pitfalls & Gotchas

- **explorer.exe is 64-bit** — mod must compile as x64
- **Taskbar recreation** — When explorer restarts or taskbar crashes, the mod reloads automatically. Re-find taskbar HWND in `Wh_ModInit`, don't cache HWNDs globally
- **PDH handles are per-process** — Initialize PDH in `Wh_ModInit`, close in `Wh_ModUninit`
- **Thread safety** — PDH queries run on a worker thread; PostMessage the results to the UI thread for rendering
- **High-DPI** — Use `GetDpiForWindow` / `EnableNonClientDpiScaling` for sharp rendering
- **Dark/light mode** — Check Windows theme via `ShouldAppsUseDarkMode()` or `UISettings->GetColorValue`
- **Taskbar position** — Taskbar can be top/bottom/left/right. Query via `SHAppBarMessage(ABM_GETTASKBARPOS)`.
- **Multiple monitors** — Taskbar may exist on multiple monitors. Use `MonitorFromWindow` to determine which one.

## Reference Mods

- **m417z/my-windhawk-mods** — Largest collection, best code quality. The taskbar-clock-customization mod has the most complete PDH data-collection pipeline.
- **ramensoftware/windhawk-mods** — Official mod collection, simpler examples.
- **Windhawk wiki**: [Creating a new mod](https://github.com/ramensoftware/windhawk/wiki/Creating-a-new-mod) — official guide.
