# PowerShell from WSL — Quirks & Workarounds

## 1. `$_` Variable Escaping

**Problem:** Bash interprets `$_` before passing the string to PowerShell.exe. `$_.Name` becomes `/mnt/c/Windows/System32.Name` (the CWD path + `.Name`).

**Fix:** Escape `$` with backslash:
```bash
# WRONG — bash expands $_
powershell.exe -Command "Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match 'NPU' }"

# RIGHT — escape $
powershell.exe -Command "Get-CimInstance Win32_PnPEntity | Where-Object { \$_.Name -match 'NPU' }"
```

## 2. UNC Path with cmd.exe

**Problem:** WSL's working directory is a UNC path (`\\wsl.localhost\Debian\home\<user>`). `cmd.exe` cannot run from UNC paths and prints:
```
CMD.EXE was started with the above path as the current directory.
UNC paths are not supported.  Defaulting to Windows directory.
```
This causes `wmic` and some other commands to silently fail (exit code 1, no output).

**Fix:** Change to a Windows drive first, or use `powershell.exe` instead (which handles UNC paths fine):
```bash
# For cmd.exe/wmic — change to /mnt/c first
cd /mnt/c/Windows/System32 && cmd.exe /c "wmic ..."

# Better: use powershell.exe (no UNC issue)
powershell.exe -Command "..."
```

## 3. Preferred Tooling

| Task | Command |
|---|---|
| Query PnP devices | `powershell.exe -Command "Get-CimInstance Win32_PnPEntity \| Where-Object { \$_.Name -match 'AMD' }"` |
| Get driver versions | `powershell.exe -Command "Get-WmiObject Win32_PnPSignedDriver \| Where-Object { \$_.DeviceName -match 'NPU' }"` |
| Get driver version by device property | `powershell.exe -Command "(Get-PnpDeviceProperty -InstanceId '<ID>' -Key 'DEVPKEY_Device_DriverVersion').Data"` |
| Query registry (installed software) | `powershell.exe -Command "Get-ItemProperty 'HKLM:\SOFTWARE\...' \| Where-Object { \$_.DisplayName -match 'foo' }"` |
| Check NPU-specific driver | Use `Get-PnpDeviceProperty` with the specific InstanceId, not `Win32_PnPSignedDriver` (may miss the NPU entry) |

## 5. PowerShell Execution Policy Blocks -File from WSL Paths

**Problem:** `powershell.exe -File /tmp/check_models.ps1` fails with:
```
File \\wsl.localhost\Debian\tmp\check_models.ps1 cannot be loaded because running scripts is disabled on this system.
```

The `/tmp/` path resolves to a UNC path (`\\wsl.localhost\Debian\...`) from Windows, which PowerShell treats as a remote/network location. The default ExecutionPolicy (`Restricted` or `RemoteSigned`) blocks script execution from such paths.

**Fix:** Write the script to a Windows-native path first, then execute with `-ExecutionPolicy Bypass`:

```bash
# WRONG — /tmp is a UNC path from Windows' perspective
cat > /tmp/check.ps1 << 'SCRIPT'
... script content ...
SCRIPT
powershell.exe -File /tmp/check.ps1          # FAILS

# RIGHT — write to /mnt/c/ (Windows native path)
cat > /mnt/c/Users/<user>/check.ps1 << 'SCRIPT'
... script content ...
SCRIPT
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\<user>\check.ps1"  # WORKS
```

**Alternative:** For simple multi-line scripts, pass the entire command as a single-quoted string with `-Command` (not `-File`), but remember to escape `$` and backticks from bash interpolation.

## 7. `powershell.exe` Exit Code Trap: Empty Pipelines Return 1

**Problem:** PowerShell commands that produce empty output (no results) often return exit code 1 from `powershell.exe`, even though the command itself succeeded. This silently breaks bash scripts using `set -euo pipefail` — the script aborts before any output is printed.

**Example — Get-Process on a non-existent process:**
```bash
powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"
# Output: 0
# Exit code: 1  ← TRAP!
```

With `set -o pipefail`, the whole pipeline inherits exit code 1 from `powershell.exe`, and `set -e` causes instant silent abort.

**Diagnose:**
```bash
powershell.exe ... ; echo "PS-EXIT: $?"
# Look for "PS-EXIT: 1" even when output looks correct
```

**Fix:** Always add `|| true` to powershell pipelines in scripts with `set -e`:
```bash
# BEFORE (breaks with set -euo pipefail)
PROC_COUNT=$(powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count" | tr -d '\r')

# AFTER (safe)
PROC_COUNT=$(powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count" 2>/dev/null | tr -d '\r' || true)
```

**Alternatively:** Drop `set -e` from the script and use explicit `exit 1` after commands that genuinely need to fail. The `|| true` guard is simpler for one-off pipelines.

**Affected patterns (non-exhaustive):**
- `Get-Process <name> | ...` when process doesn't exist → exit 1
- `Get-ChildItem | Select-Object ...` on empty directory → exit 1
- `Measure-Object | Select-Object -ExpandProperty Count` on zero results → exit 1
- `netstat ... | findstr` on no matches → exit 1 from findstr (this one is from `findstr`, not PS)

**Safe patterns** (return exit 0 even on empty output):
- `Get-CimInstance ... | Where-Object { ... }` — generally returns 0 even with empty results
- Direct property access like `(Get-Process ...).Count` — may return 0 instead of empty pipeline

**Problem:** Trying to background a command with `&` when calling PowerShell from WSL bash doesn't work:
```bash
powershell.exe -NoProfile -Command "& 'C:\Program Files\flm\flm.exe' serve qwen3:0.6b --host 0.0.0.0 &"
```
The `&` is consumed by PowerShell's call operator, not bash's background operator.

**Fix:** Use `Start-Process` to launch detached processes:
```bash
powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'C:\Program Files\flm\flm.exe' -ArgumentList 'serve qwen3:0.6b --host 0.0.0.0'"
```

Or from Hermes Agent, use `terminal(background=true)` with the command wrapped in double-quotes to prevent bash splitting:
```
terminal(command='powershell.exe -NoProfile -Command "& ''C:\\Program Files\\flm\\flm.exe'' serve qwen3.5:2b --host 0.0.0.0"', background=True)
```

- Device: `PCI\VEN_1022&DEV_17F0` (NPU Compute Accelerator)
- Service: `IpuMcdmDriver`
- PNPClass: `ComputeAccelerator`
- Architecture: XDNA2
