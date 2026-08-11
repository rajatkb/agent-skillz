---
name: streaming-display-corruption
category: windows-gaming
description: Diagnose and fix display mode corruption after using game streaming software (Moonlight/Sunshine/Apollo) with virtual display drivers (IddSampleDriver/SudoVDA). Covers flickering in exclusive fullscreen, mode list pollution, and display state recovery.
---

# Streaming Virtual Display Corruption

Diagnose games flickering/crashing in exclusive fullscreen after using Apollo/Moonlight/Sunshine with virtual display drivers.

## When To Load This Skill

- User reports games flickering/crashing after using game streaming software (Moonlight, Sunshine, Apollo) with virtual display drivers
- Games work windowed/borderless but flicker in exclusive fullscreen
- Games work at lower-than-native resolutions but flicker at native resolution fullscreen
- Issue appeared after disconnecting a virtual display session
- Only games played on the external display at native resolution are affected
- Artifacts or "alt-tab" flicker pattern (rapid display switching) in exclusive fullscreen

## Diagnostic Framework

### Step 1 — Validate the signature

Confirm virtual display corruption with these tests:

1. **Windowed vs fullscreen**: Alt+Enter the game. If it works windowed, the issue is in the exclusive fullscreen path.
2. **Resolution dependency**: Lower Windows display resolution below native (e.g., 900p on a 1080p monitor). Run game at that resolution in fullscreen. If it works, the native resolution mode is corrupted.
3. **Cross-display spread**: Test a game never played through streaming on the laptop display. If it works, then open it on the external monitor at native fullscreen. If it breaks everywhere after that, the corruption is in how the game's config interacts with the corrupted display mode.
4. **Every game vs. specific games**: If ALL games break at native fullscreen, it's a system-level mode list issue. If only games played through streaming break, it's a game config issue.

### Step 2 — Confirm virtual display was involved

- Ask if Apollo/Sunshine/Moonlight was used
- Ask if virtual display (SudoVDA/IddSampleDriver) was installed
- Check Device Manager → View → Show hidden devices → Display adapters for leftover virtual display entries

## Resolution Steps (in order)

### 1. Quick reset
- Press Win+Ctrl+Shift+B to reset the display driver stack
- Full restart (not shutdown — Fast Startup can preserve bad state)

### 2. Disable/uninstall virtual display driver
- Device Manager → View → Show hidden devices
- Expand Display adapters
- Right-click the virtual display entry (SudoVDA, IddSampleDriver, or "Microsoft Virtual Display Driver") → Disable device
- If uninstalling: check "Delete driver software" if available
- Reboot

### 3. Clear stale Enum registry entries
- Regedit → `HKLM\SYSTEM\CurrentControlSet\Enum\DISPLAY\`
- Look for any subkey that is NOT the real monitor (look for `VDD`, `MTT1337`, `SudoVDA`, `IddSample`, or `VirtualDisplay`)
- Delete that entire subkey
- Also check `HKLM\SYSTEM\CurrentControlSet\Enum\GPUDISPLAY\` for suspicious entries
- Reboot

### 4. Clear Windows monitor configuration cache
- Win+R → `regedit`
- Delete ALL subkeys under:
  - `HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\Configuration`
  - `HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\Connectivity`
  - `HKLM\\SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers\\ScaleFactors`
- Reboot

### 5. Clear Apollo display state
- Exit Apollo completely (check system tray)
- Delete the `display_device.state` file (location varies; check `%AppData%/Apollo/` or Apollo's config directory)
- Restart Apollo

### 6. CRU — reset all EDID overrides
- Download CRU from monitortests.com
- Extract and run `reset-all.exe`
- Reboot
- This clears any stale EDID data the virtual display may have left in the registry

### 7. NVIDIA color format switch (diagnostic — takes 10s)
- NVIDIA Control Panel → Display → Change resolution
- Select the affected monitor
- Change Output color format from RGB to **YCbCr422**
- Set Output dynamic range to **Limited** if available
- Click Apply
- Test a game
- This changes the display pipeline entirely, bypassing the corrupted mode negotiation
- If this fixes it, the issue is bandwidth/mode-negotiation at native resolution

### 8. NVIDIA App uninstall (50-series specific)
- Go to Add/Remove Programs
- Uninstall "NVIDIA App"
- Reboot
- Test
- Fixed in driver 581.08 per bug [5434811]: "Power cycling monitor can result in monitor flickering when NVIDIA App is installed"

### 9. Disable GSYNC / VRR
- NVIDIA Control Panel → Display → Set up G-SYNC
- Uncheck "Enable G-SYNC" for the affected monitor
- Apply and test

### 10. Switch to dGPU-only mode (laptops with Advanced Optimus)
- NVIDIA Control Panel → Manage Display Mode
- Switch from "Optimus" or "Auto Select" to **"NVIDIA GPU Only"** (dGPU mode)
- Reboot
- Test
- This bypasses the iGPU entirely — the virtual display driver sits on the iGPU side, so this avoids any corrupted Optimus routing

### 11. Check for Fullscreen Optimizations being globally disabled (CRITICAL — debloater scripts often set this)
- Open PowerShell and run:
  ```powershell
  Get-ItemProperty -Path "HKCU:\System\GameConfigStore"
  ```
- Check if `GameDVR_FSEBehaviorMode` is set to 2
- If so, restore defaults:
  ```powershell
  reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehaviorMode" /t REG_DWORD /d "0" /f
  reg add "HKCU\System\GameConfigStore" /v "GameDVR_DXGIHonorFSEWindowsCompatible" /t REG_DWORD /d "0" /f
  reg add "HKCU\System\GameConfigStore" /v "GameDVR_HonorUserFSEBehaviorMode" /t REG_DWORD /d "0" /f
  reg add "HKCU\System\GameConfigStore" /v "GameDVR_DSEBehavior" /t REG_DWORD /d "0" /f
  reg add "HKCU\System\GameConfigStore" /v "GameDVR_FSEBehavior" /t REG_DWORD /d "0" /f
  ```
- Reboot and test
- See `references/debloater-fso-conflict.md` for full explanation

### 12. Driver clean install (not DDU — just the installer's clean option)
- Download latest NVIDIA driver (581.08+ recommended — has power-cycling flicker fix)
- Run the installer
- Select **"Custom (Advanced)"** → check **"Perform a clean installation"**
- This deletes the NVIDIA driver's internal profile/mode cache without using DDU

### 13. GPU re-enable in Device Manager
- Device Manager → Display adapters → Right-click GPU → Disable device
- Wait 10 seconds → Enable device
- This forces the driver to re-enumerate all display modes from scratch

### 14. Nuclear — DDU
- Download Display Driver Uninstaller (DDU)
- Boot into Safe Mode
- Run DDU → Clean and Restart
- Reinstall latest GPU driver fresh

### 15. Windows 11 25H2 DWM/MPO fullscreen bug (edge case when none of the above works)
**When:** User is on Windows 11 build 26200+ (25H2), flicker + green line persists on BOTH GPUs, all other steps failed.

Windows 11 25H2 has a known DWM + MPO bug (github.com/microsoft/Windows-Dev-Performance/issues/129) where the Desktop Window Manager's multi-plane overlay degrades after display topology changes. Virtual display sessions trigger this by repeatedly adding/removing displays.

```powershell
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayTestMode" /t REG_DWORD /d "0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayMinFPS" /t REG_DWORD /d "0" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v "DisableOverlays" /t REG_DWORD /d "1" /f
```
Reboot after.

See `windows-gaming-fullscreen-corruption` skill for the comprehensive debugging workflow covering NVIDIA App hooks, debloater conflicts, and FSO infrastructure.

## Key Technical Explanation

### Virtual Display Mode Pollution

When a virtual display driver (IddSampleDriver/SudoVDA) creates a virtual display:

1. It registers a display with a fake EDID in Windows
2. The GPU driver caches this display's modes (resolution + refresh rate combinations) internally
3. When the virtual display is disconnected, its modes may remain cached inside the GPU driver
4. If the virtual display used the same resolution (e.g., 1920×1080) but a different refresh rate (e.g., 60Hz) than the physical monitor (e.g., 144Hz), the GPU driver's mode negotiation for exclusive fullscreen picks the wrong timing
5. The display keeps flipping between desktop and game → flickering

Lowering desktop resolution avoids this because the virtual display's cached modes don't match the new resolution. Windowed/borderless works because it uses the DWM compositor, not exclusive display mode switching.

### The Debloater Amplifier (Critical Interaction)

The Chris Titus debloater (and similar tools like it) set registry keys that **globally disable Windows Fullscreen Optimizations (FSO)**:

| Key | Value | Effect |
|-----|-------|--------|
| `GameDVR_FSEBehaviorMode` | 2 | Disables FSO for ALL games |
| `GameDVR_DXGIHonorFSEWindowsCompatible` | 1 | Lets compatible games use real FSE |
| `GameDVR_HonorUserFSEBehaviorMode` | 1 | Forces the above to apply to every game |

**Without FSO**: Games request REAL exclusive fullscreen → the GPU driver must negotiate a mode switch at native resolution → hits the corrupted virtual display mode → flickering.

**With FSO (default)**: Windows intercepts the exclusive fullscreen request and runs the game as a borderless window with DirectFlip/IndependentFlip optimization → no real mode switch happens → avoids the corrupted mode entirely.

This is why the user may have been using Apollo for days without issue (FSO was still on), then ran the debloater (which turned FSO off), and suddenly games broke. The virtual display corruption was latent — the debloater exposed it.

### 50-Series NVIDIA Specifics

- RTX 5070 Ti laptops with Advanced Optimus are particularly susceptible
- The IDD driver (SudoVDA) lives on the iGPU side — on Advanced Optimus laptops, this can corrupt the Optimus display routing table
- Fixed in driver 581.08: "Power cycling monitor can result in monitor flickering when NVIDIA App is installed" [5434811]
- Switching to dGPU-only mode bypasses the iGPU entirely, which can work around Optimus routing corruption

## Pitfalls

### Debloater advanced tweaks vs. default essential tweaks
The Chris Titus winutil "Essential Tweaks" do NOT affect display/gaming behavior. Only the explicitly-checked advanced tweaks cause issues:
- **"Fullscreen Optimizations - Disable"** (z__Advanced Tweaks - CAUTION) — sets `GameDVR_DXGIHonorFSEWindowsCompatible=1`
- **"Xbox & Gaming Components - Remove"** (z__Advanced Tweaks - CAUTION) — removes `Microsoft.XboxGamingOverlay` (Game Bar) and other Xbox AppX packages. This can break FSO infrastructure entirely because FSO depends on Game Bar's overlay system.
- **"Multiplane Overlay" toggle** (Customize Preferences) — changes `OverlayTestMode` (default 5 → 0) and `DisableOverlays` (default 1 → 0). Can affect how DWM handles fullscreen on laptops with Optimus/Advanced Optimus.

If reverting FSO registry keys doesn't fix the issue, check if Xbox Game Bar was actually REMOVED (not just disabled). Reinstall it:
```powershell
winget install "Microsoft.XboxGamingOverlay" --source msstore
```

### NVIDIA 50-series specific
- RTX 5070 Ti laptops with Advanced Optimus are particularly susceptible to IDD virtual display corruption
- Bug [5434811]: "Power cycling monitor can result in monitor flickering when NVIDIA App is installed" — fixed in driver **581.08**
- On 50-series, the NVIDIA driver's internal mode cache can persist across reboots and standard driver uninstalls — only "Perform a clean installation" checkbox or DDU clears it

### FSO registry interaction matters
Simply reverting `GameDVR_FSEBehaviorMode` to 0 isn't always enough. The debloater script from older versions (see `references/chris-titus-debloater-gaming-keys.md`) also sets:
- `GameDVR_FSEBehavior = 2`
- `GameDVR_DXGIHonorFSEWindowsCompatible = 1`
- `GameDVR_HonorUserFSEBehaviorMode = 1`
- `GameDVR_DSEBehavior = 2`
- `GameDVR_EFSEFeatureFlags = 0`
- **Deletes** `Children` and `Parents` under `GameConfigStore` — this wipes any per-game FSO settings

Revert ALL of them, not just `FSEBehaviorMode`.

## References

- references/apollo-known-issues.md — GitHub issues, Apollo wiki pages, NVIDIA forum threads
- references/chris-titus-debloater-gaming-keys.md — Full set of gaming/display registry changes from the Chris Titus winutil debloater + Microsoft Q&A documentation
