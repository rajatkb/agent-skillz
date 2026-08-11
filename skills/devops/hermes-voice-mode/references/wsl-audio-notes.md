# WSL Audio / Mic Access — sourced notes

## WSLg audio architecture (why PulseAudio)

WSL2 has no native sound drivers. WSLg (GUI + audio) bridges audio to Windows
through a **PulseAudio socket at `/mnt/wslg/PulseServer`**. The distro talks to
it via a PulseAudio client/server; no audio stack in the distro = no audio at all.

## Sources

- **microsoft/WSL discussion #9624** — "Is it possible to run pyaudio on Ubuntu 22.04 under WSL2 with Windows 11?"
  https://github.com/microsoft/WSL/discussions/9624
  Key quote: "~/.asoundrc makes ALSA's default device a Pulse shim, and PULSE_SERVER points to WSLg's Pulse socket so PyAudio can open the mic. Enable Windows mic permission for your terminal app (Windows Settings → Privacy & security → Microphone)."
  → **Windows mic privacy permission is a silent-failure trap — check it FIRST.**
- **microsoft/wslg issue #1378** — PulseAudio runs in the WSLg image, not the working distro:
  https://github.com/microsoft/wslg/issues/1378
  "PulseAudio normally runs in the WSLg image (overlayed on top of your working Ubuntu WSL image)... you don't need to run [it] in your working WSL image."
  → Distro may only need client tools (`pulseaudio-utils`) + `libportaudio2`, not a full server.
- **microsoft/wslg discussion #1141** — virtual sink/mic recipe:
  https://github.com/microsoft/wslg/discussions/1141
  module-null-sink (virtual speaker) → monitor as source → module-remap-source for a virtual microphone.
- **gemini-cli-voice wsl2-microphone-access.md** — community-confirmed on WSL 2.3.26.0+ with WSLg:
  https://github.com/diyism/gemini-cli-voice/blob/master/docs/troubleshooting/wsl2-microphone-access.md

## Diagnostic branch

1. `sudo apt install pulseaudio-utils libportaudio2` (Debian; Ubuntu: portaudio19-dev) — minimal, then `pactl list sources short`.
2. Mic visible → native path: install Hermes voice extras (sounddevice + faster-whisper), verify `sounddevice.query_devices()`.
3. Mic NOT visible → bridge: Windows-side capture (`ffmpeg -f dshow -i audio="Microphone"`) streamed over TCP into a WSL virtual PulseAudio source (module-pipe-source / null-sink+remap); TTS playback fallback = PowerShell `System.Media.SoundPlayer` on a WAV (hermes-notify.ps1 pattern).

## Local machine snapshot (Aug 2026)

- WSL 2.7.10, kernel 6.18.33.2, WSLg 1.0.73.2, MSRDC 1.2.26676, Windows 10.0.26200.8875 (25H2)
- Distro: Debian 13 trixie. NO audio stack at session start: no arecord, no pactl, no pulseaudio; DISPLAY + WAYLAND_DISPLAY empty, /mnt/wslg contained only 'run' (WSLg not active in that shell)
- No Python on Windows side (python/py not found — `winget install Python` would be needed for any Windows-side tooling)
- Hermes 0.18.2: pip-installed on asdf py3.11.0 (NOT a uv checkout — docs' `~/.hermes/hermes-agent` path does not apply); `tts.provider: edge`, voice en-US-AriaNeural already configured
- WSL sudo requires a password → agent needs `SUDO_PASSWORD` in `~/.hermes/.env` or the user runs apt commands themselves
