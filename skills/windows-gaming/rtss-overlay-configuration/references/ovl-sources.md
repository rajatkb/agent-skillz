# OVL / dual-OSD sources (researched Aug 2026)

Key claim: loading an `.ovl` in OverlayEditor does NOT disable the classic OSD — the "old default layout" that persists is the client-driven classic OSD (usually MSI Afterburner's), a separate rendering path.

## Sources

1. **Guru3D — RTSS Overlay Editor Megathread**
   https://forums.guru3d.com/threads/rtss-overlay-editor-megathread.436443/
   - *"That's because the overlay you see is not from Overlay Editor but from another Tool. i.E MSI Afterburner. Deactivate it in MSI Afterburner Settings."*
   - *"Capture Indicator for Screenshots/Video Recording is on the wrong position! The Capture Indicator will always show up in the Topmost Layer!"*
   - Note: guru3d forums are Cloudflare-walled for curl/jina readers — pull quotes via search snippets or the Reddit mirror.

2. **Reddit r/pcmasterrace — "I tried to make a custom overlay in RTSS but I can't remove the old overlay on the left"** (Sep 2024)
   https://www.reddit.com/r/pcmasterrace/comments/1f7vgku/
   - *"I had the same thing. Apparently, the overlay on the left side is because of MSI afterburner. So you gotta go to MSI afterburner and turn the 'OSD' off for the respective parameters. I didn't want to turn them off completely, so just unchecked the on screen display option."*
   - Fix: Afterburner → Settings → Monitoring tab → uncheck "Show in On-Screen Display" per entry.
   - Note: reddit `.json` endpoints now serve the HTML theme instead of JSON (old.reddit also blocked); extract via search snippets or a reader proxy.

3. **WCCFTech — "How to Set Up High-Quality Performance Overlays with RTSS"**
   https://wccftech.com/how-to-set-up-high-quality-performance-overlays-with-rtss/
   - Load path: RTSS → Setup → Plugins tab → check OverlayEditor.dll → double-click → switch to Layouts → Load → pick `.ovl` from `RTSS install dir\Plugins\Client\Overlays`.
   - RTSS needs **Show On-Screen Display** ON for the OSD to render at all.

4. **MSI Afterburner blog — On Screen Display, Monitoring and Features**
   https://www.msi.com/blog/msi-afterburner-on-screen-display
   - *"Double-click to open [OverlayEditor], and the OSD shows without a game or benchmark running. But it blocks adjusting zoom and other settings in the main RTSS window."* — explains the OverlayEditor-blocks-zoom pitfall; close the editor before tweaking main-window settings.

## Access notes (Aug 2026 environment)
- `web_extract` backend is search-only (ddgs) — returns "search-only backend cannot extract URL content"; use curl + a reader proxy (r.jina.ai) or search snippets.
- guru3d forums: Cloudflare challenge blocks direct curl AND r.jina.ai. Reddit: `www.reddit.com/<permalink>.json` and `old.reddit.com` both serve HTML now. Get the content from `web_search` description snippets — they carry the operative quotes.
