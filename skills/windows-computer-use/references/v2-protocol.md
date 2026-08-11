# Playwright MCP Bridge Extension — Protocol V2 & TCP Command Server

Discovered by reverse-engineering the extension's `background.mjs` at:
`%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Extensions\\mmlmfjhmonkocbjadbfplnigmagldckm\\<version>\\lib\\background.mjs`

## V2 vs V1

The extension has TWO protocol handlers. V1 is the default. V2 is activated by adding `&protocolVersion=2` to the connect page URL.

### V1 (ProtocolV1Handler)
- Methods: `attachToTab`, `forwardCDPCommand`, `forwardCDPEvent`
- `forwardCDPCommand` throws on `Target.createTarget`: "Tab creation is not supported yet"
- Only attaches to ONE tab (the user-selected tab from the connect page)
- When the connect page tab is navigated to a slow external page, the debugger drops

### V2 (ProtocolV2Handler)
```javascript
const ALLOWED_CHROME_COMMANDS = new Set([
  "chrome.debugger.attach",
  "chrome.debugger.detach",
  "chrome.debugger.sendCommand",
  "chrome.tabs.create",
  "chrome.tabs.remove"
]);
```

**Additional events:**
- `extension.initialized` — sent on connect (no params)
- `chrome.tabs.onCreated` — sent when user drags a tab into the Playwright group
- `chrome.debugger.onEvent` — sent for CDP events

### V2 vs V1 comparison

| Capability | V1 | V2 |
|---|---|---|
| Create tabs | ❌ | ✅ `chrome.tabs.create` |
| Survives slow nav | ❌ Extension disconnects | ✅ Stays connected |
| Proper detach | ❌ Made-up "detach" cmd | ✅ `chrome.debugger.detach` |
| Reconnection | ❌ "Already attached" forever | ✅ Clean detach+reattach |
| New tab via JS | N/A | ✅ `window.open("url","_blank")` |
| Token auto-approve | ✅ | ✅ |
| Cross-origin nav | ❌ Drops debugger | ⚠️ V2 keeps WebSocket alive but `Page.navigate` returns empty `Protocol error (Page.navigate):`. The underlying `chrome.debugger.sendCommand` for `Page.navigate` fails because Chrome invalidates the debugger session on domain change. The tab must be navigated directly (no intermediate domains). OpenClaw LHT fork has `auto-reattach debugger after cross-origin navigation` fix. |

## Bridge implementation

The bridge (`cdp-bridge.py`) intercepts CDP commands and translates them to V2 chrome.* API calls:

| CDP Command | V2 Translation |
|---|---|
| `Target.setAutoAttach` | `chrome.tabs.create({"url": "about:blank"})` → `chrome.debugger.attach({tabId})` |
| `Target.createTarget` | `chrome.tabs.create({"url": url})` → `chrome.debugger.attach({tabId})` |
| `Page.*`, `Runtime.*`, etc | `chrome.debugger.sendCommand({tabId}, method, params)` |
| `Browser.getVersion` | Fake response (no extension call) |

## Bridge Architecture (with TCP Command Server) — ACTIVE APPROACH

The bridge embeds an internal Playwright session connected to its own CDP endpoint, plus a TCP command server for sustained interaction. This is the current default approach — the bridge starts internal Playwright automatically after the extension connects.

```
Bridge process
├── Extension relay (WebSocket → Chrome extension)
├── CDP WebSocket server (for external Playwright clients)
├── Internal Playwright (connected to own CDP port)
└── TCP command server (port = CDP port + 1)
```

The TCP server accepts one line per connection, evals it as async Python in a scope with `page`, `ctx`, `browser`, `asyncio`, `json` pre-loaded, prints the result, and sends `---CMD-END---` as delimiter.

### Sending commands

```bash
# One-shot command
python3 -c "import socket;s=socket.socket();s.settimeout(10);s.connect(('127.0.0.1',CMD_PORT));s.sendall(b'await page.title()\\n');print(s.recv(8192).decode());s.close()"
```

**Quote escaping tip**: The TCP server uses `exec(f"async def _f():\n    return {line}")`. This means backslash-escaped quotes (`\"`) in JSON strings cause Python syntax errors. **Use single quotes for JS eval strings**:
```python
# WRONG — double quotes cause Python syntax error
await page.evaluate("document.querySelector(\"input[name=q]\")")
# RIGHT — single quotes work
await page.evaluate("document.querySelector('input[name=q]')")
```
For complex commands with multiple statements, write a helper `.py` file with `write_file` and run it — avoids all quoting issues.
# Multi-step sequence (each a separate TCP connection, same session)
python3 ...page.goto...     # navigate
python3 ...page.title...    # check title
python3 ...page.fill...     # fill form
python3 ...page.keyboard... # press key
```

Each command shares the SAME internal Playwright session — pages, context, and navigation state persist between commands.

### Scope variables
- `page` — current active page (`ctx.pages[0]`)
- `ctx` — browser context (`browser.contexts[0]`)
- `browser` — Playwright browser object
- `asyncio` — standard library
- `json` — standard library

## Using Protocol V2

1. Start bridge: `python3 cdp-bridge.py --port PORT --token TOKEN`
   - Bridge builds URL with `&protocolVersion=2` automatically
2. Connect Playwright (or use internal TCP command server on PORT+1)

## Internal Playwright connection

The bridge connects its own Playwright to the CDP port right after the extension connects. This:
- Creates a new tab via `chrome.tabs.create("about:blank")` triggered by `Target.setAutoAttach`
- Attaches chrome.debugger to that tab
- Makes `page`, `ctx`, `browser` available through the TCP command server

## Creating extra tabs

- Via CDP `Target.createTarget` (handled in bridge → `chrome.tabs.create`)
- Via JS in Playwright: `page.evaluate('window.open("url", "_blank")')`
- NOT via `ctx.new_page()` — this goes through Playwright's internal protocol, not CDP

## JS Dialog handling (critical for SPAs)

YouTube Music and other heavy SPAs show a "Leave site?" confirmation dialog (`beforeunload` event) when navigating away. This dialog blocks Chrome's JavaScript execution context, causing all `Page.evaluate` and `Page.goto` calls to fail with:
```
ERROR: Page.evaluate: Execution context was destroyed, most likely because of a navigation.
```
The page title stays stuck on `"Loading <url>..."` forever. Once hit, the session is irrecoverable.

**Prevention**: Set the dialog handler BEFORE navigating:
```python
page.on("dialog", lambda d: d.accept())
# Now safe to navigate
await page.goto("https://music.youtube.com/search?q=...", ...)
```
Set this in a SEPARATE TCP command call (not chained with `.goto()` in the same line).

**Recovery**: Kill the bridge, kill Chrome, restart both fresh.

## SPA navigation: use `wait_until="commit"`

Heavy single-page apps like `music.youtube.com` don't finish loading within the CDP navigation timeout. The default `wait_until="domcontentloaded"` hangs until timeout.

For SPAs, use `wait_until="commit"` which only waits for the initial HTTP response headers, not the full page render:
```python
await page.goto("https://music.youtube.com", wait_until="commit", timeout=25000)
```
The SPA continues rendering asynchronously — you can interact after a short sleep.

## Site-specific patterns

### YouTube Music (music.youtube.com)
- Use `wait_until="commit"` for all navigations
- Suppress dialogs before any navigation
- Search: `https://music.youtube.com/search?q=<query>` with commit
- Find play buttons: `document.querySelectorAll('[aria-label*=Play]')`
- Check playback: `document.querySelector('[aria-label*=Pause]')` — returns button with song name when playing

### YouTube (youtube.com)
- Standard `wait_until="domcontentloaded"` works reliably
- Search: `https://youtube.com/results?search_query=<query>`
- Video titles: `document.querySelectorAll('#video-title')` — `.first.click()` to play

## Key Fixes Applied to Bridge

1. **Websockets 16.x API**: `process_request(connection, request)` not `(path, headers)`. Return `Response` objects for 404s.
2. **WebSocket upgrades**: CDP port must let upgrades through — check `Upgrade: websocket` header before returning 404.
3. **Force-detach before attach**: On `Target.setAutoAttach`, detach first (via `chrome.debugger.detach`) then attach.
4. **Internal Playwright**: Bridge connects its own Playwright to the CDP port it just started.
