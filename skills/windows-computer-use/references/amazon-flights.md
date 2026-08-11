# Amazon.in Flights — CDP Bridge (Corrected Workflow)

**This user's established workflow is CDP Bridge first, NEVER pre-open Chrome.**
This was corrected multiple times in session 20260727. Follow the exact step order below.

## CORRECTED WORKFLOW: Bridge FIRST, Then Navigate

**CRITICAL**: Do NOT open Chrome before starting the bridge. Pre-opening Chrome creates
unmanaged tabs outside the Playwright extension's tab group — those tabs are invisible
to the bridge and cannot be controlled via Playwright/TCP commands. The bridge opens
Chrome itself.

### Correct step order:

### Step 1: Kill any existing Chrome
```bash
powershell.exe -Command "Get-Process chrome | Stop-Process -Force"
```

### Step 2: Grab token
```bash
TOKEN=$(grep -oP 'PLAYWRIGHT_MCP_EXTENSION_TOKEN=\\K.*' ~/Work/creds/playwright-mcp-token.md)
```

### Step 3: Start bridge (background)
```bash
TOKEN='<token>'; python3 ~/.hermes/skills/windows-computer-use/scripts/cdp-bridge.py --port 9350 --token "$TOKEN"
```
Bridge starts Chrome automatically with the extension connect page, then outputs:
```
Internal Playwright connected. Command port: 9351
```

### Step 4: Navigate the managed page to search results via URL shortcut

Navigate `ctx.pages[0]` (the managed connect page) directly via `page.goto()`.
This is the ONLY reliable approach — see pitfalls below for what doesn't work.

### Step 4a: Bring tab to focus (user wants to see it on screen)

After navigation, if the user asks to see the page ("show me", "bring it on focus"):

```python
import socket
s = socket.socket(); s.settimeout(10)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.bring_to_front()\n')
print(s.recv(8192).decode())
s.close()
```

This activates the Playwright-managed tab in the Chrome window — the window title
updates immediately to reflect the managed page's URL (e.g. "Flight Bookings on
Amazon" → actual search page title).

Amazon Flights URL search pattern (use this directly — skip the homepage entirely):
```
/flights/search/<FROMCODE>_<FROMCITY>_<COUNTRY>/<TOCODE>_<TOCITY>_<COUNTRY>/1/0/0/E/<YYYY-MM-DD>/?uc=YES
```

Example — Guwahati → Bengaluru on Aug 2, 2026 (needs 45s+ timeout — Amazon is slow):
```python
import socket
s = socket.socket(); s.settimeout(50)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.goto("https://www.amazon.in/flights/search/GAU_Guwahati_IN/BLR_Bengaluru_IN/1/0/0/E/2026-08-02/?uc=YES", timeout=45000)\n')
print(s.recv(16384).decode())
s.close()
```

### Step 5: Read results via TCP command server
```python
import socket, time
time.sleep(4)  # Wait for page JS to render flight data
s = socket.socket(); s.settimeout(20)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.evaluate("document.body.innerText")\n')
r = s.recv(65536).decode()
print(r)  # Flight data is in the page text
s.close()
```

### Step 6: Kill bridge when done
```bash
pkill -f cdp-bridge.py
```

## CRITICAL: CDP Bridge First, Not UIA

This was specifically corrected by the user (multiple times in this session). The rules:

1. **Do NOT open Chrome before the bridge.** Kill all Chrome processes first →
   start bridge (Chrome opens automatically via the extension connect page) →
   navigate the managed page (`ctx.pages[0]`) via `page.goto()`.
2. **Do NOT use `window.open()` to open a new tab.** The tab appears in Chrome but
   the bridge/Playwright doesn't auto-attach the debugger — the tab is invisible
   to the TCP command server. `page.goto()` on the existing managed page is the
   correct approach.
3. **Do NOT use UIA invoke/click on browser form widgets.** That was explicitly
   rejected. The flight search widget uses React components that are opaque to UIA.
4. **Amazon/Google Flights needs 45s+ timeout** on `page.goto()`.
   Use `timeout=45000` explicitly.
5. **If `page.goto()` times out and the session drops**, kill bridge + Chrome and
   restart fresh — the session is irrecoverable once the extension disconnects.
6. **After navigating to the search URL, wait 4s+** before reading
   `document.body.innerText` — the page needs time to render the search results
   after the navigation completes.
7. **`page.bring_to_front()` activates the Playwright tab but doesn't guarantee
   the Chrome window is topmost** — use `winapp ui screenshot -w <HWND> --focus`
   if the user explicitly needs the window brought to foreground.

## Amazon Flights URL Shortcut Patterns

| Route | Pattern |
|-------|---------|
| GAU → BLR | `/flights/search/GAU_Guwahati_IN/BLR_Bengaluru_IN/1/0/0/E/YYYY-MM-DD/?uc=YES` |

## UIA-only workflow (fallback — read-only text extraction)

If the bridge is unavailable and you just need to READ the page content (not interact):

```
1. Open URL          → Start-Process chrome 'https://www.amazon.in/flights'
2. Read page         → winapp ui get-value RootWebArea -w <HWND>
3. Trigger search    → winapp ui invoke <recent-search-group> -w <HWND>
4. Read results      → winapp ui get-value RootWebArea -w <HWND>
```

NOTE: UIA is read-only fallback. For interactive tasks (filling forms, clicking Book
buttons), use the CDP bridge. The user has explicitly rejected UIA for browser form
interaction.

## Key techniques

### 1. Recent Searches shortcut (UIA only, read-only)

The page caches previous searches in a "Recent Searches" section. Each entry is a
`Group` with text labels (origin, destination, date, "Search"). These Groups support
`InvokePattern` — clicking them triggers the full search for that route+date combo
without filling any form fields.

UIA tree shape (slugs are per-session — use `inspect` to find current ones):
```
grp-b4a7 Group (1445,568 64x31)          ← clickable Search button
  lbl-search-b5e4 Text "Search"
```

**Finding the right recent search**: Read the text above the Group to verify route + date.
Look for labels like:
```
lbl-guwahati-b5e1 Text "Guwahati"
lbl-bengaluru-b5e2 Text "Bengaluru"
lbl-mon3rdaug-b5e3 Text "Mon, 3rd Aug"
```

### 2. Reading search results

After triggering a search, `get-value RootWebArea` returns the full results page
including all flight listings. The text format is structured enough to parse manually:

```
Airline | Departure | Duration | Stops | Arrival | Price | Discount
IndiGo  | 23:10     | 9h 20m  | 1 stop| 08:30   | ₹8,698| ₹400 off
```

Filter sidebar items, airline counts, and layover info are all readable as UIA text labels.

### 3. Pre-filled form values

If the user has searched from/to these airports before, the origin/destination fields
are pre-filled on page load. The date may default to a previous selection — check the
date label.

## UIA tree structure (search form)

Key elements visible at --depth 12:

```
RootWebArea Document "Flight Bookings on Amazon"
  radioId-oneWay-tripTypeRadio  RadioButton "One Way"
  radioId-roundTrip-tripTypeRadio RadioButton "Round Trip"
  
  grp-bc68 Group                 ← From airport
    lbl-gau-b5c9 Text "GAU"
    lbl-guwahati-b5ca Text "Guwahati"
  
  grp-bc6f Group                 ← To airport
    lbl-blr-b5cb Text "BLR"
    lbl-bengaluru-b5cc Text "Bengaluru"
  
  grp-bc78 Group                 ← Date
    lbl-31jul-b5cd Text "31 Jul"
    lbl-fri-b5ce Text "Fri"
  
  grp-bc83 Group                 ← Travellers
    lbl-01-b5d0 Text "01"
    lbl-travellers-b5d1 Text "Travellers"
    lbl-economy-b5d4 Text "Economy"
  
  btn-search-b47f Button "Search"
  
  lbl-recentsearches-b4ae Text "Recent Searches"
```

## Pitfalls

- **`page.bring_to_front()` only activates the Playwright tab, not the Chrome window**: After calling `page.bring_to_front()`, the window title updates to show the Playwright-managed page's URL, but the Chrome window may still be behind other windows. If the window is behind other apps, use UIA screenshot with --focus to bring it forward.

- **Window title may show a different page initially**: The Chrome window title reflects the active tab. If there are unmanaged tabs open in the same window, the title may show a different page until `page.bring_to_front()` is called.

- **Slugs are per-session**: The hex suffixes (e.g. `-b5cd`) change on every page load.
  Always `inspect --depth 12` to find current slugs before interacting.
- **Search button may be offscreen**: When the page first loads, the main Search button
  (`btn-search-b47f`) shows as `[offscreen]` in the UIA tree. Use the Recent Searches
  section's Group elements instead — they're usually in the visible viewport.
- **Results page is long**: `get-value RootWebArea` returns the entire page including
  footer, ads, and recommendations. Parse the flight data section from the output manually
  — search results appear between the filter sidebar and "Buy it again".
- **One Way vs Round Trip**: The default trip type may differ per session. Check
  `radioId-oneWay-tripTypeRadio` state before searching.
- **Amazon session required**: The user must be logged into Amazon.in for the flights
  widget to work. Anonymous access redirects to login.
- **Do NOT navigate the connect page to a slow site without 45s+ timeout** —
  Amazon.in will time out with the default 30s timeout and drop the extension session.
  Always use explicit `timeout=45000` for Amazon/Google Flights.
