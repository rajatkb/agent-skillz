# DLSS Ray Reconstruction (DLSS-D) presets — versions, mechanics & control

## The preset letters

RR presets are **app-selected at feature creation** (separate letter space from SR's A–M). DLL version ≠ active model:

- **D** = DLSS 4-era RR model — the default most older integrations request
- **E/F** = newer models; **F = the DLSS 4.5 RR model** (310.5+)
  - gamegpu (Doom, 310.7.128): "the updated noise reduction and ray-tracing model appears under the designation **Preset F**" — https://en.gamegpu.com/news/igry/novyj-algoritm-ray-reconstruction-4-5-proverili-v-shutere-doom-the-dark-ages
  - YouTube DLSS4-vs-4.5 RR comparison: "DLSS 4 RR = Preset D and DLSS 4.5 RR = Preset F" — https://www.youtube.com/watch?v=Ua49BvNMDOQ
- **Symptom that matters (Halo Campaign Evolved, Aug 2026):** DLL = 310.7.0 (4.5) but HUD showed "DLSS RR - D" → the 4.5 DLL is installed but the OLD RR model is active. Force preset F to actually get 4.5's RR.

## Three independent levers (version vs preset — don't conflate)

| Lever | Mechanism | Where it lives |
|---|---|---|
| Explicit DLL version | file swap of `nvngx_dlssd.dll` into game folder | game files (dlss_manager.py's domain) |
| "Always latest" model | driver profile setting, RR `0x00FFFFFF` · SR `0x00FFFFFF` · **FG `0x00FFFFFE`** (per dlss-swapper source fallback lists — RR is NOT FFFE) | driver (NVIDIA App / DLSS Swapper) |
| Preset letter | driver profile setting **`0x10E41DF7`** (RR), values A=`0x01` … F=`0x06` | driver (NVIDIA App / DLSS Swapper / our script) |

SR = `0x10E41DF3`, FG = `0x10E41DF1` (same pattern). DLSS Swapper's source has other IDs **commented out** (i.e. it does NOT write them): RR_OVERRIDE_ID `0x10E41E02`, RR_MODE_ID `0x10BD9423`, RR scaling-ratio override `0x10C7D4A2`.

## DLSSTweaks CANNOT override RR presets

Verified on 0.310.5.0 (Aug 2026): no RR preset section in `dlsstweaks.ini` (`[DLSSPresets]` is SR-only), no RR-preset strings in `DLSSTweaksConfig.exe`. Its preset overrides cover Super Resolution only. The DLSS HUD (`tweak-hud`) shows the RR row + preset but cannot change it.

## Tools that CAN force the RR preset

| Tool | How | Caveats |
|---|---|---|
| **DLSS Swapper** v1.2.2.0+ (beeradmoore) | RR preset selection in-app (Dec 2025); 4.5 RR files added with **Preset F enableable via a small config edit** (videocardz, Aug 2026) | **GUI-only — no CLI/API, cannot be scripted from WSL**; writes the GLOBAL profile (see below); known issue: presets reset (NVIDIA App / some games) |
| **OptiScaler** | "Supports DLSS-D (Ray Reconstruction) on Nvidia cards... changing presets" + on-the-fly INSERT menu (Features.md) | Wants the `dxgi.dll` slot — conflicts with DLSSTweaks (rename one to `winmm.dll`); per-game vendor-lock quirks |
| **NVIDIA App DLSS Override** | Per-game RR model override (early 2026) | Documented conflicts: RR overrides can disable SR preset overrides |

## DLSS Swapper mechanics (from source, beeradmoore/dlss-swapper cloned Aug 2026)

- **Version control = plain DLL file swap**: reads the downloaded DLL's `VersionInfo`, signature-verifies, copies over the game's `nvngx_dlssd.dll`. Identical to dlss_manager.py's `update` (just its own library vs TPU).
- **Preset/latest control = driver profile write**: `DriverSettingsSession.CurrentGlobalProfile.SetSetting(NGX_DLSS_RR_OVERRIDE_RENDER_PRESET_SELECTION_ID, preset)` + `Save()` (`NVAPIHelper.cs`). It writes the **GLOBAL profile — not per-game** (the per-game dropdown is UI state only). Global RR preset F would affect every RR game on the system.
- **Repacks / non-Steam games work** — README: "Manually added via the `Add Game` button"; launcher auto-detect (Steam/Epic/GOG/Xbox/Battle.net) is convenience only.
- **"Always use latest"** is a dropdown value (`0x00FFFFFF` RR/SR, `0x00FFFFFE` FG), not a separate toggle.

## IMPLEMENTED: dlss_manager.py `rr-preset` subcommand (built + verified Aug 2026)

`dlss_manager.py <root> rr-preset <A-F|latest|default>` — writes the driver-profile override `0x10E41DF7` **per-game** (driver profile keyed to the game exe; NOT the global profile like DLSS Swapper). `status` prints the current override; `rr-preset default` = remove the setting (driver falls back to the game's request). Previous value recorded in dlss.json history. Applied to Halo Campaign Evolved 2026-08-24 (set to F, read-back verified `0x00000006`).

**Implementation = C# console app compiled with the built-in .NET Framework compiler** (dlss_rr.cs → dlss_rr.exe, ~10KB, no installs, C# 5 compatible). nvapi64.dll exports are ordinal-only except `nvapi_QueryInterface`; every NVAPI function is resolved by its interface hash via `nvapi_QueryInterface` (hashes from NvAPIWrapper.Net 0.8.1.101 `FunctionId` enum). Struct layouts mirror NvAPIWrapper exactly: DRSSettingV1=12320B, DRSApplicationV4=20492B (NOT 20488 — count the fields!), DRSProfileV1=4116B, version field = `(major << 16) | struct_size`, UnicodeString fields = 2048 wchars, DRSSettingValue = 4100B with the u32 at offset 0.

- Dependency: **none** — user rule: no Windows Python, no PowerShell scripts. Compile: `"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /out:dlss_rr.exe dlss_rr.cs` (csc.exe ships with .NET Framework on every Windows box). Source `dlss_rr.cs` is versioned in the skill (`scripts/dlss_rr.cs`, mirrored to `~/.hermes/scripts/`); the compiled exe deploys to `C:\Users\<user>\.hermes\dlss-rr\dlss_rr.exe`.
- Calls used: `nvapi_QueryInterface(hash)` → `NvAPI_Initialize` → `NvAPI_DRS_CreateSession` → `LoadSettings` → `FindApplicationByName` (per-game profile) or `CreateProfile`+`CreateApplication` → `GetSetting`/`SetSetting`/`DeleteProfileSetting` → `SaveSettings` → `DestroySession`. Emits one machine-readable line `RR=0xXXXXXXXX` or `RR=unset` (a deleted setting reads back as value 0 → reported as unset).
- Value map in script: D=`0x04` … F=`0x06`, latest=`0xFFFFFF`, default=`0x00` (→ unset/delete).
- Requires `nvapi64.dll` present (System32 — this box: driver 32.0.16.1074). Non-admin OK (ProgramData DRS store is user-writable; DLSS Swapper runs unprivileged too).
- WSL invocation pitfall: `dlss_manager.py` must exec the helper via the WSL path (`/mnt/c/Users/<user>/.hermes/dlss-rr/py/python.exe`) while passing the script path as a Windows path (the helper python.exe opens it).

**Argparse pitfall (bit us Aug 2026):** two `nargs="?"` positionals where one is `type=int` collide — `rr-preset f` fed 'f' into the int-typed `hud_value` → `error: argument hud_value: invalid int value: 'f'`. Fix: declare both positionals `nargs="*"` (no type) and convert per-command in the dispatch (`int(...)` for tweak-hud, string for rr-preset).

**NuGet fetch gotchas:** flat-container package ID is `nvapiwrapper.net` (lowercase) — bare `nvapiwrapper` 404s `BlobNotFound`; `index.json` carries a UTF-8 BOM → decode `utf-8-sig`; `unzip` is not installed on this WSL box → extract the nupkg with `python3 -m zipfile` (it's a zip).

Caveats stated to the user (and true): driver updates / NVIDIA App can clear overrides (documented industry-wide); override only matters where the game creates an RR feature.

## ⚠️ CRITICAL: the enable flag — preset-only override can be silently IGNORED (Halo, Aug 2026)

`rr-preset f` alone did NOT take effect on Halo: DRS read-back showed `0x00000006` but the in-game HUD still read "DLSS RR - D". The fix was ALSO setting the companion **enable flag `0x10E41E02` = 1** on the same profile — the `NGX_DLSS_RR_OVERRIDE_ID` that DLSS Swapper's source leaves commented out. With both set, the HUD flipped to F. Treat the two settings as a PAIR for games that pass an explicit RR preset at feature creation.

- **Symptom:** `status` prints `RR preset (driver override): F` but the HUD shows D → enable flag missing.
- **Verification gap (important):** `status`/`rr_override_read` proves the DRS value only, NOT the runtime effect. The DLSS HUD (`tweak-hud 1`) is the runtime proof — always verify with the HUD after changing the RR preset.
- **Predefined-profile discovery:** the driver ships its own profile for shipped games ("Halo: Campaign Evolved", `predefined=True`). `FindApplicationByName(exe)` matched it, so the per-game `CreateProfile` path never ran — our writes landed in the driver's own profile (correct behavior).
- **RESOLVED (Aug 2026):** `dlss_rr.py` set/unset handles BOTH IDs as a pair — `set` writes `0x10E41DF7` + enable `0x10E41E02=1`; `unset` deletes both. The old PowerShell gap (preset-only, silently ignored) no longer exists.

## Sources

- DLSS Swapper source: https://github.com/beeradmoore/dlss-swapper (`src/Helpers/NVAPIHelper.cs`, `src/Data/Game.cs`, `src/Assets/dlss_d_presets.json`)
- NvAPIWrapper source: https://github.com/falahati/NvAPIWrapper (`NvAPIWrapper/Native/DRS/Structures/*`, `Delegates/DRS.cs`) — authoritative C# struct layouts for DRS
- https://videocardz.com/newz/dlss-swapper-adds-dlss-4-5-ray-reconstruction-files-preset-f-can-be-enabled-manually
- https://videocardz.com/newz/dlss-swapper-v1-2-2-0-adds-ray-reconstruction-presets-next-version-to-focus-on-fsr4-and-ray-regeneration
- https://github.com/optiscaler/OptiScaler/blob/master/Features.md
- https://www.reddit.com/r/nvidia/comments/1q5ih2k/ray_reconstruction_disables_preset_lm_regardless/
