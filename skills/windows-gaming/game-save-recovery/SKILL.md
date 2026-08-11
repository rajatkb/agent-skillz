---
name: game-save-recovery
description: Recover and migrate game save files when saves stop loading — crack emulator switches (Goldberg→RUNE), Steam Account ID binding mismatches, overwritten saves, unknown save paths on repacked games (InsaneRamZes, FitGirl, RUNE, Goldberg/GSE).
---

# Game Save Recovery

## When to use
- Saves "not loading" / "not being used" after a game update, repack reinstall, or crack swap
- Game updated from vX to vY and old progress is missing
- Need to find where a game stores its saves
- Saves show up but load fails, or the game shows a fresh/empty save instead of the old one

## Core concept: the emulator owns the save path
Cracked Steam games route saves through a Steam-emulator DLL in the game folder. The emulator decides the save root:
- **Goldberg (GSE Saves)**: `%APPDATA%\GSE Saves\<AppId>\remote\` — config in `steam_settings/configs.user.ini` (`account_name`, `account_steamid`); DLL often named `steam_api64.v38`, `voices38.dll`
- **RUNE**: `C:\Users\Public\Documents\Steam\RUNE\<AppId>\remote\` — config in `Retail\steam_emu.ini`; DLL `steam_api64.rne`
- **Legit Steam**: `<SteamLibrary>\userdata\<AccountId>\<AppId>\remote\`

An update/repack silently switching emulators is the #1 cause of "lost" saves — the files are untouched, the game just looks in a different root. The internal save layout is usually identical across emulators, so files copy straight across.

## Canonical location spec
Ludusavi's manifest is the authoritative per-game save-path spec:
`%APPDATA%\ludusavi\manifest.yaml` (also `...\hydralauncher\ludusavi\manifest-*.yaml`). Grep the game name — it lists per-store paths (Steam userdata layout, Epic layout, slot file names) and registry keys. Use it to sweep drives for every copy of the saves.

## THE #1 gotcha: saves are hard-linked to the Steam Account ID
Many games embed the Steam account ID inside save containers and silently reject/overwrite saves from a different account.
- Old account's SteamID: `Retail/steam_settings/configs.user.ini` → `account_steamid=76561197960285355`
- **AccountId = SteamID64 − 76561197960265728** (e.g. 76561197960285355 → 19627)
- RUNE's `steam_emu.ini` ships with `#AccountId=0` COMMENTED = random account ID per launch → old saves always rejected. Copying files alone will NEVER fix this.
- FIX: uncomment and pin `AccountId=<old AccountId>` in `steam_emu.ini`, then copy the old saves into the new emulator's `remote\` folder.

## The mechanism: save files are XOR-encrypted with the SteamID64
IO Interactive/KNT-engine games (007 First Light is the confirmed case) **XOR-encrypt every save file with the SteamID64 as an 8-byte little-endian repeating key**:
- `data.save` = zlib-compressed payload, then XOR'd with the key
- `index.save` = XOR'd with the key (decrypts to readable `SSaveGameHeader` + field names)
- The game decrypts with whatever account ID the emulator presents; wrong key → zlib fails → **"save data is corrupt"**.
- Detect the key cheaply: `index.save` hexdump shows the account ID as repeated key bytes (e.g. `ab 4c 00 00 01 10 00 01` = 0x0110000100004CAB = SteamID64 76561197960285355). Or brute-force: XOR first bytes with candidate key, look for `SSaveGameHeader`, then zlib-decompress.
- Decrypted `index.save` headers have the SAME format markers across 1.0.0/1.1.0 → format is compatible; the problem is the KEY, not the version.

## The "corrupt" error after pinning AccountId = mixed keys
After pinning `AccountId`, the game starts writing files with the NEW key — but files it wrote BEFORE the pin (during the random-ID era: `systemdata`, `localprofile`, `*-BCK-*`) still carry the OLD key. Folder with mixed keys → game reports corrupt even though slot+profile decrypt fine. Fix: **resign EVERY file in the folder** to the target SteamID64, not just the copied saves.

## Resigning (the community fix for account-bound saves)
Tool: `github.com/Dxian998/007-First-Light-Save-Tools` → `resign_save.py` (source of the Nexus "007 Save Resigner" mod 33 and "SaveTransfer" mod 44; the AccountId=19627 trick is documented in gload.to/g4u.to comment sections + Reddit r/PiratedGames).
```
cd <new>/remote/ && python3 resign_save.py resign <TargetSteamID64> -y
```
It walks the dir, brute-forces each container's source key, and re-encrypts `index.save` + `data.save` to the target. It auto-creates `Backup/` dirs per container — remove them after (user dislikes clutter; originals are safe in the old emulator folder).

## Verification — always decrypt-test after resign/copy
Ground truth = direct zlib test, not the tool's log:
```python
import struct, zlib
kb = struct.pack("<Q", TARGET_SID)
dec = bytes(c ^ kb[i%8] for i,c in enumerate(open(f,"rb").read()))
zlib.decompress(dec)  # succeeds → correctly keyed
```
Pitfall: `resign_save.py`'s brute-force/verify helpers prefer reading from the `Backup/` subdir it creates → after resign, re-verification on a folder WITH Backup dirs reports stale keys and false "MISMATCH!". Always test the live files directly (and delete Backup dirs before trusting any verification).

## Workflow
1. Identify emulator + save root for BOTH versions (game dir: `steam_api64.*` files, `steam_emu.ini`, `steam_settings/`, `_crack/` leftovers)
2. Locate old saves (GSE Saves / RUNE / userdata) — real progress correlates with bigger `data.save` sizes
3. Check account binding; pin `AccountId` in `steam_emu.ini` if the emulator changed
4. **List the save files first, then copy only those** (user preference: surgical copy). Save data = slot saves + profile (e.g. `KntSlotSaveFile-0`, `KntProfileSaveFile`). NOT save data = `LocalProfile`, `SystemData` (settings, regenerated every launch), `*-BCK-*` (auto-backups)
5. Verify copy sizes match the source; confirm game is CLOSED (`tasklist.exe | grep -i <exe>`); launch and check both "Continue" AND "Load Game"
6. Still failing? Search the community BEFORE more local iteration — cs.rin.ru, gload.to/g4u.to comment sections, Nexus Mods, FitGirl repack page, Steam discussions. Save-migration fixes and dedicated tools are usually already documented there.

## Pitfalls
- **NEVER swap exe or crack DLLs between versions** — the other crack set (e.g. `_crack/` folder) is often the OLDER game version. Fix config, not binaries. (Explicit user rule.)
- Copying saves while the game is running = the game overwrites them (verify with tasklist first)
- `filemappings.ini` in the RUNE save dir is regenerated by the emulator per launch; the game only sees paths listed there. It usually self-heals after a launch, but a missing slot mapping hides the save
- Games rewrite settings files every launch — size changes there are NORMAL, not data loss
- `index.save` files are often unencrypted/parseable while `data.save` is encrypted — comparing index formats across versions tells you if the save FORMAT is even compatible
- A "backup" folder containing only `mapping.yaml` + `registry.reg` (Ludusavi) with no data files = configured but never ran; it is NOT a backup

## References
- `references/007-first-light.md` — full worked case: Goldberg voices38 → RUNE 1.1.0, AccountId 19627, save file roles, community sources
- `references/007-first-light-resign.md` — the XOR/SteamID64 save encryption format, the resign tool workflow, and the "corrupt = mixed keys" failure mode with exact commands
