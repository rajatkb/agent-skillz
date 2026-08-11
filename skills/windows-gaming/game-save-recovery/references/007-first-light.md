# 007 First Light — save migration case (Goldberg voices38 → RUNE 1.1.0)

Worked example from Aug 2026: user updated InsaneRamZes repack 1.0.0 → 1.1.0; old saves stopped loading.

## Situation
- 1.0.0 repack shipped **Goldberg** emulator: `Retail/steam_api64.v38` (also `voices38.dll` in `_crack/Retail/`), config `Retail/steam_settings/configs.user.ini` → `account_name=voices38`, `account_steamid=76561197960285355`
- Saves (real progress) at `C:\Users\RAJAT\AppData\Roaming\GSE Saves\3768760\remote\`
- 1.1.0 repack shipped **RUNE** emulator: `Retail/steam_api64.rne` + `steam_emu.ini`, saves at `C:\Users\Public\Documents\Steam\RUNE\3768760\remote\`
- AppId for both: **3768760** (Steam). Internal save structure identical across emulators.

## Save file roles (this game)
| File | Role |
|---|---|
| `KntSlotSaveFile-0/data.save` (18 KB) | **the actual playthrough save** (bigger = more progress) |
| `KntSlotSaveFile-0/index.save` | slot metadata |
| `KntProfileSaveFile/data.save` (1.4 KB) | profile / slot registry — needed for the game to list the slot |
| `KntProfileSaveFile-BCK-0/-1/` | profile auto-backups (NOT needed to copy) |
| `LocalProfile/`, `SystemData/` | settings — game REGENERATES every launch; not save data |
| `filemappings.ini` (RUNE dir root) | emulator's cloud-path→local-file map, regenerated per launch |

Diagnostic detail: `index.save` files are unencrypted (readable byte patterns: format markers like `00 0f 10 01`, obfuscated strings) while `data.save` is encrypted. Old vs new index matching = same format → copy is legitimate; the failure was elsewhere (account ID).

## Root cause & fix
Saves are **hard-linked to the Steam Account ID**. RUNE's `steam_emu.ini` ships `#AccountId=0` commented → random ID per launch → game rejects saves bound to the old account.

```
AccountId = SteamID64 − 76561197960265728
76561197960285355 − 76561197960265728 = 19627
```

Fix (verified by community, gload.to/g4u.to comment "Bond" 2026-07-25):
1. Edit `Retail/steam_emu.ini`: `#AccountId=0` → `AccountId=19627` (uncomment)
2. Copy `GSE Saves\3768760\remote\*` → `Public\Documents\Steam\RUNE\3768760\remote\`
3. No save-transfer tool needed; user must re-set custom graphics/control settings (regenerated fresh)

Sources: gload.to/007-first-light-deluxe-edition-elamigos/ comment thread; nexusmods.com/007firstlight/mods/44 (EonaCat FirstLight SaveTransfer — exists but unnecessary for this migration); savegame.info/007-first-light (100% saves shipped for `GSE Saves\3768760` layout); fitgirl-repacks.site/007-first-light (v1.0.0→v1.1.0 patch info, RUNE note).

## Attempts that failed (why)
- Full copy of all remote files (including BCK backups + settings): game rewrote everything on next launch
- Copying under a running game: game overwrote the copied files
- Copying slot+profile only, correct emulator folder, no AccountId pin: game read the slot (filemappings regenerated with slot entry) but showed the small/fresh save — account binding rejected it
- Ludusavi backup folder existed but contained only `mapping.yaml` + `registry.reg` → never actually backed up
