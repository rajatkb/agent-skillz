---
name: playnite-plugin-discovery
description: Discover, evaluate, install, and configure Playnite plugins — finding plugins for specific needs, reading source code to understand requirements, configuring external dependencies, and researching data sources.
triggers:
  - user asks about Playnite plugins for a specific task
  - user wants to install or configure a Playnite plugin
  - user asks about game downloading or repack sources in Playnite
  - user needs to understand plugin architecture or requirements
  - user mentions Hydra, torrent downloading, or P2P in Playnite context
---

# Playnite Plugin Discovery & Configuration

## Finding plugins

### Official sources
- **Playnite Addons Database**: `https://www.playnite.link/addons.html` — browse or install via `playnite://playnite/installaddon/<AddonId>` links
- **Playnite Forums**: `https://www.playnite.link/forum/` — community extensions board
- **GitHub**: `https://github.com/JosefNemec/PlayniteExtensions` — official extensions repo
- **GitHub**: `https://github.com/darklinkpower/PlayniteExtensionsCollection` — curated community collection

### Third-party directories
- **Playnite Extension List**: `https://scowalt.github.io/PlayniteExtensionList/`
- **Reddit r/playnite**: `https://www.reddit.com/r/playnite/` — user discussions and recommendations

## Evaluating a plugin

When a user asks if a plugin exists for a specific need, do:

1. **Search** for the use case + "Playnite plugin" on web and GitHub
2. **Read the README** — check features, requirements, dependencies
3. **Check the source code** to understand architecture:
   - `extension.yaml` — plugin ID (GUID), name, version
   - Settings class (`*Settings.cs`) — configurable options, sources list
   - Scraper/Services classes — how data is fetched and processed
   - Model classes — data format expected (JSON schema, etc.)
4. **Check releases** — `.pext` file available for installation
5. **Identify external dependencies** — does it need qBittorrent, a Web UI, an API key?

### Reading plugin source from GitHub

For raw file access (no JS rendering needed):
```
https://raw.githubusercontent.com/<user>/<repo>/<branch>/<path>
```

Browse directory structure via the GitHub web UI (browser_navigate) to find relevant files.

## Installing plugins

1. Download the `.pext` file from GitHub Releases
2. Double-click to install (Playnite handles the import)
3. Restart Playnite
4. Configure in Settings → Plugins → [Plugin Name]

## Configuring common dependencies

### qBittorrent Web UI (for plugins like HydraTorrent)
1. Open qBittorrent → **Tools** → **Options** → **Web UI**
2. Check **"Enable Web User Interface"**
3. Set a **Username** and **Password**
4. Note the **Port** (default: `8080`)
5. Apply → In Playnite plugin settings, enter `localhost`, port, username, password

## HydraTorrent plugin deep-dive

The **Playnite-HydraTorrent** plugin (`https://github.com/BCDezgun/Playnite-HydraTorrent`) integrates torrent download management into Playnite via qBittorrent.

### Architecture
- **JSON source system**: Plugin fetches JSON from configured `{Name, URL}` pairs
- **Expected JSON format** (FitGirl-root compatible):
  ```json
  {
    "name": "SourceName",
    "downloads": [
      {
        "title": "Game Name v1.0",
        "uris": ["magnet:?xt=urn:btih:..."],
        "fileSize": "15.2 GB",
        "uploadDate": "2025-01-15T00:00:00.000Z"
      }
    ]
  }
  ```
- **Scraper**: `JsonSourceScraper` fetches JSON, builds a word-indexed search cache, and searches locally
- **Cloudflare bypass**: Falls back to WebView2 if HTTP 403 (for Cloudflare-protected sources)

### Default source URLs (from Hydra ecosystem)

| Source | URL |
|--------|-----|
| FitGirl Repacks | `https://hydralinks.cloud/sources/fitgirl.json` |
| DODI Repacks | `https://hydralinks.cloud/sources/dodi.json` |
| Xatab | `https://hydralinks.cloud/sources/xatab.json` |
| SteamRip | `https://hydralinks.cloud/sources/steamrip.json` |
| OnlineFix | `https://hydralinks.cloud/sources/onlinefix.json` |
| ErtilaRepo (general) | `https://raw.githubusercontent.com/ertila007/ErtilaRepo.json/main/ErtilaRepo.json` |

### Community source directories
- **Hydra Community Links**: `https://library.hydra.wiki/sources/` — 40+ sources, searchable
- **library.hydra.wiki**: Browse/search all available sources
- **GitHub gists**: Users share source collections (search "hydra sources.json")

## Checking if a repacker/group has a JSON source

Some repackers (FitGirl, DODI, Xatab, SteamRip) have community-maintained JSON databases. Others do not.

To check: Search for `<repackername> json hydra OR hydralinks OR hydralibrary OR ertilarepo`.

**Repackers without known JSON sources** (as of mid-2026):
- InsaneRamZes — releases via game-repack.site, gamedrive.org, rutor.info, Telegram (@irzgameschannel)
- KaOs Krew — may have some coverage in community repos
- ElAmigos — DDL-focused, limited torrent presence

**Fallback**: If no JSON source exists for a repacker, user can either:
1. Use other repackers' sources (FitGirl + DODI cover the most games)
2. Build and self-host a JSON source by scraping the repacker's site
3. Use Hydra Launcher (standalone app, similar source system) for broader coverage

## Building custom source bridges (torrent site → HydraTorrent)

When no JSON source exists for a repacker/tracker, build a local bridge that converts HTML scraping into HydraTorrent's JSON format.

### CRITICAL: HydraTorrent's URL handling limitation

The plugin's `JsonSourceScraper` fetches the source URL as a **static JSON file**, caches it ~1 hour, builds a word-index, and searches locally. It does NOT forward search queries to the URL.

This means:
1. **Static bulk dump** — Periodically scrape the site, output full dataset as JSON. Host on a GitHub gist. Point HydraTorrent at the raw URL.
2. **Standalone tool** (bypasses HydraTorrent) — Script scrapes site → magnet → qBittorrent Web API. Trigger via Playnite "Additional Applications" or PowerShell extension.
3. **Fork HydraTorrent** — Add a `SearchUrl` pattern that parameterizes queries per source.

### Standalone tool pattern for rutor — WSL TLS constraint

Python scripts from WSL fail with TLS errors (`SSLZeroReturnError`) against rutor.info/rutor.is — the server's TLS stack is incompatible with Linux's OpenSSL. **Windows PowerShell works** because it uses the Schannel TLS stack.

#### A) PowerShell script on Windows (recommended — simplest)

```powershell
$url = "https://rutor.info/search/0/0/000/0/$([System.Uri]::EscapeDataString($query))"
$r = Invoke-WebRequest -Uri $url -UserAgent "Mozilla/5.0" -TimeoutSec 20 -UseBasicParsing
# Parse rows
[regex]::Matches($r.Content, '<tr class="(?:gai|tum)">(.*?)</tr>', 'Singleline') | %{
    $title = [regex]::Match($_.Groups[1].Value, 'href="/torrent/\d+/[^"]*">(.*?)</a>').Groups[1].Value
    $magnet = [regex]::Match($_.Groups[1].Value, 'href="(magnet:\?[^"]+)"').Groups[1].Value
}
```

Open magnet in qBittorrent via Windows protocol handler:
```powershell
Start-Process $magnet
```

This is **simpler than the qBittorrent Web API** — no auth, no cookie management, no port config. It uses the system's default magnet:// handler.

The user's deployed interactive script is at `C:\Users\RAJAT\.hermes\rutor-search.ps1` (PowerShell + `Start-Process` approach, no Web API needed). See the `references/hydra-source-ecosystem.md` or `templates/rutor-hydra-bridge.py` for alternative Python + Web API approaches.

#### B) Python script on native Windows (not WSL)

If running Python directly on Windows (not via WSL), Python's urllib uses Schannel and rutor.info works. See `templates/rutor-hydra-bridge.py` for the qBittorrent Web API approach (useful when you want to control download path, category, or queue position without user interaction).

### rutor scraping details

See `references/hydra-source-ecosystem.md` for HTML structure and parsing patterns.

### Key differences: Start-Process vs qBittorrent Web API

| Method | Pros | Cons |
|--------|------|------|
| `Start-Process $magnet` | Zero config, works with any torrent client | Can't set save path/queue, no auth |
| qBittorrent Web API | Full control (path, category, paused) | Needs Web UI enabled + credentials |

## Pitfalls

- **Cloudflare blocking**: Some JSON endpoints (hydralinks.cloud) are behind Cloudflare. The plugin has WebView2 fallback but may still fail. Try community mirrors on raw.githubusercontent.com instead.
- **403 errors**: If a source returns 403, check if the plugin supports WebView2 bypass or switch to a different mirror.
- **InsaneRamZes has NO JSON source**: No community-maintained Hydra JSON exists. Don't spend time searching for one — state this clearly and offer alternatives.
- **Plugin ID mismatch**: `PluginStatus` bindings use the addon GUID from `extension.yaml`; `PluginSettings` uses the short plugin name. These are different.
