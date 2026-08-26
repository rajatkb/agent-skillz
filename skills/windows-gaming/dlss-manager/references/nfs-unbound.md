# NFS Unbound — DLSS research (Aug 2026)

Crawler session: `nfs-unbound-dlss-4-best-preset-recommendation-dlss-quality-s`

## Findings
- Game shipped with DLSS 2.4.x; community standard fix = DLL swap (gamepressure DLSS Upgrade mod page documents the 2.4.x→3.5.10 swap pattern).
- **Community rec: in-game Upsampler Preset = Quality** — "Balanced and Performance makes the game too blurry" (fpsindex.com). Do NOT recommend Balanced/Performance for this title.
- Preset system (xda-developers): K = general/60fps, L = IQ-first, M = Performance (~5% FPS cost).
- Applied: DLSS 4 (310.4.0) SR+FG, auto-selects preset K on Quality — no DLSSTweaks required for the recommended config.

## Per-setting sweet spot (fpsindex + itemlevel)
Shadow Quality Medium, Reflection Medium (huge perf impact, keep car visuals), Texture Quality Low/Medium, Texture Filtering Ultra, Terrain Medium, Post-Process High, Lighting Medium.

## Sources
- https://fpsindex.com/need-for-speed-unbound-best-graphics-settings/
- https://itemlevel.net/nfs-unbound-best-optimization-guide-best-settings-max-performance/
- https://www.xda-developers.com/gamers-arent-using-new-dlss-transformer-model-how-to-fix/
- https://www.gamepressure.com/download/need-for-speed-unbound-dlss-upgrade-v3510-mod/z214b65
