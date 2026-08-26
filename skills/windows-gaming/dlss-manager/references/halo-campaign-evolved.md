# Halo: Campaign Evolved — DLSS research (Aug 2026)

Researched via research.py crawler + direct fetches. Game root: `/mnt/d/<Game>` (UE engine, project name **Meteorite**, exe `Meteorite/Binaries/Win64/HaloCampaignEvolved.exe` — the UE5 Halo CE remake; Blam-style input mappings, MotionTracker HUD, Warthog). Currently at DLSS **310.7.0 (4.5)** + DLSSTweaks 0.310.5.0 (wrapper `dxgi.dll` next to exe). Hybrid stack: **SR direct NGX** (`Engine/Plugins/Halo.External/DLSS/.../nvngx_dlss.dll`), **FG + Reflex via Streamline** (`Engine/Plugins/Halo.External/StreamlineCore/.../sl.dlss_g.dll`, `sl.reflex.dll`, `nvngx_dlssg.dll`). No `sl.dlss.dll` → SR is NOT Streamline.

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

## Ray Reconstruction — no in-game option, but enableable via mods (verified Aug 23)

**The game exposes NO ray-tracing toggle in its settings** — the complete video-settings schema (`HaloLocalGameUserSettings.ini`) = `Upscaler`, `UpscalingQuality`, `bFrameGeneration`, `LowLatencyMode`, `ResolutionScale`, FPS caps, 10 quality tiers: **zero RT keys**, zero `RayTracing|RayReconstruction` matches in shipped/user configs. `nvngx_dlssd.dll` loads + gets hooked at init (dlsstweaks.log) — that's NGX preloading all feature DLLs, NOT feature creation (loaded ≠ enabled, see SKILL.md section).

**BUT the game DOES have ray-traced effects (UE5, denoiser-based) and the community enables RR via Engine.ini tweaks / mods** — the earlier "RR can never be enabled" conclusion was wrong; it just isn't exposed in-game. Sources (search-snippet evidence):
- "with a few Engine.ini tweaks I was able to enable DLSS Ray Reconstruction (verified using the DLSS Swapper...)" — https://www.youtube.com/shorts/6GV4nKEE59s
- "Ray reconstruction replaces UE5's own temporal, bilinear, and spatial denoisers with AI-based denoising. This often results in smoother and much clearer reflections." — pcoptimizedsettings "Ray Tracing Extreme Mod + Ray Reconstruction (Almost Path Tracing)": https://pcoptimizedsettings.com/halo-campaign-evolved-ray-tracing-extreme-mod-ray-reconstruction-almost-path-tracing/
- FSR-RR variant via Engine.ini edits + OptiScaler + registry identifier swap: https://en.gamegpu.com/news/igry/entuziasty-zapustili-fsr-ray-reconstruction-v-igre-halo-campaign-evolved
- OptiScaler RR + MFG setup walkthrough: https://www.youtube.com/watch?v=0wzLwAYM5Ac
- DF first-look thread discusses disabling the in-game denoiser in favor of DLSS 4.5 denoising: https://www.resetera.com/threads/digital-foundry-halo-campaign-evolved-first-look-xbox-pc-ally-x-og-vs-new-game-performance-more.1548622/

Verdict for this user (RTX 5070 Ti): DLSS RR is achievable via Engine.ini tweaks (or the "RT Extreme" mod) and community consensus is it improves reflection clarity/ghosting vs the built-in denoiser. Runtime proof of activation: `VerboseLogging=true` / `OverrideDlssHud=1` in dlsstweaks.ini → log/overlay shows whether `NVSDK_NGX_D3D12_CreateFeature` RR ever fires.

### Exact enable recipe (pcoptimizedsettings, July 28 2026) — verified against local findings

Engine.ini at `%LOCALAPPDATA%\Meteorite\Saved\Config\Windows\Engine.ini` (same dir as GameUserSettings.ini; create if missing):

```
r.NGX.DLSS.denoisermode=1
r.Lumen.Reflections.BilateralFilter=0
r.Lumen.Reflections.ScreenSpaceReconstruction=0
r.Lumen.Reflections.Temporal=0
r.Shadow.Denoiser=0
```

- **Perf cost (pcoptimizedsettings):** RR = **10-15% overhead** on RTX 40/50; optional "RT Extreme" Lumen upgrades (LightingMode=3 hit-lighting, MaxIterations=12288, culling tweaks) add another 5-20% — skip unless chasing max fidelity.
- **Why it helps THIS game:** it runs Hardware Lumen + MegaLights (UE 5.5.4.0, vpesports) and the Lumen denoiser is its known weak spot — "sparkling, bubbling, temporal noise in dark scenes" (vpesports). RR replaces temporal/bilinear/spatial denoisers with AI denoising → smoother, much clearer reflections, higher effective RT resolution; biggest gain indoors/glossy surfaces.
- **DLSS path needs NO OptiScaler** — `nvngx_dlssd.dll` already ships in the game; just the 5 Engine.ini lines. OptiScaler (FSR-RR variant, gamegpu) also wants the `dxgi.dll` slot that DLSSTweaks already occupies — the DLSS route avoids that conflict entirely.
- DSOGaming pre-release article confirms no RT toggle / no RR in vanilla settings: https://www.dsogaming.com/articles/halo-campaign-evolved-runs-with-90fps-at-native-1440p-ultra-settings-on-an-nvidia-geforce-rtx-5090/

## Actual runtime config (Aug 23, from `%LOCALAPPDATA%\Meteorite\Saved\Config\invalid_id\HaloLocalGameUserSettings.ini`)

- `Upscaler=DLSS`, `UpscalingQuality=Low` (this game's ladder is Ultra/High/Medium/**Low** — Low = most aggressive scaling tier, likely maps to Performance/UltraPerf), `bFrameGeneration=True`, `LowLatencyMode=VendorSpecific` (Reflex), `MaximumFrameRate=60`, `ResolutionSize=1920x1080` borderless on the MSI OLED, `HDR=1000`, `QualityPreset=Ultra` (all tiers Ultra). Monitor key: `MSI4DD3(2)`.
- GameUserSettings.ini: `SwapChainProvider=FStreamlineD3D12DXGISwapchainProvider` (the Streamline tell), `bUseHDRDisplayOutput=True`.

## Applied profile (CURRENT state — verified from live dlsstweaks.ini + log, Aug 23)

```json
{
  "dll_version": "310.7.0",
  "presets": {"DLAA": "M", "UltraQuality": "M", "Quality": "M", "Balanced": "M", "Performance": "M", "UltraPerformance": "M"}
}
```

**History (order matters):** M applied first (gamegpu/Nexus consensus) → research session switched to **K** (1st-gen, lighter — same reasoning as Dead Space on this laptop) → user asked to test **M** for perf impact (Aug 11) → **M stuck and is still live**. K backup is one `tweak-config` away. Note: laptop 2nd-gen L/M penalty (G14 5070 Ti + 4K OLED) applies here too — user is currently on 1080p, so M's FPS cost is less painful than at 4K.

## Clarity block — extra Engine.ini lines beyond RR (verified Aug 23)

CA + film grain are FORCED ON with no menu toggle (vpesports: "cannot be disabled even in the PC settings"). The widely-deployed fix block (DSOGaming July 24 + Steam "transform image quality" thread + Nexus mod 48 ships exactly this file):

```ini
[SystemSettings]
r.FilmGrain=0
r.Tonemapper.GrainQuantization=0
r.SceneColorFringeQuality=0
r.Tonemapper.Quality=0
r.MegaLights.DownsampleFactor=1          ; default 2 → 1: less noise in shadowed areas, ZERO perf cost
r.Lumen.ScreenProbeGather.Temporal.MaxFramesAccumulated=12
r.Lumen.DiffuseIndirect.Temporal.MaxFramesAccumulated=12
[/Script/Engine.InputSettings]
bEnableMouseSmoothing=False
bViewAccelerationEnabled=False
bDisableMouseAcceleration=True
```

The two Lumen temporal lines = the "transformed the game from an impressive looking but blurry game, to pin sharp and clean and crisp" tweak (Steam StuartAce).

## ⚠️ Dev-locked cvars pitfall (Steam "UE tweaking guy", July 28)

Most cvars are dev-LOCKED and will NOT apply from a read-only Engine.ini. Confirmed Engine.ini-compatible: `r.SceneColorFringeQuality`, `r.FilmGrain`, `r.MegaLights.DownsampleFactor`. Everything else (Lumen temporal MaxFramesAccumulated, `r.Tonemapper.Quality`, InputSettings block, `r.AntiAliasingMethod`/TSR-TAA history %, `r.Tonemapper.Sharpen`, `r.Nanite.MaxPixelsPerEdge`, foliage `WPODisableDistance`) reportedly needs the **in-game console** (Nexus mods/9) + manual input each launch. The DSOGaming block is still universally deployed as read-only Engine.ini anyway — treat as "likely works, verify visually", and when the user reports a tweak did nothing, blame the lock, not the file.

## Engine.ini mechanics
- Path: `%LOCALAPPDATA%\Meteorite\Saved\Config\Windows\Engine.ini` — create if missing.
- **Set Read-only after editing** or the game overwrites it (every guide + Nexus mod 48 note this).
- **APPLIED 2026-08-24** — file created from scratch (game never shipped one; vanilla = file absent) with the full RR + clarity block. Recovery record: `DLSSManager/ENGINE-INI-RECOVERY.md` (game root) + applied-copy backup `DLSSManager/backups/engine-ini/20260824_created_new_engine_ini.ini`. Verified intact after launch (md5 match + `A R` attrib still set).
- RR verified ACTIVE via `tweak-hud 1` overlay (2026-08-24) — HUD shows SR/FG/RR rows; **RR row showed preset D** → 4.5 DLL (310.7.0) but old RR model active; forcing F = the real 4.5 RR model (see `references/ray-reconstruction-presets.md`). HUD back to 0 via `tweak-hud 0` — script-managed since Aug 2026: `dlss_manager.py <root> tweak-hud <0|1|2|-1>`; `status` prints the current value.
- **RR preset forced via driver override (Aug 24–26):** `dlss_manager.py <root> rr-preset <letter>` — driver-level per-game override (NVAPI DRS `0x10E41DF7` + enable flag `0x10E41E02` as a pair), read-back verified, recorded in dlss.json history. `status` prints `RR preset (driver override): <letter>`. Revert: `rr-preset default`. Driver updates / NVIDIA App can reset it (re-apply — one command). History: F set first (verified via HUD) → **E is the LIVE preset since Aug 26** (chosen for the star-noise issue below; see `references/ray-reconstruction-presets.md` for the mechanism + the pure-Python helper).

## RR F confirmed + starfield noise caveat (Aug 25, user-verified)

- **Enable flag was the missing piece:** `rr-preset f` alone left the HUD at D; adding driver flag `0x10E41E02=1` flipped it to F — user confirmed "the switch worked". `status` read-back alone is NOT proof; the HUD (`tweak-hud 1`) is the runtime proof. (Now handled automatically as a PAIR by `dlss_rr.cs`/`dlss_rr.exe` set/unset — the temp `set-rr-flag.ps1` is deleted; full mechanism: `references/ray-reconstruction-presets.md`.)
- **RESOLVED — E is the final pick (Aug 26, user-verified):** after F showed the star noise, `rr-preset e` was applied and the user confirmed "No noise now". RR preset **E** (1st-gen transformer, "improved sub-variant of D" / "the better one" vs D per Destructoid + ResetEra) matches the only explicit Halo datapoint ([GamingOptimiz on X](https://x.com/GamingOptimiz/status/2083657103357423943) runs E + Ultra Reflections "to avoid noise") — now two independent confirmations. F remains one `rr-preset f` away.
- **Noisy skybox/stars with RR F:** stars read as white noise. Cause class: RR + tiny bright sub-pixel sources at low internal res (this user runs `UpscalingQuality=Low` @1080p → aggressive internal scale) + all UE5 denoisers disabled (RR must cover every pass). No Halo-specific starfield report exists; closest precedents: [GamingOptimiz on X](https://x.com/GamingOptimiz/status/2083657103357423943) runs **RR Preset E + Ultra Reflections "to avoid noise"**; [NeonLightsMedia](https://www.neonlightsmedia.com/blog/halo-campaign-evolved-pc-fix-guide-blur-crashing-input-lag): confetti-flicker on reflections → Ultra reflections fixes it (user already Ultra).
- **Fix levers, one change at a time:** (1) `rr-preset e` (Halo community precedent); (2) raise `UpscalingQuality` from Low → High/Ultra (internal-res lever — biggest for sub-pixel stars); (3) restore one Lumen denoiser (`r.Lumen.Reflections.Temporal=1`) for passes RR doesn't cover.
- gamegpu's 4.5 RR review confirms F is generally the "complete noise/artifact removal" model — starfields are a content-specific weakness, not an F-wide regression.
- Sources: dsogaming.com CA/FG/mouse article; steamcommunity.com/app/2806050 discussions 590684692649530622 + 590685251875962676; nexusmods.com/halocampaignevolved/mods/48 (CA/FG removal) + /mods/9 (console); OptiScaler wiki page (upscalers vendor-locked, DLSS only pairs with DLSS-FG; tested 0.9.4 as dxgi.dll).
