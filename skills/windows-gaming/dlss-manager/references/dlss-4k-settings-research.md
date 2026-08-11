# DLSS 4K settings research (research.py session, Aug 2026)

Source session: `~/.hermes/crawl_sessions/best-dlss-4-5-settings-for-4k-gaming-per-game-which-quality-/`
(read `05_synthesis/findings.md` + `03_notes/` for quote receipts).

## Verified conclusion

**No official per-game DLSSTweaks config exists.** DLSSTweaks is a community tool
(emoose/Nexus mod 550); there is no per-game official table of scaling ratios or
presets. What exists is resolution-level guidance + per-game community threads.
The crawler's own open-questions section confirmed this — treat "no official per-game
recommendation" as a verified negative, not an assumption.

## Resolution-level guidance (well documented, multi-source)

| Mode | Render scale @4K | Internal res | Notes |
|---|---|---|---|
| DLAA | 100% | 4K | native res + AI AA; DLSSTweaks can force it on DLSS-only games |
| Quality | 66.7% | 3200×1800 | go-to for 4K; recommended for 4K monitors (TechSpot, BenQ, so-nerdy) |
| Balanced | 58% | ~2480×1395 | viable at 4K, little texture loss vs Quality |
| Performance | 50% | 1080p | **at 4K, near-zero texture/quality loss vs Quality**; very viable (TechSpot) |
| Ultra Performance | 33.3% | 720p | "ultra frames, not ultra quality"; only at 4K when fps is critical; DLSS 4.5 Preset L makes it usable |

- Each step down (Quality→Balanced→Performance) ≈ **10–15% fps** at higher resolutions.
- **Below 4K (1440p/1080p), Performance is NOT recommended** — fine detail degrades;
  stick to Quality (1080p) / Performance is the 1440p sweet spot.
- DLSS 4.5 Ultra Performance ≈ DLSS 4 Quality in image quality (gamegpu claim).

## Preset mapping (DLSS 4.5)

- **K** = 1st-gen transformer (DLSS 4.0 era; default for Quality/Balanced/DLAA in older games)
- **M** = 2nd-gen transformer, tuned for **Performance** mode
- **L** = 2nd-gen transformer, tuned for **Ultra Performance**; recommended for UHD output

NoobFeed numbers (**tested on RTX 5070 Ti — the user's exact GPU**, Cyberpunk 2077 @4K):
- L vs M: L costs ~3–6% fps but better visuals; ~1–2 fps slower in Quality/Balanced, ~same in Performance.
- Preset L @ 4K Ultra Performance (720p→4K, 3× upscale) is the "great at ultra performance" case.

## DLSSTweaks ini mechanics (what the knobs do)

- `[DLSS] ForceDLAA` — force DLAA on DLSS-only games.
- `[DLSSQualityLevels] Enable=true` + per-mode ratios — custom scaling ratios per mode
  (e.g. "Ultra Quality at 80%").
- `[DLSSPresets]` per-mode override — force K/M/L per quality mode (DLAA/UltraQuality/
  Quality/Balanced/Performance/UltraPerformance). Default = game's choice.
- Default shipped ini applies NO tweaks (ForceDLAA=false, presets=Default) — hook only.

## Default 4K quality-first profile (fallback when no per-game research)

```json
{
  "dll_version": "310.7.0",
  "resolution": "4K",
  "presets":  {"DLAA": "L", "UltraQuality": "L", "Quality": "L", "Balanced": "L",
               "Performance": "M", "UltraPerformance": "L"},
  "scaling":  {"Enable": true, "UltraPerformance": 0.333, "Performance": 0.5,
               "Balanced": 0.58, "Quality": 0.667, "UltraQuality": 0.8},
  "dlss":     {"ForceDLAA": false, "OverrideSharpening": "Default"}
}
```

Rationale: L for quality-first modes (better 2nd-gen visuals, 3–6% cost is fine on a
5070 Ti), M for Performance (M is literally tuned for it). Custom scaling keeps the
game's own quality-mode ratios unless per-game research says otherwise.

## Per-game research pattern (agent loop)

Before writing a profile for a specific game: `web_search "<game> DLSS 4.5 settings 4K"`
and `"<game> DLSSTweaks"` (single-title threads are fine as web_search; multi-title
comparisons → research.py). If nothing found → fall back to the 4K default profile and
record `"source": "default-4k"` vs `"source": "researched"` in the applied state so the
user can see which games got custom tuning.
