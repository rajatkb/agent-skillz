---
name: dlss-manager
description: Update a game's DLSS DLLs (super resolution, frame gen, ray reconstruction) to the latest TechPowerUp version from a single game root dir, with immutable backups and undo. Also knows the DLSS version↔generation mapping and how to verify game DLSS status.
triggers:
  - user wants to update/upgrade DLSS DLLs in games
  - user asks which DLSS version a game has or whether it's DLSS 4/4.5
  - user wants to pin a specific DLSS DLL version in a game
  - user wants to undo a DLSS DLL swap
---

# DLSS Manager

One script, pure Python 3 stdlib, run from WSL against `/mnt/d` / `/mnt/f` game roots. Uses `powershell.exe` only to read DLL file versions; uses `curl` for all HTTP (see pitfall below).

Script lives at `~/.hermes/scripts/dlss_manager.py` (also mirrored in this skill's `scripts/` dir).

## Usage

```bash
python3 ~/.hermes/scripts/dlss_manager.py <game_root> [command] [flags]

commands (default = update):
  discover      scan for nvngx_dlss*.dll, write DLSSManager/dlss.json — no downloads
  update        fetch latest (or pinned) DLLs from TechPowerUp → backup → apply
  status        show discovered/applied vs latest available
  undo          restore newest backup per DLL (backups NEVER deleted)

flags:
  --version X.Y.Z    pin target version (default: latest on TechPowerUp)
  --components sr,fg,rr
  --mirror N         TPU server_id (default 15 = SG)
```

Examples:
```bash
# upgrade everything to latest
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame update
# pin a specific version
python3 ~/.hermes/scripts/dlss_manager.py /mnt/f/Game --version 310.5.0 update
# check what's old
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame status
# roll back (originals are never deleted)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame undo
# apply DLSSTweaks next to the game EXE (legit Nexus zip; see DLSSTweaks section)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-install --tweak-zip /mnt/c/Users/RAJAT/Downloads/DLSSTweaks-550-0-310-5-0-1767931303.zip
# remove DLSSTweaks (DLSS DLLs + backups untouched)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-remove
# apply a researched per-game config profile (agent researches; script applies)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-config --profile /tmp/profile.json
```

## What it does

1. **Discover** — recursive scan for `nvngx_dlss.dll` (SR), `nvngx_dlssg.dll` (FG), `nvngx_dlssd.dll` (RR). Skips `DLSSManager/` and stash dirs (`bakup`, `backup`, `_crack`, `_original files`, `old`, `_extras`, …) so repack leftovers are never touched.
2. **Fetch** — TechPowerUp pages: `nvidia-dlss-dll`, `nvidia-dlss-3-frame-generation-dll`, `nvidia-dlss-3-ray-reconstruction-dll`. Parses newest version id, POSTs `id`+`server_id`, follows the 302 to the direct zip, caches in `DLSSManager/stash/`.
3. **Backup** — originals copied to `DLSSManager/backups/<dll>/<ts>_<ver>.dll`, content-hash deduped, immutable (never overwritten/deleted).
4. **Apply** — extracts the matching DLL over the discovered path, PowerShell-verifies the applied version.
5. **State** — `DLSSManager/dlss.json` records discovered paths/versions, applied state, history. Paths stored relative to game root (survives drive-letter changes).

## DLSS version ↔ generation mapping

| DLL version | DLSS generation |
|---|---|
| 2.x | DLSS 2 (SR only, no FG) |
| 3.0–3.4 | DLSS 3 (CNN) |
| 3.5.x | DLSS 3.5 (Ray Reconstruction era) |
| 3.7.x | DLSS 3.7 |
| 310.0–310.4 | DLSS 4 (1st-gen transformer, MFG) |
| **310.5.0+** | **DLSS 4.5** (2nd-gen transformer, 6x/Dynamic MFG) — released Jan 6, 2026; 310.6.0 added Dynamic MFG (Mar 31, 2026) |

Presets in DLSS 4.5: **K** = 1st-gen transformer (Quality/Balanced/DLAA default), **M** = 2nd-gen tuned for Performance, **L** = 2nd-gen tuned for Ultra Performance (recommended for UHD). Ultra Performance = 33.3% render scale (720p internal @ 4K).

Verify latest versions: https://www.techpowerup.com/download/nvidia-dlss-dll/ (SR), `.../nvidia-dlss-3-frame-generation-dll/` (FG), `.../nvidia-dlss-3-ray-reconstruction-dll/` (RR).

## Scraping break — detection, acknowledgment, fix (act immediately)

TechPowerUp has no version API — "latest" is parsed from their HTML page. If their markup changes, `status` shows `?` or `update` dies with `Could not parse versions from ...`. The script handles this in 3 tiers:

1. **Retry** — page fetch is retried 3× with backoff before giving up (handles transient 403/5xx/conn drops). You'll see `(fetch <dll> attempt N/3 failed: ...)` lines.
2. **Fallback** — if the heading parser finds zero pairs, it falls back to pairing the `<title>` version (the title always carries the latest) with the first form `id`. Logs `used <title> fallback`.
3. **Fail loud with evidence** — if both fail, the script dumps the raw HTML to `<game_root>/DLSSManager/tpu_parse_fail_<dll>.html`, prints the dump path + FIX pointer, and exits non-zero. It never silently returns `[]`.

**When you see the fail message — do this now:**

```bash
# 1. Look at what TPU changed (dump is already on disk):
read_file <game_root>/DLSSManager/tpu_parse_fail_nvngx_dlss.dll.html
#    check: do <h1-6> headings still contain the version? do
#    <input type="hidden" name="id" value="N"> forms still exist?

# 2. Update the parse logic in tpu_versions() in ~/.hermes/scripts/dlss_manager.py
#    (primary regex + <title> fallback). Patch the skill's scripts/ copy too:
cp ~/.hermes/scripts/dlss_manager.py ~/.hermes/skills/windows-gaming/dlss-manager/scripts/dlss_manager.py

# 3. Verify against live TPU + a synthetic HTML harness, then re-run:
python3 ~/.hermes/scripts/dlss_manager.py <game_root> status
```

No cache hides the break: `status`/`update` always re-fetch the live page. If a new TPU structure is non-trivial, update the "Pitfalls" section below with the new markup before moving on.

- **urllib gets 403 from TechPowerUp** (TLS fingerprinting); `curl` works. The script shells out to `curl` — do not "fix" it back to urllib.
- **Never `curl -L` the POST** — TPU's file server returns 405 for re-POSTed redirects. Capture `%{redirect_url}` without `-L`, then GET it.
- **PowerShell can't read Linux `/tmp`** — temp extraction for version verification goes into the game's `DLSSManager/stash/`, not `/tmp`. Inline `powershell.exe -Command` mangles `$env:` refs from WSL; use the script-file (`-File`) pattern (see `read_dll_version`).
- **PE version strings use commas** (`310,2,1,0`) — normalize to dots before writing JSON.
- **Version compare as int tuples, compare first 3 components** — `310.7.0.0` vs `310.7.0` differ in length.
- **Don't mutate dicts while iterating** (undo pops from `applied`) — iterate `list(applied.keys())`.
- WSL→NTFS BOM: state JSON written as utf-8 no-BOM, read as `utf-8-sig`.
- Version reads of uninstalled/repack dirs can return `0.0.0.0` — the script warns but applies anyway (TPU zip naming is authoritative).
- TPU `status` "Latest" column: fetch is retried 3×, then `<title>` fallback, then a hard fail with an HTML dump — a `?` should never appear silently anymore (see "Scraping break" above).

## DLSSTweaks — zip-based install (security-validated)

**Security**: the GitHub org `DLSSTweaks/.github` "latest release" (ver.4.0.6, mid-2026) is an **impersonator** — its zip is a mod-manager bundle (obfuscated JS task-broker, encrypted pack.bin, RPCS3 test ELFs, MSI with no wrapper DLLs). The legitimate tool is emoose's, distributed only via [Nexus Mods site/mods/550](https://www.nexusmods.com/site/mods/550). The user has the legit zip downloaded: `C:\Users\RAJAT\Downloads\DLSSTweaks-550-0-310-5-0-1767931303.zip` (Nexus build 0.310.5.0, DLSS 4.5 presets L/M support).

**How it works (per Nexus docs)**: the zip extracts **next to the game's main EXE** (UE games: `*-Win64-Shipping.exe`). `dxgi.dll` is a wrapper that can be **renamed** to `dxgi.dll` / `winmm.dll` / `XInput1_3.dll` / `XInput1_4.dll` (best success rates). Only the `nvngx.dll` wrapping method needs the registry signature override (`EnableNvidiaSigOverride.reg`) — we never use that method, so no registry changes. A `dlsstweaks.log` appearing next to the EXE confirms it loaded. Uninstall = remove wrapper + ini + config tool. The default `dlsstweaks.ini` applies **no tweaks** (ForceDLAA=false, presets=Default) — it's a hook you configure later via `DLSSTweaksConfig.exe` (presets L/M for DLSS 4.5).

The script's `tweak-install --tweak-zip <path>`:
1. Validates the zip contains `dxgi.dll` + `dlsstweaks.ini` + `DLSSTweaksConfig.exe` (rejects the impersonator bundle)
2. Finds the game EXE via `find_game_exe()` (normalized name match > UE `*-Win64-Shipping` > shallowest; excludes extras/bonus/crash-report shells)
3. Picks a wrapper name that **doesn't already exist** in the EXE dir (never clobbers a real `dxgi.dll`)
4. Caches the zip in `DLSSManager/stash/`, backs up any existing ini/config, installs next to the EXE
5. **Preserves pristine originals** (the unmodified wrapper/ini/config from the zip) under the game root at `DLSSManager/backups/dlsstweaks/pristine_<version>/` — same backup tree as the DLL originals, so the untouched tweak files are recoverable even after the live ini gets edited
6. Records state under `dlsstweaks` (wrapper, version, exe_dir)

`tweak-remove` removes wrapper + ini + config tool; DLSS DLLs, backups, and cached zip untouched.

### tweak-config — apply a researched profile JSON

The script itself does NO research — the AGENT researches per-game settings and hands the result to the script as a profile JSON:

```bash
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-config --profile /tmp/halo_profile.json
```

**Profile JSON schema** (validation: unknown keys/slots rejected, preset values must be A–M/Default, scaling ratios must be in (0,1]):

```json
{
  "dll_version": "310.7.0",
  "resolution": "4K",
  "source": "researched",
  "presets": {"DLAA": "L", "UltraQuality": "L", "Quality": "L", "Balanced": "L", "Performance": "M", "UltraPerformance": "L"},
  "scaling": {"Enable": true, "UltraPerformance": 0.333, "Performance": 0.5, "Balanced": 0.58, "Quality": 0.75, "UltraQuality": 0.8},
  "dlss": {"ForceDLAA": false, "OverrideSharpening": "Default"}
}
```
- `presets` → `[DLSSPresets]`, `scaling` → `[DLSSQualityLevels]`, `dlss` → `[DLSS]`
- Merge is line-preserving: comments and unrelated sections/keys survive (verified)
- Current ini is backed up to `DLSSManager/backups/dlsstweaks/<ts>_dlsstweaks.ini` before writing (immutable, same discipline as DLL backups)
- Requires DLSSTweaks installed first (`tweak-install`)

**Research procedure (agent side — this is the required workflow):**
1. Check the game's DLSS DLL version first (`status`); profile `dll_version` should match what's applied.
2. **LEAD with `research.py` for per-game preset research** — user correction (Aug 2026): multi-source research questions like "which DLSS preset for game X" must use the local research crawler, NOT ad-hoc web_search. Run `research.py research "<game> DLSS 4.5 preset recommendation ..."` (see local-web-crawler skill) and read `03_notes/` + `05_synthesis/findings.md` when done. Use plain `web_search` only for a quick single-source confirmation while the crawler runs.
3. **403 pitfall**: gamegpu.com, overclock3d.net, techspot.com return 403 to `web_extract`/urllib. Fallbacks that work: (a) research.py's crawl4ai (real browser), (b) curl with a full browser UA (`-A "Mozilla/5.0 ... Chrome/126..."` + Accept/Accept-Language headers). Both verified fetching gamegpu + OC3D this session.
4. Known source patterns: **gamegpu.com per-game DLSS 4-vs-4.5 comparisons** (often the single best per-title source — preset-by-preset FPS + image-quality verdicts), PCGamingWiki (per-game DLSS implementation details), TechSpot/DF preset articles, NoobFeed preset L-vs-M numbers, dlsstools.com (DLSSTweaks mechanics), Nexus per-game mod pages (often state a recommended preset, e.g. Halo "Ultra Plus" mod says M), Steam/Reddit per-game threads.
5. **No per-game findings → use the 4K default profile** (below) and set `"source": "default-4k"`. The crawler's research confirmed there is NO official per-game DLSSTweaks config table — resolution-level guidance is the best available default.
6. **Record per-game findings** in `references/` (e.g. `references/halo-campaign-evolved.md`) with source URLs — reuses the research instead of re-crawling next session.

**4K default profile (researched baseline, RTX 5070 Ti friendly):**
- At 4K, Quality (67%) is the quality sweet spot; Performance (50%) loses almost no texture quality at 4K (TechSpot); Ultra Perf (33%) is viable only for max-FPS.
- Preset L = best image quality, 3–6% slower than M (NoobFeed, tested on 5070 Ti); M tuned for Performance mode; L is the 2nd-gen transformer tuned for Ultra Performance.
- Default profile: presets L for DLAA/UltraQuality/Quality/Balanced/UltraPerformance, M for Performance; scaling left at DLSS defaults unless the game research says otherwise; ForceDLAA=false.

## Related

- Full game-DLSS inventory scans: run `status` per game, or a manual `find` for `nvngx_dlss*.dll` + PowerShell `VersionInfo.FileVersion` across drives (PS1-from-WSL: invoke via `powershell.exe -NoProfile -Command`).
- DLSS 4K quality-mode/preset guidance + default profile: `references/dlss-4k-settings-research.md`.
- Per-game researched findings (Halo Campaign Evolved — M-preset consensus, 6x MFG notes): `references/halo-campaign-evolved.md`.
