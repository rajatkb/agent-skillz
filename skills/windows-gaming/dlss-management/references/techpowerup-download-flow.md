# TechPowerUp DLSS Download Flow (verified Aug 2026)

Downloads the latest (or pinned) DLSS DLL zip without browser interaction. Three-step: GET → POST → follow redirect with plain GET.

## Pages

| DLL | Page slug |
|---|---|
| Super Resolution (`nvngx_dlss.dll`) | `nvidia-dlss-dll` |
| Frame Generation (`nvngx_dlssg.dll`) | `nvidia-dlss-3-frame-generation-dll` |
| Ray Reconstruction (`nvngx_dlssd.dll`) | `nvidia-dlss-3-ray-reconstruction-dll` |

Base: `https://www.techpowerup.com/download/<slug>/`

## Step 1 — GET the page, parse latest version id

The page lists versions newest-first as `<form class="download-version-form">` blocks containing `<input type="hidden" name="id" value="3187">`. **First form = newest version.**

```bash
curl -sL "https://www.techpowerup.com/download/nvidia-dlss-dll/" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -o page.html
# extract: re.findall(r'<form action="[^"]*" method="POST" class="download-version-form">(.*?)</form>', html, re.S)
# then first form's re.search(r'name="id" value="(\d+)"')
```

## Step 2 — POST id + server_id, capture redirect (NO -L!)

```bash
DLURL=$(curl -s -o /dev/null -w "%{redirect_url}" \
  -X POST "https://www.techpowerup.com/download/nvidia-dlss-dll/" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  -d "id=3187&server_id=5")
```

`redirect_url` looks like `https://uk1-dl.techpowerup.com/files/<token>/<ts>/nvngx_dlss_310.7.0.zip`

## Step 3 — plain GET the mirror URL

```bash
curl -s -o nvngx_dlss_310.7.0.zip "$DLURL" -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
# expect HTTP 200, content-type application/zip, PK\x03\x04 magic
```

## Mirror ids

- `15` = TechPowerUp SG ("closest to you" for this user)
- `5` = TechPowerUp GB
- `25` = TechPowerUp DE

Any works; load shown on page. Use one consistently.

## Pitfalls (all observed)

- **`curl -L` on the POST → HTTP 405 Not Allowed.** The mirror rejects re-POSTed redirects. Always capture `redirect_url` with `-o /dev/null -w "%{redirect_url}"` first, then GET it separately.
- Page HTML must be fetched with a desktop UA; mobile/absent UA can get different markup.
- Zip filename encodes the version (`nvngx_dlss_310.7.0.zip`) — usable as the applied-version record after extraction.
- Zip contains exactly the one DLL matching the page (extract `nvngx_dlss.dll` from SR zip, `nvngx_dlssg.dll` from FG zip, `nvngx_dlssd.dll` from RR zip).
- Version ids differ per page (SR 3187, FG 3186, RR 3185 for 310.7.0) — never reuse an id across pages.

## Verification after applying

Read back the applied DLL's version via PowerShell `VersionInfo.FileVersion` (returns `310,7,0,0`) and compare as tuple. Use the script-file pattern, not inline `-Command`.
