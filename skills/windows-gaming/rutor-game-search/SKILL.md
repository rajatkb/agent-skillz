---
name: rutor-game-search
description: Search rutor.info for game torrents and open magnet links in qBittorrent on Windows
---

# RuTor Game Search

Search rutor.info for PC game torrents and open the chosen magnet link directly in qBittorrent.

## Script Location

- **PowerShell:** `C:\Users\RAJAT\.hermes\rutor-search.ps1`
- **BAT wrapper:** `C:\Users\RAJAT\.hermes\rutor-search.bat`
- **WSL wrapper:** `~/.hermes/scripts/rutor-search.sh`

## Usage

```powershell
# From Windows (cmd/PowerShell/run)
powershell -File "C:\Users\RAJAT\.hermes\rutor-search.ps1" -Q "game name"
powershell -File "C:\Users\RAJAT\.hermes\rutor-search.ps1" -Q "game name" -F "InsaneRamZes"

# From WSL
~/.hermes/scripts/rutor-search.sh "game name"
~/.hermes/scripts/rutor-search.sh "game name" InsaneRamZes

# No args = interactive prompt
```

## Parameters

| Param | Description |
|-------|-------------|
| `-Q`   | Game name to search (required) |
| `-F`   | Optional filter text (e.g. `InsaneRamZes`, `FitGirl`, `Portable`) |

## How to invoke from Hermes (direct workflow)

**This is the preferred workflow — Hermes does the scraping and sends the magnet directly, no interactive prompt needed.**

When the user asks to find and download a game from rutor:

1. **Identify** the game name and optional repacker filter (e.g. InsaneRamZes, FitGirl, Portable)
2. **Search** via curl from WSL: `curl -sL --max-time 10 "https://rutor.info/search/0/0/000/0/{urlencoded_query}" -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"`
3. **Parse** with Python: extract rows matching `<tr class="gai">` or `<tr class="tum">`, then grab title (`href="/torrent/\d+/..."`), magnet (`href="(magnet:\?...)"`), and size
4. **Filter** by repacker name if user specified one (case-insensitive substring match)
5. **Send magnet** to qBittorrent: `powershell.exe -NoProfile -Command "Start-Process 'magnet:?...'"`
6. **Report** what was sent (title, size, repacker)

### Interactive fallback
If the user prefers to pick from results themselves, run the PowerShell script interactively:
```powershell
powershell -File "C:\Users\RAJAT\.hermes\rutor-search.ps1" -Q "<game>" -F "<filter>"
```
This opens a Windows console window — the user picks a number and qBittorrent launches.

## Pitfalls & Troubleshooting

### Intermittent connectivity
rutor.info is frequently flaky — TLS handshake drops, returns 0 bytes, or times out on one request then works fine on the next retry seconds later. **Always retry 2-5 times with 3-5 second delays** if a search returns empty. The site comes back after short outages. Pattern:
```bash
for i in 1 2 3 4 5; do
  sz=$(curl -sL --max-time 10 "https://rutor.info/search/0/0/000/0/{query}" -H "User-Agent: ..." | wc -c)
  [ "$sz" -gt 1000 ] && break
  sleep 3-5
done
```

### Game naming quirks
Russian repack sites often use translated/localized names not matching English titles. Known examples:
- "Halo Combat Evolved Remake (2026)" = **"Halo: Campaign Evolved"**
- Games may omit "The", articles, or subtitles

**If a search returns nothing, try:**
- Shorter queries (drop year, drop subtitles)
- Franchise name alone (e.g. "Halo" instead of "Halo Combat Evolved Remake 2026")
- Alternative name variants (translated, abbreviated)
- Broader terms then narrow by repacker filter

### Empty results != no game
A search returning 0 results could mean:
- **Site is temporarily down** (most common — retry 2-5 times)
- Query is too specific (try broader terms)
- Game genuinely isn't on rutor (rare — check other sources like rutracker.org)

### Magnet delivery
Send magnets via:
```powershell
powershell.exe -NoProfile -Command "Start-Process 'magnet:?...'"
```
qBittorrent must be registered as the default magnet:// protocol handler on Windows. No credentials needed — Windows handles the UAC/protocol association.

## Requirements

- qBittorrent installed and registered as the default magnet:// handler on Windows
- curl (available in WSL)
- Python 3 (for parsing)
- PowerShell (comes with Windows, no install needed)

## Search URL structure

`https://rutor.info/search/{page}/{category}/{method}{search_in}0/{sort}/{query}`

Known-good parameters: `page=0, category=0, method=0, search_in=0, sort=0`

## HTML parsing reference (result rows)

Each result is a `<tr>` with class `gai` or `tum`:
```
<tr class="gai">
  <td>date</td>
  <td><a class="downgif" href="//d.rutor.info/download/ID">[D]</a>
      <a href="magnet:?...">[M]</a>
      <a href="/torrent/ID/title-slug">Game Title [v X.X] (YEAR) PC | Repack от RepackerName</a></td>
  <td>Size GB</td>
  <td><span class="green">S seeds</span> <span class="red">L leechers</span></td>
</tr>
```
