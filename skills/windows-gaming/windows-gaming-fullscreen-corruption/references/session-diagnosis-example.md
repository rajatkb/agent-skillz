# Session Diagnosis Log — Fullscreen Flickering After Apollo Virtual Display

## Machine
- Laptop: RTX 5070 Ti Laptop GPU (12GB GDDR7)
- OS: Windows 11 **25H2** (build 26200)
- GPU mode: dGPU-only (Advanced Optimus, manually set)
- NVIDIA Driver: 32.0.16.1074 (= 610.74, July 2026)
- NVIDIA App: 11.0.8.299 (installed, overlay toggled OFF)
- Also has AMD Ryzen iGPU
- External monitor: 1080p @ 60Hz
- Internal display: laptop panel (also 60Hz)

## Timeline
1. Installed Apollo + Moonlight, used virtual display streaming to iPad and TV for a few days
2. Also ran Chris Titus debloater script in the same window
3. After returning to main PC, games flicker/crash in fullscreen at 1080p
4. Windowed/borderless works fine
5. Lowering Windows to 900p and running games fullscreen works fine
6. Games that weren't played remotely work fine until first played on the external monitor at 1080p

## What Was Tried (in order)

### Did NOT fix:
- Win+Ctrl+Shift+B (temporary display driver reset)
- Full cold reboot (Restart, not fast startup)
- Uninstall virtual display driver (Device Manager → Show hidden → Display adapters → removed SudoVDA)
- Delete GraphicsDrivers registry keys (Configuration, Connectivity, ScaleFactors)
- CRU reset-all.exe (cleared EDID overrides)
- Color format change (RGB → YCbCr422 8-bit)
- FSO registry revert (reset all GameConfigStore keys to defaults)
- dGPU-only mode (was already set)
- Switch resolution to 900p (workaround, not fix)
- MSI Afterburner / RTSS shutdown
- NVIDIA App uninstall from Add/Remove Programs (partial — files remained)

### Key diagnostic findings:
- Green line at top of screen during flicker
- Persisted on AMD iGPU too (ruled out NVIDIA driver)
- Persisted with external monitor disconnected (ruled out cable/monitor)
- NVIDIA App splash appeared for 007 First Light despite App "uninstalled"
- **FSO GameConfigStore keys were at Windows defaults** (debloater NOT the cause)
- **NVIDIA App folder still existed at C:\Program Files\NVIDIA Corporation\NVIDIA App\**
- **Registry still showed HKLM\SOFTWARE\NVIDIA Corporation\Global\NvApp: Installed=1**
- MPO overlay settings at defaults (OverlayTestMode=5, DisableOverlays=1)
- HAGS not set (default = off on laptop, normal)
- Xbox Game Bar package was still present

### Likely root cause:
Combination of:
1. **Windows 11 25H2 DWM/MPO bug** (github.com/microsoft/Windows-Dev-Performance/issues/129) — known issue where 25H2's DWM MPO handling degrades after display topology changes
2. **NVIDIA App driver-level hooks** persisted even after "uninstall" (files + registry left behind)
3. **Virtual display sessions** repeatedly cycled the display topology, stressing the buggy DWM path

### Still outstanding:
- OverlayTestMode=0 + OverlayMinFPS=0 + DisableOverlays=1 fix (from Step 11.5 in skill) was not yet tested when session ended
- Manual NVIDIA App folder deletion (Remove-Item) was not yet done

## Registry Values Checked
```
HKCU\System\GameConfigStore
  GameDVR_Enabled = 1 (default)
  GameDVR_FSEBehaviorMode = 0 (default)
  GameDVR_DXGIHonorFSEWindowsCompatible = 0 (default)
  GameDVR_HonorUserFSEBehaviorMode = 0 (default)
  GameDVR_DSEBehavior = 0 (default)
  GameDVR_EFSEFeatureFlags = 0 (default)

HKLM\SOFTWARE\Microsoft\Windows\Dwm
  OverlayTestMode = 5 (default)

HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers
  DisableOverlays = 1 (default)
  HwSchMode = not set (default = off on laptop)

HKLM\SOFTWARE\NVIDIA Corporation\Global\NvApp
  FullPath = C:\Program Files\NVIDIA Corporation\NVIDIA App\CEF\NVIDIA App.exe
  Installed = 1
  Version = 11.0.8.299

HKLM\SOFTWARE\NVIDIA Corporation\Global\NGXCore
  AllowGameOverlays = 0
```
