# dGPU Won't Sleep — Idle Diagnosis Playbook

Ordered end-to-end procedure for "dGPU never sleeps / stays hot on AC" on hybrid (Optimus) laptops.
Derived from GA403 + RTX 5070 Ti + driver 610.74 case (Aug 2026). Run steps in order; each narrows the cause.

## 0. Baseline snapshot (one query, then STOP polling)

```powershell
nvidia-smi
nvidia-smi -q -d POWER
nvidia-smi --query-gpu=timestamp,pstate,power.draw,clocks.gr,clocks.mem,utilization.gpu --format=csv,noheader
```

Interpretation:
- `P0` + ~19W + 0% util + `0 MiB` + "No running processes found" + mem clock at max = **held awake at D0**.
- 54°C idle on a 5070 Ti while iGPU drives the displays = not sleeping (D3 GPU reads ~ambient).

## 1. Display binding — is the dGPU driving anything?

- `nvidia-smi` header `Disp.A = Off` → no display attached to dGPU.
- Confirm topology: `dxdiag /t "$env:TEMP\dxdiag.txt"` (takes 30-60s), then grep `Card name` + `Current Mode` per adapter. On G14 hybrid, both internal + USB-C external should list under "AMD Radeon 890M", NVIDIA shows `Current Mode: Unknown`.

## 2. What could hold it — process & registry sweep

- Process check: G-Helper, HWiNFO, FanControl, RTSS/MSI Afterburner, RGB tools, wallpaper engines (Sucrose), NVIDIA App containers (nvcontainer), Armoury Crate.
- Windows GPU pinning: `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` — `GpuPreference=2` forces an app onto the dGPU. Wallpaper engines are the classic offender (Sucrose sets GpuPreference=2 for a dozen processes).
- `powercfg /requests` — nothing blocking system sleep does NOT prove the GPU is free (GPU holds are separate from system sleep blockers).

## 3. Platform blocker — PCIe ASPM

```powershell
powercfg /q SCHEME_CURRENT SUB_PCIEXPRESS
```

AC index `0x0` (Off) + DC `0x2` (Max) = the ASUS default; RTD3 can never engage on AC. Fix:

```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_PCIEXPRESS ee12f906-d277-404b-b6da-e5fa1a576df5 2
powercfg /setactive SCHEME_CURRENT
```

Reboot re-trains the link. This is necessary but was NOT sufficient in the 5070 Ti case — the GPU stayed D0 after the fix (see step 4/6).

## 4. Quiet-period test (critical — avoid self-interference)

nvidia-smi/NVAPI queries WAKE the dGPU. Observed: 2s polling ramped core clocks 570→7094 MHz at 0% util, and a 1s PnP poll loop may also prevent idle.

1. Last query → then 90s–3min of ABSOLUTE silence (no nvidia-smi, no PnP loops).
2. ONE read, least-invasive: PnP `DEVPKEY_Device_PowerData` (read `bytes[4]` as uint32; 1 = D0, 4 = D3).
3. Still D0 after 3 clean minutes = genuinely held (driver/settings/platform). D3 = your own polling was the waker.

## 5. Driver 3D settings (DRS) — CLI limits

- Global "Power management mode" lives in `C:\ProgramData\NVIDIA Corporation\Drs\nvdrsdb*.bin`. On r610+ drivers the settings section is a **keyed cipher** — not readable via strings/UTF-16/ROT. Don't decode; verify in NVIDIA App → Manage 3D Settings → Global → Power management mode ("Optimal power" preferred).
- `HKLM\SOFTWARE\NVIDIA Corporation\Global\NVTweak` exists on modern drivers but is typically empty — not a lever.
- Signature: prefer-max-perf pins CORE clocks high. Mem-pinned + core-idling-at-570MHz points at a wake-hold instead.

## 6. External-display waker test (Advanced Optimus / DDS readiness)

With a USB-C/HDMI monitor connected, the NVIDIA driver may keep the dGPU "ready" for dynamic display switching even when the iGPU drives the display.

Test: unplug the monitor for 1-2 min while watching PnP state with the loop below (2s interval; PnP reads are least invasive). D3 with monitor out → the display path is the waker → fix via NVIDIA Control Panel → set display to integrated-only / disable Advanced Optimus for that display.

```powershell
$gpu = Get-PnpDevice | Where-Object { $_.FriendlyName -match "NVIDIA GeForce" -and $_.Class -eq "Display" }
while ($true) {
    $pd = Get-PnpDeviceProperty -InstanceId $gpu.InstanceId -KeyName 'DEVPKEY_Device_PowerData'
    $bytes = [byte[]]$pd.Data
    $state = [BitConverter]::ToUInt32($bytes, 4)
    $label = switch ($state) { 1 { 'D0/awake' } 4 { 'D3/asleep' } default { "Unknown: $state" } }
    Write-Host "$(Get-Date -Format HH:mm:ss)  $label"
    Start-Sleep 2
}
```

## Known result pattern (Aug 2026, GA403 + 5070 Ti + 610.74)

P0 / 19.4W / 54°C / D0 for 3+ min of quiet / no processes / no display / ASPM fixed → matches the NVIDIA dev-forum class "GPU stuck P0 with no active processes" (RTX 4090 mobile 37W idle, Mar 2026; 5070 Ti desktop 35-40W). Remaining suspects: NVIDIA App global power mode (UI check) or external-display DDS readiness (unplug test).
