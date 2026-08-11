---
name: windows-software-management
description: Install, configure, and manage Windows software from WSL — MSI/exe install patterns, PowerShell script file technique, config cleanup, and verification. Covers the WSL→Windows bridge with tested working approaches.
triggers:
  - user wants to install desktop software on Windows from WSL
  - user needs to configure a Windows application's config files
  - user asks to set up development tools or window managers on Windows
  - user runs into WSL→Windows path/powershell mangling during install
---

# Windows Software Management (from WSL)

General patterns for installing, configuring, and managing Windows software from a WSL environment.

## Core Pattern: PowerShell script files over inline commands

When running Windows PowerShell commands from WSL, **write a `.ps1` script file and execute it** instead of inline `-Command`:

```bash
# BAD — $env:USERPROFILE gets mangled by WSL's UNC path handling
powershell.exe -Command "Get-ChildItem \"$env:USERPROFILE\.glzr\""

# GOOD — write to a PS1 file, copy to Windows side, run via -File
# (write_file /tmp/script.ps1, then:)
cp /tmp/script.ps1 /mnt/c/Users/RAJAT/Downloads/
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\RAJAT\Downloads\script.ps1"
```

**Why**: WSL prepends `/home/<user>` or a UNC path to bare expressions in `-Command`, breaking `$env:USERPROFILE` and `$_.PropertyName` references.

## Installation Methods from WSL

| Method | Command / Approach | Notes |
|--------|-------------------|-------|
| **MSI** | Write PS1 with `Start-Process msiexec.exe -ArgumentList "/i <msi> /quiet /norestart /log <log>" -Wait` | Exit 1625 = "forbidden by system policy" — run non-silent, installer GUI appears for the user |
| **EXE** | Same PS1 approach with silent flag (often `/S`) | Run non-silent as fallback; user clicks through installer |
| **winget** | Unreliable from WSL (UNC path issues) | Prefer direct GitHub release download |
| **Direct download** | `curl -L -o /mnt/c/Users/<user>/Downloads/file.exe <url>` | Most reliable |
| **Standalone MSI** | Download from GitHub releases (look for `standalone-*-x64.msi`) | Bundled EXE may include optional add-ons — standalone MSI is clean |

## Config File Management

Software that generates a default config on first launch often includes bundled companion app references (e.g., GlazeWM adds Zebar by default). Workflow:

1. **Write a PS1 script** to read the config file from Windows paths
2. **Inspect for bloat** — startup commands, shutdown commands, window rules referencing companion apps
3. **Replace with minimal config**, backing up the original with `.default-backup` suffix
4. **Adjust display-related defaults** — e.g., GlazeWM's default `outer_gap.top: '60px'` assumes a bar; reduce to `10px` when no bar is used

## Critical Pitfall: UTF-8 BOM on YAML/JSON config files

YAML/JSON/Toml config files **written from WSL to an NTFS mount** (`/mnt/c/`) can acquire a **UTF-8 Byte Order Mark** (`ef bb bf`) at the start. Most YAML parsers used by Rust/C# applications (serde_yaml, etc.) reject this with a confusing error like `"more than one doc not supported"`.

**Fix**: Strip the BOM from the first line:
```bash
sed -i '1s/^\xEF\xBB\xBF//' /mnt/c/Users/<user>/path/to/config.yaml
```

**Detection**:
```bash
od -A x -t x1z -v /mnt/c/path/to/config.yaml | head -3
# If first byte is ef (not 67 = 'g' for 'general:'), BOM is present
```

**Prevention**: `write_file` from the agent's toolset does write clean files, but the WSL→NTFS bridge may add the BOM regardless. Always verify after writing config files to Windows paths.

## Flow Launcher Plugin Research

When the user needs a Flow Launcher plugin with a specific capability (reminders, notifications, search, etc.):

1. **Enumerate the official manifest first** — grep the store manifest for candidates:
   ```bash
   curl -sL "https://raw.githubusercontent.com/Flow-Launcher/Flow.Launcher.PluginsManifest/plugin_api_v2/plugins.json" -o /tmp/plugins.json
   # then json-grep Name+Description for capability keywords (python3 -c json.load)
   ```
   Plugins missing from the manifest still exist and install via `pm install <path-or-url-to-zip>` inside Flow.
2. **Verify capability from source, not README** — READMEs overstate features. Curl raw `.cs` files from GitHub and check what the code actually does.
3. **Native Windows notification discriminator** — the deciding check for "does it fire a real Windows notification":
   - `Microsoft.Toolkit.Uwp.Notifications` / `CommunityToolkit.WinUI.Notifications` → real Action Center toasts ✅
   - `context.API.ShowMsg(...)` or custom WPF `Window` → Flow-Launcher-internal notification, NOT a native Windows toast ❌
4. **Check maintenance** — latest release tag + `pushed_at` from the GitHub API.

Reminder-plugin landscape with install commands: `references/flow-launcher-plugins.md`.

## Launching Windows GUI apps on WSL files (Zed, editors, viewers)

**Preferred method — `zed .` from inside the target directory** (the Zed Windows CLI is on PATH inside WSL and resolves to `C:\Users\RAJAT\AppData\Local\Programs\Zed\bin\zed`):

```bash
cd ~/.hermes/scripts && zed .      # opens the CURRENT directory as a Zed project
cd ~/.hermes/crawl_sessions/<session> && zed .   # inspect a research session tree
```

- The CLI **blocks while attached** to the app (terminal command appears to "time out") — that is normal Zed behavior, not a failure. Run it, then verify in a separate call.
- Verify the window opened:
  ```bash
  powershell.exe -NoProfile -Command "Get-Process zed -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle} | Select-Object Id,MainWindowTitle"
  # title = folder name (e.g. "scripts" or the session slug) = project opened correctly
  ```
- If multiple Zed windows appear, the one titled exactly the folder name is the good one; stale windows from earlier failed launches may show "folder - folder" and should be closed.

**Fallback — PowerShell `Start-Process` with a translated path** (only when you must open a specific path without cd'ing):

```bash
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Users\RAJAT\AppData\Local\Programs\Zed\zed.exe' -ArgumentList '\\wsl.localhost\Debian\home\rajat-g14\.hermes\scripts'"
```

**Pitfalls (all observed live):**
- `cmd.exe /c start "" "<exe>" "<unc-path>"` **fails or hangs** — cmd inherits the WSL cwd (a UNC path) and errors "UNC paths are not supported. Defaulting to Windows directory." Never use cmd.exe for this.
- **Open a folder, not multiple file args** — passing two separate UNC file paths made Zed open improperly/blank. A single directory argument opens as a project with the file tree visible. Prefer `zed .` after `cd` over any UNC form.
- PowerShell `Start-Process` returns immediately (no hang) and handles UNC paths natively.
- These are real WSL files behind the `\\wsl.localhost\...` path — editor saves apply directly to `~/.hermes/...` (may be slow over the 9p mount; warn the user if the file is large).

## Verification

After install, use a PS1 script to confirm:

```powershell
# Check common install paths
$paths = @(
    "$env:LOCALAPPDATA\<vendor>",
    "$env:PROGRAMFILES\<vendor>",
    "C:\Program Files\<vendor>",
    "C:\Program Files\<vendor>\<app>\app.exe"
)
foreach ($p in $paths) { if (Test-Path $p) { Write-Output "FOUND: $p" } }

# Search for executable
Get-ChildItem "C:\Program Files" -Recurse -Filter "app.exe" -ErrorAction SilentlyContinue

# Check Start Menu
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs" -Recurse -Filter "*app*"
```

**Locating an installed app — order of attempts:**
1. `Get-StartApps` (filter Name/AppID) — instant, authoritative for anything with a start-menu entry
2. Known per-vendor paths (`$env:LOCALAPPDATA\<vendor>\`, `$env:LOCALAPPDATA\Programs\<vendor>\` — Tauri apps install per-user here, not Program Files)
3. LAST resort: `Get-ChildItem "$env:LOCALAPPDATA" -Recurse -Filter "App.exe"` — recursive AppData scans are slow and time out (observed 60s+); never use them as the first attempt.

## Related Files

- `references/glazewm-setup.md` — GlazeWM-specific install, config, and keybinding reference
- `references/flow-launcher-plugins.md` — Flow Launcher plugin evaluation (reminder plugins, native-toast discriminator, manifest scan)
