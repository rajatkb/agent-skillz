# PRAGMATA — DLSS research + applied state (Aug 2026)

Capcom (RE Engine). Repack: `D:\<Game>`, exe `PRAGMATA.exe`.

## Applied state (2026-08-26, via dlss_manager.py)

- **DLLs: 310.3.0 (DLSS 4, as shipped) → 310.7.129 (DLSS 4.5)** SR/FG/RR — immutable backups in `DLSSManager/backups/` (originals `310_3_0_0`).
- **SR preset: K forced via DLSSTweaks** (all quality levels: DLAA→UltraPerformance) — DLSSTweaks installed fresh (wrapper dxgi.dll next to PRAGMATA.exe, `tweak-install` with the legit Nexus zip).
- **RR preset: E via driver override** (`rr-preset e`) — game default was D.
- HUD off (`OverrideDlssHud=0`).

## Community verdict (sources)

**SR = Preset K — beats DLSS 4.5's L/M in THIS game** (same conclusion as Dead Space):
- gamegpu "DLSS 4 vs DLSS 4.5" comparison, 4K native, RTX 4070 Ti: Preset K (DLSS 4) sharpest, **56 FPS**; Preset L (4.5) "overall softening... slight loss of texture", **41 FPS**; title: "Why Preset K (DLSS 4) Outperforms New Algorithms". Also noted: **4.5 does not yet support reflection reconstruction** (which the game enables automatically with path tracing).
- https://en.gamegpu.com/test-gpu/action-fps-tps/pragmata-sravnenie-nastroek-dlss-4-protiv-dlss-4-5

**RR = E — the default D is the problem:**
- gamegpu news (Apr 2026): user changed RR preset "from the standard D to E... removed noise from the image and eliminated motion blur" (via DLSS Swapper).
- r/OptimizedGaming: "DLSS ray reconstruction uses preset D in this game. Apparently preset E looks significantly better" (caveat: E ghosted in RE9 — content-dependent).
- https://en.gamegpu.com/news/igry/preset-e-v-dlss-znachitelno-uluchshaet-kachestvo-trassirovki-puti-v-pragmata

## Notes

- 4.5 DLLs still auto-default K for Quality/Balanced/DLAA but M for Performance, L for UltraPerf — the K-forced profile keeps the community-best model regardless of tier.
- RR preset E mirrors the Halo outcome (E over F/D for noise) — E is shaping up as the general "safe RR pick" for 4.5-era games.
