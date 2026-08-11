# Rajat's GlazeWM Config (C:\Users\RAJAT\.glzr\glazewm\config.yaml)

## General
- `hide_method: 'cloak'` with `show_all_in_taskbar: true`
- `cursor_jump.enabled: true` on `monitor_focus`
- Single workspace: `name: '1'` only

## Gaps
- inner: 3px, outer: 3px all sides
- `scale_with_dpi: true`

## Window Effects
- Focused window: blue border (#8dbcff), square corners, no title bar hide
- Other windows: no border

## Ignore Rules
- Picture-in-Picture (Chrome/Mozilla)
- PowerToys (PowerAccent, Peek, Command Palette)
- Lively wallpaper
- Office: EXCEL (non-XLMAIN), WINWORD (non-OpusApp), POWERPNT (non-PPTFrameClass)
- Flow.Launcher, GHelper, Playnite.DesktopApp, Playnite.FullscreenApp, AnyFSE
  - Resolution (2026-08-03): Playnite.FullscreenApp launched from Xbox FSE via AnyFSE appeared "half screen" (2560x1080 on a 2560x1440 monitor). Ignore rule WAS matching — window was floating, app just launched windowed. Fully closing and relaunching Playnite confirmed the ignore works (rules evaluate at window creation). User's final position: Playnite + AnyFSE must stay COMPLETELY unmanaged — do NOT add `set-fullscreen` (that re-engages GlazeWM management). See `window-rule-debugging.md`.
  - Hardening (2026-08-05): recurring "Playnite not ignored" despite correct, live process-name rules (GlazeWM 3.10.1, config verified loaded). Added class catch-all `- window_class: { regex: 'HwndWrapper.*Playnite' }` to the same ignore rule — catches ANY Playnite WPF window (Desktop/Fullscreen/dialogs/progress windows) regardless of which process hosts it (Playnite 10.55 single-instance pipe forwards launches to the running instance; window ownership can differ from the assumed exe). No set-fullscreen (user wants fully unmanaged).

## Custom Keybindings (non-default)
| Binding | Action |
|---------|--------|
| `alt+u/p/o/i` | Resize width -2%/+2%, height +2%/-2% |
| `alt+r` | Enter resize mode |
| `alt+grave` | Cycle focus |
| `alt+enter` | Open cmd |
| `alt+s/a/d` | Next/prev/recent workspace |
| `alt+shift+a/f/d/s` | Move workspace left/right/up/down |
| `alt+shift+1` | Move window to ws 1 + follow |

No workspace bindings beyond `alt+1` / `alt+shift+1` (single workspace setup).
