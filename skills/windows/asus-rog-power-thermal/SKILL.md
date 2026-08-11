---
name: asus-rog-power-thermal
description: Diagnose and fix power/thermal issues on ASUS ROG laptops (Zephyrus G14/G16, Strix, TUF). Covers Modern Standby S0ix, dGPU power state management, G-Helper sensor polling bugs, clamshell/clamshell thermal behavior, and power/thermal debugging tools.
---

# ASUS ROG Laptop Power & Thermal Troubleshooting

## When to use

A user reports unexplained heat, fan noise, battery drain, or performance issues on an ASUS ROG laptop — especially:

- Hot/bag while in standby or lid-closed clamshell mode
- Fans at max when system appears idle
- High idle power draw on battery (30W+ when 5-15W expected)
- dGPU not entering low-power states
- G-Helper running and laptop staying warm/hot
- "I left it overnight and it was cooking when I woke up"

## Root Causes (check in priority order)

### 0. AMD Task Scheduler bloat causes inconsistent battery drain across boot/wake/unplug states

On 2025 Zephyrus G14 models (Ryzen AI 300 series + RTX 5070 Ti), specific AMD task scheduler entries fire at every logon or power-mode change, keeping the CPU/GPU awake longer than needed. The telltale symptom is **different battery drain depending on how you started**:

| Scenario | Drain (before fix) |
|---|---|
| Fresh boot on battery | 7-9W |
| Wake from sleep/hibernation | 10-12W |
| Unplugged from AC while running | 11-13W |

**Tasks to check in Task Scheduler (`taskschd.msc`):**

| Task Name | What it does |
|---|---|
| `AMDScoSupportTypeUpdate` | AMD support type update — runs at every logon |
| `ModifyLinkUpdate` | AMD Adrenalin update check at login/power-mode change |
| `StartCN` | AMD bloat — hogs CPU/GPU for no apparent reason |
| `StartDVR` | AMD Relive/Recording feature (most never use it) |
| `ASUS Hotplug Controller` | May show Nvidia GPU as ejectable on pre-2025 models when disabled |
| `MicrosoftEdge*` | Edge update tasks (safe to disable if not using Edge) |

**Fix:** Open Task Scheduler → locate each task → right-click → Disable. Also disable AMD overlays/hotkeys/logging in AMD Adrenalin.

**Note:** Chris Titus WinUtil removes most of these already. The AMD tasks above are typically found under `\AMD\` in Task Scheduler (e.g., `\AMD\Framework Service` and `\AMD\P508PowerAgent_sdk` may remain even after debloat — these are lean AMD chipset drivers and can stay).

### 1. G-Helper NVAPI thermal polling keeps dGPU awake

G-Helper calls `NvAPI_GPU_GetThermalSettings` every 1-2 seconds to read GPU temperature. This NVAPI call **wakes the dGPU from D3 (asleep) to D0 (awake)** on each poll, preventing it from entering low-power idle.

**Symptoms:**
- Battery discharge 30-35W vs expected 5-15W (on battery, but heat output same on AC)
- dGPU cycles D0 ↔ D3 repeatedly when it should stay D3
- Laptop noticeably warmer with G-Helper running vs closed
- 0% GPU utilization in taskman but high total system power

**Verify (run from PowerShell as admin):**
```powershell
$gpu = Get-PnpDevice | Where { $_.FriendlyName -match "NVIDIA" -and $_.Class -eq "Display" }
while ($true) {
    $pd = Get-PnpDeviceProperty -InstanceId $gpu.InstanceId -KeyName 'DEVPKEY_Device_PowerData'
    $bytes = [byte[]]$pd.Data
    $state = [BitConverter]::ToUInt32($bytes, 4)
    $label = switch ($state) { 1 { 'D0/awake' } 4 { 'D3/asleep' } default { "Unknown: $state" } }
    Write-Host "$(Get-Date -Format HH:mm:ss)  $label"
    Start-Sleep 1
}
# If dGPU cycles D0/D3 while idle → NVAPI polling is waking it
```

**Fix:** Use experimental G-Helper build (v0.245+) that gates NVAPI temperature reads behind a D3/D12 state check. Or close G-Helper to tray when system should idle (window doesn't need to be open).

### 2. G-Helper CPU polling spike bugs

G-Helper can spike CPU 6-7% every ~3 seconds after autostart, or get stuck at 5-6% after power-state transitions (plugged ↔ unplugged). This prevents CPU from entering deep C-states, adding 5-8W of sustained CPU package power.

**Fix:** Open G-Helper window, then minimize back to tray — this resets the polling loop. Update to latest version.

### 3. dGPU-only mode / MUX switch position

On laptops in dGPU-only mode, the discrete GPU can never fully power off — it's driving the display. RTD3 (Runtime D3) doesn't apply. Combined with NVAPI thermal polling, this compounds continuous heat output.

**Check:**
```powershell
nvidia-smi -q -d POWER
nvidia-smi -q | findstr "PState"  # Expect P8/P12 at idle, not P0/P2
```

If MUX switch available, suggest trying Optimus/hybrid mode temporarily to isolate if dGPU mode is compounding the issue.

### 4. Clamshell + external display + lid-close = "Do Nothing"

With lid-close set to "Do Nothing" (common for desktop-clamshell use), the system stays **fully awake** when lid is closed. Windows 11 25H2 Modern Standby changes (audio cut on explicit standby) don't apply since the system never enters standby. Primary cooling paths (keyboard deck) are blocked, turning the chassis into an oven.

If a media app (browser, Spotify, Netflix) with hardware acceleration is left open, the GPU stays at elevated clocks and the video decoder remains active. Combined with dGPU-only mode, this means 20-50W sustained in a sealed chassis.

**Mitigation:** No clean fix for desktop-clamshell users. Either:
- Ensure G-Helper is minimized to tray before leaving system idle
- Set a sleep timer after idle (system enters S0ix eventually)
- Or accept that clamshell + dGPU-only = needs active cooling path

### 5. RTX 50-series high idle power

Blackwell laptop GPUs (RTX 5070 Ti, 5080, 5090) have known high idle power issues — 30-40W at P0 with zero processes running. This is a GPU firmware/driver issue.

**Check:** NVIDIA Control Panel → Manage 3D Settings → Power management mode = "Adaptive" or "Optimal Power" (NOT "Prefer Maximum Performance").

### 6. PCIe ASPM disabled on AC blocks RTD3

On many G14s the power plan sets **Link State Power Management = Off on AC** (Max on DC is the ASUS default). RTD3 requires the PCIe link to reach L1; with ASPM off, the dGPU can never Runtime-D3 while plugged in — it sits at D0 with memory clocks pinned: ~19W / 50-55°C on a 5070 Ti, 0% util, no processes, no display. Symptom: dGPU "never sleeps" specifically on AC.

**Check:**
```powershell
powercfg /q SCHEME_CURRENT SUB_PCIEXPRESS
# "Link State Power Management": AC index 0x0 = Off, 0x2 = Maximum
```

**Fix:**
```powershell
powercfg /setacvalueindex SCHEME_CURRENT SUB_PCIEXPRESS ee12f906-d277-404b-b6da-e5fa1a576df5 2
powercfg /setactive SCHEME_CURRENT
```

Enabling ASPM is necessary but may not be sufficient — re-check PnP state after a few minutes of quiet (see playbook step 4), and a reboot re-trains the PCIe link so the change fully applies.

## Diagnostic commands

```powershell
# Last wake source
powercfg /lastwake

# Sleep study report (HTML — open in browser)
powercfg /sleepstudy /output sleepstudy.html

# Check supported sleep states
powercfg /a

# GPU processes, power, and P-state
nvidia-smi
nvidia-smi -q -d POWER

# Top CPU consumers
Get-Process | Sort-Object CPU -Desc | Select -First 10

# Processes blocking system sleep
powercfg /requests

# Active power plan
powercfg /getactivescheme

# Sleep/hibernate timers + power-plan provenance forensics (list/delete plans, hex timer decode,
# "who set this value" attribution via registry store) → references/power-plans-sleep-hibernate.md
powercfg /q SCHEME_CURRENT SUB_SLEEP

# Battery discharge rate
$b = Get-CimInstance -Namespace root\wmi -ClassName BatteryStatus
"{0:N1} W" -f ($b.DischargeRate / 1000)

# GPU PnP power state (run in loop — see root cause #1 above)

# PCIe ASPM — RTD3 prerequisite (see root cause #6)
powercfg /q SCHEME_CURRENT SUB_PCIEXPRESS

# Per-app GPU pinning — which GPU an app uses, and how to pin it (GpuPreference=1 = iGPU, 2 = dGPU)
# Full flow: which GPU renders, display binding, iGPU-lag diagnosis → references/hybrid-gpu-app-pinning.md
Get-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences'
nvidia-smi --query-gpu=display_mode,display_active --format=csv,noheader   # dGPU driving a display?

# Display binding per adapter (Card name + Current Mode lines)
dxdiag /t "$env:TEMP\dxdiag.txt"   # takes 30-60s; then read the file
```

## Missing NVIDIA display settings (G-Sync / aspect-ratio / scaling) on hybrid laptops

"None of the NVIDIA display settings exist" — NCP G-Sync page absent, "Adjust desktop size and position" (scaling/aspect) missing or grayed. This is topology, not a bug: in Standard (hybrid/Optimus) mode the iGPU physically owns every display (internal eDP + external ports); NCP only exposes display-management for panels wired DIRECTLY to the dGPU. NVIDIA: "Display-specific features available on discrete GPU (like NVIDIA G-SYNC, higher refresh rates) may not be available on the laptop display even though the discrete GPU can support them" (Advanced Optimus overview, nvidia.custhelp.com/a_id/5097).

One-probe diagnosis:
```powershell
nvidia-smi --query-gpu=display_active --format=csv,noheader   # Disabled ⇒ dGPU owns zero displays ⇒ everything is iGPU-driven
Get-CimInstance Win32_VideoController | fl Name,CurrentHorizontalResolution  # controllers reporting a res = the ones driving displays
```

Fix = MUX to dGPU-only: G-Helper GPU mode → Ultimate (enum from G-Helper source `app/AsusACPI.cs`: 0=Eco, 1=Standard, 2=Ultimate), restart. Internal panel G-Sync unlocks; external must sit on a dGPU-wired port — if it goes dark in Ultimate, move the cable (other USB-C / HDMI). Full walkthrough + citations → `references/display-topology-ncp-gsync.md`.

## GPU undervolting & overclocking (RTX 50 mobile)

The GA403's RTX 5070 Ti is a **110W Max-Q part** (85W + 25W Dynamic Boost), power-limited not clock-limited: vBIOS allows up to **120 W** PL (current cap 108 W, default 80 W), silicon max 3090 MHz core / 14001 MHz mem, real boost ~2167 MHz under the cap. Undervolting frees wattage → higher clocks at same power.

Two paths (full detail → `references/gpu-undervolt-oc.md`):
- **Afterburner curve** (daily): needs 4.6.6+ (Blackwell support), run as admin, +400~450 core offset, Ctrl+F → select ~900–950 mV → Shift+Enter flatten → Apply. Grayed "Unlock voltage control" checkbox is normal on laptops — doesn't block undervolt.
- **nvidia-smi (official, zero third-party)**: `-pl 120` (raise PL), `-lgc 0,3090` (clock cap) / `-lgc 3090,3090` (hard lock), `-rgc` (reset). Both reset on reboot → logon scheduled task. Hard lock = constant 30–40 W idle draw; use for gaming sessions only.

Laptop curve-editor pitfalls: admin rights required; hybrid laptops show 2 GPUs — select the NVIDIA one; padlock must be unlocked; curve points only move up/down, never left/right (normal). Recovery: nothing commits until Apply; Reset buttons; Safe Mode if unstable; delete `Profiles\*.cfg` / `MSIAfterburner.cfg` as nuclear option.

## Pitfalls

- **Don't guess.** Users reject "fugazi" reasoning — always back claims with actual GitHub issues, forum threads, or Microsoft docs before asserting a root cause. Research first, answer second.
- **Modern Standby (S0ix) ≠ S3 sleep.** Most modern laptops (all Zephyrus G14 2025+ with AMD Strix Point) don't support legacy S3. Don't recommend enabling S3 unless you verify firmware support exists.
- **G-Helper experimental fix has a trade-off:** When dGPU is D3/asleep, GPU temp reads return null and GPU fan falls back to CPU fan curve. This saves power but loses real-time GPU temp display.
- **ASUS ACPI GPU temp endpoint (0x00120097)** returns -65536 on 2025 G14 GA403 models — it's unreliable. Don't debug against it.
- **D3 ≠ asleep.** In NVIDIA's power model, D3 is a "balanced" low-power state, not deep sleep. P12 is the actual deepest idle. D3-gating helps but doesn't fully stop power draw.
- **dGPU-only mode is the worst case for clamshell thermals.** Without iGPU fallback, the dGPU can never power down to the base level that Optimus/hybrid enables.
- **nvidia-smi/NVAPI polling wakes the dGPU (self-interference).** Querying every 1-2s ramps clocks (observed: core 570→7094 MHz at 0% util from 2s polling). To distinguish "genuinely stuck awake" from "my probes keep it awake": run ONE query, then 90s–3min of absolute silence (no nvidia-smi, no PnP loops), then a SINGLE `DEVPKEY_Device_PowerData` read — PnP property reads are the least invasive.
- **DRS 3D-settings DB is obfuscated on r610+ drivers.** `C:\ProgramData\NVIDIA Corporation\Drs\nvdrsdb0.bin`/`nvdrsdb1.bin` hold per-app profiles (UTF-16 app names are readable) but global settings ("Power management mode") are encoded — not CLI-readable, the strings are a keyed cipher. Don't waste time decoding; verify via NVIDIA App → Manage 3D Settings → Global → Power management mode.
- **`GpuPreference=2` in `HKCU\Software\Microsoft\DirectX\UserGpuPreferences` pins an app to the dGPU.** Wallpaper engines (Sucrose etc.) and other always-on tools commonly get set to High Performance — check this when "nothing is using the GPU" but it stays awake.
- **`GpuPreference=1` pins an app to the iGPU** (power-saving). Set the app's FULL exe path as the value name, data `GpuPreference=1;` — read at process start, so relaunch the app. Use when the user wants an app OFF the dGPU or complains it lags on the iGPU (diagnosis flow in `references/hybrid-gpu-app-pinning.md`).
- **Signature tells:** "Prefer Maximum Performance" pins CORE clocks high; a mem-clock-pinned + core-idling (570 MHz) + 0% util signature points more at a wake-hold (ASPM off, DDS/Advanced Optimus readiness, periodic NVAPI poke) than at max-perf. Check both.
- **WSL interop: PS registry provider returns null `LastWriteTime` on HKLM power-scheme keys** ("cannot call a method on a null-valued expression") even though `Test-Path` is True and `reg.exe query` reads values fine. Use `reg.exe query` for values; for key timestamps use regedit ("Modified" in status bar). Don't re-probe with different PS provider variants — it stays null.

## Reference files

- `references/known-issues-catalog.md` — Curated table of upstream GitHub issues, ASUS forum threads, NVIDIA dev forum reports, and Windows Latest articles with dates, model numbers, and symptoms. Check before debugging from scratch.
- `references/dgpu-idle-diagnosis-playbook.md` — Ordered end-to-end procedure for "dGPU won't sleep" cases: baseline snapshot, display binding, GPU-pinning registry, ASPM fix, quiet-period test (self-interference avoidance), DRS limits, external-display waker test.
- `references/hybrid-gpu-app-pinning.md` — Which GPU an app renders on, pinning apps to iGPU/dGPU via `UserGpuPreferences`, and the "app lags on the iGPU" diagnosis flow (worked example: Playnite on Radeon iGPU at 4K/165Hz).
- `references/power-plans-sleep-hibernate.md` — Plan list/delete, SUB_SLEEP timer read/write with GUIDs and hex decode, Modern Standby hibernate-after caveat, and registry provenance forensics ("who set this value").
- `references/display-topology-ncp-gsync.md` — Why NVIDIA display settings (G-Sync page, scaling/aspect-ratio) are missing on hybrid laptops: probe sequence (nvidia-smi display_active, Win32_VideoController, monitor PNP decode, G-Helper gpu_mode enum), MUX fix, `optimized_usbc` misconception, citations.
- `references/gpu-undervolt-oc.md` — RTX 5070 Ti mobile undervolt/OC: verified vBIOS numbers (PL 80/108/120 W, max clocks 3090/14001 MHz), Afterburner 4.6.6 curve method, nvidia-smi -pl/-lgc official path, curve-editor troubleshooting, curve restore/recovery.