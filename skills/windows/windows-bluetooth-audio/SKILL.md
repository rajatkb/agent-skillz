---
name: windows-bluetooth-audio
description: Diagnose Windows Bluetooth audio quality collapse — speaker/headset flips to mono, muffled "hands-free/telephone" sound, or crackle when a game or app opens the microphone. Covers the A2DP→HFP profile switch, dual audio endpoints, Hands-Free Telephony, Bluetooth Audio Gateway Service, and LE Audio stereo-while-mic.
---

# Windows Bluetooth Audio Quality Collapse (A2DP → HFP profile switch)

## When to use

- "Game X destroys the quality of my Bluetooth speaker/headset" — sound collapses exactly when a game/app starts
- BT audio turns mono, muffled, "underwater", or phone-call-like while a mic-using app runs
- Audio only recovers after closing the game
- Crackling/distorted BT audio during games

## The core mechanism (state it first — it explains everything)

Standard Bluetooth cannot transmit high-quality stereo and microphone data simultaneously. The instant ANY app opens a mic endpoint on a BT device, Windows switches the WHOLE device from A2DP (high-quality stereo playback) to the Hands-Free Profile HFP/HSP (mono, narrowband voice codec, aggressive compression). There is no partial mode — it's all-or-nothing.

Games are the most common trigger because they initialize voice chat / silently probe the default input device at launch, even when the player never uses it and even when muted in-game — the profile switch already happened at the OS level, so in-game muting does NOT undo it. This is NOT a game bug and not a driver failure; any mic-touching app (games, Discord polling the mic, launchers) triggers it. BT **speakers with built-in mics** are just as vulnerable as headsets.

## Diagnosis

1. **Confirm the device exposes dual endpoints** (the smoking gun):
```powershell
Get-PnpDevice -Class AudioEndpoint | Select FriendlyName,Status
# "Headphones (Tribit XSound Go)"        ← A2DP stereo endpoint
# "Headset (Tribit XSound Go Hands-Free)" ← HFP endpoint — its presence means the downgrade is possible
```
2. **Reproduce and observe:** launch the game, then check the active output — tray volume popup or Settings → System → Sound → output device properties. If the name reads "… Hands-Free", the switch is confirmed. Keep Sound Control Panel (mmsys.cpl) Playback tab open during launch and watch which endpoint lights up.
3. Note whether the BT device is the default **recording** device too — if its mic is the default input, every app request routes to it.

## Fix ladder (try in order)

1. **Point the game's voice input elsewhere (zero-risk, first choice).** Xbox Game Bar (Win+G) → Voice tab → capture device = anything non-BT (e.g. "Steam Streaming Microphone" — the community-standard dummy). Or in-game voice input setting → another device / voice off. Restores quality instantly without system changes.
2. **Disable Hands-Free Telephony on the device (bulletproof).** Settings → Bluetooth & devices → Devices → <device> → Device properties → *More Bluetooth settings* → Properties → Services tab → uncheck **Hands-Free Telephony**. Windows can no longer negotiate the device mic → the HFP endpoint disappears → the downgrade becomes impossible. Trade-off: the device's own mic dies (irrelevant for speakers). Caveat: some devices re-enable this after a reboot.
3. **Disable the Bluetooth Audio Gateway Service (nuclear, last resort).** services.msc → stop + Startup type = Disabled. System-wide — affects ALL BT audio devices (a second headset, buds, etc.), and some users report total BT audio loss until re-enabled. Only when #2 won't stick.
4. **Windows Sonic spatial sound → Off** (System → Sound → <device> → properties → Spatial sound). One documented cause of the "shitty sound" (Sonic toggle flapping on/off).
5. **Crackle specifically:** <device> properties → Advanced → set format to 48 kHz (game engines run 48 kHz; mismatches crackle).
6. **Modern path (LE Audio):** Win11 24H2 build 26100.4484+ supports stereo-while-mic — but ONLY over Bluetooth LE Audio, requiring LE Audio on BOTH the adapter AND the device. Most classic BT speakers never get this; say so plainly rather than promising a fix that hardware can't deliver.

## Pitfalls

- Muting in-game or disabling voice chat does NOT stop the switch (the mic endpoint stays open; profile already switched).
- Don't chase driver reinstalls or game updates — expected OS behavior, not a fault of either.
- Wired / USB / 2.4 GHz-dongle audio is structurally immune (separate input/output channels) — that's the honest long-term answer when workarounds are unacceptable.
- The service-name fix (#3) is often copy-pasted as the universal answer; it's the bluntest tool with the worst collateral. Prefer #1/#2.
- Verify the fix by watching the endpoint name during game launch, not by ear.

## Support files

- `references/helldivers2-case.md` — worked case: Helldivers 2 + Tribit XSound Go speaker (dual endpoints observed), community fix reports with caveats, source links.
