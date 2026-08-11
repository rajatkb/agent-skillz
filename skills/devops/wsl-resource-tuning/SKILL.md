---
name: wsl-resource-tuning
description: Tune WSL2 memory/CPU/disk via .wslconfig — build OOM fixes, natural memory growth, autoMemoryReclaim, sparse VHDX conversion, and flags that are unsafe on this machine (Hermes TUI runs inside the VM)
tags: [wsl, wsl2, wslconfig, memory, oom, vhdx, sparse, debian]
---

# WSL2 Resource Tuning (.wslconfig)

Trigger when: npm/build processes get OOM-killed in WSL, user asks about WSL memory/CPU/disk, `.wslconfig` edits, growing `ext4.vhdx`, WSL startup/memory questions, or WSL audio/mic/GUI (WSLg) issues.

## Current machine state (Debian distro, Windows 11 25H2, 31GB host RAM)

`.wslconfig` lives at `C:\Users\RAJAT\.wslconfig` (WSL path `/mnt/c/Users/RAJAT/.wslconfig`). Working config as of Aug 2026:

```ini
[wsl2]
networkingMode=mirrored
memory=4GB
processors=2
swap=4GB
guiApplications=true   # was false (headless); true enables WSLg = GUI + audio

[experimental]
autoMemoryReclaim=gradual
```

The build-OOM root cause was `memory=2GB` + `swap=0` — hard cap with zero overflow. `autoMemoryReclaim=gradual` was already set and is NOT the blocker.

## WSLg GUI + audio (mic/speakers)

`guiApplications=false` **disables WSLg entirely** — no X11/Wayland, no `DISPLAY`, and NO audio in/out. WSL2 has no native sound drivers; WSLg IS the audio bridge (PulseAudio socket `/mnt/wslg/PulseServer`; endpoints `PulseAudioRDPSink` = out, `PulseAudioRDPSource` = in, i.e. the Windows mic). Flipped to `true` Aug 2026 to enable Hermes voice mode.

- **Diagnosis when audio/GUI is missing:** `/mnt/wslg/` containing only `run/user/`, empty `DISPLAY`/`WAYLAND_DISPLAY`, no `PulseServer` socket ⇒ check `.wslconfig` for `guiApplications=false`. A restart does NOT help — it's config-disabled by design. After enabling: `wsl --shutdown` (from PowerShell), reopen, then `ls /mnt/wslg/PulseServer` must exist; `PULSE_SERVER=unix:/mnt/wslg/PulseServer` + `DISPLAY` are set automatically.
- **Distro packages for mic capture:** `libportaudio2` (system PortAudio — `sounddevice` is just cffi bindings; without the lib it raises `OSError: PortAudio library not found`), `pulseaudio-utils` (pactl diagnostics), `libasound2-plugins` (ALSA→Pulse shim). Also enable Windows mic privacy permission for the terminal app (Settings → Privacy → Microphone) or capture stays silent.
- **WSLg overhead:** a Weston compositor runs in the background (~200–400MB inside the WSL memory cap). Headless workflows are unaffected; revert by flipping the one line back.
- **Never create `.bak` copies when editing `.wslconfig`** — user considers them clutter (Aug 2026 correction). It's a one-line diff; revert directly.

## Key concepts

- **`memory=` is a ceiling, not a reservation.** Idle WSL sits ~1GB regardless of cap. Default cap with no `memory=` line is 50% of host RAM (15.5GB on this 31GB box). Removing/raising the cap = "natural growth" — the VM grows on demand, never hogs when idle.
- **`swap=0` + low cap = OOM kills.** A swap file (e.g. `swap=4GB`) is the safety net — a spike swaps instead of killing the instance.
- **Fast reclaim = two mechanisms, both automatic:** (1) the balloon driver returns *unused committed* memory to Windows as the guest frees it (VMMEM shrinks); (2) `autoMemoryReclaim=gradual` (Win11 22H2+/WSL 0.69.2+) additionally drops Linux page cache slowly under Windows memory pressure. `dropCache` mode drops it all at once.
- **Builds also need CPU headroom:** 1 core starves Turbopack/webpack worker parallelism. Cores are free at idle; don't leave `processors=1` if builds are slow.

## Pitfalls

- **NEVER set `vmIdleTimeout`** (shuts the VM down after N ms idle). This machine runs Hermes TUI *inside* the WSL VM — an idle timeout kills the user's own sessions after ~60s of inactivity. Also kills background in-VM processes (e.g. the vault sync watcher). FLM is safe (runs Windows-side at `C:\Program Files\flm\flm.exe`), but Hermes isn't.
- **Honor the user's stated numbers.** When the user specifies values (e.g. "4GB 2core"), use exactly those. Suggesting an upgrade instead (6GB) got pushed back — propose alternatives in one line, don't substitute. The ceiling being free at idle is why his number works anyway.
- **`.wslconfig` is sensitive — never read or edit it unprompted.** The user blocked a plain read of it during the crawl4ai OOM debugging session (Aug 2026). Even a read-only `cat`/`ls` of the Windows-side file is off-limits without explicit permission. When a WSL memory problem surfaces, diagnose from inside the VM (`/proc/meminfo`, `free -h`) and ask before touching `.wslconfig` — the working config is documented above anyway.
- **Changes apply only after `wsl --shutdown`** (from PowerShell). Running it kills the current session — warn the user. `wsl --terminate <distro>` kills the distro only (still kills in-VM sessions).

## Sparse VHDX (disk, not RAM)

The distro filesystem is one `ext4.vhdx` that **grows but never shrinks** — deleted files inside WSL never return disk to C:.

- `sparseVhd=true` in `.wslconfig` only affects **newly created** VHDs. For an existing distro, convert in place (distro must be stopped):
  ```powershell
  wsl --shutdown
  wsl --manage Debian --set-sparse true
  ```
  Requires WSL ≥ 2.4.4 (present on this machine's 2.7.10 — verified via `wsl.exe --help`, which is the authoritative flag source; the raw MicrosoftDocs md files don't document `--set-sparse`).
- Backup insurance before converting: `wsl --export Debian D:\debian-pre-sparse.tar`.
- Sparse files materialize to full size when copied by non-sparse-aware tools — use `robocopy /SPARSE` or `wsl --export`/`--import` when moving them.
- Worth-it check: `ls -lh <vhdx>` vs `df -h /` — only the difference is reclaimable (this machine: 16G file vs 12G used → ~4GB now; ongoing benefit is the file stops growing forever).

## Verification one-liners

- `wsl.exe` CLI output is UTF-16 → always pipe through `tr -d '\0\r'`.
- Find the distro's vhdx (naive `Packages/*/LocalState` glob misses it — this machine stores it at `AppData\Local\wsl\{GUID}\ext4.vhdx`):
  ```bash
  BASE=$(reg.exe query "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Lxss" /s 2>/dev/null | tr -d '\0\r' | grep -i 'BasePath' | head -1 | sed 's/.*REG_SZ[[:space:]]*//')
  ls -lh "$(wslpath "$BASE")/ext4.vhdx"
  ```
- BOM check after writing `.wslconfig`/YAML from WSL to NTFS: `od -A x -t x1z -v <file> | head` — first byte must be `5b` (`[`), not `EF BB BF` (`xxd` is not installed on this machine; use `od`). If BOM present: `sed -i '1s/^\xEF\xBB\xBF//'`.
- Distro list: `wsl.exe -l -q | tr -d '\0'`.
