# Worked case: Helldivers 2 destroys Bluetooth speaker quality (Tribit XSound Go)

Session-tested on G14 GA403 (Win11 25H2), HD2 via Steam, output = Tribit XSound Go BT speaker.

## Confirmed on the machine

`Get-PnpDevice -Class AudioEndpoint` showed the Tribit exposing BOTH endpoints (status OK):
- `Headphones (Tribit XSound Go)` — A2DP stereo
- `Headset (Tribit XSound Go Hands-Free)` — HFP (speaker has a built-in speakerphone mic)

The game (HD2) initializes its voice system at launch and grabs the default input; the Tribit's mic was reachable ⇒ Windows switches the whole device to HFP ⇒ mono/"telephone" quality for ALL audio until the mic endpoint is released. User's framing: "starting the game destroys the quality of the speaker."

## Community fix reports (r/Helldivers thread 1cistwi, ~2y old, still corroborated in 2025-2026 comments)

| Fix | Reports |
|---|---|
| Xbox Game Bar (Win+G) → Voice tab → capture ≠ BT device (e.g. "Steam Streaming Microphone") | Top fix, 172 upvotes; "audio cut out for a second and came back in all its rich glory" |
| Change game's "Default Communications Output" away from the BT device | Confirmed by several |
| Disable Hands-Free Telephony on the device (Services tab) | Standard fix, from original thread 1anrewp |
| Disable "Bluetooth Audio Gateway Service" (services.msc) | The "FIX FOUND" post; works but: one user got ALL BT audio cut until re-enabling; affects other BT devices; "may affect other Bluetooth functionalities" |
| Disable "Bluetooth Support Service" too | One report, after Gateway alone failed |
| Windows Sonic spatial sound → Off (device properties → Spatial sound) | One user traced the "shitty sound" directly to Sonic flapping on/off |

Same fix works in Space Marine 2 and Star Citizen (one commenter theorizes Easy Anti-Cheat's audio-device probing is the common trigger — unverified). Mechanism comment worth quoting: "bluetooth cannot run high quality output and input at the same time, so it has to lower the quality of one or both to compensate."

## Sources

- https://www.reddit.com/r/Helldivers/comments/1cistwi/ — FIX FOUND thread (fix table + caveats above)
- https://www.reddit.com/r/Helldivers/comments/1anrewp/ — original BT headset fix thread
- https://macmyths.com/how-to-fix-audio-quality-drop-in-bluetooth-headphones-while-gaming-on-windows-11/ — A2DP vs HFP/HSP mechanism + full 4-step fix ladder (hands-free disable, default devices, launcher voice settings, comms tab "Do nothing")
- https://support.microsoft.com/en-US/Windows/Hardware/Bluetooth/configuring-bluetooth-le-audio-quality-settings-on-windows-11 — Microsoft: mono fallback "when the microphone is used" is by design; stereo-while-mic needs LE Audio + build 26100.4484+
- https://steamcommunity.com/app/553850/discussions/1/7599331177365497208/ — Hands-Free Telephony re-enables after restart on some devices
- https://helldivers.wiki.gg/wiki/Audio_Problems — HD2 audio problems wiki (exclusive mode, audio enhancements; Cloudflare-walled to crawlers, read in browser)
- https://www.gamerhero.net/2025/09/11/helldivers-2-audio-issues-5-common-problems-and-how-to-fix-them/ — 48 kHz format fix for crackle

## Caveat for future sessions

If the user's BT device is a pure playback speaker with NO mic (no HFP endpoint), the HFP switch can't happen — then look at sample-rate/exclusive-mode/codec causes instead. The dual-endpoint probe decides which branch to take.
