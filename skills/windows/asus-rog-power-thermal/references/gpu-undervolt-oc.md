# GPU Undervolting & Overclocking — RTX 5070 Ti Mobile (G14 GA403)

## Hardware reality (verified via nvidia-smi, driver 610.74)

- The GA403's 5070 Ti is a **110W Max-Q part** (85W base + 25W Dynamic Boost) — NOT the 175W mobile variant. ASUS spec: Turbo = 2217 MHz (2167 MHz boost + 50 MHz OC). (Sources: ASUS India store spec sheet, rog.asus.com 2025 G14 page)
- Live nvidia-smi numbers from the user's machine:
  - Power limit: current 108 W (Turbo cap), default 80 W, **vBIOS max 120 W** → +12 W headroom is free
  - Max Clocks: core **3090 MHz**, memory **14001 MHz** (28 Gbps GDDR7) — never reached, power-limited
  - Idle signature: 480 MHz / 57 °C / ~14 W (dGPU stuck awake — see main SKILL.md)
- **Key insight: the GPU is power-limited, not clock-limited.** Under the ~108 W cap it holds ~2167 MHz while the curve wants 3090 MHz. Undervolting frees wattage → higher sustained clocks inside the same envelope. This is the "more perf at same watts" case, not just the "cooler" case.
- Read these from WSL: `/mnt/c/Windows/System32/nvidia-smi.exe -q -d POWER` / `-q -d CLOCK` / `-h` (read-only; -lgc/-pl flags confirmed present on Windows builds).

## Method A — Afterburner curve undervolt (recommended daily driver)

1. **Version must be 4.6.6+** — RTX 50 (Blackwell) support only landed in 4.6.6 betas (Feb 2025) / stable (Sep 2025). Older versions misbehave on Blackwell.
2. **Run as Administrator** (curve/voltage features restricted without elevation).
3. Settings → General → try "Unlock voltage control/monitoring" — **grayed out is normal on laptops**, NVIDIA locks voltage raise on mobile vBIOS since the 10-series. Does NOT block undervolting.
4. Raise core offset to **+400 to +450 MHz** first (shifts whole curve up = headroom to flatten higher).
5. Ctrl+F curve editor → click point at **~900–950 mV** → Shift-click to select everything beyond → **Shift+Enter twice** to flatten → main window Apply.
6. Points only move **up/down (clock), never left/right (voltage)** — that's correct behavior, not a bug.
7. Test: 3DMark Steel Nomad (free) + heavy RTX games. Unstable → drop 25–30 MHz or +25 mV. Expect ~2500–2700 MHz @ 900–950 mV vs stock ~2167 @ ~1.0 V+.
8. Memory OC +1000 to +2000: GDDR7 has error-correction that **silently rolls back perf instead of crashing** — benchmark before/after each step.
9. Save profile; "Apply overclocking at system startup" + "Start with Windows". Curve below target voltage untouched → idle still downclocks to 480 MHz (no battery/heat penalty).

## Method B — NVIDIA-official tools (nvidia-smi, zero third-party)

- Peak wattage: `nvidia-smi -pl 120` (108 → 120 W vBIOS max; verify `nvidia-smi -q -d POWER`)
- Clock cap (idle still downclocks): `nvidia-smi -lgc 0,3090`; hard lock (benchmarks only): `nvidia-smi -lgc 3090,3090`
- Reset: `nvidia-smi -rgc`; power back to default: `nvidia-smi -pl 80`
- **Both -pl and -lgc reset on reboot/driver reload** → logon scheduled task (admin) to re-apply: `nvidia-smi -pl 120 && nvidia-smi -lgc 0,3090`
- Official UI toggle: NVIDIA Control Panel → Power management mode → "Prefer Maximum Performance"
- Concept source: NVIDIA dev blog "SetStablePowerState" (uses -lgc for clock locking).

## Curve editor "not unlocking" checklist (laptop)

1. "Unlock voltage control" grayed → normal, ignore (see Method A step 3).
2. Editor won't open / grayed → run as Admin; verify 4.6.6+; **wrong GPU selected** (G14 has Radeon iGPU + NVIDIA dGPU — dropdown top-left, hybrid laptops show 2 GPUs / 2 graphs); bottom-left **padlock icon** must be unlocked.
3. Fallback if Afterburner curve won't work at all → nvidia-smi -lgc (Method B), no curve editor needed.

## Curve restore / recovery

- **Nothing is committed until Apply** — close editor without Apply = changes discarded. Biggest safety net.
- Stable + want stock: Reset button (circular arrow) in curve editor (bottom-right) or on main window, then Apply.
- Applied + crashing: Settings → uncheck "Apply overclocking at system startup"; if unreachable, boot Safe Mode (Afterburner doesn't run/apply), reset, reboot. Nuclear: delete `Profiles\` folder (per-GPU .cfg files) or `MSIAfterburner.cfg` in install dir (usually `C:\Program Files (x86)\MSI Afterburner\`).
- Keep profile slot 1 = tuned, slot 2 = stock — one click undo.

## Caveats

- 120 W is a hard vBIOS cap; no software exceeds it. Mobile Blackwell overvolting is locked (desktop 5080/5090 "unlocked voltage" is VRM-controller-specific, N/A to laptops).
- Hard clock lock = constant 30–40 W idle draw + heat/fan noise on the 14" chassis (dGPU already idles at 57 °C). Use hard lock only during gaming/bench sessions; daily = curve undervolt.
- Full method walkthrough sourced from: esportstales.com 5070 Ti undervolt guide, MSI blog "RTX 5070/5060 Ti OC+UV guide", VideoCardz (4.6.6 release), Tom's Hardware (Blackwell voltage lock).
