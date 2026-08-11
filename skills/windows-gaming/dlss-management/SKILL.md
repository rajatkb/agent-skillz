---
name: dlss-management
description: Scan installed games for DLSS DLLs, map DLL versions to DLSS generations (2/3/4/4.5), download latest DLSS DLLs from TechPowerUp, and set up DLSSTweaks wrapper for preset/scaling control.
triggers:
  - user wants to check or compare DLSS versions across installed games
  - user asks which games have DLSS 4.5 / latest frame gen or super resolution
  - user wants to update game DLSS DLLs to latest or pinned version
  - user wants DLSSTweak/DLSSTweaks applied to a game
  - user asks how DLSS 4.5 presets (K/M/L) or Ultra Performance work
---

# DLSS Management

Inventory, version mapping, updating, and tweaking DLSS across a game library (RTX 50-series friendly).

## 1. DLSS DLL inventory scan

Three DLLs per game, all matched by `nvngx_dlss*.dll`:
- `nvngx_dlss.dll` — Super Resolution (the scaler)
- `nvngx_dlssg.dll` — Frame Generation
- `nvngx_dlssd.dll` — Ray Reconstruction

Scan via a **PowerShell script file** (never inline `-Command` — WSL mangles `$env` / `$_`; see windows-software-management skill). Native NTFS recursion is far faster than WSL 9p. Pattern:

```powershell
$roots = @("D:\Game1", "D:\Game2")
foreach ($root in $roots) {
  Write-Output "=== $root"
  $dlls = Get-ChildItem -Path $root -Recurse -Filter "nvngx_dlss*.dll" -File -ErrorAction SilentlyContinue
  if (-not $dlls) { Write-Output "  (no DLSS DLLs)"; continue }
  foreach ($d in $dlls) {
    $v = $d.VersionInfo
    $rel = $d.FullName.Substring($root.Length).TrimStart('\')
    Write-Output ("  {0} | {1}" -f $rel, $v.FileVersion)
  }
}
```

Run: `cp /tmp/scan.ps1 /mnt/c/Users/RAJAT/Downloads/` then `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\RAJAT\Downloads\scan.ps1"`. FileVersion comes back comma-separated (`310,6,0,0`) — compare as numeric tuples, not strings. A `bakup/` or `backup/` subfolder in repacks holds pre-swap originals (older versions) — the active DLLs are the root-level ones.

## 2. Version → generation mapping

| DLL version | Generation |
|---|---|
| 2.x | DLSS 2 (SR only, no FG support) |
| 3.0–3.7.x | DLSS 3 / 3.5 (CNN model) |
| 310.0–310.4.x | DLSS 4 (1st-gen transformer, MFG) |
| **310.5.0+** | **DLSS 4.5** (2nd-gen transformer SR, 6x MFG; 310.6.0 = Dynamic MFG; 310.7.0 latest) |

Full dated timeline + preset system: `references/dlss-version-timeline.md`.

Preset cheat-sheet (DLSS 4.5 auto-selects): **K** = 1st-gen transformer (Quality/Balanced/DLAA), **M** = 2nd-gen (Performance), **L** = 2nd-gen (Ultra Performance, recommended for UHD). Ultra Performance = 33.3% render scale → 720p internal at 4K, 480p at 1440p. L/M presets need game DLL ≥ 310.5.0 (can be enabled via DLSSTweaks config).

## 3. Downloading latest DLLs from TechPowerUp (verified flow)

Pages:
- SR: `https://www.techpowerup.com/download/nvidia-dlss-dll/`
- FG: `https://www.techpowerup.com/download/nvidia-dlss-3-frame-generation-dll/`
- RR: `https://www.techpowerup.com/download/nvidia-dlss-3-ray-reconstruction-dll/`

Flow: GET page → parse the FIRST `<form class="download-version-form">` hidden `<input name="id">` (newest version) → POST `id=<id>&server_id=<n>` **without `-L`** → capture `redirect_url` header → plain GET that URL → zip (`nvngx_dlss_<ver>.zip`). **Pitfall: `curl -L` on the POST re-POSTs and the mirror returns 405.** Full recipe: `references/techpowerup-download-flow.md`.

## 4. DLSSTweaks setup (wrapper, no tweaks configured)

Purpose: drop the hook in place so the user can control presets/scaling later via DLSSTweaksConfig.exe. No tweak mods applied.

- **Get it**: latest release from `github.com/DLSSTweaks/.github` releases (e.g. ver.4.0.6, `DLSSTweaks.zip` ~128 MB). Note: `emoose/DLSSTweaks` GitHub repo is frozen at 0.200.8.0 — newer builds ship via Nexus Mods; the `.github` org release is the current one.
- **Install**: find the game EXE (UE titles: `GameName-Win64-Shipping.exe`; else best match to folder name). Copy wrapper DLL + `dlsstweaks.ini` + `DLSSTweaksConfig.exe` next to the EXE.
- **Wrapper filename**: pick the first free of `dxgi.dll, winmm.dll, XInput1_3.dll, XInput1_4.dll` — **never overwrite an existing dxgi.dll** (some games ship their own). The `nvngx.dll` wrapping method requires a registry signature override (`EnableNvidiaSigOverride.reg`) — avoid it unless the standard wrappers fail.
- **Verify**: `dlsstweaks.log` appears next to the EXE on successful load.
- **DLSS 4.5 presets L/M**: only available if the game's DLSS DLL is ≥ 310.5.0 — update the DLLs first.
- **Warning**: hooking is detected by anti-cheats — never apply to online/multiplayer titles.

## 5. Game library enumeration gotchas

- **Playnite**: `games.db` in the library folder is NOT SQLite in current versions (sqlite3 fails "file is not a database") — the library moved to JSON (`database.json` = `{"Version":4}`). Enumerate install directories directly instead of querying the DB.
- **Steam**: `steamapps/appmanifest_*.acf` files carry `"appid"` + `"name"` per game; `libraryfolders.vdf` maps drive → library. `steamapps/common/` folder names differ from display names (e.g. `AFOP` = Avatar: Frontiers of Pandora).
- **Repacks** (InsaneRamZes style on D:/F:): game files at repack root or in `Retail/`; may also contain `_crack/`, `_extras/`, `_original files/`.

## Planned tooling

`dlss_manager.py` (unified manager: point at game root → discover → write `DLSSManager/dlss.json` → fetch latest/pinned from TPU → immutable backup → apply → undo keeps backups forever → `tweak-install`/`tweak-remove` for DLSSTweaks). Plan reviewed with user; add to `scripts/` once built.

## References
- `references/dlss-version-timeline.md` — dated TechPowerUp version history, DLSS 4.5 facts, preset system
- `references/techpowerup-download-flow.md` — exact curl recipe + mirror ids + pitfalls
