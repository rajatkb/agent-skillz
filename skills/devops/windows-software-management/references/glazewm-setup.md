# GlazeWM Setup Reference

## Keybinding Conflicts with Other Apps

GlazeWM's default `Alt+Space` binding for `wm-cycle-focus` steals focus from launchers (Flow Launcher, PowerToys Run, etc.).

**Fix**: Change the binding to something unused:
```yaml
  - commands: ['wm-cycle-focus']
    bindings: ['alt+grave']   # backtick ` instead of space
```
This frees `Alt+Space` for launcher shortcuts.

## Ignoring Apps (Window Rules)

Add launchers and other non-tiling apps to `window_rules` so they float above everything:

```yaml
window_rules:
  - commands: ['ignore']
    match:
      - window_process: { equals: 'Flow.Launcher' }
```

The `ignore` command tells GlazeWM to leave the window alone — it stays floating and on top, never tiled.

## Window Borders

The `window_effects` section controls colored borders around focused/unfocused windows:

```yaml
window_effects:
  focused_window:
    border:
      enabled: true
      color: '#8dbcff'         # Windows accent blue
```

**Limitation**: There's no conditional logic to hide the border when only one window exists on a workspace. It's either globally on or off. With 3px gaps, a lone window fills almost the entire screen so the border is minimally visible.

## Using a Tiling WM (Mental Model)

Core principle: **windows never overlap** — every new window splits the screen, and you navigate by direction, not clicking.

- `Alt+V` toggles between **horizontal** (new windows go right) and **vertical** (new windows go below) split direction
- The **focused window** is where the next split happens
- Close a window → remaining ones expand to fill the space
- Use **workspaces** (`Alt+1`–`Alt+9`) as separate desktops — one for coding, one for browser/research, one for chat/music
- Pause tiling with `Alt+Shift+P` when you need to drag-and-drop, then resume

## Installation

**v3.10.1** (latest as of July 2026).

| Step | Command |
|------|---------|
| Standalone MSI | `curl -L -o /mnt/c/Users/RAJAT/Downloads/glazewm-x64.msi "https://github.com/glzr-io/glazewm/releases/download/v3.10.1/standalone-glazewm-v3.10.1-x64.msi"` then `msiexec /i ...` | Clean install, no optional Zebar checkbox. Exit 1625 = system policy blocks silent — run EXE instead |
| Silent install | `powershell.exe -ExecutionPolicy Bypass -Command "Start-Process msiexec.exe -ArgumentList '/i \"C:\Users\RAJAT\Downloads\glazewm-x64.msi\" /quiet /norestart' -Wait"` |
| Manual install | Run the EXE (`glazewm-v3.10.1.exe`) — installer GUI appears, user clicks through |

**Install path**: `C:\Program Files\glzr.io\GlazeWM\` (contains `glazewm.exe`, `glazewm-watcher.exe`, `cli\glazewm.exe`)

## Config File

**Path**: `%userprofile%\.glzr\glazewm\config.yaml` → `C:\Users\<user>\.glzr\glazewm\config.yaml`

**⚠️ Critical: UTF-8 BOM pitfall.** Config files written from WSL to NTFS (`/mnt/c/`) may acquire a UTF-8 BOM (`ef bb bf`). Rust YAML parsers (serde_yaml) reject this with `"more than one doc not supported"`.

Detect:
```bash
od -A x -t x1z -v /mnt/c/Users/<user>/.glzr/glazewm/config.yaml | head -3
# First byte should be 67 ('g'), not ef (BOM)
```

Fix:
```bash
sed -i '1s/^\xEF\xBB\xBF//' /mnt/c/Users/<user>/.glzr/glazewm/config.yaml
```

Validate:
```bash
python3 -c "import yaml; yaml.safe_load(open('/mnt/c/Users/<user>/.glzr/glazewm/config.yaml')); print('OK')"
```

On first launch, GlazeWM writes a default config. It includes Zebar references that must be removed:

### Items to remove for a Zebar-free setup

```yaml
# From general section:
general:
  startup_commands: ['shell-exec zebar']         # ← REMOVE (or set to [])
  shutdown_commands: ['shell-exec taskkill /IM zebar.exe /F']  # ← REMOVE

# From window_rules:
window_rules:
  - commands: ['ignore']
    match:
      - window_process: { equals: 'zebar' }      # ← REMOVE this entry
```

### Gap adjustment

Default outer_gap.top assumes a bar. For **no bar / maximum screen space**:
```yaml
gaps:
  scale_with_dpi: true
  inner_gap: '3px'
  outer_gap:
    top: '3px'
    right: '3px'
    bottom: '3px'
    left: '3px'
```

Defaults (with bar):
```yaml
gaps:
  inner_gap: '20px'          # keep or reduce to 10px
  outer_gap:
    top: '60px'              # ← assumes bar
    right: '20px'
    bottom: '20px'
    left: '20px'
```

## Starting GlazeWM

- **Start Menu**: Search "GlazeWM" → click
- **Command line**: `glazewm.exe start`
- **System tray**: Right-click icon for Pause/Resume/Exit/Reload config
- **Reload config**: `Alt+Shift+R`
- **Pause/Resume**: `Alt+Shift+P`
- **Exit**: `Alt+Shift+E`

## Default Keybinding Reference

All bindings use `Alt` as modifier. Grouped by category:

### Focus / Move
| Keys | Action |
|------|--------|
| `Alt+H/J/K/L` or `Alt+Arrow` | Focus left/down/up/right |
| `Alt+Shift+H/J/K/L` | Move window in direction |
| `Alt+Space` | Cycle focus: tiling → floating → fullscreen |
| `Alt+S` / `Alt+A` | Next/previous active workspace |
| `Alt+D` | Recent workspace (toggle) |

### Workspaces
| Keys | Action |
|------|--------|
| `Alt+1` through `Alt+9` | Focus workspace N |
| `Alt+Shift+1` through `Alt+Shift+9` | Move window to workspace N + follow |
| `Alt+Shift+A/S/D/F` | Move workspace to monitor (left/down/up/right) |

### Window State
| Keys | Action |
|------|--------|
| `Alt+F` | Toggle fullscreen |
| `Alt+T` | Toggle tiling |
| `Alt+Shift+Space` | Toggle floating (centered) |
| `Alt+M` | Minimize |
| `Alt+Shift+Q` | Close focused window |
| `Alt+V` | Toggle tiling direction |

### Resize
| Keys | Action |
|------|--------|
| `Alt+U/I/O/P` | Resize: −width, +height, +width, −height (2% each) |
| `Alt+R` | Enter resize mode (then HJKL/arrows, Esc to exit) |

### Apps
| Keys | Action |
|------|--------|
| `Alt+Enter` | Launch CMD (change to `wt` for Windows Terminal, or path to git-bash) |
