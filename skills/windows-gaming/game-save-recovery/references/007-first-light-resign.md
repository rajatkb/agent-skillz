# 007 First Light — save recovery & resigning (worked case, Aug 2026)

Full worked case: InsaneRamZes repack updated 1.0.0 → 1.1.0, saves "lost".
AppId **3768760**. Crack switched from Goldberg (voices38) to RUNE between versions.

## Layout
- Old saves (1.0.0, Goldberg voices38): `C:\Users\<user>\AppData\Roaming\GSE Saves\3768760\remote\`
- New saves (1.1.0, RUNE): `C:\Users\Public\Documents\Steam\RUNE\3768760\remote\`
- Game dir: `Retail\steam_emu.ini` (RUNE config), `Retail\steam_settings\configs.user.ini` (Goldberg config, `account_name=voices38`, `account_steamid=76561197960285355`)
- Save containers under `remote/`: `KntSlotSaveFile-0` (the playthrough), `KntProfileSaveFile` (+ `-BCK-0/-BCK-1` auto-backups), `LocalProfile`, `SystemData` (both settings — regenerated every launch)

## Account math
- SteamID64 76561197960285355 → AccountId 19627 (`76561197960265728 + 19627`)
- RUNE `steam_emu.ini` ships `#AccountId=0` commented → random account per launch
- FIX in `Retail\steam_emu.ini`: `AccountId=19627` (uncommented). CRLF preserved.

## Why plain copying failed (the three failure modes observed)
1. **Random account ID** → game didn't see old saves at all (showed fresh profile).
2. After pinning AccountId → game FOUND saves but **"save data is corrupt"**: `systemdata`/`localprofile`/`BCK-*` files written during the pre-pin launches were still keyed with the old random ID (6144). Mixed-key folder.
3. Plain copies are also wrong because the saves are **XOR-encrypted with the SteamID64** — the copy must be *resigned*, not just placed.

## Encryption format (from Dxian998/007-First-Light-Save-Tools source)
- Key = SteamID64 as 8-byte LE repeated: `struct.pack("<Q", sid)` cycling `i % 8`
- `index.save`: plain XOR; decrypts to `\x03\x00\x00\x00\x01\x0f\x00\x00\x80SSaveGameHeader...` + field names (`uint32`, etc.)
- `data.save`: zlib-compressed then XOR'd. Slot payload ~86,633 raw bytes for a real playthrough.
- `guess_xor_mask()` finds key by XORing offset-16 bytes against `b"meHeader"` and checking for `b"SSaveGameHeader"`; `bruteforce_data_save_key()` tries the 2-byte key tail `[0x01,0x00,0x10,0x01]` (account-id low bytes) + zlib check.

## Resign command (run from the RUNE remote dir)
```bash
cd "/mnt/c/Users/Public/Documents/Steam/RUNE/3768760/remote"
python3 /tmp/flt-save-tools/resign_save.py resign 76561197960285355 -y
# walks ./, bruteforces each container's source key, re-encrypts index.save + data.save
# creates ./<container>/Backup/ — delete after
```
Direct decrypt-test (ground truth — do NOT trust the tool's log or its brute-force read-back when Backup dirs exist):
```python
import struct, zlib
kb = struct.pack("<Q", 76561197960285355)
for root,_,fs in os.walk("."):
    if "data.save" in fs:
        dec = bytes(c ^ kb[i%8] for i,c in enumerate(open(root+"/data.save","rb").read()))
        print(root, len(zlib.decompress(dec)))
```

## Community sources
- gload.to / g4u.to 007 First Light ElAmigos page comments — the `AccountId=19627` trick (user "Bond", 25.07.2026): "savegame files are hard linked to that... change #AccountId=0 to AccountId=19627... then just copy over the 1.0 savegame"
- Nexus Mods: mod 33 "007 - Save Resigner" (tool + VDF generator for legit Steam), mod 44 "FirstLight SaveTransfer" (EonaCat) — posts confirm voices38→RUNE issues; "I also tried to put the same user id in the .ini to no avail" (needs resign, not just ini)
- Reddit r/PiratedGames "007 First Light - Convert HV Saves to Voices38" → points to the Save Resigner as the solution
- GitHub: https://github.com/Dxian998/007-First-Light-Save-Tools (resign_save.py, decrypt_save.py, encrypt_save.py, parse_save_variables.py)
- Ludusavi manifest: `%APPDATA%\ludusavi\manifest.yaml` → Steam path `<root>/userdata/<storeUserId>/3768760`, Epic path `%APPDATA%\IO Interactive\Epic\<storeUserId>\007 First Light\KntSlotSaveFile-0`; user's F:\ludusavi-backup\007 First Light had only mapping.yaml+registry.reg (configured, never backed up)

## Session traps
- Verify game closed via `tasklist.exe | grep -i 007FirstLight` before AND after copy; a mid-copy launch rewrites settings files and invalidates the test.
- Do NOT swap exe/crack DLLs — `_crack/Retail/007FirstLight.exe` (Jun 10, 342 MB) is the OLD 1.0.0 binary; `Retail/007FirstLight.exe` (Aug 5, 64 MB) is current.
- The game rewrote `localprofile`/`systemdata` every launch (sizes: 954→1073→954; 1953→1900) — never interpret those as save data.
