# Google Flights — Price Comparison via CDP Bridge

Used to compare flight prices across platforms (Amazon, MakeMyTrip, airline direct).
Works from the same bridge session as Amazon Flights — just navigate `page.goto()` to
the Google Flights URL while staying under the Playwright-managed tab.

## URL Shortcut Pattern

One-way search for a specific date:
```
https://www.google.com/travel/flights?q=Flights+to+<TO>+from+<FROM>+on+<YYYY-MM-DD>+one+way
```

Example — Guwahati to Bengaluru on Aug 3, 2026:
```
https://www.google.com/travel/flights?q=Flights+to+BLR+from+GAU+on+2026-08-03+one+way
```

The `+one+way` suffix forces one-way mode instead of the default round trip.

## Workflow

### Navigate to Google Flights
```python
import socket
s = socket.socket(); s.settimeout(50)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.goto("https://www.google.com/travel/flights?q=Flights+to+BLR+from+GAU+on+2026-08-03+one+way", timeout=45000)\n')
print(s.recv(16384).decode())
s.close()
```

### Bring tab to focus (user wants to see it)
```python
import socket
s = socket.socket(); s.settimeout(10)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.bring_to_front()\n')
print(s.recv(8192).decode())
s.close()
```

### Read results (wait 4-6s for page to render async content)
```python
import socket, time
time.sleep(5)
s = socket.socket(); s.settimeout(20)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.evaluate("document.body.innerText")\n')
r = s.recv(65536).decode()
print(r)  # Results include airline, times, duration, price, stops, emissions
s.close()
```

## Filtering to Non-stop (via Playwright locators)

When the user wants only non-stop flights, click filter elements by visible text:

```python
import socket, time

# Click "Stops" to open the filter dropdown
s = socket.socket(); s.settimeout(10)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.get_by_text("Stops").first.click()\n')
print(s.recv(8192).decode())
s.close()

time.sleep(1)

# Click "Nonstop" to apply the filter
s = socket.socket(); s.settimeout(10)
s.connect(('127.0.0.1', 9351))
s.sendall(b'await page.get_by_text("Nonstop").first.click()\n')
print(s.recv(8192).decode())
s.close()
```

After filtering, the header shows "All filters (1)" and results update to only
non-stop flights. Read `document.body.innerText` after ~3s to get filtered results.

## Output structure

Google Flights results text is well-structured:

```
Cheapest
from ₹8,240

5:35 PM  –  12:25 AM+1
Air India
6 hr 50 min
GAU–BLR
1 stop
1 hr 15 min DEL
269 kg CO2e
+58% emissions
₹8,300

...

4:55 PM  –  8:25 PM
Akasa Air
3 hr 30 min
GAU–BLR
Nonstop
137 kg CO2e
-19% emissions
₹11,398
```

Each flight entry follows this pattern:
- `Departure time  –  Arrival time`
- `Airline name` (may include connecting carrier like `Air India ExpressAir India`)
- `Duration` (e.g. `3 hr 20 min`)
- `GAU–BLR` (route display)
- `Nonstop` / `1 stop` (+ layover airport code and duration)
- `CO2 emissions info`
- `₹Price` (in INR, with comma separators)

"Best" flights appear first (sorted by Google's ranking), "Other flights" below.

## Price comparison with Amazon

When comparing Amazon vs Google Flights prices, note:

| Difference | Cause |
|------------|-------|
| Google's prices may differ by ₹100-₹800 | Different OTA/airline inventory allocations |
| Amazon shows ₹400-₹420 "off" per booking | Amazon-specific discount |
| Both platforms show **published airline fares** | Base fare is the same — differences come from platform offers/cashback |

Verified from session 20260727: the ₹8,240 Air India 1-stop on Google Flights was
not available on Amazon at that exact price — Amazon showed ₹8,698 for the same
route via different airlines.

## Multi-date comparison pattern

Navigate sequentially for the same route on different dates:
```python
# Monday
await page.goto("https://www.google.com/travel/flights?...on+2026-08-03+one+way", ...)
# Read results
await page.goto("https://www.google.com/travel/flights?...on+2026-08-04+one+way", ...)
# Read results
```

Note: each `page.goto()` replaces the previous page content. Read results before
navigating to the next date.

## Pitfalls

- **Round trip by default**: Google Flights defaults to round trip mode. Always
  append `+one+way` to the URL query to force one-way mode.
- **Emission figures in output**: The text includes CO2 emission estimates per
  flight — parse carefully when extracting price data.
- **"Fetching results" state**: On some queries, Google shows "Fetching results"
  with the cheapest price shown separately. Wait 5-6s before reading.
- **Price tracking overlay**: A "Track prices" card may overlay near the top
  results. The flight data is below it.
- **Same 45s+ timeout rule applies**: Google Flights can be slow to respond.
  Use `timeout=45000` just like Amazon.
- **Cross-origin navigation**: Navigating from Amazon to Google Flights is a
  domain change. The V2 extension keeps the WebSocket alive, but the CDP session
  may be invalidated — always restart if `page.goto` or `page.evaluate` fails
  after navigation.
