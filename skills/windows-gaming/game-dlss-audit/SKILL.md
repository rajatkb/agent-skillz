---
name: game-dlss-audit
description: Audit installed games across Windows drives for DLSS DLL versions (super resolution / frame gen / ray reconstruction) from WSL — enumerate game dirs, scan nvngx_dlss*.dll, map versions to DLSS generations, and report per game.
triggers:
  - user asks which games have DLSS 4 / 4.5 or what DLSS versions their games ship
  - user wants to audit or upgrade DLSS DLLs across their library
  - user asks to check frame gen / upscaler support in installed games
---

# Game DLSS Audit (from WSL)

## What the DLLs are
- `nvngx_dlss.dll` = DLSS Super Resolution (the scaler)
- `nvngx_dlssg.dll` = DLSS Frame Generation
- `nvngx_dlssd.dll` = DLSS Ray Reconstruction

Version → generation map and ground-truth tracker URLs: `references/dlss-version-map.md`.
Key threshold: **≥310.5.0 = DLSS 4.5** (Jan 2026+); 310.0–310.4 = DLSS 4; 3.x = DLSS 3/3.5; 2.x = DLSS 2.

## Steps
1. **Enumerate game dirs.** Steam: parse `appmanifest_*.acf` in each `SteamLibrary\steamapps` for `appid`/`name`, then list `steamapps\common\` for actual folder names (they differ from manifest names — e.g. manifest "Avatar: Frontiers of Pandora" → folder `AFOP`). Repacks sit at drive root (InsaneRamZes-style dirs). Check `C:\Program Files (x86)\Steam`, `XboxGames`, etc. Note: **Playnite's `games.db` may not be SQLite** in newer versions (library `database.json` = `{"Version":4}`; sqlite3 open fails) — fall back to manual enumeration instead of fighting the DB.
2. **Write a PS1 script file** (see `scripts/dlss-scan.ps1`; per windows-software-management, never inline `-Command`), copy to Windows, run:
   `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\RAJAT\Downloads\dlss-scan.ps1"`
   Native NTFS recursion is far faster than WSL 9p for deep game trees.
3. **Scan each root recursively** for `nvngx_dlss*.dll`, read `.VersionInfo.FileVersion` (renders dotted, e.g. `310,6,0,0` → 310.6.0.0).
4. **Report per game** SR + FG + RR independently, mapped to generation.

## Pitfalls
- **`bakup/` / `backup/` subfolders hold pre-swap originals** (repacks ship 310.x swapped in, 3.x originals saved aside). Report the active path, not the backup — or note both.
- **Mixed kits are common**: one game can have SR 3.1.30 + FG 310.1.0 (Black Myth Wukong). Check each DLL independently, don't infer from one.
- **No FG DLL ≠ broken** — some games load FG via Streamline (`sl.dlss_g.dll`); check `Engine\Plugins\...\Streamline` dirs. KCD2 had no FG DLL at all (its FG path is unavailable; a DLL swap won't add it if the engine doesn't load one).
- **No DLSS DLL ≠ no upscaler** — game may use FSR (`amd_fidelityfx_*.dll`) instead.
- Some titles (Dead Space 2023) ship DLSS 2.x with no FG — engine predates FG; swapping won't add it.
- TechPowerUp tracker pages are the version↔date ground truth. When `web_extract` is unavailable (search-only backend), `curl -sL <url> | python3` with a regex HTML-strip pipeline works fine (see reference for the pattern).

## Script
`scripts/dlss-scan.ps1` — parameterized scanner (`-Roots` array). Copy to Windows side and run with `-File` as above; update the root list to match current drive layout.

## Drive layout (Aug 2026 baseline)
- **D:** repacks (007 First Light, Black Myth Wukong, Death Stranding 2, Forza Horizon 6, Halo Campaign Evolved, KCD2, PRAGMATA, TLoU Part II) + Steam (Dead Space 2023, Avatar FoP)
- **F:** repacks (Cyberpunk 2077, Dying Light The Beast, Ghost of Tsushima, GoW Ragnarök, Horizon Forbidden West, RDR, Resident Evil Requiem, STALKER 2) + Steam (Dead Cells, Helldivers 2, INSIDE)
- **C:** no games (Steam redistributables only) · **E:** empty
