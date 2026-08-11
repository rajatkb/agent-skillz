# Chrome Browser — UIA Selectors & Extension CDP Setup (V2)

The single reference for anything Chrome-related on Windows. Three layers: **UIA** (headless reading), **CDP via extension V2** (full DOM, sustained session), and **URL shortcuts** (skip UI entirely).

## Working Summary

**Goal**: Control a Chrome tab on Windows from Hermes in WSL — click, type, navigate, read DOM. Sustained session, no disconnects.

**How it works**: The Playwright MCP Bridge extension's **protocol V2** (activated by `&protocolVersion=2` in the connect URL) allows `chrome.tabs.create`, `chrome.debugger.attach/detach`, and `chrome.debugger.sendCommand` directly. The bridge script in WSL connects extension ↔ CDP, and also runs an internal Playwright instance + TCP command server for sustained sessions.

**Flow**:
1. Start bridge with `--token` — extension auto-connects in V2 mode
2. Bridge connects internal Playwright to its own CDP endpoint
3. TCP command server starts on `CDP_PORT + 1`
4. Send one-line Python commands via socket, get results with `---CMD-END---` delimiter
5. Single session stays alive — no reconnect overhead

**Token**: At `~/Work/creds/playwright-mcp-token.md`. Extracted via UIA from the extension connect page's `PLAYWRIGHT_MCP_EXTENSION_TOKEN=` text. Changes on extension reinstall.

## 1. URL Shortcut Patterns (always try first)

**WARNING**: `Start-Process chrome '<url>'` creates tabs OUTSIDE the Playwright extension's
managed tab group. Only use this for UIA-based read-only tasks (get-value RootWebArea).
For CDP bridge tasks, do NOT pre-open Chrome — start the bridge first (it opens Chrome),
then navigate via TCP commands.

One `Start-Process` replaces all UI interaction (read-only UIA use):
```powershell
Start-Process chrome -ArgumentList 'https://google.com/search?q=<query>'
Start-Process chrome -ArgumentList 'https://google.com/maps/dir/<from>/<to>'
Start-Process chrome -ArgumentList 'https://youtube.com/results?search_query=<query>'
Start-Process chrome -ArgumentList 'https://amazon.in/s?k=<query>'
```

Amazon Flights URL search pattern (use this directly, skip the homepage):
```
https://www.amazon.in/flights/search/GAU_Guwahati_IN/BLR_Bengaluru_IN/1/0/0/E/2026-08-02/?uc=YES
```
Pattern: `/flights/search/<FROMCODE>_<FROMCITY>_<COUNTRY>/<TOCODE>_<TOCITY>_<COUNTRY>/1/0/0/E/<YYYY-MM-DD>/`
Note: Amazon Flights needs 45s+ timeout on `page.goto()`.

Google Flights URL pattern for one-way price comparison:
```
https://www.google.com/travel/flights?q=Flights+to+<TO>+from+<FROM>+on+<YYYY-MM-DD>+one+way
```
Example: `?q=Flights+to+BLR+from+GAU+on+2026-08-02+one+way`
Returns structured pricing across all OTAs + airlines. Use `page.evaluate("document.body.innerText")` to read the price list.

## 2. UIA Element Selectors (headless Windows interaction)

| Element | Selector | Capabilities |
|---------|----------|-------------|
| Address bar (omnibox) | `view_1012` or search "Address and search bar" | `set-value` for text entry |
| Page content | `RootWebArea` (Document) | `get-value` (read all text), `scroll` |
| New tab button | Search "New tab" → `btn-newtab-<hash>` | `invoke` |
| Tabs | Search page title → `tab-<title>-<hash>` | `invoke` via SelectionItemPattern |
| Tab close buttons | Each tab has `btn-close-<hash>` as child | `invoke` to close that tab |
| Window close | `view_4` | `invoke` to close window |
| Back/Forward/Reload/Home | `view_1001-1004` | Display-only — no invoke |

**Limitations**: Back/Forward/Reload have no invoke. Context menus invisible to UIA. Slugs change on page load.

## 3. CDP via Playwright MCP Bridge Extension (V2 protocol)

### Architecture

```
┌──────────────┐  TCP command   ┌───────────┐  V2 relay     ┌───────────────┐
│  TCP client  │ ◄─── port ───► │  bridge   │ ◄──────────► │  Chrome ext.  │
│  (my script) │   CMD+RESP     │  server   │  chrome.* API │  (debugger)   │
└──────────────┘                └──────┬────┘               └───────────────┘
                                       │ internal Playwright
                                       │ (sustained session)
                                  ┌────▼────┐
                                  │ CDP WS  │
                                  └─────────┘
```

### Setup & Start

**Prerequisites**: WSL mirrored networking, Playwright MCP Bridge extension installed (ID: `mmlmfjhmonkocbjadbfplnigmagldckm`), token file at `~/Work/creds/`.

```bash
TOKEN=$(grep -oP 'PLAYWRIGHT_MCP_EXTENSION_TOKEN=\K.*' ~/Work/creds/playwright-mcp-token.md)
python3 ~/.hermes/skills/windows-computer-use/scripts/cdp-bridge.py --port 9350 --token "$TOKEN"
```

Bridge output:
```
CDP Bridge (V2) running on ws://127.0.0.1:9350
Internal Playwright connected. Command port: 9351
```

### TCP Command Server

Send one-line Python expressions to the command port. Available in scope: `page`, `ctx`, `browser`, `asyncio`, `json`.

```bash
# Get page title
python3 -c "import socket;s=socket.socket();s.settimeout(10);s.connect(('127.0.0.1',9351));s.sendall(b'await page.title()\n');print(s.recv(8192).decode());s.close()"
# → Google
# → ---CMD-END---

# Navigate
python3 -c "import socket;s=socket.socket();s.settimeout(15);s.connect(('127.0.0.1',9351));s.sendall(b'await page.goto(\"https://google.com\", timeout=10000)\n');print(s.recv(8192).decode());s.close()"

# Type into a field
python3 -c "import socket;s=socket.socket();s.settimeout(10);s.connect(('127.0.0.1',9351));s.sendall(b'await page.locator(\"textarea[name=q]\").fill(\"hello\")\n');print(s.recv(8192).decode());s.close()"

# Click a button by text
python3 -c "import socket;s=socket.socket();s.settimeout(10);s.connect(('127.0.0.1',9351));s.sendall(b'await page.get_by_text(\"One Way\").first.click()\n');print(s.recv(8192).decode());s.close()"
```

**Important**: The session is sustained — `page` is the same tab across commands. No reconnection needed.

**CRITICAL — `window.open()` does NOT create Playwright-managed tabs**: Using
`page.evaluate("window.open(url, '_blank')")` opens a new tab in Chrome, but the bridge's
Playwright does NOT auto-detect or auto-attach the debugger to it. The new tab is invisible
to the TCP command server — `ctx.pages` count won't increase and the new tab can't be
controlled. Always use `page.goto()` on the existing managed page instead. This was
explicitly corrected by the user.

**Quote escaping tip**: The TCP server uses `exec(f"async def _f():\n    return {line}")`.
This means backslash-escaped quotes (`\"`) in JSON strings cause Python syntax errors.
**Use single quotes for JS eval strings**:
```python
# WRONG — double quotes cause Python syntax error
await page.evaluate("document.querySelector(\"input[name=q]\")")
# RIGHT — single quotes work
await page.evaluate("document.querySelector('input[name=q]')")
```
For complex commands with multiple statements, write a helper `.py` file with `write_file`
and run it — avoids all quoting issues.

### V2 Protocol Commands

The extension's V2 handler accepts these commands over the relay WebSocket:

| Command | What it does |
|---------|-------------|
| `chrome.tabs.create` | Creates a real Chrome tab in the Playwright group |
| `chrome.tabs.remove` | Closes a tab |
| `chrome.debugger.attach` | Attaches debugger to a tab |
| `chrome.debugger.detach` | Detaches debugger (WORKS in V2) |
| `chrome.debugger.sendCommand` | Sends any CDP command to an attached tab |

Events from extension:
- `extension.initialized` — sent when V2 handler starts
- `chrome.tabs.onCreated` — sent when user drags a tab into the group
- `chrome.debugger.onEvent` — CDP events forwarded from Chrome

### Token Extraction (first-time or after reinstall)

```powershell
# 1. Start bridge WITHOUT token
python3 ~/.hermes/skills/windows-computer-use/scripts/cdp-bridge.py --port 9350

# 2. Find the Chrome HWND
$hwnd = (winapp ui list-windows | Select-String 'Google Chrome').Line -replace '.*HWND (\d+).*', '$1'

# 3. Grab the token from the UIA tree
winapp ui inspect -w $hwnd --depth 15 2>&1 | grep PLAYWRIGHT_MCP_EXTENSION_TOKEN
# → "PLAYWRIGHT_MCP_EXTENSION_TOKEN=<value>"

# 4. Save
echo "PLAYWRIGHT_MCP_EXTENSION_TOKEN=<value>" > ~/Work/creds/playwright-mcp-token.md
```

## 4. Interaction Strategies (custom React widgets)

Not all pages use standard HTML inputs. Amazon Flights uses a custom React widget with obfuscated class names. Strategy priority:

### Layer 1 — Read text, click text (the golden rule)
Before any CSS selector or ARIA role hunting, try this: read the page text, then click the visible label. Works on React, Shadow DOM, custom widgets — anything that displays text to the user.

```python
# Read the page to find what's visible
text = await page.inner_text('body')

# Click by visible text — no selectors needed
await page.get_by_text("One Way").first.click()
await page.get_by_text("Guwahati, India").first.click()
await page.get_by_text("Search").first.click()
await page.get_by_text("We Don't Talk Anymore").first.click()
```

**Why it works**: Every UI has text labels. CSS classes get obfuscated (React CSS modules), ARIA roles get omitted, but the text "One Way" or "Guwahati" is always displayed. `get_by_text()` finds the element at the rendering layer, not the DOM layer.

**Click-then-find pattern**: Some forms only reveal input fields after clicking a text label.
```python
# Click the "From" city text → reveals hidden input
await page.get_by_text("From").first.click()
# Now type into the revealed input
await page.keyboard.type("Guwahati", delay=30)
# Click the suggestion
await page.get_by_text("Guwahati, India").first.click()
```

### Layer 2 — URL parameters (zero interaction)
If the page has a URL pattern, navigate directly. Amazon Flights:
```
/flights/search/FROM_TO/1/0/0/E/2026-07-31/
```

### Layer 2 — Playwright locators
First try standard locators. If they find nothing:
```python
page.get_by_role("button", name="Search").count()
page.get_by_role("combobox").count()
page.get_by_text("One Way").first.click()
```

### Layer 3 — Click-then-find
Some widgets reveal form fields only after clicking (e.g., clicking the "From" city selector reveals `input[placeholder="Select Airport"]`). Pattern:
```python
# Click on the widget area
await page.get_by_text("From").first.click()
# Now the input appears
await page.keyboard.type("Guwahati", delay=30)
await page.get_by_text("Guwahati, India").first.click()
```

### Layer 4 — Screenshot + NPU vision (last resort)
Use `process(poll)` to check bridge status after failed navigation.

## 5. Site-Specific Navigation Patterns

### YouTube Music (music.youtube.com)
- **Navigation**: Use `wait_until="commit"` instead of `wait_until="domcontentloaded"` — YT Music's SPA hangs on full DOM load via CDP
- **Search**: `https://music.youtube.com/search?q=<query>` with `wait_until="commit"`
- **Playing music**: Look for `[aria-label*=Play]` buttons after search → click the playlist or song button
- **Check playback**: `document.querySelector('[aria-label*=Pause]')` returns the Pause button with song name when playing (e.g. `Pause What Makes You Beautiful - One Direction`)
- **Dialog handling**: YT Music may show JS alerts/dialogs on navigation — suppress with `page.on("dialog", lambda d: d.accept())` before navigating
- **Cross-origin**: Navigating FROM YT Music to another domain drops the CDP session. Restart bridge fresh for each target URL.

### YouTube (youtube.com)
- **Fast and reliable**: Works with standard `wait_until="domcontentloaded"`
- **Search**: `https://youtube.com/results?search_query=<query>`
- **Video titles**: Use `document.querySelectorAll('#video-title')` to find video titles, then `.first.click()` to play
- **Works reliably** from extension connect page navigation

## 6. Known Limitations

| Issue | Cause | Workaround |
|-------|-------|------------|
| Cross-origin navigation fails | Extension debugger detaches on domain change | Navigate directly to target URL, avoid hops |
| Slow page load kills debugger | Extension timeout during long nav | Use URL parameters instead of form interaction |
| TCP command quoting issues | `exec()` inside bridge handles escaping poorly | Use single quotes in JS eval strings, or write helper script files |
| Extension reinstall changes token | New install = new token | Re-extract via UIA |

## 6. What Didn't Work (dead ends)

- `--remote-debugging-port=9222`: Chrome 136+ ignores on default profile
- `chrome://inspect/#remote-debugging`: MCP relay protocol, not standard CDP
- `browser.new_page()` / `ctx.new_page()`: Both blocked by extension
- V1 protocol (`attachToTab` + `forwardCDPCommand`): No tab creation, no proper detach
- OpenClaw extension not yet tested: Available as alternative if V2 limits bite

## 7. Comparison: Playwright MCP Bridge vs OpenClaw

| Feature | Playwright MCP Bridge (V2) | OpenClaw Browser Relay |
|---------|---------------------------|----------------------|
| Tab creation | ✅ `chrome.tabs.create` | ✅ Per-tab sessions |
| Cross-origin navigation | ⚠️ May fail silently | ✅ Auto-reattach |
| Sustained session | ✅ TCP command server | ✅ OpenClaw daemon |
| Multi-tab | ⚠️ One tab per session | ✅ Multiple tabs |
| Token required | ✅ Auto-approve via URL | ✅ Pairing string |
| Chrome Web Store | ✅ Installed | ID: `nglingapjinhecnfejdcpihlpneeadjp` |
