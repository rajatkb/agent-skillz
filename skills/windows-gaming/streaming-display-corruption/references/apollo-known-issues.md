# Apollo/Moonlight Virtual Display — Known Issues Reference

## Relevant GitHub Issues

### Apollo (ClassicOldSong/Apollo)

| Issue | Title | Relevance |
|-------|-------|-----------|
| [#532](https://github.com/ClassicOldSong/Apollo/issues/532) | Weird visual artifacts and glitching after installing Apollo and using the virtual displays | Artifacts on physical monitor after virtual display use. Closed as not planned. Suggests client-side or GPU issue. |
| [#1215](https://github.com/ClassicOldSong/Apollo/issues/1215) | Virtual Display/Headless Mode BugCheck/Display Driver Crash Only After Running Desktop Mirror | System crash with Kernel-PnP error `\Driver\WUDFRd` failed to load. NVIDIA 5070 Ti and AMD 9070XT both affected. Disabling virtual display aspect prevented crashes. |
| [#1461](https://github.com/ClassicOldSong/Apollo/issues/1461) | Virtual display hitching with Apollo/Moonlight | Periodic stutter/black screen. Fixed by disabling virtual display and using HDMI dummy plug instead. |
| [#338](https://github.com/ClassicOldSong/Apollo/issues/338) | Games still try to launch at main monitor resolution in virtual desktop | Games remember previous resolution config. Apollo can't force per-game resolution. |
| [#1365](https://github.com/ClassicOldSong/Apollo/issues/1365) | Apps Launching on Wrong Display & Other Weirdness | Display topology corruption. |
| [#453](https://github.com/ClassicOldSong/Apollo/issues/453) | Client specs not being used for virtual display | Points to FAQ about clearing `display_device.state`. |
| [#1453](https://github.com/ClassicOldSong/Apollo/issues/1453) | Games don't expose virtual display resolution as option | RDR2 not showing correct resolution options on virtual display. |
| [#768](https://github.com/ClassicOldSong/Apollo/issues/768) | Display Mode Override Not Updating Client Refresh Rate | Display Mode Override feature not applying correctly. |

### Virtual-Display-Driver (VirtualDrivers/Virtual-Display-Driver)

| Issue | Title | Relevance |
|-------|-------|-----------|
| [#204](https://github.com/VirtualDrivers/Virtual-Display-Driver/issues/204) | Monitor modes not changing | Virtual display picks up modes from physical display (1920x1080@144Hz shared). Confirms mode list cross-contamination. |
| [#363](https://github.com/VirtualDrivers/Virtual-Display-Driver/issues/363) | Custom Resolution | Resolution not changing from 1920x1080. |
| [#471](https://github.com/VirtualDrivers/Virtual-Display-Driver/issues/471) | IDD virtual display can no longer be set as primary | Windows 11 24H2/25H2 regression. |

## NVIDIA Forum

- [Artifacts after using Virtual Display Driver (Sunshine/Apollo)](https://www.nvidia.com/en-us/geforce/forums/geforce-graphics-cards/5/569828/artifacts-after-using-virtual-display-driver-sunsh/) — Artifacts persist until full reboot. Specific to 50 series. Multiple pages of users reporting same.
- [RTX 5070 Display Flickering](https://www.nvidia.com/en-us/geforce/forums/geforce-graphics-cards/5/560825/rtx-5070-display-flickering/) — Fix: change RGB to YCbCr422 in NVIDIA Control Panel. Multiple users confirming.
- [Driver 581.08 fix](https://www.guru3d.com/download/nvidia-geforce-58101-whql-driver-download/) — Bug [5434811]: Power cycling monitor can result in monitor flickering when NVIDIA App is installed.

## Reddit / Other

- [Installed new RTX 5070 — black screen when alt-tabbing like HDR is on](https://www.reddit.com/r/pcmasterrace/comments/1k32whr/installed_new_rtx_5070_and_now_the_screen_goes/) — Fixed by driver 581.08
- [Advanced Optimus freezes on ASUS ROG](https://rog-forum.asus.com/t5/tuf-asus-gaming-notebooks/nvidia-advanced-optimus-or-dgpu-only-freezes/td-p/1081678) — Workaround: manually disable/re-enable dGPU after gaming sessions

## Apollo Wiki Pages

- [FAQ](https://github.com/ClassicOldSong/Apollo/wiki/FAQ) — "Resolution can't match client side request anymore" section gives registry keys to clear monitor configuration cache.
- [Display Mode Override](https://github.com/ClassicOldSong/Apollo/wiki/Display-Mode-Override) — Per-client fractional refresh rate override for stutter fix.
- [Stuttering Clinic](https://github.com/ClassicOldSong/Apollo/wiki/Stuttering-Clinic) — Periodic micro-stutters, hiccups from monitor input auto-detect.

## Registry Keys (Monitor Configuration Cache)

```
HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Configuration
HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\Connectivity
HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers\ScaleFactors
```

Delete ALL subkeys under each — forces Windows to re-detect displays from scratch on next boot.

## Apollo State File

`display_device.state` — stores Apollo's display topology configuration. Delete it (while Apollo is not running) to reset Apollo's display device management.

## Key Diagnostic Observations (from real session)

- Native 1080p fullscreen → flickering/crashing
- 900p fullscreen → no issue
- Windowed/borderless at any resolution → no issue
- Games not played through streaming worked fine until played on the external monitor at native resolution
- Laptop display also affected AFTER playing game on external monitor at native fullscreen
- Lowering Windows desktop resolution below native resolution was a workaround

This pattern points to the native resolution's display mode being corrupted by the virtual display, specifically in the exclusive fullscreen path. The game config inherits the bad mode when played on the corrupted display.
