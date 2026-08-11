# Drive-root mystery files — case study (F: drive, Aug 2026)

User saw hidden files at F:\ root and asked what they were / whether they could be deleted.
Identified all three in one pass; the workflow generalizes to any drive-root forensics question.

## The files
| File | Size | Mtime | Identity | Verdict |
|---|---|---|---|---|
| `.GamingRoot` | 18 B | 2024-07-18 | Xbox app install-drive marker | Leave it (self-regenerating; deleting can break Xbox drive detection) |
| `.417c88886c9d9f9483bda62e72d668e1dfc06776.parts` | 33.5 MB | 2025-07-29 | Orphaned partial download fragment | Safe to delete |
| `.92e706adab65a400bd1bf5622000b59182202498.parts` | 4.2 MB | 2024-12-07 | Orphaned partial download fragment | Safe to delete |

## Decode commands (what actually identified them)
```bash
ls -la /mnt/f/                       # list hidden files at drive root
od -c /mnt/f/.GamingRoot             # -> R G B X \x01 \0 \0 \0 x \0 b \0 o \0 x \0 \0 \0
od -A d -N 64 -c /mnt/f/.*.parts     # headers: \0\0 1E 55 01 00 00 00 FF FF... (binary pkg data)
# cross-attribution: qBittorrent.ini SavePathHistory contained F:\\  -> qBittorrent downloaded to F: root
```

## Key facts
- **`.GamingRoot`** = `RGBX` magic + version byte + UTF-16LE string naming the gaming root ("xbox").
  Created by the Xbox app (and Game Bar on C:) to mark drives it may install games to.
  Sources: HowToGeek (howtogeek.com/872922/what-is-the-gamingroot-file/), SuperUser
  (superuser.com/questions/1881513 — deleting it is the documented FIX step for "installation folder
  can't be changed" errors; the Reddit PSA r/XboxGamePass/u42a5h says COPY it back to restore
  drive detection), XDA (xda-developers.com — recreates on next Xbox launch), PartitionWizard
  (says delete only works if you uninstall Xbox app, otherwise it returns).
- **Hash-named `.parts` files** = qBittorrent incomplete-download fragments. qBittorrent appends
  `.parts` to not-yet-finished files; 40-hex hash names are temp identifiers when the real filename
  was never finalized. Stale mtime + no running process + SavePathHistory matching the drive =
  orphaned garbage, safe to delete.
- **Verdict pattern**: bytes-sized marker files → app markers, leave alone (deleting gains ~nothing
  and can break app drive detection); MB-sized stale `.parts`/temp fragments → safe to delete.
- **User expectation**: sources cited for every claim (HowToGeek/SuperUser/Reddit), direct answer,
  no fluff, and offer to perform the deletion rather than doing it unprompted.
