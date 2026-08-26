# Dead Space (2023) — DLSS research findings

Researched Aug 11, 2026 via research.py crawler session `dead-space-2023-remake-dlss-4-5-transformer-preset-recommend` + direct source verification.

## Game facts (verified)
- Install: `/mnt/d/<Game>` (Steam appid 1693980)
- EXE: `Dead Space.exe` (Frostbite — NOT UE, so no `*-Win64-Shipping.exe`)
- **Ships DLSS 2.5.0** — community calls it one of the blurriest DLSS implementations ever shipped
- **Streamline-based** (`sl.interposer.dll`, `sl.dlss.dll`, `sl.reflex.dll` present, **Streamline 1.1.1 = 2023 era**) — only SR DLL (`nvngx_dlss.dll`), no FG/RR at root
- DLSSTweaks wrapper used: `dxgi.dll` (was free in game root; script never clobbers existing)
- Display: 4K OLED (MAG321UP); GPU: laptop RTX 5070 Ti (hybrid mode)

## Community consensus (with sources)
1. **The DLL swap is THE fix** for blur — r/FuckTAA: "You can only fix it by replacing old DLSS version in the game root folder with the current DLSS version. That's it." — https://www.reddit.com/r/FuckTAA/comments/18oohtd/fixed_the_blurry_dlss_in_dead_space_remake/
2. **DLSS 4 / preset K confirmed great in this game** — Steam discussion (Feb 2025), 310.2.1 swap, preset K: "with great results" — https://steamcommunity.com/app/1693980/discussions/0/600771424734463630/
3. **DLSSTweaks author's own test** (emoose, issue #48): DLSSTweaks works in Dead Space; era-preset D best for quality modes, F for ultra-perf; DLAA+D "looked great"; **in-world holographic UI blur is an inherent game issue** (not DLSSTweaks' fault); NPI workaround = AA transparency multisampling `0x00000008 AA_MODE_REPLAY_MODE_ALL` + negative LOD bias (-0.5 @ quality 0.66667, -1.0 balanced, -1.5 perf, ~-1.8 ultra-perf) — https://github.com/emoose/DLSSTweaks/issues/48
4. **DLSS 4.5 L/M presets** need game DLL ≥ 310.5.0 + DLSSTweaks config `[DLSSPresets]` — https://www.nexusmods.com/site/mods/550
5. Preset semantics (dtgre): L = 2nd-gen best IQ at high render scales, M = 2nd-gen tuned for Performance; DLAA+K = cleanest pipeline — https://www.dtgre.com/2026/01/dlss-4-5-preset-overrides-guide-nvidia-app.html
6. NoobFeed L-vs-M (5070 Ti): L = best image quality, 3–6% slower than M — https://www.noobfeed.com/hardware/dlss-4-5-preset-l-m-comparison

## ⚠️ DLSS 4.5 performance penalty — why it hit hard here (researched Aug 11, 2026, session `why-is-dlss-4-5-preset-l-m-2nd-gen-transformer-slower-with-b`)
**User reported a massive FPS drop on 310.7.0 (L/M) vs old 2.5.0 — root causes:**
1. **Preset M (2nd-gen) has a real, game-dependent penalty** — NotebookCheck: 44.5% in Doom: TDA (175→97 fps), 7% in Battlefield 6, 5% in Black Myth: Wukong, ~3% in CP2077+PT. Deltia's: 25% real-world penalty in Arc Raiders (4070 Super 100→75 fps). The 2–3% figure is NVIDIA's marketing number; real-world varies 3–45% by title. https://www.notebookcheck.net/DLSS-4-5-image-quality-and-performance-analysis-2nd-gen-Transformer-brings-improved-visual-fidelity-with-hidden-performance-penalty.1194908.0.html + https://deltiasgaming.com/arc-raiders-is-dlss-4-5-worth-using/
2. **Laptop + 4K worsens it** — r/nvidia laptop tests: CNN→Transformer gap ~5% at 1080p but ~10% at 4K output; laptops can see worse (25% on a 3070 Ti laptop vs ~5% desktop). Transformer = bursty tensor load → hits laptop power/thermal ceilings sooner. https://www.reddit.com/r/nvidia/comments/1ihh06f/dlss_transformer_model_performance_impact/
3. **L/M's IQ wins are RT-heavy** — L/M mainly improve ray-traced lighting resolve, distance sharpness, temporal stability. Dead Space's RT use is minimal (AO/shadows) → pays the cost, gets little. Deltia's also notes M oversharpens.
4. **Old Streamline 1.1.1** (2023) — game's SL layer predates DLSS 4.5; not the primary cause (DLSSTweaks hooks nvngx_dlss.dll directly) but a contributing compatibility factor.
5. FP8 note: 2nd-gen relies on FP8 — RTX 20/30 lack it (their 20%+ hits); RTX 50 HAS it, so on the 5070 Ti the penalty is compute-heavy, not architecture-blocked.

**Resolution (applied):** pinned 310.2.1 (DLSS 4, 1st-gen) + preset K everywhere → Steam-community-verified combo for this game, much lighter than L/M. User confirmed FPS restored.

## Applied config (Aug 11, 2026)
- DLL: nvngx_dlss.dll **2.5.0 → 310.7.0 (4.5/L-M, perf drop) → 310.2.1 (DLSS 4/K — final)**; backups for all versions in `DLSSManager/backups/nvngx_dlss.dll/`
- DLSSTweaks 310.5.0 installed (dxgi.dll wrapper + dlsstweaks.ini + DLSSTweaksConfig.exe); pristine originals in `DLSSManager/backups/dlsstweaks/pristine_310.5.0/`
- Final profile: `[DLSSPresets]` all = K; `[DLSSQualityLevels] Enable=false`; `[DLSS] ForceDLAA=false, OverrideSharpening=Default, OverrideDlssHud=1`
- Overlay: `OverrideDlssHud=1` (bottom-left HUD; use 2 if post-FX hides it)

## Verify after first launch
- `dlsstweaks.log` next to `Dead Space.exe` confirms the wrapper loaded
- In-game: pick DLSS Quality or DLAA for best IQ; UI blur on holograms persists (inherent) — optional NPI negative-LOD-bias per #3 if it bothers
- Undo: `dlss_manager.py <root> undo` (DLL) / `tweak-remove` (wrapper)
