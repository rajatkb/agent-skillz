# Workflow Reference: Direct Hermes-driven rutor search + magnet send

This is the preferred non-interactive workflow. Used for the user: RAJAT, who uses this frequently.

## Full sequence (as executed in session)

### Step 1: Determine exact game name
The user may give a colloquial name (e.g. "new Halo Combat Evolve Remake of 2026").
- Search web first to find the exact release name: **"Halo: Campaign Evolved"**
- Note the repacker preference: **InsaneRamZes** (Portable releases)

### Step 2: Search rutor with retry
rutor.info is unreliable. Curl from WSL, retry loop:
```bash
for i in 1 2 3 4 5; do
  sz=$(curl -sL --max-time 10 \
    "https://rutor.info/search/0/0/000/0/$(python3 -c 'import urllib.parse; print(urllib.parse.quote("Campaign Evolved"))')" \
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" \
    | wc -c)
  echo "[$i] $sz bytes"
  [ "$sz" -gt 1000 ] && break
  sleep 3
done
```

### Step 3: Parse results
Pipe curl output to Python:
```python
import sys, re, html as h
data = sys.stdin.read()
rows = re.findall(r'<tr class="(?:gai|tum)">(.*?)</tr>', data, re.DOTALL)
for r in rows:
    t = re.search(r'href="/torrent/\d+/[^"]*">(.*?)</a>', r)
    m = re.search(r'href="(magnet:\?[^"]+)"', r)
    title = h.unescape(t.group(1)) if t else 'N/A'
    is_irz = 'InsaneRamZes' in title
    mag = m.group(1) if m else ''
    # ... report to user, identify IRZ match
```

### Step 4: Send magnet to qBittorrent
```powershell
powershell.exe -NoProfile -Command "Start-Process 'magnet:?xt=urn:btih:...'"
```

### Step 5: Confirm
Tell the user what was sent (title, size, repacker). No further action needed.

## Search-term narrowing strategy (when 0 results)

| If full name fails... | Try... |
|----------------------|--------|
| "Halo Combat Evolved Remake 2026" | "Campaign Evolved" |
| Includes year | Drop year |
| Has subtitle | Drop subtitle, try franchise only |
| Too many words | Try 2-3 word core |

## Known rutor quirks
- Category `8` = Games. Search without category filter (`0`) works fine
- Search method `0` = exact phrase. If that fails, try `1` = all words
- Results are max 2000, paginated
- The search page URL format is fragile — changing parameters can return 0 results silently
