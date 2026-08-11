# Harbor API Key Storage (this install, verified Aug 2026)

Where Harbor keeps the user's streaming/debrid/API keys on this machine.

## Location

`C:\Users\RAJAT\AppData\Roaming\app.harbor\settings.json`
(WSL: `/mnt/c/Users/RAJAT/AppData/Roaming/app.harbor/settings.json`)

Tauri-persisted settings store — flat JSON with dotted-key-style field names
(`{"tmdbKey": "...", "tbKey": "...", ...}`). This is separate from the frontend
localStorage `harbor.settings` mentioned in the architecture notes; the
API-key fields live in this disk file.

## Key fields

| Field | Service | Notes |
|-------|---------|-------|
| `.tbKey` | TorBox | **UUID format** (e.g. `6524dee1-a80d-4d09-8ebf-b53cdd2fa961`) |
| `.rdKey` | Real-Debrid | |
| `.adKey` | AllDebrid | |
| `.pmKey` | Premiumize | |
| `.dlKey` | Debrid-Link | |
| `.tmdbKey` | TMDB | Also duplicated in `~/Work/creds/tmdb-api-creds.md` |
| `.fanartKey`, `.tvdbKey`, `.mdblistKey`, `.jinaKey`, `.opensubtitlesApiKey`, ... | misc addon/metadata APIs | empty string = unset |
| `.traktAccessToken` / `.traktRefreshToken` | Trakt OAuth | may be `None` — OAuth tokens live elsewhere |

`secrets.json` exists in the same dir but the API keys are in `settings.json`.

## Quick scan

```bash
python3 -c "
import json
d = json.load(open('/mnt/c/Users/RAJAT/AppData/Roaming/app.harbor/settings.json'))
[print(f'{k} = {v}') for k, v in d.items() if k.lower().endswith('key') or 'token' in k.lower()]
"
```

## Pitfall: keys are NOT in ~/Work/creds

The user expects credentials in `~/Work/creds/` — that dir currently holds only
`tmdb-api-creds.md` and `playwright-mcp-token.md`. Debrid/streaming keys are
**not** there. When asked for a TorBox/debrid key (or "find my key in work
dir"), check Harbor's `settings.json` first.
