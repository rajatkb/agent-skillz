# Worked example: 007 First Light 1.0.0 → 1.1.0 (Goldberg → RUNE)

Session: Aug 2026. User updated InsaneRamZes repack from 1.0.0 to 1.1.0; saves not picked up. User said "previous user probably voice38".

## Diagnosis

- Game dir: `/mnt/d/007.First.Light-InsaneRamZes` (Retail/, _crack/, _original files/, _extras/)
- Retail/ contained BOTH cracks:
  - `steam_api64.rne` (2026-08-05) — RUNE crack, active in 1.1.0
  - `steam_api64.v38` (2026-06-10) — Goldberg crack ("v38" = voices38 account), used by 1.0.0
  - `steam_settings/configs.user.ini` → `account_name=voices38` (the "voice38" the user remembered)
  - `steam_emu.ini` header → `Game data is stored at %SystemDrive%\Users\Public\Documents\Steam\RUNE\3768760`
- AppId: **3768760** (Steam AppId for 007 First Light)

## Save roots

| Version | Emulator | Save root |
|---|---|---|
| 1.0.0 | Goldberg | `C:\Users\RAJAT\AppData\Roaming\GSE Saves\3768760\remote\` |
| 1.1.0 | RUNE | `C:\Users\Public\Documents\Steam\RUNE\3768760\remote\` |

## Save file layout (game engine "KNT" structure, identical in both)

- `KntProfileSaveFile/` (+ `-BCK-0`, `-BCK-1` backups) — profile: `data.save` + `index.save`
- `KntSlotSaveFile-0/` — **actual playthrough slot** (18,282 bytes data.save = real progress; fresh/empty profile is ~157 bytes)
- `LocalProfile/`, `SystemData/` — settings

## Migration performed

```bash
cp -r "/mnt/c/Users/RAJAT/AppData/Roaming/GSE Saves/3768760/remote/." \
      "/mnt/c/Users/Public/Documents/Steam/RUNE/3768760/remote/"
```

Then patched `filemappings.ini` (RUNE manifest generated from fresh first launch didn't list the slot save) — appended with CRLF:

```
KntSlotSaveFile-0\data.save=KntSlotSaveFile-0/data.save
KntSlotSaveFile-0\index.save=KntSlotSaveFile-0/index.save
```

## Follow-up session (same case, copy still "didn't work")

- **Evidence the game rewrites settings on every launch**: after the first full copy, a launch rewrote `localprofile` (2057→954 B, back to fresh size) and `systemdata` (1915→1900 B) but left the slot save (18,282 B) and profile (1453 B) untouched. So `LocalProfile`/`SystemData` are settings, NOT save data — copying them is pointless.
- **Contaminated test**: the game was RUNNING during one copy attempt (timestamps 03:04–03:11 vs copy at 03:08). Check `tasklist.exe | grep -i 007FirstLight` before copying.
- **Plaintext index diagnostic**: `index.save` files are readable, `data.save` payloads are encrypted. Old vs new slot index both contain the same markers (`00 0f 10 01`) and strings ("SaweW", "Heldus") → save format is compatible between 1.0.0 and 1.1.0; the problem is location/state, not version. Use `od -A x -t x1z -N 96 <file>` (xxd absent on WSL).
- **Surgical copy (user preference)**: copy ONLY `KntSlotSaveFile-0/` + `KntProfileSaveFile/` (4 files: data.save + index.save each). Skip `LocalProfile/`, `SystemData/`, `-BCK-*`. List files+sizes first, then copy.
- **Do NOT swap `steam_api64.v38` / `_crack/Retail/007FirstLight.exe` back in** — those are the OLD 1.0.0 version's binaries (v38 crack dated 2026-06-10, exe 342 MB vs current 64 MB). Explicit user rule: never touch exe/dll files.
- **Ludusavi manifest as location spec**: `%APPDATA%\ludusavi\manifest.yaml` shows 007 First Light canonical paths — Steam: `<root>/userdata/<storeUserId>/3768760`; Epic: `<winAppData>/IO Interactive/Epic/<storeUserId>/007 First Light/KntSlotSaveFile-0`. Sweep confirmed only the two emulator roots exist on disk; no Epic path present.
- `filemappings.ini` regenerates on launch and eventually contained both `KntSlotSaveFile-0\data.save` and lowercase `kntslotsavefile-0\data.save` mappings — so after a launch the slot mapping may already exist; re-check before patching.

## Other observations

- Ludusavi backup at `/mnt/f/ludusavi-backup/007 First Light/` had ONLY `mapping.yaml` + `registry.reg` — configured but never backed up. Real saves were never captured there.
- `filemappings.ini` maps lowercase local dirs to mixed-case virtual paths (e.g. `kntprofilesavefile\data.save=KntProfileSaveFile/data.save`) — the emulator's disk naming differs from the game's virtual path naming, but NTFS case-insensitivity makes this transparent.
