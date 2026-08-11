# Chris Titus Windows Debloater — Gaming/Display Registry Changes

## Source

- winutil config/tweaks.json: `github.com/ChrisTitusTech/winutil/blob/main/config/tweaks.json`
- GitHub issue #486: `github.com/ChrisTitusTech/winutil/issues/486` — full "Disable FSO Globally" script
- WinUtil docs: `winutil.christitus.com/dev/tweaks/z--advanced-tweaks---caution/disablefso/`
- Microsoft Q&A: `learn.microsoft.com/en-us/answers/questions/3741077/fullscreen-optimizations-windows-registry`

## Caution Level Classification

| Tweak | Category | Must be Explicitly Checked? |
|-------|----------|-----------------------------|
| Fullscreen Optimizations - Disable | z__Advanced Tweaks - CAUTION | Yes |
| Xbox & Gaming Components - Remove | z__Advanced Tweaks - CAUTION | Yes |
| Multiplane Overlay toggle | Customize Preferences | Yes |
| Game Mode toggle | Customize Preferences | Yes |
| Essential Tweaks (default) | Essential Tweaks | No — runs by default |

**The default "Essential Tweaks" do NOT touch gaming/display registry keys.** Only the CAUTION-level and Customize Preferences tweaks do, and they must be manually checked.

## Fullscreen Optimizations Registry Changes

### What the debloater sets (from issue #486)

```powershell
reg add "HKCU\SOFTWARE\Microsoft\GameBar" /v "ShowStartupPanel" /t REG_DWORD /d "0" /f
reg add "HKCU\SOFTWARE\Microsoft\GameBar" /v "GamePanelStartupTipIndex" /t REG_DWORD /d "3" /f
reg add "HKCU\SOFTWARE\Microsoft\GameBar" /v "AllowAutoGameMode" /t REG_DWORD /d "0" /f
reg add "HKCU\SOFTWARE\Microsoft\GameBar" /v "AutoGameModeEnabled" /t REG_DWORD /d "0" /f
reg add "HKCU\SOFTWARE\Microsoft\GameBar" /v "UseNexusForGameBarEnabled" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_Enabled" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehaviorMode" /t REG_DWORD /d "2" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehavior" /t REG_DWORD /d "2" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_HonorUserFSEBehaviorMode" /t REG_DWORD /d "1" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_DXGIHonorFSEWindowsCompatible" /t REG_DWORD /d "1" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_EFSEFeatureFlags" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_DSEBehavior" /t REG_DWORD /d "2" /f
reg add "HKLM\SOFTWARE\Microsoft\PolicyManager\default\ApplicationManagement\AllowGameDVR" /v "value" /t REG_DWORD /d "0" /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR" /v "AllowGameDVR" /t REG_DWORD /d "0" /f
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR" /v "AppCaptureEnabled" /t REG_DWORD /d "0" /f
reg add "HKU.DEFAULT\SOFTWARE\Microsoft\GameBar" /v "AutoGameModeEnabled" /t REG_DWORD /d "0" /f
reg delete "HKCU\System\GameConfigStore\Children" /f
reg delete "HKCU\System\GameConfigStore\Parents" /f
```

### Key documentation (from Microsoft Q&A)

| Key | Values | Description |
|-----|--------|-------------|
| `GameDVR_FSEBehaviorMode` | 0 (default): Only applies to high-impact games |
| | 1: Applies to all full-screen games |
| | **2: Disables Fullscreen Optimizations for ALL games** |
| `GameDVR_DXGIHonorFSEWindowsCompatible` | 0 (default): Game DVR doesn't record in FSE | 
| | **1: Game DVR respects the FSE flag, lets games use true FSE** |
| `GameDVR_HonorUserFSEBehaviorMode` | 0 (default): Uses default mode |
| | **1: Forces FSE behavior to apply to all games** |
| `GameDVR_DSEBehavior` | 0 (default): Game DVR can use full resources in DSE |
| | **2: Limits Game DVR resource usage in DirectFlip Exclusive** |
| `GameDVR_EFSEFeatureFlags` | 0 (default): Controls Enhanced Full-screen Exclusive features |
| `GameDVR_Enabled` | 0 (default): Game DVR is enabled |
| | 1: Game DVR is disabled |
| `GameDVR_FSEBehavior` | 0 (default): Game DVR can use full resources in fullscreen |
| | 2: Limits Game DVR resource usage in fullscreen |

### Critical observation

Even after reverting all registry keys above, if the **Xbox Game Bar** AppX package (`Microsoft.XboxGamingOverlay`) was removed by the debloater, Windows Fullscreen Optimizations **cannot function** because FSO depends on Game Bar's overlay infrastructure. Reinstall it:

```powershell
winget install "Microsoft.XboxGamingOverlay" --source msstore
```

## Multiplane Overlay (MPO) Toggle

From winutil Customize Preferences:

```json
{
  "Path": "HKLM:\\SOFTWARE\\Microsoft\\Windows\\Dwm",
  "Name": "OverlayTestMode",
  "Value": "0",          // default was 5
  "DefaultState": "true"
},
{
  "Path": "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers",
  "Name": "DisableOverlays",
  "Value": "0",          // default was 1 (disabled)
  "DefaultState": "true"
}
```

- `OverlayTestMode = 0` changes how DWM allocates MPO planes
- `DisableOverlays = 0` enables MPO overlays (default is 1 = overlays disabled)
- On laptops with Optimus/Advanced Optimus, MPO plane negotiation between iGPU and dGPU can cause flickering in fullscreen games
- This toggle is particularly relevant when the user is in dGPU-only mode — MPO is handled entirely by the NVIDIA GPU in that mode

## Complete FSO Revert (restore all to Windows defaults)

```powershell
reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehaviorMode" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_DXGIHonorFSEWindowsCompatible" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_HonorUserFSEBehaviorMode" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_DSEBehavior" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehavior" /t REG_DWORD /d "0" /f
reg add "HKCU\System\GameConfigStore" /v "GameDVR_EFSEFeatureFlags" /t REG_DWORD /d "0" /f
```

Reboot after applying.
