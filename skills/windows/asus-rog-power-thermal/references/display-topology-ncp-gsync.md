# Display topology → NVIDIA Control Panel availability (G-Sync, scaling) on hybrid laptops

Session-tested walkthrough (G14 GA403 2025, RTX 5070 Ti + Radeon 890M, Win11 25H2).

## The rule

In hybrid/Optimus mode the iGPU physically owns all displays (internal eDP + external ports). The dGPU renders into them but holds no display controller. NVIDIA Control Panel only shows display-management features — the "Set up G-SYNC" page and "Adjust desktop size and position" (aspect ratio / scaling modes) — for displays DIRECTLY wired to the NVIDIA GPU. Displays seen through the iGPU get reduced or absent options. Nothing is broken; the RTX is just not in the signal path.

Canonical citation (quote directly in answers):
> "Display-specific features available on discrete GPU (like NVIDIA® G-SYNC®, higher refresh rates) may not be available on the laptop display even though the discrete GPU can support them"
> — NVIDIA Advanced Optimus Overview, https://nvidia.custhelp.com/app/answers/detail/a_id/5097/

## Probe sequence (all read-only, run from WSL via powershell.exe / nvidia-smi.exe)

1. `nvidia-smi --query-gpu=name,driver_version,display_active,display_mode --format=csv,noheader`
   - `display_active: Disabled` ⇒ dGPU drives NO display ⇒ every active monitor is iGPU-owned. **The single most decisive probe.**
2. `Get-CimInstance Win32_VideoController | Select Name,CurrentHorizontalResolution,CurrentVerticalResolution,PNPDeviceID`
   - The controller(s) reporting a resolution are the ones driving displays. Internal panel res (e.g. 2880×1800) on AMD + none on NVIDIA = hybrid confirmed.
3. Monitor identity + connection:
   - `Get-PnpDevice -Class Monitor | Select FriendlyName,InstanceId,Status` — PNP prefix decodes the panel: SDC419C = Samsung (internal), MSI4DD3 = MSI, BNQ = BenQ. Status "Unknown" = not currently connected (ghost / secondary off).
   - `Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorConnectionParams` → VideoOutputTechnology: 10 = DisplayPort external (USB-C alt mode reports as DP), 11 = eDP (internal), 5 = HDMI.
4. GPU mode: read `%APPDATA%\GHelper\config.json` → `gpu_mode`. Enum from G-Helper source (`app/AsusACPI.cs`): `GPUModeEco=0`, `GPUModeStandard=1`, `GPUModeUltimate=2`. Standard = hybrid. (Verify against source via codeload tarball if unsure — `https://codeload.github.com/seerge/g-helper/tar.gz/refs/heads/main`.)

## Fix

- G-Helper GPU mode → **Ultimate** (dGPU only, MUX switch) → restart. After restart the internal panel is dGPU-driven: NCP "Set up G-SYNC" appears, "Adjust desktop size and position" unlocks. (ROG forum GA403WR: "In Ultimate mode, the display does correctly switch to the dGPU after a restart.")
- External monitor: must be on a **dGPU-wired port**. Free empirical test: in Ultimate, if the external goes dark it's on an iGPU-routed port → move the cable (try the other USB-C, or HDMI 2.1).
- External monitor OSD: enable the Adaptive-Sync/FreeSync toggle, then tick "Enable G-SYNC" in NCP.
- Stay-in-hybrid alternative: AMD Adrenalin FreeSync works for iGPU-owned displays (AMD owns them in hybrid mode) — offer this when the user won't accept dGPU-only trade-offs.

## Pitfalls

- **`optimized_usbc` in G-Helper config is about USB-C POWER ADAPTER detection** (treats USB-C PD as "not plugged" for auto GPU-mode switching — `GPUModeControl.cs IsPlugged()`), NOT display routing. Verified in source. Don't blame it for display issues; it does explain why auto mode stays in Standard/Eco on USB-C power.
- **Panel G-Sync capability ≠ available in hybrid.** Panels are often G-Sync capable (2024/2025 G14 3K OLED is, per RTINGS 2024 review "G-SYNC support" and Notebookcheck CES 2025 "ROG Nebula OLED display with Nvidia G-Sync") but ASUS only wires them to the dGPU through the MUX. Verify capability via reviews before telling a user their panel can't do VRR.
- **Scaling options are moot at native resolution** — "Adjust desktop size and position" only matters at non-native res (e.g. 1080p on a 4K panel). On OLED at native res there is nothing to scale.
- **Even in Ultimate, grayed scaling can be the Image Sharpening "GPU scaling" checkbox** (NCP → Manage 3D Settings → Global → Image Sharpening → uncheck). NVIDIA forum thread 338451.
- **Ultimate = dGPU always on**: worse battery/thermals. State the trade-off explicitly; suggest Standard + toggle-when-gaming, or FreeSync-via-Adrenalin for externals.
- **NCP presence check**: `Get-AppxPackage *nvidia*` — classic NVIDIA Control Panel is a Store package (NVIDIACorp.NVIDIAControlPanel). The new NVIDIA App doesn't expose the scaling/aspect-ratio section. Rule that out before concluding topology.
