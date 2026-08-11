---
name: crack-emulator-save-migration
description: Migrate game saves when a repack update (InsaneRamZes, FitGirl, etc.) switches Steam emulators (Goldberg↔RUNE↔CODEX). Use when saves stop being picked up after updating a cracked game, when the user mentions a "previous user" whose saves vanished, or when an update shows a fresh profile/save despite old progress existing.
---

# Crack Emulator Save Migration

Repack updates often swap the Steam emulator between releases (Goldberg ↔ RUNE ↔ CODEX ↔ ALI213). Each emulator stores saves under its **own root**, keyed by Steam AppId — so an update shows a blank profile even though the old saves are intact on disk. The saves are almost always recoverable by copying.

## Core concept: emulator save roots

- **RUNE**: `C:\Users\Public\Documents\Steam\RUNE\<AppId>\remote\` (the `steam_emu.ini` header comment literally states the path — always read it)
- **Goldberg (GSE)**: `%APPDATA%\GSE Saves\<AppId>\remote\`
- **CODEX**: `%APPDATA%\<Publisher>\<Game>\` or `C:\Users\Public\Documents\Steam\CODEX\<AppId>\`
- Internal layout under `remote/` is set by the game engine, not the emulator — so it's usually identical across emulators for the same game. Files copy straight across.

## Steps

1. **Locate the game install** — repack folders on this machine are named `<Game>-InsaneRamZes` on D: or F: (e.g. `/mnt/d/007.First.Light-InsaneRamZes`). Structure: `Retail/` (game), `_crack/`, `_original files/`, `_extras/`.
2. **Identify which emulators are present** in `Retail/`:
   - `steam_emu.ini` → RUNE/CODEX-style emulator
   - `steam_settings/` (configs.app.ini, configs.user.ini) → Goldberg
   - Renamed crack DLLs: `steam_api64.rne` = RUNE crack, `steam_api64.v38` = Goldberg crack. The **active** one is `steam_api64.dll` — check mtimes; the newest-dated .rne/.v38/.dll trio reveals which crack the current version uses.
3. **Read `steam_settings/configs.user.ini`** — `account_name=voices38` etc. is the emulator account. When the user says "previous user voice38", that's this account name, **not** a Windows user folder. Don't waste time searching `C:\Users\` for it.
4. **Read `steam_emu.ini` header** for the current save path; compare against the old emulator's path to find where old saves live.
5. **Verify old saves are real progress**: slot saves are large (10s of KB, e.g. 18 KB), fresh/empty profile files are tiny (100–200 bytes). Timestamps confirm.
6. **Copy, don't move — and be surgical**: `cp -r "<old>/remote/." "<new>/remote/"` works, but the user prefers copying ONLY the save-bearing files, not settings. Identify which files are the actual save:
   - **Save files** (copy these): the slot save(s) (e.g. `KntSlotSaveFile-0/`, 10s of KB) + the profile (`KntProfileSaveFile/`, ~1–2 KB).
   - **Settings, NOT save data** (skip — the game regenerates them every launch, so copying is pointless): `LocalProfile/`, `SystemData/`, and any `-BCK-*` auto-backup dirs.
   - If unsure, list the files and sizes first and let the user pick; they explicitly asked for list-then-copy workflow.
   - The old folder stays untouched as insurance.
7. **Patch RUNE's `filemappings.ini`** if the new save dir was created by a fresh first launch: the manifest only lists files the emulator has seen. Add lines for any save files not listed (typically the slot saves). Format, per line, CRLF endings: `LocalDir\file.save=VirtualDir/file.save` (backslashes left, forward slashes right, same name both sides).
8. **Verify** with `find ... -type f -exec ls -la {} \;` and check sizes landed, then have the user launch the game.

## Pitfalls

- **NEVER swap crack DLLs or the game exe to "recover" saves** (explicit user rule). Repacks bundle the old crack alongside the new (e.g. `steam_api64.v38` = old Goldberg, `steam_api64.rne` = new RUNE, plus an older exe in `_crack/`). The old crack belongs to the OLD game version — swapping it back downgrades/mismatches the game. Migrate the SAVES to the new crack's location instead; never touch exe/dll files. `_crack/Retail/007FirstLight.exe` at a much older date + larger size than `Retail/` exe = the old version's binary, do not use it.
- **Copy with the game CLOSED, then verify — a mid-copy launch contaminates the test**. In one session the game was running during the copy: it rewrote `localprofile`/`systemdata` AFTER the copy landed (timestamps show it), so the user's "didn't work" verdict was measured against a corrupted state. Check `tasklist.exe | grep -i <exe>` before AND after copying. The game rewrites settings files on EVERY launch — don't interpret the post-launch sizes of `LocalProfile`/`SystemData` as evidence about the save.
- **"Previous user" trap**: emulator account name ≠ Windows username. Check `configs.user.ini`, don't search user folders.
- **Ludusavi backup folders with only `mapping.yaml` + `registry.reg`** = game was *configured* in Ludusavi but never actually backed up. No saves there — don't count on it.
- **Check the game isn't running** before copying: `tasklist.exe | grep -i <exe>` (from WSL). Files lock and the copy silently fails or half-copies.
- **NTFS case-insensitivity**: dirs differing only in case (`kntprofilesavefile` vs `KntProfileSaveFile`) are the SAME dir on Windows — `cp -r` merges them, which is correct. Don't panic at duplicate-looking entries in the listing.
- **`filemappings.ini` regenerates on launch** — if the game still doesn't see saves after the first run, re-check the file and re-add the slot-save mappings.
- **Windows INI files need CRLF**: append with `printf '...\r\n' >> file`, not echo.
- **Never overwrite the old save dir**; copy-only. The update may have been installed over the old version, so old saves can be the ONLY copy (Ludusavi may not have run).

## Diagnostics when the copy still "doesn't work"

- **Compare the `index.save` files (plaintext) between old and new** — `data.save` payloads are encrypted/high-entropy, but the sibling `index.save` files are readable. Same format markers/strings in both = save format is compatible and the problem is location/state, not version. Use `od -A x -t x1z -N 96 <file>` (xxd often absent on WSL).
- **Use Ludusavi's manifest as the authoritative save-location spec**: `%APPDATA%\ludusavi\manifest.yaml` (also `%APPDATA%\hydralauncher\ludusavi\`) lists every canonical save path per game — e.g. for Steam: `<root>/userdata/<storeUserId>/<AppId>`, plus Epic/Microsoft-store variants. Grep it for the game name to learn ALL locations the game legitimately uses, then sweep the filesystem for any other copies (`find /mnt/c /mnt/d /mnt/f -maxdepth 12 -type d -iname "<AppId>"`). User explicitly prefers this approach over ad-hoc guessing.
- **Check whether the game rewrote the files after your copy** (mtime comparison) — if it did, the state you tested was not the state you copied.

## Support files

- `references/007-first-light.md` — worked example: Goldberg→RUNE migration for 007 First Light (AppId 3768760), exact paths and mapping lines.
