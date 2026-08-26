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

Script lives at `~/.hermes/scripts/dlss_manager.py` (also mirrored in this skill's `scripts/` dir). Companion helper `dlss_rr.cs` (same mirror; C# source) is the Windows-side runtime for `rr-preset`: compiled once with the built-in .NET Framework compiler to `C:\Users\<user>\.hermes\dlss-rr\dlss_rr.exe` — no Python or PowerShell on Windows:
`"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /out:dlss_rr.exe dlss_rr.cs` (C# 5 — no local functions). Sync rule: after editing, `cp` the script to the skill's `scripts/` AND recompile the exe at the deploy path.

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
  --components <dll1,dll2>   filter by DLL FILENAME (nvngx_dlss.dll / nvngx_dlssg.dll /
                    nvngx_dlssd.dll) — NOT sr/fg/rr. Passing "sr" matches nothing and
                    update silently no-ops while printing "Update complete" (bit us Aug 2026)
  --mirror N         TPU server_id (default 15 = SG)
```

Examples:
```bash
# upgrade everything to latest
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame update
# pin a specific version (COMMAND BEFORE FLAGS — see pitfall below)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/f/Game update --version 310.5.0
# check what's old
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame status
# roll back (originals are never deleted)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame undo
# apply DLSSTweaks next to the game EXE (legit Nexus zip; see DLSSTweaks section)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-install --tweak-zip /mnt/c/Users/<user>/Downloads/DLSSTweaks-550-0-310-5-0-1767931303.zip
# remove DLSSTweaks (DLSS DLLs + backups untouched)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-remove
# apply a researched per-game config profile (agent researches; script applies)
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-config --profile /tmp/profile.json
# toggle the DLSS debug HUD overlay (0 off/default, 1 on, 2 alt draw, -1 force off)
# — draws SR/FG/RR rows bottom-left; RR row present = Ray Reconstruction active
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame tweak-hud 1
# set the DRIVER-LEVEL DLSS RR preset override (per-game, NvAPI DRS — same mechanism
# as DLSS Swapper / NVIDIA App). F = the DLSS 4.5 RR model; D = DLSS 4-era — many
# games default to D despite 4.5 DLLs (Halo, Pragmata do). Needs the 310.5+ RR DLL and
# the compiled C# helper (dlss_rr.exe, built from dlss_rr.cs with built-in csc.exe —
# see header note; no Python/PowerShell on Windows).
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame rr-preset F
python3 ~/.hermes/scripts/dlss_manager.py /mnt/d/SomeGame rr-preset default   # remove override
# status also prints the current OverrideDlssHud value AND the RR preset override
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

**Perf ladder (learned Aug 2026, Dead Space 2023 on 5070 Ti):** DLSS 4.5's 2nd-gen presets (L/M) cost noticeably more FPS than DLSS 4's 1st-gen preset K — a user running 310.7.0 reported a "massive" drop at Performance mode vs the old CNN DLL. Downgrade ladder when FPS regresses: **310.5.0+/4.5 (L/M, heaviest) → 310.2.x/4 (K, lighter, community-verified great in most titles) → 3.7.x CNN (lightest but blurrier era)**. When pinning to a 310.2.x DLSS 4 DLL, the DLSSTweaks preset profile MUST switch to K (L/M are 4.5-only and will misbehave/fall back on older DLLs). Pin via `--version 310.2.1`; every swap keeps immutable backups so all three tiers stay one `undo` or re-pin away.

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
- **`USERPROFILE` can be unset in WSL** (observed on this box Aug 2026) — the old code fell back to `C:\Users\Public`, the PS1 helper write failed silently (`except: pass`), PowerShell never found the file, and EVERY version read came back `0.0.0.0` (symptom: `status`/`discover` shows all-zero Current). Fixed: `_resolve_win_userprofile()` asks `cmd.exe /c echo %USERPROFILE%`, then derives from the WSL home, and the write failure now logs a warning. If all-zero versions ever reappear, check the helper at `%USERPROFILE%\AppData\Local\Temp\dlss_getver.ps1` exists and the write isn't being swallowed.
- **argparse arg order: COMMAND BEFORE FLAGS** — `dlss_manager.py <root> --version 310.4.0 update` dies with `unrecognized arguments: update`; `dlss_manager.py <root> update --version 310.4.0` works (observed Aug 2026 on NFS Unbound). Put the command positional right after the game root, flags after it. The older examples showing `--version X.Y.Z update` are wrong — command first.
- **`status` on a game with no `DLSSManager/dlss.json` yet shows `0.0.0.0` for Current** — run `discover` once first to write state, then `status`. (Missing-state artifact, distinct from the USERPROFILE bug below; both look like all-zero versions.)
- **Don't pipe `update` output through `head`/`less`** — SIGPIPE can kill the process mid-download (observed Aug 2026: SR applied, FG download truncated). `update` is idempotent (`already at X — skip`), so just re-run without the pipe to complete cleanly.
- **PowerShell stdout can carry banner lines** ("Windows PowerShell / Copyright (C) Microsoft...") that poison naive `splitlines()[-1]` version reads — `read_dll_version` now scans reversed lines for a `^\d+([,.]\d+)+$` match instead of trusting the last line (fixed Aug 2026; see `references/dead-space-2023.md` for the run where this bit us). **Root cause**: when the `-File <script>` path is missing/stale (e.g. temp cleanup), PowerShell falls back to interactive mode and prints the banner. Verify the PS1 exists before invoking; recreate from `_VER_PS1_TEMPLATE` on demand.
- **Transient `0.0.0.0` version reads are benign** — the temp-extraction read (`DLSSManager/stash/.tmp_*.dll`) can race or return 0.0.0.0 while the final applied file verifies fine via direct PowerShell. The script warns and applies anyway (TPU zip naming is authoritative); confirm with a direct `VersionInfo.FileVersion` read of the applied DLL rather than trusting the WARNING line.
- **PE version strings use commas** (`310,2,1,0`) — normalize to dots before writing JSON.
- **Version compare as int tuples, compare first 3 components** — `310.7.0.0` vs `310.7.0` differ in length.
- **Don't mutate dicts while iterating** (undo pops from `applied`) — iterate `list(applied.keys())`.
- WSL→NTFS BOM: state JSON written as utf-8 no-BOM, read as `utf-8-sig`.
- Version reads of uninstalled/repack dirs can return `0.0.0.0` — the script warns but applies anyway (TPU zip naming is authoritative).
- TPU `status` "Latest" column: fetch is retried 3×, then `<title>` fallback, then a hard fail with an HTML dump — a `?` should never appear silently anymore (see "Scraping break" above).

## DLSSTweaks — zip-based install (security-validated)

**Security**: the GitHub org `DLSSTweaks/.github` "latest release" (ver.4.0.6, mid-2026) is an **impersonator** — its zip is a mod-manager bundle (obfuscated JS task-broker, encrypted pack.bin, RPCS3 test ELFs, MSI with no wrapper DLLs). The legitimate tool is emoose's, distributed only via [Nexus Mods site/mods/550](https://www.nexusmods.com/site/mods/550). The user has the legit zip downloaded: `C:\Users\<user>\Downloads\DLSSTweaks-550-0-310-5-0-1767931303.zip` (Nexus build 0.310.5.0, DLSS 4.5 presets L/M support).

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
2. **Per-game preset lookups: quick `web_search` FIRST** — user correction (Aug 2026, Halo + Pragmata sessions): the slow NPU crawler gets killed when it drags, so single-game preset questions ("which SR/RR preset for game X") = 2–3 targeted `web_search` queries + curl-with-browser-UA fetches of the top articles (gamegpu.com 403s to urllib — `-A "Mozilla/5.0 ... Chrome/126..."` works). This produced sourced verdicts fast (Halo RR E, Pragmata SR K + RR E). Reserve `research.py research` for genuinely deep multi-source dives ONLY (10–35 min NPU; if the user aborts it, salvage `03_notes/` + `02_pages/` from the crawl session).
3. **403 pitfall**: gamegpu.com, overclock3d.net, techspot.com return 403 to `web_extract`/urllib. Fallbacks that work: (a) research.py's crawl4ai (real browser), (b) curl with a full browser UA (`-A "Mozilla/5.0 ... Chrome/126..."` + Accept/Accept-Language headers). Both verified fetching gamegpu + OC3D this session.
4. Known source patterns: **gamegpu.com per-game DLSS 4-vs-4.5 comparisons** (often the single best per-title source — preset-by-preset FPS + image-quality verdicts), PCGamingWiki (per-game DLSS implementation details), TechSpot/DF preset articles, NoobFeed preset L-vs-M numbers, dlsstools.com (DLSSTweaks mechanics), Nexus per-game mod pages (often state a recommended preset, e.g. Halo "Ultra Plus" mod says M), Steam/Reddit per-game threads.
5. **No per-game findings → use the 4K default profile** (below) and set `"source": "default-4k"`. The crawler's research confirmed there is NO official per-game DLSSTweaks config table — resolution-level guidance is the best available default.
6. **Record per-game findings** in `references/` (e.g. `references/halo-campaign-evolved.md`) with source URLs — reuses the research instead of re-crawling next session.

**4K default profile (researched baseline, RTX 5070 Ti friendly):**
- At 4K, Quality (67%) is the quality sweet spot; Performance (50%) loses almost no texture quality at 4K (TechSpot); Ultra Perf (33%) is viable only for max-FPS.
- Preset L = best image quality, 3–6% slower than M (NoobFeed, tested on 5070 Ti); M tuned for Performance mode; L is the 2nd-gen transformer tuned for Ultra Performance.
- Default profile: presets L for DLAA/UltraQuality/Quality/Balanced/UltraPerformance, M for Performance; scaling left at DLSS defaults unless the game research says otherwise; ForceDLAA=false.
- **LAPTOP CAVEAT (user-verified Aug 2026, G14 5070 Ti + 4K OLED):** on laptops the L/M 2nd-gen penalty is worse than desktop tests suggest (laptop power/thermal ceilings + 4K output widen the transformer gap; NotebookCheck measured 3–45% game-dependent M penalties even on RTX 50). If a game regresses badly on 4.5 L/M, fall back to **DLSS 4 (310.2.x) + preset K** — much lighter, community-verified great in most titles. Full research: `references/dead-space-2023.md`, crawler session `why-is-dlss-4-5-preset-l-m-2nd-gen-transformer-slower-with-b`.

## Verifying a DLSS feature is actually ACTIVE (loaded ≠ enabled)

Presence of a DLL — or a dlsstweaks.log hook line — does NOT mean the feature runs. `nvngx_dlssd.dll` (RR) in particular gets **preloaded at NGX init and hooked by DLSSTweaks even when the game never creates the RR feature** (verified on Halo Campaign Evolved, Aug 2026: RR DLL loaded + hooked, zero RT in any config, no RT option in the game's settings schema → RR inert). Loaded ≠ created.

Evidence ladder, cheapest → definitive:

1. **`dlss_manager.py status`** — versions + DLSSTweaks install state.
2. **dlsstweaks.ini `[DLSSPresets]`** — preset per quality level.
3. **dlsstweaks.log** — which modules loaded/hooked (init evidence ONLY, not feature creation).
4. **The game's ACTUAL video settings.** For UE games with custom settings classes the real keys live in `%LOCALAPPDATA%\<Project>\Saved\Config\invalid_id\<Game>LocalGameUserSettings.ini` (e.g. `Upscaler=DLSS`, `UpscalingQuality=Low`, `bFrameGeneration=True`), NOT in `Windows/GameUserSettings.ini` (that holds only generic UE keys — resolution, vsync, scalability groups). The `invalid_id` dir is the device-id-miss config slot — check it FIRST. A missing feature key (e.g. no RT toggle at all in the settings schema) = that feature cannot be enabled, period.
5. **Grep all shipped configs** (`*.ini`/`*.cfg`/`*.json`) for the feature name (`RayTracing|RayReconstruction|NVSDK|NGX|DLSS`). Zero hits outside dlsstweaks.ini = no RT path wired in shipped defaults.
6. **Runtime proof** (needs user OK — one ini edit + game relaunch): set `VerboseLogging = true` in dlsstweaks.ini → log records every `NVSDK_NGX_D3D12_CreateFeature` call (feature type = definitive). Or `OverrideDlssHud = 1` → on-screen overlay bottom-left lists active features (`DLSS SR` / `DLSS FG` / `DLSS RR` rows; `= 2` if it doesn't draw). This is the ONLY fully definitive answer on stripped/repack installs. **HUD toggle is script-managed since Aug 2026: `dlss_manager.py <root> tweak-hud <0|1|2|-1>`** (backups the ini, records history, `status` prints the current value). `VerboseLogging` is NOT script-managed — edit dlsstweaks.ini directly. Neither belongs in `tweak-config`'s profile schema (presets/scaling/ForceDLAA/Sharpening only).

Pitfalls:
- The game's `Saved\Logs\*.log` may be a Gauntlet automation session (near-empty), not gameplay — check content before trusting it.
- **Streamline tell:** `SwapChainProvider=FStreamlineD3D12DXGISwapchainProvider` in GameUserSettings.ini + `sl.dlss_g.dll` / `sl.reflex.dll` / `nvngx_dlssg.dll` in a StreamlineCore dir = FG/Reflex via Streamline; SR may still be direct NGX (no `sl.dlss.dll` present → SR is direct). Hybrid stacks are common — check each feature's path independently.
- Repack/stripped installs: engine defaults live inside `.pak` files — static analysis can't see compiled config; only the runtime-proof step (6) settles it.

### Per-game Engine.ini changes — apply + recovery record (user-requested discipline, Aug 2026)

UE user cvars live in `%LOCALAPPDATA%\<Project>\Saved\Config\Windows\Engine.ini` — **game-specific** (the `<Project>` folder belongs to that one game only; other titles untouched; each UE game has its own). Workflow the user requires for any Engine.ini change (same discipline as DLL backups):

1. **Write the file** — create if missing; plain ASCII comments; after WSL writes verify no BOM (`head -c 8 <file> | od -An -c`).
2. **Record in the game's `DLSSManager/`** — copy applied ini to `DLSSManager/backups/engine-ini/<ts>_<desc>.ini`, and write `DLSSManager/<NAME>-RECOVERY.md` (e.g. `ENGINE-INI-RECOVERY.md`) covering: what changed + sources, live path, created-from-scratch vs modified (vanilla = file absent for repacks that never shipped one), restore steps (`attrib -R` → delete-or-restore-backup → `attrib +R`), and a cross-reference that DLSS DLL/preset state is separate (`undo` / `tweak-config`).
3. **Set Read-only** or the game overwrites it on next launch: `powershell.exe -NoProfile -Command "attrib +R '<win-path>'"`; confirm `attrib` shows `A R`.
4. **Verify after the user launches** — `md5sum` live file vs the backup + confirm `R` still set; unchanged = game is respecting the file.

**User preference (Aug 2026): recurring toggles get SCRIPTED as dlss_manager.py subcommands** — the `tweak-hud` pattern: one command, ini backed up, history in dlss.json, `status` readout, zero token-heavy hand-edits ("use more of the script and less tokens"). When a recurring knob comes up, add a subcommand in the same backup→apply→history→status shape instead of editing inis ad hoc. Implemented examples: `tweak-hud` (ini) and `rr-preset` (driver-level RR preset override — full mechanism + helper layout in `references/ray-reconstruction-presets.md`).

## Related

- Full game-DLSS inventory scans: run `status` per game, or a manual `find` for `nvngx_dlss*.dll` + PowerShell `VersionInfo.FileVersion` across drives (PS1-from-WSL: invoke via `powershell.exe -NoProfile -Command`).
- DLSS 4K quality-mode/preset guidance + default profile: `references/dlss-4k-settings-research.md`.
- Ray Reconstruction (DLSS-D) presets — D/E/F letter system, **4.5 RR model = Preset F** (D = DLSS 4-era; a 4.5 DLL can still run the old D model, verified on Halo Aug 2026), DLSSTweaks CANNOT override RR presets (SR-only), forcing F via DLSS Swapper / OptiScaler / NVIDIA App: `references/ray-reconstruction-presets.md`. **PITFALL (Aug 2026): the preset value alone can be silently ignored — companion enable flag `0x10E41E02` = 1 is required** (Halo's HUD stayed at D until the flag was set); `status` read-back proves the DRS value, NOT runtime — verify with `tweak-hud 1`.
- Per-game researched findings (Halo Campaign Evolved — M-preset consensus, 6x MFG via NVIDIA App, RR enable via Engine.ini `r.NGX.DLSS.denoisermode=1` + denoiser kills, clarity block incl. `r.MegaLights.DownsampleFactor=1` + forced-on film grain/CA removal, dev-locked cvar caveat, Read-only Engine.ini mechanics): `references/halo-campaign-evolved.md`.
- Dead Space (2023) — Streamline game, ships DLSS 2.5.0, community blur-fix = DLL swap; ended on DLSS 4 (310.2.1) + preset K after 4.5 L/M cost too much FPS: `references/dead-space-2023.md`.
- NFS Unbound — shipped DLSS 3.7.20/3.7.10 (CNN, no RR DLL), upgraded to DLSS 4 310.4.0 with immutable backups: `references/nfs-unbound.md`.
- PRAGMATA — shipped DLSS 4 (310.3.0); community verdict: **SR preset K beats 4.5 L/M** (gamegpu) and **RR E fixes the default-D noise**; ended on 310.7.129 + K + RR E: `references/pragmata.md`.
