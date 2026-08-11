# Hybrid-GPU App Assignment & "App Lags on the iGPU" Diagnosis

Worked on 2026-08-03 (G14 GA403, hybrid mode, external 4K@165Hz on USB-C): Playnite.FullscreenApp "slightly lagging when using the AMD iGPU".

## Which GPU is an app actually on?

```bash
# Anything on the dGPU? Empty process table = app is on the iGPU.
nvidia-smi            # bottom "Processes" section
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# Does the dGPU drive any display? "Disabled" = ALL displays are on the iGPU.
nvidia-smi --query-gpu=display_mode,display_active --format=csv,noheader

# Confirm the app is running at all
powershell.exe -NoProfile -Command "Get-Process Playnite* | Select-Object ProcessName, Id"
```

`display_active=Disabled` + empty process table ⇒ render and present are BOTH on the iGPU — there is no cross-GPU (PCIe copy) path, so lag is pure iGPU rendering/composition load, not GPU switching.

## Pin an app to the iGPU (deterministic)

Registry: `HKCU:\SOFTWARE\Microsoft\DirectX\UserGpuPreferences`
- Value **name** = FULL path to the exe, value data = `GpuPreference=1;`
- `1` = power-saving (iGPU), `2` = high-performance (dGPU), `0` = let Windows decide
- Read at **process start** → the app must be relaunched to take effect
- UI equivalent: Settings → System → Display → Graphics → app → Power saving
- Apps without an entry (typical for non-game WPF apps) land on the iGPU anyway; pinning makes it deterministic so Windows can't reassign later

```powershell
New-ItemProperty -Path 'HKCU:\SOFTWARE\Microsoft\DirectX\UserGpuPreferences' `
  -Name 'C:\Users\RAJAT\AppData\Local\Playnite\Playnite.FullscreenApp.exe' `
  -Value 'GpuPreference=1;' -PropertyType String -Force
```

## "App lags on the iGPU" — diagnosis order

1. **Rule out cross-GPU** (above). If dGPU has no display and no processes, both render+present are on the iGPU.
2. **Read the app's own rendering config** — don't guess, open the real config file:
   - Playnite (WPF + CefSharp): `%APPDATA%\Playnite\config.json` — keys: `DisableHwAcceleration` (false = HW accel ON), `BackgroundImageAnimation`, `GridViewSmoothScrollEnabled`, `DetailsViewSmoothScrollEnabled`, `ListViewSmoothScrollEnabled`, `UseCompositionWebViewRenderer`. Heavy scenes (background animation + smooth scroll) at 4K/165Hz on an iGPU drop frames — and at 165Hz every dropped frame is visible.
   - `%APPDATA%\Playnite\cef.log`: `GetGpuDriverOverlayInfo: Failed to retrieve video device` = benign AMD-driver/Chromium overlay quirk, NOT the lag cause.
3. **Check power mode.** G-Helper Silent/Eco caps iGPU TDP → 4K composition suffers. Standard/Balanced gives the iGPU headroom.
4. **Mitigations:** pin to iGPU (above) + reduce app rendering load (disable background animation / smooth scroll in the app's config) — trade UI feel for smoothness. On the dGPU the same app is smooth because of ~10× fill rate; that's the tradeoff the user accepts for iGPU-only.

## Notes

- Playnite's real version is NOT in `Playnite.FullscreenApp.exe` FileVersion (always 1.0.0.0) — don't use it to pin the release.
- Pinning an app to the iGPU doubles as a power fix: the dGPU stays in D3 (see main SKILL.md dGPU-idle work).
