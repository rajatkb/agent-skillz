# Hydra Source Ecosystem Reference

This document catalogs known JSON sources for the HydraTorrent Playnite plugin and the standalone Hydra Launcher. Sources follow the `{name, downloads: [{title, uris[], fileSize, uploadDate}]}` schema.

## Primary hydralinks.cloud sources (Cloudflare-protected)

| Source | URL | Status |
|--------|-----|--------|
| FitGirl | `https://hydralinks.cloud/sources/fitgirl.json` | Cloudflare |
| DODI | `https://hydralinks.cloud/sources/dodi.json` | Cloudflare |
| Xatab | `https://hydralinks.cloud/sources/xatab.json` | Cloudflare |
| SteamRip | `https://hydralinks.cloud/sources/steamrip.json` | Cloudflare |
| OnlineFix | `https://hydralinks.cloud/sources/onlinefix.json` | Cloudflare |
| SteamRip Software | `https://hydralinks.cloud/sources/steamrip-software.json` | Cloudflare |

These may be blocked by Cloudflare — the HydraTorrent plugin has a WebView2 fallback but results vary.

## Community GitHub-hosted sources (no Cloudflare)

| Source | URL |
|--------|-----|
| ErtilaRepo (general) | `https://raw.githubusercontent.com/ertila007/ErtilaRepo.json/main/ErtilaRepo.json` |
| ArnamentGames FitGirl | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/fitgirl.json` |
| ArnamentGames DODI | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/dodi.json` |
| ArnamentGames KaOs | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/kaoskrew.json` |
| ArnamentGames GOG | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/gog.json` |
| ArnamentGames Empress | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/empress.json` |
| ArnamentGames Xatab | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/xatab.json` |
| ArnamentGames SteamRip | `https://raw.githubusercontent.com/ArnamentGames/HydraLinks/refs/heads/main/steamrip.json` |
| RuTracker (all cats) | `https://raw.githubusercontent.com/KekitU/rutracker-hydra-links/main/all_categories.json` |
| PoBruno Hydra List | `https://raw.githubusercontent.com/PoBruno/Hydra-List/main/ErtilaRepo.json` |

## Community source directories

- **Hydra Library**: `https://library.hydra.wiki/sources/` — browse/search 40+ sources, has search at `https://library.hydra.wiki/search/`
- **Hydra Community Links**: `https://hydralinks.cloud/` — main hub (Cloudflare)

## Repackers' JSON source availability (as of mid-2026)

| Repacker | Has JSON source? | Notes |
|----------|-----------------|-------|
| FitGirl | ✅ Yes | hydralinks.cloud + community mirrors |
| DODI | ✅ Yes | hydralinks.cloud + community mirrors |
| Xatab | ✅ Yes | hydralinks.cloud + community mirrors |
| SteamRip | ✅ Yes | hydralinks.cloud + community mirrors |
| OnlineFix | ✅ Yes | hydralinks.cloud |
| KaOs Krew | ✅ Partial | ArnamentGames mirror |
| Empress | ✅ Partial | ArnamentGames mirror |
| GOG (scene) | ✅ Yes | Community mirrors |
| InsaneRamZes | ❌ No | Releases on game-repack.site, gamedrive.org, rutor.info, Telegram @irzgameschannel |
| ElAmigos | ❌ No | DDL-focused, no torrent JSON |

## Creating a custom JSON source

If a repacker doesn't have a JSON source, one can be scraped and hosted. See the SKILL.md section "Building custom source bridges" for architecture decisions.

## rutor scraping reference

### Domain notes — WSL TLS constraint

| Domain | Works from WSL? | Works from Windows? | Notes |
|--------|----------------|---------------------|-------|
| `rutor.is` | ❌ No — TLS errors | ✅ Yes (Schannel) | Intermittently blocks curl, avoid |
| `rutor.info` | ❌ No — TLS errors | ✅ Yes (Schannel) | Same server, works via browser |

**TLS root cause**: The rutor server uses a TLS stack that closes the connection during handshake with OpenSSL ≥1.1 (Linux/WSL). Windows' Schannel handles it fine. PowerShell's `Invoke-WebRequest` and Windows-native Python (`urllib` on Windows) both work.

### Search URL format (rutor.info)

`https://rutor.info/search/{page}/{category}/{method}{search_in}00/{sort}/{query}`

- `page`: 0 = page 1
- `category`: 0 = all, 8 = games
- `method`: 0 (phrase), 1 (all words), 2 (any word)
- `search_in`: 0 (title), 1 (title+description)
- `sort`: 0 (date desc), 2 (seeders desc), 6 (name), 8 (size), 10 (relevance)
- `query`: URL-encoded, `&` replaced with `AND`

Example: `https://rutor.info/search/0/0/000/0/elden%20ring`

### HTML structure

Results are in static HTML (not JS-loaded). Each row:

```html
<tr class="gai">
  <td>22&nbsp;Май&nbsp;26</td>
  <td>
    <a class="downgif" href="//d.rutor.info/download/1086274"><img src="...d.gif" alt="D" /></a>
    <a href="magnet:?xt=urn:btih:...&amp;dn=rutor.info&amp;tr=..."><img src="...m.png" alt="M" /></a>
    <a href="/torrent/1086274/slug">Game Title [v 2.31a + DLCs] (2020) PC | Repack by XYZ</a>
  </td>
  <td>78.04&nbsp;GB</td>
  <td align="center">
    <span class="green"><img src="...arrowup.gif" />&nbsp;34</span>
    <span class="red">&nbsp;12</span>
  </td>
</tr>
```

### PowerShell parsing (recommended, works from Windows)

```powershell
$results = [regex]::Matches($html, '<tr class="(?:gai|tum)">(.*?)</tr>', 'Singleline') | ForEach-Object {
    $row = $_.Groups[1].Value
    $title = [regex]::Match($row, 'href="/torrent/\d+/[^"]*">(.*?)</a>').Groups[1].Value
    $magnet = [regex]::Match($row, 'href="(magnet:\?[^"]+)"').Groups[1].Value
    if (-not $magnet) { return }
    $size = [regex]::Match($row, '([\d.]+)\s*(?:&nbsp;)?\s*(GB|MB|KB)')
    $sizeStr = if ($size.Success) { "$($size.Groups[1].Value) $($size.Groups[2].Value)" } else { "" }
    $seeds = [regex]::Match($row, 'arrowup.*?>\s*(\d+)')
    $seedCount = if ($seeds.Success) { [int]$seeds.Groups[1].Value } else { 0 }
    [PSCustomObject]@{
        Title = [System.Net.WebUtility]::HtmlDecode($title)
        Size = $sizeStr
        Seeds = $seedCount
        Magnet = $magnet
    }
} | Sort-Object Seeds -Descending
```

**HtmlDecode note**: `[System.Net.WebUtility]::HtmlDecode()` works in PowerShell 5+ (Windows). `[System.Web.HttpUtility]::HtmlDecode()` requires loading `System.Web` assembly — prefer the former.

### Opening magnet in qBittorrent

Simplest approach — no Web API needed:

```powershell
Start-Process $magnet
```

Uses the Windows protocol handler (magnet://), which qBittorrent registers on install. No auth, no port, no cookie management.

### Python parsing (stdlib) — native Windows only

When running Python natively on Windows (not WSL), urllib uses Schannel and works:

```python
import urllib.request, re, urllib.parse
def search_rutor(query):
    url = f'https://rutor.info/search/0/0/000/0/{urllib.parse.quote(query)}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0...'})
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='replace')
    results = []
    for row in re.findall(r'<tr class="(?:gai|tum)">(.*?)</tr>', html, re.DOTALL):
        magnet = re.search(r'href="(magnet:\?[^"]+)"', row)
        title_m = re.search(r'href="/torrent/\d+/[^"]*">(.*?)</a>', row)
        if magnet and title_m:
            results.append({'title': title_m.group(1), 'magnet': magnet.group(1)})
    return results
```

### Notes
- User-Agent header required (bare requests blocked by nginx)
- Max 2000 results per search
- Rows use `<tr class="gai">` or `<tr class="tum">` — identical structure, just alternating background color
- Repacker name is in the display title — filter via `where Title -like "*InsaneRamZes*"` or `if 'InsaneRamZes' in r['title']`
- See `templates/rutor-search.ps1` for a complete interactive PowerShell script
