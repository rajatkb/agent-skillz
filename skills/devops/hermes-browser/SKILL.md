---
name: hermes-browser
description: Configure, set up, and use Hermes Agent's browser automation tools (browser_navigate, browser_click, browser_snapshot, browser_back, etc.) across all backend options
triggers:
  - user asks to control a browser via Hermes
  - user asks about browser tools (browser_*, browser_back, browser_click)
  - browser tools not available/loaded in current session
  - need to set up or switch browser backend provider
---

# Hermes Browser Tools

Hermes ships with a full browser automation toolset including: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_scroll`, `browser_press`, `browser_back`, `browser_get_images`, `browser_vision`, `browser_console`, `browser_cdp`, `browser_dialog`.

These tools require a **backend provider** to work — the toolset name `browser` in `toolsets` is necessary but not sufficient.

## Initial Triage (always run this first when tools are missing)

Hermes v2026.7.1+ has stricter dependency checks. Use **`hermes doctor`** and **`hermes config check`** as your primary diagnostics:

```bash
# 1. PRIMARY: run doctor — shows tool availability, missing deps, and which env vars
hermes doctor

# 2. Check which tools need which env vars
hermes config check

# 3. Verify toolset is enabled in config
grep -q 'browser' ~/.hermes/config.yaml && echo "browser toolset enabled"
grep -q 'web' ~/.hermes/config.yaml && echo "web toolset enabled"
```

The doctor output tells you exactly what's wrong (e.g. "Playwright Chromium not installed", "missing EXA_API_KEY"). Check the `Tool Availability` section first — tools marked `⚠` are blocked.

Silent-missing tools mean the dependency check failed at session init. Do NOT guess — run `hermes doctor`.

## Backend Options

### A) Browserbase (cloud, recommended for ease)
Add to `~/.hermes/.env`:
```
BROWSERBASE_API_KEY=***
BROWSERBASE_PROJECT_ID=your-project-id
```
Get credentials at [browserbase.com](https://browserbase.com). Includes stealth features (random fingerprints, CAPTCHA solving, residential proxies).

### B) Browser Use (cloud alternative)
```
BROWSER_USE_API_KEY=***
```
Get key at [browser-use.com](https://browser-use.com). Browserbase takes priority if both are set.

### C) Firecrawl (cloud)
```
FIRECRAWL_API_KEY=fc-***
```
Get key at [firecrawl.dev](https://firecrawl.dev). Select via `hermes setup tools` → Browser Automation → Firecrawl.

### D) agent-browser CLI (local, no cloud dependency)
```bash
npm install -g agent-browser
# or auto-install via hermes setup tools
```
No env vars needed — `AGENT_BROWSER_ENGINE` defaults to `auto` (valid: auto, lightpanda, chrome).

After installing the CLI, download Chromium via Playwright:
```bash
# Option 1: agent-browser built-in
agent-browser install

# Option 2: npx (works when agent-browser install fails or Hermes doctor complains)
cd /home/linuxbrew/.linuxbrew/Cellar/hermes-agent/*/libexec/lib/python3.14/site-packages
npx playwright install chromium
```

On Linux/WSL, all system dependencies are typically already present (WSL Ubuntu ships them). If they aren't:
```bash
# apt packages needed for Chromium (all deps at once)
sudo apt-get install -y libxcb-shm0 libx11-xcb1 libx11-6 libxcb1 libxext6 libxrandr2 \
  libxcomposite1 libxcursor1 libxdamage1 libxfixes3 libxi6 libgtk-3-0t64 \
  libpangocairo-1.0-0 libpango-1.0-0 libatk1.0-0t64 libcairo-gobject2 libcairo2 \
  libgdk-pixbuf-2.0-0 libxrender1 libasound2t64 libfreetype6 libfontconfig1 \
  libdbus-1-3 libnss3 libnspr4 libatk-bridge2.0-0t64 libdrm2 libxkbcommon0 \
  libatspi2.0-0t64 libcups2t64 libxshmfence1 libgbm1 fonts-noto-color-emoji
```

⚠ `agent-browser install --with-deps` (sudo) **fails in non-interactive terminals** — use the apt-get command above instead.

### E) CDP Connect (attach to existing Chrome)
Start Chrome/Edge with remote debugging:
```bash
# Windows (from cmd/powershell):
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```
Then in Hermes CLI (terminal only, not gateway):
```
/browser connect
```

### F) Camofox (local Firefox fork with stealth)
Requires Docker and [camofox-browser](https://github.com/jo-inc/camofox-browser) repo.
Set `CAMOFOX_URL=http://localhost:9377` in `~/.hermes/.env`.

### G) Nous Portal (one-shot setup)
```bash
hermes setup --portal
```
Enables browser + web search + image gen + TTS through Tool Gateway — no individual API keys.

## WSL2-Specific Notes

- **Hybrid routing**: When cloud provider is set, private URLs (localhost, 192.168.x.x) auto-route through local Chromium. Public URLs use cloud. On by default.
- **Windows Chrome via CDP**: Chrome on Windows binds to 127.0.0.1 — from WSL2 use `--remote-allow-origins=*` or set up a portproxy.
- **MCP as alternative**: For WSL2 + Windows Chrome, an MCP browser server may work better than raw CDP.

## Verification

Before doing `/new`, confirm all deps are met:

```bash
hermes doctor | grep -E '^(  ✓|  ⚠)' | grep -E 'browser|web|Playwright|agent-browser'
```

Look for browser/web showing `✓` (ready) not `⚠` (blocked). Then start a fresh session and test:

```bash
browser_navigate(url="https://example.com")
browser_snapshot()
```

## Pitfalls

- **Browser tools not available despite toolset being enabled**: Check a backend is actually configured. The toolset name alone won't make tools functional.
- **`/browser connect` fails in gateway chat**: CLI-only slash command. Only works from `hermes` or `hermes chat` terminal session, not Telegram/Discord/WebUI.
- **`hermes tools` requires interactive terminal**: Cannot run via pipe or subprocess.
- **No `browser_cdp` in cloud mode**: Only works with CDP-connected browsers. Use `browser_console(expression=...)` as JS evaluation workaround for cloud sessions.
- **Cloud session timeouts**: Inactive sessions expire (~2 min default). Keep navigating/interacting to stay alive.
- **agent-browser CLI fails on Linux/WSL with shared library errors**: After `agent-browser install`, Chrome may crash with `libglib-2.0.so.0: cannot open shared object file`. Run `agent-browser install --with-deps` or install the apt packages listed in section D manually.
- **Tools still missing after installing backends** — Browser and web search tools are loaded **at session start only**. Running `npm install -g agent-browser` or setting env vars mid-session won't make them appear. Run `/new` to start a fresh session after installing dependencies.
- **Web search tool exists but returns errors** — the tool *name* may be in the list but the backend provider may not be registered if `discover_plugins()` was skipped. Check with `python3 -c "from hermes_cli.plugins import discover_plugins; from agent import web_search_registry as r; discover_plugins(); [print(f'{p.name} avail={p.is_available()}') for p in r.list_providers()]"` (use the Hermes Homebrew python on Homebrew installs).
- **Web search backends are now plugins** — all providers live under `plugins/web/<name>/` and need `discover_plugins()` to be called before they register. See `references/web-tool-setup.md` for diagnosis, provider comparison, and the per-capability split pattern.
- **DDGS is back as a plugin** — `pip install ddgs` makes it available with no API key. Not removed.
- **web_extract is NOT a primary tool** — do NOT call `web_extract`. It requires a backend with extract support (Firecrawl, Exa, Tavily) and fails silently with search-only backends. Use `browser_navigate` + `browser_snapshot` for interactive page reading instead.
- **For bulk/offline extraction** (full page markdown, RAG, offline reading), use the local crawl4ai wrapper: `python3 ~/.hermes/scripts/crawl.py <url>`. See skill `local-web-crawler`.
- **Snapshot truncation workaround** — when `browser_snapshot` truncates, use `browser_console(expression="document.body.innerText")` for full text, or switch to crawl4ai for complete markdown.
