---
name: windows-gaming-fullscreen-corruption
description: Diagnose and fix fullscreen exclusive mode corruption in games on Windows — flickering, alt-tab cycling, black screens that affect exclusive fullscreen but not windowed/borderless. Covers corruption from virtual display drivers (Moonlight/Apollo/Sunshine/IddSampleDriver), NVIDIA App overlay hooks, debloater FSO breaking, and stale GPU driver mode tables.
---

# Windows Gaming — Fullscreen Corruption Diagnosis & Repair

Games that flicker, cycle like rapid alt-tabbing, or crash specifically in **exclusive fullscreen** mode — but work fine in windowed, borderless, or at non-native resolutions — indicate a corrupted display mode negotiation path, not a per-game config issue.

## Key Diagnostic Patterns

| Symptom | Likely Cause |
|---|---|
| Works at non-native res (900p) but not native (1080p) | Stale display mode entry from virtual display driver |
| Works windowed/borderless but not fullscreen | Flip chain / exclusive mode corruption |
| All games affected | System-level driver state, not game config |
| Spreads from external monitor to laptop display | Corrupted mode propagates system-wide |
| Started after Moonlight/Apollo streaming session | IddSampleDriver/SudoVDA contaminated NVIDIA internal mode table |
| Started after Chris Titus / debloater script | FSO disabled or Xbox infrastructure removed |
| Green line at top of screen during flicker | Partial render of overlay/FPS counter due to MPO plane corruption. Key: persists on AMD iGPU too → DWM-level issue, not NVIDIA-specific |
| Issue persists on BOTH dGPU and iGPU | Rules out NVIDIA driver as root cause. Points to Windows DWM / MPO corruption at the OS level |
| NVIDIA App splash appears for games despite App showing as uninstalled | NVIDIA App files + registry (NvApp, Installed=1) still on disk — Add/Remove Programs uninstall did not fully clean up |
| Green line / flicker persists with external monitor disconnected, on laptop display alone | Not a monitor/cable issue — confirms software-level DWM flip chain corruption |

### Cross-GPU isolation test

Run a game briefly on the integrated GPU to isolate the fault layer:

- **Settings → System → Display → Graphics** → pick game → Options → **"Power Saving"** (iGPU)
- If green line + flickering **persists** on iGPU → issue is at the **Windows DWM level**, not GPU-driver-specific. Target DWM, MPO, and overlay infrastructure for debugging (Step 11.5).
- If green line + flickering **disappears** on iGPU → issue is **NVIDIA-driver-specific**. Target NVIDIA overlay hooks, driver mode cache, or Optimus routing (Steps 9, 12).

## Systematic Debug Chain

Try in order. Each step rules out a layer.

### Step 1 — Quick resets
- `Win+Ctrl+Shift+B` — resets display driver stack (takes 1s)
- **Full cold reboot** — not fast startup shutdown, use Restart

### Step 2 — Remove virtual display driver
- `devmgmt.msc` → View → Show hidden devices
- Expand **Display adapters** — look for `Virtual Display Driver`, `IddSampleDriver`, `SudoVDA`, or `VDD`
- Right-click → **Disable device** (or Uninstall)
- Reboot

### Step 3 — Clear Windows display cache
- `regedit` → delete ALL subkeys under:
  - `HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration`
  - `HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Connectivity`
  - `HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\ScaleFactors`
- Reboot

### Step 4 — CRU (Custom Resolution Utility)
- Download from monitortests.com
- Run **`reset-all.exe`** — deletes all EDID software overrides, forces GPU to re-read real monitor EDID from hardware
- Reboot

### Step 5 — Color format switch (quick test)
- NVIDIA Control Panel → Display → Change resolution
- Select affected monitor → change **Output color format** from RGB to **YCbCr422**, bit depth to **8-bit**
- Apply, test. Reverts the display pipeline entirely, bypassing corrupt RGB timing negotiation

### Step 6 — Fullscreen Optimizations — restore defaults
- If you or a debloater script changed FSO settings, revert to defaults:
```powershell
reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehaviorMode" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_DXGIHonorFSEWindowsCompatible" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_HonorUserFSEBehaviorMode" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_DSEBehavior" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehavior" /t REG_DWORD /d "0" /f
```
- Reboot

### Step 7 — dGPU-only mode (laptops with Optimus/Advanced Optimus)
- NVIDIA Control Panel → **Manage Display Mode** → switch to **"NVIDIA GPU only"** (or "dGPU Only")
- Reboot. Bypasses the iGPU entirely — if this fixes it, the Optimus routing table was corrupted

### Step 8 — Xbox / Game Bar infrastructure check (debloater damage)
- Check if Xbox Game Bar AppX package is present:
```powershell
Get-AppxPackage Microsoft.XboxGamingOverlay
```
- If missing, reinstall:
```powershell
winget install Microsoft.XboxGamingOverlay
```
- Check Xbox services are not disabled:
```powershell
Get-Service XboxGipSvc, XblAuthManager, XblGameSave, XboxNetApiSvc | Select-Object Name, Status, StartType
```

### Step 9 — NVIDIA App — CRITICAL for 50-series
- **NVIDIA App's capture hooks corrupt the fullscreen flip chain on RTX 50-series**, even with the in-game overlay toggled OFF in settings
- Uninstall from Add/Remove Programs: **"NVIDIA App"** and **"NVIDIA App driver settings"**
- **After uninstalling, verify cleanup** — the uninstaller often leaves files + registry entry intact:
  ```powershell
  # Check if files remain on disk
  Test-Path "C:\Program Files\NVIDIA Corporation\NVIDIA App"
  # Check if registry still shows installed — key path:
  # HKLM\SOFTWARE\NVIDIA Corporation\Global\NvApp
  Get-ItemProperty "HKLM:\SOFTWARE\NVIDIA Corporation\Global\NvApp" -Name Installed -ErrorAction SilentlyContinue
  Get-ItemProperty "HKLM:\SOFTWARE\NVIDIA Corporation\Global\NvApp" -Name FullPath -ErrorAction SilentlyContinue
  ```
- If leftovers found, manually clean:
  ```powershell
  Remove-Item "C:\Program Files\NVIDIA Corporation\NVIDIA App" -Recurse -Force
  Remove-Item "HKLM:\SOFTWARE\NVIDIA Corporation\Global\NvApp" -Force
  Remove-Item "$env:LOCALAPPDATA\NVIDIA\NVIDIA App" -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item "$env:PROGRAMDATA\NVIDIA\NVIDIA App" -Recurse -Force -ErrorAction SilentlyContinue
  ```
- Reboot and test
- Reinstall later from NVIDIA.com if needed for driver updates (the overlay toggle may still cause issues)

### Step 10 — Check HAGS (Hardware-Accelerated GPU Scheduling)
```powershell
Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name HwSchMode
```
- Value `1` = enabled, `2` = enabled (auto). Missing or `0` = disabled on laptop (default).
- Try toggling: Settings → System → Display → Graphics → Change default graphics settings → Hardware-accelerated GPU scheduling

### Step 11 — MPO (Multiplane Overlay) check
```powershell
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\Dwm" -Name OverlayTestMode
Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" -Name DisableOverlays
```
- Default: `OverlayTestMode=5`, `DisableOverlays=1`
- If someone toggled these via WinUtil's "Multiplane Overlay" customize preference, set back to defaults

### Step 11.5 — Windows 11 25H2 DWM/MPO fullscreen flicker bug
**Applies when:** user is on Windows 11 build 26200+ (25H2), flicker + green line persists on BOTH GPUs, none of the above steps resolved it.

Windows 11 25H2 has a known DWM + MPO bug (tracked at github.com/microsoft/Windows-Dev-Performance/issues/129 and learn.microsoft.com/en-us/answers/questions/5749171) where the Desktop Window Manager's multi-plane overlay handling degrades after display topology changes (which is exactly what virtual display drivers do — they add/remove displays repeatedly).

**Fix — force DWM to bypass the broken MPO path:**
```powershell
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayTestMode" /t REG_DWORD /d "0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayMinFPS" /t REG_DWORD /d "0" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v "DisableOverlays" /t REG_DWORD /d "1" /f
```
- `OverlayTestMode=0` disables MPO testing mode (default 5 enables it)
- `OverlayMinFPS=0` companion fix specific to 25H2 builds — prevents DWM from re-engaging MPO at low framerates
- Reboot after
- Revert by deleting these keys if they cause issues

**To verify this is the right path:** If Print Screen captures the green line in screenshots, it's a DWM/compositor overlay — this registry fix targets that layer. If the green line doesn't appear in screenshots, it's at the GPU output level (follow Step 12 instead).

**MPO toggle-as-flush recovery (edge case):** If neither the fix nor reverting MPO settings resolves the issue, the corruption may be cached in the GPU kernel driver's persistent state. Toggle MPO off, reboot, then re-enable:

```powershell
# Phase 1 — disable MPO
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayTestMode" /t REG_DWORD /d "0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayMinFPS" /t REG_DWORD /d "0" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v "DisableOverlays" /t REG_DWORD /d "1" /f
# Reboot here, confirm games work, then:
Remove-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\Dwm" -Name "OverlayTestMode" -ErrorAction SilentlyContinue
Remove-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\Dwm" -Name "OverlayMinFPS" -ErrorAction SilentlyContinue
# Reboot again
```

This forces DWM + the GPU kernel driver to tear down all overlay allocations, then re-initialize from scratch on the second boot. The corruption is in runtime DWM memory and kernel driver cache — it doesn't survive two cold boots with different MPO states. See `references/25h2-mpo-dwm-bug.md` for the full research including source links, cross-GPU isolation results, and the real-world reproduction context.

### Step 12 — NVIDIA driver clean install (NOT DDU)
- Download latest driver from NVIDIA.com (581.08+ recommended for 50-series)
- Run installer → **Custom (Advanced)** → check **"Perform a clean installation"**
- This clears the NVIDIA driver's **internal mode cache** (separate from Windows registry), which is where stale virtual display modes persist

## Why Virtual Display Drivers Cause This

IddSampleDriver-based virtual displays (SudoVDA used by Apollo, itsmikethetech's VDD used by Sunshine) register fake display EDIDs in Windows. On 50-series NVIDIA laptops with Advanced Optimus:

1. The virtual display's 1920x1080 mode (or whatever res the client requested) gets cached in the NVIDIA driver's **internal display mode table**
2. When the virtual display is removed, the stale entry persists — the driver doesn't flush it
3. When a game requests exclusive fullscreen at the same resolution, the NVIDIA driver finds **two entries** (real monitor + stale virtual) with potentially different timings
4. The driver tries to use the wrong timing → mode switch fails → flickering/crashing
5. At non-native resolutions (900p, 720p), there's no stale virtual entry → works fine

The corruption lives in the **NVIDIA driver binary state**, not Windows registry — which is why:
- Clearing GraphicsDrivers registry keys doesn't fix it
- CRU reset-all doesn't fix it (EDID overrides are clean, driver cache is not)
- Only a **driver clean install** or **cold driver reload** clears it

## Chris Titus WinUtil Specifics

The `tweaks.json` at `github.com/ChrisTitusTech/winutil/blob/main/config/tweaks.json` contains these gaming-affecting advanced tweaks:

| Tweak ID | What it does | Gaming impact |
|---|---|---|
| `WPFTweaksDisableFSO` | Sets `GameDVR_DXGIHonorFSEWindowsCompatible=1` | Forces real exclusive fullscreen — exposes driver mode corruption |
| `WPFTweaksXboxRemoval` | Removes `Microsoft.XboxGamingOverlay` AppX + related services | The Windows FSO infrastructure depends on Game Bar system; full removal can break the flip model fallback |
| `WPFToggleGameMode` | Toggles `AllowAutoGameMode` / `AutoGameModeEnabled` | Usually harmless, Game Mode is optional |
| `WPFToggleMultiplaneOverlay` | Changes `OverlayTestMode` + `DisableOverlays` | Can alter DWM's MPO handling; rarely the root cause |
| `WPFTweaksDisplay` | Visual effects → best performance, disables Aero Peek, DWM animations | Minor, doesn't affect flip chain |

The **default Essential Tweaks** do NOT touch any gaming/display settings. The above are all in "Advanced Tweaks - CAUTION" or "Customize Preferences" panels.

## Related Skills

- `windows-debloating` — exhaustive service auditing; has a table comparing debloater tools including Chris Titus WinUtil with a cross-reference to this skill
- `windhawk-windows-ui-customization` — Windows UI modding via Windhawk
- `streaming-display-corruption` — narrower sibling: focuses specifically on display mode corruption from virtual display streaming software
