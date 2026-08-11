# Windows 11 25H2 DWM / MPO Fullscreen Flicker Bug

## Sources

- **Microsoft GitHub Issue #129**: github.com/microsoft/Windows-Dev-Performance/issues/129
  "Windows 11 24H2/25H2 Display Flicker & Game Crash Bug"
  Reports DWM fullscreen pipeline corruption on hybrid GPU laptops after
  display topology changes (mouse clicks trigger compositor flip → flicker).

- **Microsoft Q&A**: learn.microsoft.com/en-us/answers/questions/5749171
  "Screen flickering stems from conflict between DWM and MPO"
  Solution: disable Multiplane Overlay via `OverlayTestMode` registry,
  clean install graphics drivers.

- **Schalk Burger blog**: schalkburger.dev/posts/fix-windows-chromium-freezing/
  Documents `OverlayMinFPS=0` companion fix for 24H2/25H2 builds.

- **SmoothFPS MPO guide**: smoothfps.com/solutions/mpo
  "OverlayTestMode is an unofficial registry value (documented by NVIDIA,
  not Microsoft)."

- **NVIDIA driver 581.08 release notes**:
  Bug [5434811]: "Power cycling monitor can result in monitor flickering
  when NVIDIA App is installed"

- **Microsoft D3D driver docs**:
  learn.microsoft.com/en-us/windows-hardware/drivers/ddi/d3dkmddi/nc-d3dkmddi-dxgkcb_multiplaneoverlaydisabled
  "A display change or hot plug event on one output makes it no longer
  possible to support an MPO configuration."

## Mechanism

1. Apollo creates a virtual display via SudoVDA (IddSampleDriver)
2. Windows adds the virtual display to the display topology
3. DWM allocates MPO planes across all active displays
4. When the virtual display is removed, DWM reallocates the plane table
5. On 25H2, this reallocation is buggy — the plane table becomes corrupted
6. Games requesting fullscreen try to allocate planes from the corrupted table
7. Planes render at wrong offsets (green line at top) or swap incorrectly (flickering)
8. The corruption persists across reboots — it's cached in the GPU kernel
   driver's memory (nvlddmkm.sys on NVIDIA), not on disk

## Fix

Three registry changes that force DWM to use software composition instead of
hardware overlay planes:

```powershell
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayTestMode" /t REG_DWORD /d "0" /f
reg add "HKLM\SOFTWARE\Microsoft\Windows\Dwm" /v "OverlayMinFPS" /t REG_DWORD /d "0" /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v "DisableOverlays" /t REG_DWORD /d "1" /f
```

| Key | Default | Fix value | Effect |
|-----|---------|-----------|--------|
| `OverlayTestMode` | 5 | 0 | Disables MPO testing mode |
| `OverlayMinFPS` | (not set) | 0 | Prevents DWM re-engaging MPO at low framerates |
| `DisableOverlays` | 1 | 1 | Kernel-level overlay disable (unchanged) |

## Toggle-as-Flush Recovery

If DWM's MPO state is corrupted, toggling the registry and rebooting twice
acts as a forced flush:

1. Set `OverlayTestMode=0`, reboot → DWM starts without MPO, corruption is
   not loaded because the subsystem isn't initialized
2. Delete/remove `OverlayTestMode`, reboot → DWM re-initializes MPO from
   scratch, reading fresh EDID instead of stale cached state

The corruption lives in runtime DWM memory and GPU kernel driver cache —
it doesn't survive two cold boots with different MPO states.

## Real-World Reproduction

Reproduced on:
- ASUS ROG G16 (Ryzen + RTX 5070 Ti Laptop)
- Windows 11 25H2 (build 26200)
- NVIDIA driver 610.74
- Apollo v0.4.x with SudoVDA virtual display
- iPad and TV as Moonlight clients at 1080p 60Hz

Symptom: green line at top of screen + flickering in all games at fullscreen.
Persisted on AMD iGPU (cross-GPU test confirmed DWM-level issue).
Resolution: MPO toggle-as-flush cleared the corruption entirely.
