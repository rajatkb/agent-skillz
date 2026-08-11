# Session Research — July 19, 2026

## Apollo Virtual Display → Windows 11 25H2 DWM MPO Corruption

### System

- Laptop: ASUS ROG G16 with RTX 5070 Ti Laptop GPU + AMD iGPU
- OS: Windows 11 25H2 (build 26200)
- Driver: NVIDIA 610.74
- Apollo v0.4.x with SudoVDA virtual display
- iPad + TV Moonlight clients at 1080p 60Hz

### Symptom Progression

1. Used Apollo + Moonlight with virtual displays for several days (iPad, TV)
2. After disconnecting, all games flickered in fullscreen — "like alt-tabbing"
3. Green line at top of screen during flicker (partial overlay render)
4. Worked at 900p fullscreen, worked windowed, broke at 1080p fullscreen
5. Cross-GPU test: persisted on AMD iGPU → confirmed DWM-level, not NVIDIA
6. NVIDIA App splash appeared for games despite App showing as uninstalled

### Resolution Path

None of these fixed it:
- Registry cache delete (Configuration, Connectivity, ScaleFactors)
- CRU reset-all (EDID override cleanup)
- Virtual display driver uninstall
- FSO registry revert (GameConfigStore defaults)
- Color format switch (RGB → YCbCr422)
- NVIDIA App uninstall + manual file cleanup
- dGPU-only mode
- Running on AMD iGPU
- MSI Afterburner / RTSS off
- Win+Ctrl+Shift+B

The fix that worked:
```
OverlayTestMode=0, OverlayMinFPS=0, DisableOverlays=1 → reboot
then revert OverlayTestMode → reboot
```
This toggle forced DWM + NVIDIA kernel driver to flush corrupted MPO state.

### Sources

See skill `windows-gaming-fullscreen-corruption` → `references/25h2-mpo-dwm-bug.md`
