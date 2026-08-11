# Floating Window Minimize/Restore Re-Tiling

## The Bug

Reproduction:
1. Window is tiled → `alt+t` (toggle-tiling) → window becomes floating
2. `alt+m` (toggle-minimized) → window minimized
3. Alt+Tab or click taskbar to restore → window rejoins tiling grid

## Root Cause

`toggle-minimized` transitions GlazeWM's internal state to the `Minimized` enum variant (one of four: Tiling, Floating, Fullscreen, Minimized). When Windows-native restore fires (Alt+Tab, taskbar click), GlazeWM's event handler resets the window state to `initial_state: "tiling"` — it doesn't remember the previous Floating state.

## Related Issues

- [#906](https://github.com/glzr-io/glazewm/issues/906) — Fullscreen + minimize → stuck maximized (same state-reset mechanism)
- [#1070](https://github.com/glzr-io/glazewm/issues/1070) — Toggle fullscreen + minimize → always maximized (PR #1071 fix)
- [#1013](https://github.com/glzr-io/glazewm/issues/1013) — Fullscreen while floating → untilable afterward

## Window States (from DeepWiki / source)

Enum in `wm_common` → `packages/wm/src/wm.rs:7-10`:

| State | Description |
|-------|-------------|
| `Tiling` | Participates in tiling layout |
| `Floating(FloatingStateConfig)` | Floats freely, bypasses tiling |
| `Fullscreen(FullscreenStateConfig)` | Covers full workspace |
| `Minimized` | Minimized to taskbar |

State transitions handled by `update_window_state` in `packages/wm/src/wm.rs:218-732`.

## Workarounds

1. **Native minimize** (Win+Down or title bar — button) — OS-level hide, GlazeWM state stays Floating
2. **Switch workspace** (alt+2) — no state transition
3. **`toggle-floating`** (`alt+shift+space`) over `toggle-tiling` (`alt+t`) — more explicit state binding
4. If re-tiled, press `alt+t` again to re-float
