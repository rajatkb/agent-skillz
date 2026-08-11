# Halo: Campaign Evolved — DLSS preset research (Aug 2026)

Researched via research.py crawler + direct fetches. Game root: `/mnt/d/Halo.Campaign.Evolved.Premium.Edition-InsaneRamZes` (UE engine, exe `Meteorite/Binaries/Win64/HaloCampaignEvolved.exe`). Currently at DLSS 310.7.0 (4.5) + DLSSTweaks 0.310.5.0 installed (wrapper `dxgi.dll` next to exe).

## Preset consensus: DLSS 4.5 **Preset M**

Two independent sources agree:

1. **gamegpu.com — "DLSS 4 vs. DLSS 4.5 Settings Comparison in Halo Campaign Evolved"** (tested on RTX 4070 Ti):
   > "If a clean, artifact-free image is your priority: **DLSS 4.5 Preset M is the clear favorite**... It removes the visual noise and grain of Preset K, but doesn't suffer from the excessive softness of Preset L."
   > "Preset M (65 FPS) remains the optimal DLSS 4.5 preset: it runs 1 FPS faster than L and produces a much more balanced, sharper image without pixel noise."
   > "Switching to Preset M in a lower scaling mode (e.g. Quality K → Balanced M, Balanced K → Performance M) gains smoothness + stable image without pixel garbage."
   URL: https://en.gamegpu.com/test-gpu/action-fps-tps/sravnenie-nastroek-dlss-4-protiv-dlss-4-5-v-halo-campaign-evolved (403 to web_extract — use curl w/ browser UA or crawler)

2. **Nexus "Ultra Plus" mod page** for Halo: Campaign Evolved:
   > "Allows optimizing for your specific upscaler (**DLSS 4.5 preset M is recommended** if you can use it)"
   URL: https://www.nexusmods.com/halocampaignevolved/mods/68

### gamegpu measured numbers (Performance mode)

| Preset | FPS | Verdict |
|---|---|---|
| DLSS 4.0 K | 70 | Sharpest micro-detail, max FPS, but pixel noise on dense grass/foliage |
| DLSS 4.5 M | 65 | **Best balance** — removes K's grain, keeps detail, no L's softness |
| DLSS 4.5 L | 64 | Smoothest/least grain, but softest image, worst balance |

Halo's vegetation-heavy environments make K's grain visible → M is the right pick for quality.

## 6x Multi Frame Generation — mechanism & caveats

Source: OC3D "How to enable DLSS Multi and Dynamic Frame Generation in Halo Campaign Evolved" (https://overclock3d.net/reviews/software/how-to-enable-dlss-multi-and-dynamic-frame-generation-in-halo-campaign-evolved/):

- Game menu exposes **only 2x FG** — 6x/Dynamic MFG requires **NVIDIA App → Graphics → Halo: Campaign Evolved → DLSS Override** (RTX 50-series only; no login needed for NVIDIA App).
- **Cutscene bug**: cutscenes are capped at 30 FPS *after* FG is applied and FG isn't disabled → 2x FG shows 15 FPS cutscenes, **6x FG shows 5 FPS cutscenes**. Community fix: "Cinematic Frame Generation Fix" mod on Nexus Mods (runs cutscenes at native 30 FPS with FG enabled).
- MFG is NOT an ini knob — the NVIDIA App override is the only lever; DLSSTweaks ini only controls SR preset + scaling.

## Applied profile (user-approved direction)

```json
{
  "dll_version": "310.7.0",
  "resolution": "4K",
  "source": "researched (gamegpu + nexus ultra-plus)",
  "presets": {"DLAA": "M", "UltraQuality": "M", "Quality": "M", "Balanced": "M", "Performance": "M", "UltraPerformance": "M"}
}
```

All slots → M per consensus (preset override forces the model independent of scaling mode). User wants 6x MFG always on → flag the cutscene bug; suggest Cinematic FG Fix mod.
