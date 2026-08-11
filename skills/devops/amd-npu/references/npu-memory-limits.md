# NPU Memory / Shared Memory Limits (XDNA2)

## iGPU vs NPU: Critical Distinction

**The iGPU (Radeon 890M) and NPU (XDNA2) are completely separate hardware blocks with independent memory domains.** The iGPU's dedicated VRAM is for graphics frame buffer only and does not affect NPU model capacity.

| Component | Memory Type | Size (G14 GA403WR) | Used For |
|---|---|---|---|
| Radeon 890M (iGPU) | Dedicated VRAM | 284 MB (dxdiag) / 512 MB (WMI) | Graphics frame buffer, display output |
| XDNA2 NPU | Local tile SRAM | ~16 MB (32 tiles × 512 KB) | Streaming workspace — weights don't persist here |
| System RAM (NPU accessible) | DDR5 via UMA | 32 GB total, ~22 GB free | Where FLM model weights live |

**Key takeaway:** A model that "gets stuck" on the NPU is NOT hitting an iGPU VRAM limit. The NPU streams weights from system RAM (32 GB available). Stalls are more likely due to:
- Thermal/power throttling on battery
- NPU queue saturation (`--q-len` default is 10)
- Context length pushing KV cache
- Driver or firmware issues

## Checking Display/GPU Memory (from WSL)

### Quick check (WMI — less accurate for iGPU)

```bash
powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Where-Object { \$_.Name -like '*Radeon*' } | Select-Object Name, AdapterRAM"
```

WMI reports the BIOS pre-allocated buffer (512 MB on G14), not actual usable VRAM.

### Detailed check (dxdiag — authoritative)

```bash
powershell.exe -NoProfile -Command "
\$tmp = [System.IO.Path]::GetTempFileName() + '.txt'
Start-Process -NoNewWindow -Wait dxdiag -ArgumentList \"/t \$tmp\"
Start-Sleep -Seconds 2
\$content = Get-Content \$tmp -Raw
\$lines = \$content -split \"`r?`n\"
\$lines | Select-String 'Card name|Display Memory|Dedicated Memory|Shared Memory|890M|Radeon|5070' | ForEach-Object { \$_.Line.Trim() }
Remove-Item \$tmp -Force
"
```

Example output from G14 (Ryzen AI 9 HX 370 + RTX 5070 Ti):
```
Card name: NVIDIA GeForce RTX 5070 Ti Laptop GPU
Display Memory: 27876 MB
Dedicated Memory: 11944 MB
Shared Memory: 15932 MB
Card name: AMD Radeon(TM) 890M Graphics
Display Memory: 16216 MB
Dedicated Memory: 284 MB
Shared Memory: 15932 MB
```

Note: **Shared Memory** is the same pool (15,932 MB) for both GPUs — this is the system RAM aperture they can both draw from. The iGPU's 284 MB dedicated is a fixed BIOS carve-out; the remaining ~15.5 GB shared comes from system RAM on demand.

### NPU memory check (not directly exposed)

The NPU does not appear in `Win32_VideoController` or dxdiag Display tabs. Check NPU accessibility via FLM:

```bash
# FLM will load a model up to system RAM capacity
flm.exe validate
flm.exe serve qwen3.5:2b --host 0.0.0.0  # If this loads, NPU is fine
```

If FLM fails to load a model with a memory-related error, the issue is likely:
- System RAM exhaustion (check with `Get-CimInstance Win32_OperatingSystem`)
- NPU driver crash (check `flm.exe validate`)
- BIOS NPU UMA setting too low (G14: Advanced → AMD CBS → NPU Configuration)

## Background

AMD XDNA2 NPUs have **no dedicated VRAM**. The NPU exclusively uses system RAM via shared memory (UMA — Unified Memory Architecture). The amount of memory the NPU can access is limited by:

1. **BIOS setting** — ASUS G14 (and other laptops) may have an NPU UMA allocation in BIOS under Advanced → AMD CBS → NPU Configuration
2. **Windows driver allocation** — The `amdxdna` driver controls how much system RAM the NPU can carve out
3. **Windows Graphics Settings** — Windows 11 (24H2+) has NPU memory settings under Settings → System → Display → Graphics → Change default graphics settings
4. **WSL2 VM memory** — NOT an NPU limit, but often confused with it. WSL2's VM memory (`.wslconfig`) has nothing to do with NPU accessibility — the NPU runs on the Windows side

## Memory limit confusion (WSL2 vs NPU)

From WSL2, `free -h` shows ~3.3-3.8 GB available — this is the WSL2 VM allocation (configurable in `%UserProfile%\.wslconfig`). This is **not** the NPU's memory limit. FLM and the NPU run on the Windows host and can access all system RAM.

To check actual system RAM on Windows from WSL:
```bash
powershell.exe -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB"
powershell.exe -Command "Get-WmiObject Win32_PhysicalMemory | Select-Object @{N='GB';E={[math]::Round(\$_.Capacity/1GB,1)}}, Manufacturer, Speed"
```

## Checking NPU state

```bash
# NPU device status
powershell.exe -Command "Get-CimInstance Win32_PnPEntity | Where-Object { \$_.Name -match 'NPU' } | Select-Object Name, Status"

# NPU driver version
powershell.exe -Command "Get-WmiObject Win32_PnPSignedDriver | Where-Object { \$_.DeviceName -match 'NPU' } | Select-Object DeviceName, DriverVersion, DriverDate"

# FLM validation
flm.exe validate

# FLM running state
powershell.exe -Command "Get-Process flm" | Select-Object Id, ProcessName, @{N='WS_GB';E={[math]::Round(\$_.WorkingSet64/1GB,2)}}
```

## Investigating NPU memory allocation on Windows

The NPU driver (`amdxdna.sys`) is at PCI `VEN_1022&DEV_17F0` on Strix Point. The driver does not expose memory allocation values in standard registry locations:

- `HKLM:\SYSTEM\CurrentControlSet\Services\amdxdna*` — no NPU service key exposed
- `HKLM:\SYSTEM\CurrentControlSet\Control\Class\{d8b424ff-3679-4b7c-86f0-215a1c04e34c}\*` — the NPU device class GUID, but no memory settings exposed
- `HKLM:\HARDWARE\DEVICEMAP\VIDEO` — no NPU entry (only display GPUs)
- `HKLM:\SOFTWARE\AMD\*` — no NPU-specific settings in registry

The NPU memory limit is likely set at the **BIOS/firmware level** (UMA Frame Buffer Size for NPU) or via **Windows Graphics Settings** (System → Display → Graphics → Change default graphics settings → NPU memory slider) — not in Windows registry.

## WSL2 memory configuration (for reference)

Edit `%UserProfile%\.wslconfig` on Windows:
```ini
[wsl2]
memory=16GB
processors=8
```

Then restart WSL: `wsl.exe --shutdown` + reopen.

## System detection commands

```bash
# Total physical memory
powershell.exe -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB"

# Per-stick RAM info
powershell.exe -Command "Get-WmiObject Win32_PhysicalMemory | Select-Object @{N='GB';E={[math]::Round(\$_.Capacity/1GB,1)}}, Manufacturer, Speed, PartNumber"

# Motherboard + model
powershell.exe -Command "Get-WmiObject Win32_ComputerSystem | Select-Object Model, Manufacturer, TotalPhysicalMemory, SystemType"
```

## Known G14 (GA403WR) config

- **Model:** ROG Zephyrus G14 GA403WR
- **CPU:** Ryzen AI 9 (Strix Point / HX 370)
- **NPU:** XDNA2, driver 32.0.203.314 (Oct 2025)
- **RAM:** 32 GB DDR5-8000 (4× 8GB Samsung K3KL9L90DM-MGCU)
- **Windows usable:** ~31.1 GB (remainder hardware reserved)
