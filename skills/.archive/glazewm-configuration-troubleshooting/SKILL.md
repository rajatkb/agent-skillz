---
name: glazewm-configuration-troubleshooting
description: Configure, troubleshoot, and extend GlazeWM tiling window manager for Windows — covers config editing, hide/cloak mechanism fixes, workspace management, keybinding cleanup, virtual desktop incompatibility, and third-party workspace visualization tools.
---

# GlazeWM — Configuration & Troubleshooting

GlazeWM is a tiling window manager for Windows (written in C#/.NET) that operates **on top of Windows DWM** via Win32 API calls (`SetWindowPos`, `SW_HIDE`, `WS_EX_CLOAKED`, etc.). It does **not** replace DWM or have its own windowing system.

## Config File

**Path:** `C:\Users\<USER>\.glzr\glazewm\config.yaml`

Reload with `alt+shift+r` or right-click tray icon → Reload config.

## Vanishing Windows — Root Cause & Fix

GlazeWM uses a **window hiding mechanism** when switching workspaces. The `hide_method` setting controls how:

| Method | API Used | Behavior | Stability |
|--------|---------|----------|-----------|
| `cloak` (default) | `WS_EX_CLOAKED` via COM `set_cloak` | DWM stops rendering the window but it stays in the window tree. Taskbar configurable via `show_all_in_taskbar`. | **Buggy** — windows can entirely disappear from Alt+Tab, taskbar, and Task Manager. DWM "forgets" them. Known issue ([#880](https://github.com/glzr-io/glazewm/issues/880)). |
| `hide` (legacy) | `SW_HIDE` Win32 call | Window fully hidden — removed from screen AND taskbar. | **More reliable** — decades-old, well-tested API. |
| `place_in_corner` | Move offscreen | Artificially hides by placing in monitor corner. macOS-only mostly. | N/A |

### Fixes

**Option A — Keep cloaking but stay discoverable:**
```yaml
hide_method: 'cloak'
show_all_in_taskbar: true   # shows windows from ALL workspaces in taskbar
```

**Option B — Switch to legacy hide (more reliable):**
```yaml
hide_method: 'hide'          # SW_HIDE — windows leave taskbar when workspace is switched
```

**Option C — Eliminate the mechanism entirely (single workspace):**
```yaml
workspaces:
  - name: '1'               # only one workspace — no hiding ever needed
```
With only 1 workspace, `hide_method` and `show_all_in_taskbar` are irrelevant since there's nothing to switch away from. Completely solves vanishing windows.

## Workspace Management

Workspaces are GlazeWM's own concept — **not** Windows virtual desktops. They manage window visibility entirely through the hide/cloak mechanism above.

- Workspaces are defined in config under `workspaces:` as a list
- Adding/removing workspaces requires a config reload
- Only the extra 2-9 can be removed if you only use workspace 1
- Workspace names (the `name` field) are the labels shown in Zebar/tray tools

### Cleaning up keybindings when reducing workspaces

When removing workspaces (e.g. going from 9 to 1), remove the associated keybindings:
- `focus --workspace N` with `alt+N`
- `move --workspace N, focus --workspace N` with `alt+shift+N`
- Dead keys like `alt+s` / `alt+a` / `alt+d` (next/prev/recent workspace) are also no-ops with 1 workspace

## Windows Virtual Desktop Incompatibility

**GlazeWM does not integrate with Windows native virtual desktops** (Win+Ctrl+D / Win+Tab). This is a known limitation ([#671](https://github.com/glzr-io/glazewm/issues/671), [#169](https://github.com/glzr-io/glazewm/issues/169), [#1145](https://github.com/glzr-io/glazewm/issues/1145)).

- GlazeWM manages windows **globally** — creating a new Windows virtual desktop and launching an app there tiles it alongside your other windows on workspace 1
- Switching Windows virtual desktops confuses the layout because GlazeWM doesn't track per-desktop state
- Layouts don't persist when switching back ([#1145](https://github.com/glzr-io/glazewm/issues/1145))
- Microsoft's virtual desktop API is incomplete — there's no proper API for activating desktops per-monitor, which is why GlazeWM built its own system

**What works:** `Win+D` (Show Desktop) minimizes all windows to show the desktop. GlazeWM does NOT intercept this — it's native Windows behavior. Win+D again restores windows.

## Third-Party Workspace Visualization Tools

| Tool | Lang | Type | Notes |
|------|------|------|-------|
| **[glazetray](https://github.com/Drysua/glazetray)** | Go | System tray icon | Shows active workspace number (1-10). Very minimal. Single monitor only, default names only. Best "native" feel. |
| **[glazewm-tray](https://github.com/nickxar1/glazewm-tray)** | Python | Floating bar + tray | Floating bar overlays the taskbar showing workspaces + app icons. Also tray mode. Auto-hides during fullscreen. |
| **[glazeid](https://lib.rs/crates/glazeid)** | Rust | Standalone bar | Minimal workspace bar. Rust-based but renders as its own window, not embedded in taskbar. |
| **GlazeWM built-in tray** | C# | System tray | Already present. Right-click for Reload/Pause/Exit. **No** workspace info shown. |
| **YASB** | Python | Full status bar | Highly configurable. Has dedicated GlazeWM workspaces widget. Replaces entire taskbar essentially. |

## Keybinding Management

- Modifier: `alt` by default (Windows key is hard to remap on Windows)
- Bindings format: `['alt+key']` or `['alt+shift+key']`
- Multiple commands can be chained: `['move --workspace 1', 'focus --workspace 1']`
- Binding modes (like resize mode) use `wm-enable-binding-mode` / `wm-disable-binding-mode`

### Useful Commands

| Command | Default Binding |
|---------|----------------|
| `wm-reload-config` | `alt+shift+r` |
| `wm-toggle-pause` | `alt+shift+p` |
| `toggle-minimized` | `alt+m` |
| `toggle-floating --centered` | `alt+shift+space` |
| `toggle-fullscreen` | `alt+f` |
| `close` | `alt+shift+q` |
| `wm-cycle-focus` | `alt+grave` |

## Window Rules

Rules match against `window_process`, `window_title`, or `window_class`:

```yaml
window_rules:
  - commands: ['ignore']                          # GlazeWM won't manage this window
    match:
      - window_process: { equals: 'Flow.Launcher' }
      - window_process: { equals: 'GHelper' }
  - commands: ['set-floating']
    match:
      - window_process: { equals: 'EXCEL' }
        window_class: { not_regex: 'XLMAIN' }     # popup dialogs, not main window
```

Use `ignore` for apps GlazeWM should not manage at all (launchers, tray tools, utility overlays).

## Pitfalls

- **YAML BOM:** Windows tools may add UTF-8 BOM to config.yaml. Fix with `sed -i '1s/^\xEF\xBB\xBF//' path` on WSL.
- **Config reload** is not automatic — must press `alt+shift+r` or use tray menu.
- **Flow Launcher hotkey conflict:** GlazeWM's Alt modifier clashes with Flow Launcher. Flow Launcher uses Alt+Space which GlazeWM respects (not intercepted). But some binds may overlap.
- **Fullscreen minimze bug:** `toggle-fullscreen` then `toggle-minimized` can get windows stuck in maximized state. Fix: `toggle-tiling` to reset ([#906](https://github.com/glzr-io/glazewm/issues/906)).
