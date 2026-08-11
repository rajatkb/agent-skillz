# Known Issues Reference — ASUS ROG Power/Thermal

Curated catalog of upstream reports. Check these first before debugging from scratch.

## G-Helper Issues

| Issue | Date | Model | Summary |
|-------|------|-------|---------|
| [#5290](https://github.com/seerge/g-helper/issues/5290) | Apr 2026 | GU405AW (RTX 5080) | NVAPI `GetThermalSettings` polling wakes dGPU D3→D0 every 1-2s. Discharge 10W→35W. Dev confirmed, partial fix in experimental build. |
| [#5143](https://github.com/seerge/g-helper/issues/5143) | Mar 2026 | FX505DT (GTX 1650) | CPU spikes 7% every 3s after autostart. Opening window then closing to tray fixes it. |
| [#5422](https://github.com/seerge/g-helper/issues/5422) | May 2026 | GA403UI (G14 2025) | Stuck at 5-6% CPU after plugged→unplugged transition. |
| [#5171](https://github.com/seerge/g-helper/issues/5171) | Mar 2026 | G832LW | CPU 80-100°C with G-Helper, 55-85°C without it. User abandoned after ASUS warranty service. |
| [#4930](https://github.com/seerge/g-helper/issues/4930) | Jan 2026 | GA403WR (G14 2025, 5070 Ti) | Same model as user's. G-Helper stops respecting wattage/temp limits. Duplicate of #4901. |

## Windows 11 25H2 Modern Standby Changes

- [Windows Latest: "Microsoft quietly changed Windows 11 to stop playing audio when you close the lid"](https://www.windowslatest.com/2026/05/23/microsoft-quietly-changed-windows-11-to-stop-playing-audio-when-you-close-the-lid-or-press-sleep-and-its-due-to-modern-standby/) (May 2026)
  - Win11 24H2/25H2: audio stops on **explicit** standby entry (lid close, power button, Start → Sleep)
  - Audio continues on **idle-to-screen-off** (natural timeout)
  - Microsoft doc: "audio playback is not supported when standby is entered explicitly"
- [Windows Latest: "Modern Standby limits wake sources"](https://www.windowslatest.com/2026/02/10/microsoft-confirms-windows-11-no-longer-triggers-unexpected-wake-ups-or-battery-drain-due-to-modern-standby/) (Feb 2026)
  - Power button in clamshell mode engages input suppression → no display-on unless external monitor connected
  - Wake sources throttled when excessive drain detected

## ASUS Forum / Known Firmware Issues

- [2025 G14 GA403WR keyboard light flickers during standby](https://rog-forum.asus.com/t5/rog-zephyrus-series/2025-asus-zephyrus-g14-ga403wr-keyboard-light-flickers-every/td-p/1132514) (Dec 2025)
  - Disabling sleep lighting state removes a USB polling loop → S0ix reaches DRIPS cleanly
  - Shows the 2025 G14 has S0ix entry defects from USB device polling
- [Zephyrus G16 2024 overheating in Modern Standby screen-off state](https://rog-forum.asus.com/t5/rog-zephyrus-series/zephyrus-g16-2024-overheating-in-modern-standby-screen-off-state/td-p/1114375)
  - Locking the screen (Win+L) or letting display turn off → machine gets extremely hot
  - Parallel symptom to clamshell scenario

## NVIDIA / dGPU Issues

- [RTX 4090 Mobile stuck in P0 state (37W idle)](https://forums.developer.nvidia.com/t/rtx-4090-mobile-stuck-in-p0-state-37w-idle-with-no-active-processes/362287) (Mar 2026)
  - dGPU stuck at P0 with zero processes, 0% utilization, 0 MiB memory in use
  - Same pattern as user's 5070 Ti — NVIDIA driver/firmware issue across generations
- [RTX 5070 laptop high idle power (Linux)](https://forums.developer.nvidia.com/t/rtx-5070-laptop-high-idle-power-consumption/355638) (Dec 2025)
  - Dropping 30W+ idle, resolved by disabling dGPU in BIOS
- [RTX 5070 Ti desktop high idle (35-40W)](https://steamcommunity.com/discussions/forum/11/601906461957685327/) (May 2025)
  - Desktop 5070 Ti idles at 35-40W on a single display despite DDU, driver swaps, VBIOS changes
- [GPU stuck at max power state with multiple monitors](https://forums.developer.nvidia.com/t/gpu-is-stuck-to-maximum-power-state-at-idle-when-using-multiple-monitors/310924) (Oct 2024)
  - Certain monitor refresh rate combos prevent GPU clock ramp-down
- [NVIDIA RTX 5000 Series + Windows 11 24H2 temperature bug](https://windowsforum.com/threads/nvidia-rtx-5000-series-windows-11-24h2-the-hidden-gpu-temperature-bug-everyones-talking-about.361529/)
  - Known interaction between 50-series and 24H2/25H2
- [Mega thread: Black screen/freezing for RTX 5000 series](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/573244/mega-thread-for-black-screen-freezing-for-5000-seri/) (Aug 2025)
  - Includes ROG Zephyrus G14 GA403W / RTX 5060 as a reported model with BugcheckCode 275

## Known Patterns Summary

| Pattern | Likely on dGPU-only? | Likely on Optimus? |
|---------|---------------------|-------------------|
| G-Helper NVAPI → dGPU wake | **Yes — can't fully sleep anyway** | Yes — wakes from RTD3 |
| G-Helper CPU spike 6-7% | Yes | Yes |
| RTX 50-series P0 stuck idle | **Yes — always active** | Less likely (iGPU takes over) |
| Clamshell airflow restriction | **Worst case** | Same hardware constraint |
| Windows 25H2 Modern Standby | Less relevant (system stays on) | Relevant if using sleep |
