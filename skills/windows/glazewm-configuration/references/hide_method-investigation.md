# hide_method Investigation (July 2026)

## Context

User reported windows "vanishing" — switching workspaces in GlazeWM and being unable to find applications. The user wanted to know if GlazeWM has its own windowing system and whether it could "use Windows' one" for discoverability.

## Architecture Answer

GlazeWM does NOT have its own windowing system. It runs on top of Windows DWM (Desktop Window Manager) via Win32 API calls (`MoveWindow`, `SetWindowPos`, `SW_HIDE`, `WS_EX_CLOAKED`). It cannot "fall back to DWM" — it already uses DWM for all display.

## The Bug: cloak vs hide

### cloak (current default, introduced in PR #792)
- Uses `WS_EX_CLOAKED` extended window style via COM `IVirtualDesktopManager::SetCloak`
- Window stays in the window tree and taskbar but DWM is told not to render it
- **Smoother** — no visual animation on hide/show
- **Buggier** — issue #880 documents windows not properly hiding (ghosting behind), and the converse issue (windows silently vanishing entirely)
- Some apps with transparency/glass rendering are more affected

### hide (legacy, pre-v3.7)
- Uses `SW_HIDE` Win32 message
- Window is fully hidden including from taskbar enumeration
- **More reliable** — well-tested Win32 behavior
- **Slower** — brief animation on hide/show

## Config Change

```yaml
general:
  hide_method: 'hide'   # Changed from 'cloak'
```

## Related Settings
- `show_all_in_taskbar: true` — when using `cloak`, shows windows from all workspaces in the taskbar so they're discoverable. Has no effect with `hide` method.
- **Key lesson from this session**: For users who say "I want my tasks visible in the taskbar," `show_all_in_taskbar: true` is the correct fix — NOT switching to `hide`, which makes the problem worse.
- This user's config had NO `taskbar_hide` section and NO bar config at all — just gaps, window_effects, window_rules, and keybindings.

## Session Outcome (July 24, 2026) — Session 2

User came back wanting to understand workspaces better, and the conversation evolved significantly:

### What was done (cumulative)
1. Changed `show_all_in_taskbar: false → true` — cloaked windows stay visible in taskbar
2. Reduced `workspaces:` from 9 to `['1']` — eliminates workspace-switching/hiding entirely
3. Stripped dead keybindings (`alt+2..9`, `alt+shift+2..9`)
4. Added Playnite to window_rules as `ignore` (both DesktopApp and FullscreenApp)
5. Kept `hide_method: 'cloak'` (default) — irrelevant with single workspace

### Key user preferences discovered
- **Hates Zebar** (too bulky, separate bar taking screen space)
- **Prefers Rust tools** — rejected glazetray (Go) and glazewm-tray (Python) on principle
- **Wants taskbar-embedded indicators** — but this is fundamentally impossible on Windows (no API for third-party taskbar widgets)
- **Wants direct, sourced answers** — pushes back on claims without evidence
- **Single workspace user** — uses Win+D (Show Desktop) instead of workspace switching

### Layout confusion resolved
User asked about creating a "master-and-stack" layout: vertical left split, right split into top/bottom, new windows stacking on right. This is achievable manually by:
1. `alt+v` → horizontal → window 2 (splits left/right)
2. Focus left, `alt+v` → vertical → window 3 (left splits top/bottom)
3. Focus right, `alt+v` → vertical → window 4 (right splits top/bottom)
4. New windows while focused on right split further right (stacking effect)

Key insight: `alt+v` is **per-container**, not global. This was the user's conceptual block.

### GAT-GWM auto-tiler
https://github.com/Dutch-Raptor/GAT-GWM — Rust auto-tiler that alternates split direction by nesting depth. `cargo install gat-gwm`. Automates what the user would otherwise do manually with `alt+v`.

### Windhawk mod dead end
The only Windhawk GlazeWM mod (1duxa/Windhawk_GlazeWM_Mod) is a desktop widget, NOT taskbar-embedded. Windhawk patches DLLs for visual styling but can't insert live IPC data from third-party apps into the taskbar. No Windhawk solution exists for GlazeWM workspace indicators.

### Visualization tool decision logic (for future sessions)
When a user says "I need an indicator to use this setup":
1. Ask: do you want zero screen-space cost? → **glazetray** (tray number)
2. Ask: do you want Rust specifically? → **glazeid** (~3 MB, standalone bar)
3. Ask: do you want clickable buttons on the taskbar? → **glazewm-tray** (overlay mode)
4. Explain: Windows has no taskbar widget API — every option has a tradeoff

### Remaining dead keybindings to offer stripping
- `focus --workspace 2..9` (alt+2..9)
- `move --workspace 2..9, focus --workspace 2..9` (alt+shift+2..9)
- `focus --next-active-workspace` / `--prev-active-workspace` / `--recent-workspace` (alt+s/a/d)

## Sources (updated)
- GlazeWM README: https://github.com/glzr-io/glazewm
- Issue #880 (cloak hiding method bug): https://github.com/glzr-io/glazewm/issues/880
- PR #792 (cloak implementation): https://github.com/glzr-io/glazewm/pull/792
- Sample config: https://github.com/glzr-io/glazewm/blob/main/resources/assets/sample-config.yaml
- Issue #671 (virtual desktop feature request): https://github.com/glzr-io/glazewm/issues/671
- Issue #891 (tray indicator feature request): https://github.com/glzr-io/glazewm/issues/891
- Discussion #1280 (taskbar display alternatives): https://github.com/glzr-io/glazewm/discussions/1280
- Issue #169 (virtual desktop support): https://github.com/glzr-io/glazewm/issues/169
- Issue #1142 (Task View closes on hover bug): https://github.com/glzr-io/glazewm/issues/1142
- Issue #729 (auto-pause on fullscreen feature request): https://github.com/glzr-io/glazewm/issues/729
- GAT-GWM auto-tiler: https://github.com/Dutch-Raptor/GAT-GWM
- glazeid (Rust workspace bar): https://lib.rs/crates/glazeid
- glazetray (Go tray indicator): https://github.com/Drysua/glazetray
- glazewm-tray (Python tray+floating bar): https://github.com/nickxar1/glazewm-tray
- YASB status bar: https://github.com/amnweb/yasb
- Windhawk GlazeWM mod: https://github.com/1duxa/Windhawk_GlazeWM_Mod
