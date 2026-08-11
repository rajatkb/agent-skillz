---
name: glazewm-configuration
title: GlazeWM Configuration
description: Configure, troubleshoot, and tune GlazeWM tiling window manager on Windows — window hiding methods, layout, keybindings, window rules, and common issues.
---

# GlazeWM Configuration

GlazeWM is a tiling window manager for Windows (written in Rust) that runs **on top of Windows DWM** — it does NOT replace the window manager. It repositions and manages windows via Win32 API calls (P/Invoke). This means it cannot "fall back to Windows' native WM" — it already uses it.

## Config File

Windows location: `C:\Users\<USER>\.glzr\glazewm\config.yaml`

Reload config at runtime: `wm-reload-config` (bound to `alt+shift+r` in the default sample config).

## Window Vanishing Issues (hide_method)

The most common source of "windows vanished" bugs is the `general.hide_method` setting, which controls how windows are hidden when switching workspaces.

```yaml
general:
  hide_method: 'cloak'    # DEFAULT — uses WS_EX_CLOAKED via COM API
  show_all_in_taskbar: false  # Only applies when hide_method is cloak
```

| Method | API | Behavior | Known Issues |
|--------|-----|----------|--------------|
| `cloak` | `WS_EX_CLOAKED` (COM `set_cloak`) | Window hidden from render but stays in taskbar (smoother, no animation) | Windows can silently vanish or appear ghosted behind others (issue #880). Bug since method introduced in PR #792. |
| `hide` | `SW_HIDE` (legacy Win32) | Window fully hidden, removed from taskbar | More reliable/stable. No animation. Windows completely invisible until workspace refocused. |

### Fix: Vanishing Windows

There are two paths depending on the user's taskbar preference:

**Path A — User wants windows discoverable in taskbar (recommended when vanishing is rare/intermittent):**
Keep `cloak` but enable taskbar visibility for all workspaces:
```yaml
general:
  hide_method: 'cloak'          # Keep the default
  show_all_in_taskbar: true     # ← KEY FIX: windows from all workspaces stay in taskbar
```
This is the right choice when the user said "I would prefer if my tasks are still visible in my task bar." Cloak may still glitch but the taskbar always shows where every window lives — click any taskbar entry to focus its workspace.

**Path B — User doesn't need taskbar discoverability (fixes the vanishing bug at the source):**
Switch from `cloak` to `hide`:
```yaml
general:
  hide_method: 'hide'
```
**Tradeoff**: Windows are completely hidden from taskbar when workspace-switched, but the `SW_HIDE` API is decades-proven and never silently loses windows.

**Path C — Eliminate the hiding mechanism entirely (single workspace):**
If the user only needs one workspace, reduce the `workspaces:` list to a single entry. With only one workspace, there is nothing to switch/hide away from — `hide_method` is never exercised and the vanishing bug cannot occur regardless of setting.
```yaml
workspaces:
  - name: '1'
```
After this change, `alt+2` through `alt+9` bindings become dead keys — offer to strip them. The `show_all_in_taskbar` setting is also irrelevant (no other workspaces to show). Windows-native Show Desktop (Win+D) still works: it minimizes all tiled windows to the taskbar, and Win+D again restores them. GlazeWM does NOT intercept Win+D.

**Decision rule**: Ask "do you need multiple workspaces or just tiling on one desktop?" One workspace → Path C. Need workspaces + taskbar visibility → Path A. Need workspaces without taskbar → Path B.

### Show Desktop (Win+D)

Windows' native Show Desktop (`Win+D`) sends `SC_MINIMIZE` / `SC_RESTORE` to all top-level windows — **GlazeWM does not intercept or override this**. All tiled windows minimize to the taskbar, showing desktop icons. Win+D again restores them and GlazeWM re-applies tiling. This works identically regardless of `hide_method`.

## Tiling Layout Mechanics

GlazeWM uses a **split-based tiling model** (like i3), not a grid. Understanding this is critical for users who complain they can't create specific layouts.

### How splitting works

- **`alt+v`** toggles the **tiling direction** for the currently focused container (not globally)
- Direction determines where the **next window** or **moved window** is placed, relative to the focused window
- Direction is **per-container** — each split pane remembers its own direction independently

### Creating a nested layout (e.g. vertical master + two stacked side windows)

1. Open 2 windows → they split horizontally (side-by-side) by default
2. Focus the right window, press **`alt+v`** → direction switches to vertical
3. Open a 3rd window → it splits the right pane vertically (top/bottom inside)
4. Result: left 50% = window A, right 50% = windows B (top) and C (bottom)

**"Master-and-stack" layout (vertical left, stacked right):**
```
+-------+-------+
| Left  | Right |
| Top   | Top   |
+-------+-------+
| Left  | Right |
| Bottom| Bottom|
+-------+-------+
```
1. Window 1 → full screen
2. `alt+v` → horizontal. Window 2 → left/right split
3. **Focus left**, `alt+v` → vertical. Window 3 → left splits top/bottom
4. **Focus right**, `alt+v` → vertical. Window 4 → right splits top/bottom
5. New windows while focused on right continue splitting rightward (acts like stacking)

### Auto-Tiling (GAT-GWM)

**[GAT-GWM](https://github.com/Dutch-Raptor/GAT-GWM)** is a Rust auto-tiler that alternates split direction by nesting depth, producing a balanced tree automatically. Install: `cargo install gat-gwm`. Run alongside GlazeWM.

### Practical rules of thumb

- **`alt+v` toggles direction** — press it and watch what changes. The focused window's border color helps track which pane is active
- **`alt+h/j/k/l`** moves focus between windows in the current layout
- **`alt+shift+h/j/k/l`** moves the focused window in that direction (reorganizing splits as it goes)
- If a window ends up in the wrong place, move it in the opposite direction to re-split

### Common mistake

Users often think `alt+v` is a global setting. It's not — it sets the direction for the focused container only. Two different panes can have different directions simultaneously.

## Game Handling

GlazeWM does **not** automatically detect or handle games. There is no auto-pause-on-fullscreen (feature request [#729](https://github.com/glzr-io/glazewm/issues/729) — still open).

### How games behave

- **Fullscreen exclusive**: Game takes over GPU output. GlazeWM can't interfere directly, but at non-native resolutions the DWM resolution switch can cause brief re-tiling on secondary monitors.
- **Borderless fullscreen**: Game runs as a regular maximized window. **GlazeWM will tile it** like any other app unless paused.

### Manual pause workflow

The binding `alt+shift+p` (already present in sample configs) runs `wm-toggle-pause`:
- Disables ALL keybindings (except `alt+shift+p`)
- Stops all window management
- GlazeWM becomes invisible to running apps

**Before gaming → `alt+shift+p` → play → done → `alt+shift+p` to resume**

### Window rules for launchers

Add game launchers as `ignore` rules so they float unmanaged:

```yaml
window_rules:
  - commands: ['ignore']
    match:
      - window_process: { equals: 'Playnite.DesktopApp' }
      - window_process: { equals: 'Playnite.FullscreenApp' }
      - window_process: { equals: 'Steam' }
```

Note: ignoring the launcher does NOT ignore games launched through it — games are separate processes. They still need `alt+shift+p` before launch.

### Fullscreen/window state commands

```yaml
  - commands: ['toggle-fullscreen']
    bindings: ['alt+f']
  - commands: ['toggle-minimized']
    bindings: ['alt+m']
  - commands: ['toggle-floating --centered']
    bindings: ['alt+shift+space']
```

Beware of the interaction: toggling fullscreen then minimize can cause windows to get stuck maximized (issue [#906](https://github.com/glzr-io/glazewm/issues/906)). Use `toggle-tiling` (default `alt+t`) to reset.

#### Floating window minimize/restore re-tiling (common issue)

When a window is floated (via `toggle-tiling` or `toggle-floating`), then minimized via `toggle-minimized` (`alt+m`), then restored via Windows-native methods (Alt+Tab, taskbar click), GlazeWM **re-inserts it into the tiling grid**. This happens because `toggle-minimized` transitions to GlazeWM's formal Minimized state, and Windows-native restore triggers a state reset back to `initial_state: 'tiling'`.

**Workarounds (best first):**

1. **Native minimize instead of `toggle-minimized`** — Press **Win+Down arrow** or click the title bar **—** button. This hides the window at the OS level without transitioning GlazeWM's internal state away from Floating. Restoring (Alt+Tab / taskbar click) brings it back floating.
2. **Switch workspace** — `alt+2` moves the window (still floating) to another workspace, no state transition at all.
3. **`toggle-floating` (`alt+shift+space`) over `toggle-tiling` (`alt+t`)** — `toggle-floating` explicitly sets the Floating state rather than toggling between arbitrary previous states. Pairs better with native minimize (option 1).

If the window does re-tile, press `alt+t` (`toggle-tiling`) again to re-float it.

#### "Two windows stuck in fullscreen" (common glitch)

When GlazeWM enters a state where **two or more windows both appear fullscreen** and don't tile properly:
1. **`alt+t`** (toggle-tiling) — forces all windows back into tiled layout, clearing the stuck state.
2. Still broken? **`alt+shift+w`** (wm-redraw) — re-renders the entire window tree.
3. Last resort: **`alt+shift+r`** (wm-reload-config) — reloads config without closing any windows.

This typically happens when apps requesting exclusive fullscreen (games, media players) interact poorly with GlazeWM's window-state tracking. The `toggle-tiling` reset is instant — no restart needed. For persistent issues during gaming, pre-empt with `alt+shift+p` (toggle pause) before launching the game.

### Notifications not appearing

If Windows toast notifications don't appear while using GlazeWM (e.g. cron job notifications, music player toasts, messenger popups):

1. **This is NOT a GlazeWM issue** — GlazeWM has no notification suppression or focus-assist functionality
2. Windows **Focus Assist** auto-enables "Alarms only" mode when any app enters exclusive fullscreen
3. Diagnose: check `HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\QuietHours` — `QuietHoursServiceState: 2` = Alarms only, `FullScreenProcess` shows the triggering app
4. Fix: **Settings → System → Focus Assist → Automatic rules → uncheck "When I'm using an app in full screen mode"**
5. Common trigger: `chrome.exe` when watching fullscreen video (YouTube, Netflix, etc.)

GlazeWM's `toggle-fullscreen` does NOT trigger Focus Assist — this is purely a Windows native behavior for apps using DXGI/IDXGIOutput exclusive fullscreen.

## Key Config Sections

### Gaps
```yaml
gaps:
  scale_with_dpi: true      # Recommended for mixed-DPI setups
  inner_gap: '3px'          # Gap between adjacent windows
  outer_gap:                 # Gap between windows and screen edge
    top: '3px'
    right: '3px'
    bottom: '3px'
    left: '3px'
```

### Window Effects (Windows 11 exclusive features)
```yaml
window_effects:
  focused_window:
    border:
      enabled: true
      color: '#8dbcff'
    corner_style:
      enabled: false       # square/rounded/small_rounded — Win11 only
    hide_title_bar:
      enabled: false
```

### Window Rules (ignore/app-specific)
```yaml
window_rules:
  - commands: ['ignore']
    match:
      - window_process: { equals: 'Flow.Launcher' }
      - window_process: { equals: 'GHelper' }
```

**`ignore` ≠ fullscreen**: an ignored window floats at whatever size the app chose — if the app launches windowed (e.g. Playnite.FullscreenApp launched from another app), it stays windowed, which reads as "half screen". Rule commands run in order and combine, so force it:
```yaml
  - commands: ['ignore', 'set-fullscreen']
    match:
      - window_process: { equals: 'Playnite.FullscreenApp' }
```
Combining pattern confirmed in glzr-io/glazewm issue #699: `['move --workspace Gaming', 'set-floating', 'set-fullscreen']`. To test whether GlazeWM can drive the state before editing, press the `toggle-fullscreen` binding (default `alt+f`) on the focused window.

**Reload workflow — no IPC experiments**: after any config edit, apply with `alt+shift+r` (wm-reload-config) or restart glazewm.exe. Do NOT go down the WebSocket IPC path (port 6123) — raw command messages can silently no-op and it burns tokens. Explicit user preference: concise fix, ask before multi-approach testing.

**Rule not matching? Diagnose, don't guess**: `window_process` matches the exe name WITHOUT `.exe` — verify against the real binaries, and confirm which process actually owns the visible window (launch paths like "launched from Xbox via AnyFSE" can differ from assumptions). To tell "rule not matching (tiled)" apart from "rule working but app launched windowed", inspect the window rect vs monitor bounds. Full recipe (PowerShell window inspection + decision tree): `references/window-rule-debugging.md`.

### Workspaces
```yaml
workspaces:
  - name: '1'
  - name: '2'
  # ... up to 9
```

### Binding Modes (resize mode)
```yaml
binding_modes:
  - name: 'resize'
    keybindings:
      - commands: ['resize --width -2%']
        bindings: ['h', 'left']
      - commands: ['wm-disable-binding-mode --name resize']
        bindings: ['escape', 'enter']
```

## Window State Options
```yaml
window_behavior:
  initial_state: 'tiling'    # New windows open tiled by default
  state_defaults:
    floating:
      centered: true
      shown_on_top: false
    fullscreen:
      maximized: false       # Prefer application's own fullscreen
      shown_on_top: false
```

## Workspaces vs Windows Virtual Desktops

GlazeWM workspaces are its own concept, **completely separate** from Windows Task View virtual desktops (Win+Tab). There is no integration — GlazeWM hides/shows windows within the same desktop rather than switching Windows virtual desktops.

- **Feature request [#671](https://github.com/glzr-io/glazewm/issues/671)** ("Use Virtual Desktops instead of window hiding mechanism") is still open and unimplemented.
- The 9 default workspaces are just config defaults — you can reduce or increase them. Unused workspaces have zero cost.
- If you only use 1–2 workspaces, delete the rest from the config.

## Workspace Visualization (without Zebar)

If the user doesn't want a separate status bar (Zebar) but needs to see which workspace is active, these third-party tools exist:

| Tool | Language | Type | Notes |
|------|----------|------|-------|
| **[glazetray](https://github.com/Drysua/glazetray)** | Go | System tray icon | Shows active workspace number (1–10). Single monitor only, default names only. Simplest native-feeling option. |
| **[glazewm-tray](https://github.com/nickxar1/glazewm-tray)** | Python | Floating bar + tray | Floating bar overlays taskbar with workspace buttons + app icons. Click to switch. Auto-hides during fullscreen. Most feature-rich; needs Python. |
| **[glazeid](https://lib.rs/crates/glazeid)** | **Rust** | **~3 MB** standalone bar | Shows active + all workspaces as pills. Anchors to any screen edge, transparent bg. Pure Rust (tiny-skia, no WebView/JS). Real-time WebSocket, auto-reconnect. Install: `cargo install glazeid`. Config at `%USERPROFILE%\\.glzr\\glazeid\\config.yaml`. |
| **[YASB](https://github.com/amnweb/yasb) (widget)** | Python | Full status bar | Customizable GlazeWM workspaces widget with app icons, scroll-to-switch, offline indicator. Replaces/hides taskbar. |
| GlazeWM built-in tray | C# | System tray | Already present — right-click for Pause/Reload/Exit. **No** workspace info shown. |
| **Windhawk mod** ([1duxa/Windhawk_GlazeWM_Mod](https://github.com/1duxa/Windhawk_GlazeWM_Mod)) | C++ | Desktop widget | Early stage (0★, 2 commits). Shows workspace as a desktop widget, NOT taskbar-embedded. Not recommended. |

**Caveat**: Windows has no public API for embedding widgets into the native taskbar itself. All approaches are either: (a) system tray icon, (b) floating overlay on the taskbar, or (c) standalone bar window. No Windhawk mod can insert live GlazeWM IPC data into the taskbar.

**Recommendation by user preference:**
- "I want minimal / nothing extra on screen" → **glazetray** (zero screen space, just a tray number)
- "I want Rust, lightweight" → **glazeid** (~3 MB, pure Rust, but takes ~20px of screen space)
- "I want clickable workspace buttons on my taskbar" → **glazewm-tray** (floating bar mode overlays the taskbar)
- "I want to replace the taskbar entirely" → **YASB**

## Known Pitfalls

- **Floating window re-tiles after minimize/restore**: Using `toggle-minimized` on a floating window, then restoring via Alt+Tab/taskbar, resets the window to tiling. Use native Win+Down minimize instead. See "Floating window minimize/restore re-tiling" above for full workarounds.
- **BOM corruption**: When editing YAML from WSL, NTFS can inject a UTF-8 BOM that breaks the parser. Fix: `sed -i '1s/^\xEF\xBB\xBF//' config.yaml`
- **hide_method switch requires reload**: Change the config and run `wm-reload-config` — no restart needed.
- **Cloak + transparency apps**: Apps with transparent/translucent rendering (glass, acrylic) are most likely to show ghosting through cloak (issue #880).
- **DWM composition must be on**: GlazeWM cannot function if DWM is disabled.
- **Don't attempt IPC reload after config edits**: use `alt+shift+r` (wm-reload-config) or restart glazewm.exe. Raw WebSocket commands on port 6123 can silently no-op; the hotkey/restart is the simple, user-preferred path (user explicitly asked for concise fixes over multi-approach experimentation).
