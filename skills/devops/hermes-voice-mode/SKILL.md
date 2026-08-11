---
name: hermes-voice-mode
description: "Set up and troubleshoot Hermes voice — Voice Mode (/voice, Ctrl+B push-to-talk), wake word (/wake 'hey hermes'), local STT (faster-whisper), TTS (edge), and WSL audio plumbing (WSLg/PulseAudio mic access)."
tags: [hermes, voice, stt, tts, wake-word, faster-whisper, wslg, pulseaudio, audio]
category: devops
---

# Hermes Voice Mode — talk to your machine

## Trigger

- User wants voice input / hands-free control: "talk to my machine", "voice working", dictation, voice commands
- Setting up `/voice`, `/wake`, STT or TTS providers
- WSL mic/audio problems (no audio device, mic not visible to WSL)

## Key facts

- **Voice Mode is NATIVE in Hermes** (CLI + TUI): `/voice on` → press Ctrl+B → speak → silence auto-stops after 3s → transcribed → sent to the normal agent loop (all tools available: terminal, winappcli/UIA, NPU, MCP) → spoken reply if TTS on. Loop auto-restarts. Record key configurable via `voice.record_key` (default `ctrl+b`). `/voice tts` toggles spoken replies; `/voice status` shows state.
- **STT providers**: `faster-whisper` (LOCAL, free, zero keys, ~150MB base model auto-downloads on first use) | Groq (`GROQ_API_KEY`, cloud free tier) | OpenAI (`VOICE_TOOLS_OPENAI_KEY`, paid). Zero-key path = just have faster-whisper installed.
- **TTS**: `edge` works keyless — this user already has `tts.provider: edge`, voice `en-US-AriaNeural` in `~/.hermes/config.yaml`. Others: elevenlabs/openai/minimax/neutts/piper/kittentts/gemini/xai.
- **Wake word**: `/wake on` — openWakeWord (default) ships a bundled "hey hermes" model, free, fully on-device; `sherpa` engine = open-vocabulary any phrase; Porcupine needs a key. Lazy-installs on first enable; toggle persists `wake_word.enabled` in config.yaml. Hands-free: say "hey hermes" → records one utterance → agent replies → listener resumes.
- Docs: hermes-agent.nousresearch.com/docs/user-guide/features/voice-mode, /features/wake-word, /features/tts. Raw markdown is curl-able from raw.githubusercontent.com/NousResearch/hermes-agent/main/website/docs/... (useful since the docs site pages can be thin/garbled).

## Install — match the ACTUAL install, not the docs' path

- Docs say `cd ~/.hermes/hermes-agent && uv pip install -e ".[voice]"` — that path is only valid for uv checkouts. **PITFALL: this machine installs Hermes via pip on asdf py3.11** (`pip show hermes-agent` → `~/.asdf/installs/python/3.11.0/lib/python3.11/site-packages`), no `~/.hermes/hermes-agent` dir. Equivalent here: `pip install sounddevice faster-whisper` (numpy already present).
- System deps (Linux): PortAudio + ffmpeg. Ubuntu: `sudo apt install portaudio19-dev ffmpeg`; Debian: `libportaudio2`. This box is **Debian 13 trixie**. sounddevice fails without the PortAudio lib.
- Exception to python-venv-hygiene: hermes ITSELF lives in the asdf py3.11 env, so voice extras go into that same env.

## WSL audio — the mic problem

- WSL2 has no native sound drivers; **WSLg bridges audio through a PulseAudio socket at /mnt/wslg/PulseServer**. PulseAudio often ALREADY runs inside the WSLg image — the distro may only need client tools (`pulseaudio-utils`) + `libportaudio2`, not a full pulse server (microsoft/wslg#1378).
- Mic path (microsoft/WSL#9624): ALSA shim (`~/.asoundrc` → Pulse) + `PULSE_SERVER` pointing at the WSLg socket + **Windows mic privacy permission enabled for the terminal app** (Settings → Privacy & security → Microphone). Missing permission fails SILENTLY — check it first.
- Community-confirmed mic-in-WSL on WSL 2.3.26.0+ with WSLg. This box: WSL 2.7.10, Win11 25H2 (26200.8875).
- **Diagnose first, branch after**: install `pulseaudio-utils` only, run `pactl list sources short`. Mic visible → native path. Not visible → bridge: Windows-side capture (ffmpeg `-f dshow`) streamed into a virtual PulseAudio source in WSL (module-pipe-source, or null-sink + remap-source per wslg#1141); TTS playback fallback = PowerShell `System.Media.SoundPlayer` (hermes-notify.ps1 pattern).

## Sudo in WSL

- This user's WSL account requires a sudo password; the agent cannot apt install without either the user running the command themselves or `SUDO_PASSWORD` in `~/.hermes/.env` (Hermes' designed path for agent sudo).

## Machine state (Aug 2026 — after WSLg fix)

- **Diagnostic RESULT: native WSLg mic path is viable on this box.** Root cause of no-audio was `.wslconfig guiApplications=false` (disables WSLg = GUI + audio entirely; `/mnt/wslg` had only `run/user/`, no `PulseServer`). Flipped to `true` + `wsl --shutdown` → `/mnt/wslg/PulseServer` socket, `PulseAudioRDPSink`/`PulseAudioRDPSource` endpoints, `DISPLAY=:0`, `PULSE_SERVER=unix:/mnt/wslg/PulseServer` all present. WSLg plumbing details in `references/wsl-audio-notes.md`.
- **Voice deps ALREADY installed** (were absent pre-restart, present post-restart, no recorded install step — check `pip list` before reinstalling): `sounddevice 0.5.5`, `faster-whisper 1.2.1`, `numpy`, in the asdf py3.11 env.
- **Remaining blocker: system libs only** — `sudo apt install -y libportaudio2 pulseaudio-utils libasound2-plugins` (sounddevice currently raises `OSError: PortAudio library not found` on import). Then `pactl list sources short` → then user live test.
- **Code-verified STT facts (0.18.2):** `tools/transcription_tools.py` → `DEFAULT_LOCAL_MODEL = "base"`, `STT_GROQ_MODEL` default `whisper-large-v3-turbo`, local sizes `tiny/base/small/medium/large-v3`. Dispatch path: `hermes_cli/voice.py` → `tools/voice_mode.py` (recording, silence, hallucination filter: 26 phrases + repeat regex) → `tools/transcription_tools.py`.
- **No TTS in FLM catalog** — voice loop output stays on Edge TTS (or local NeuTTS/sherpa-onnx Kokoro) unless sherpa-onnx is added.

## Verification sequence (headless → interactive)

1. `pactl list sources short` — is the mic visible to WSL?
2. Python: `import sounddevice; sounddevice.query_devices()` — PortAudio sees it
3. faster-whisper transcribes a generated test WAV — verify text comes back
4. **USER does the final test**: `/voice on`, Ctrl+B, say "open notepad" → agent executes via winappcli → spoken reply. That loop proves voice → machine-action.

## FLM/NPU angle (future)

- gemma4-it:e2b (FLM default) has native audio input (~300M audio encoder) — could replace faster-whisper for on-NPU STT, but **FLM API audio acceptance is UNVERIFIED — spike first** (see flm-lifecycle skill model catalog).
- FLM catalog also has `whisper-v3:turbo` (NPU Whisper) — not downloaded.

## Working with this user

- Present build plans as **plain-language prose with sources cited** for every technical claim; close with a simple go/no-go question in prose. Avoid multi-choice clarify lists before the user has stated their goal (one was interrupted with "stop").
- When asked to re-explain ("can you reexplain the plan"), walk the actual steps in plain language — no jargon recap, no structured tables.

## References

- `references/wsl-audio-notes.md` — sourced WSLg/PulseAudio notes (URLs + quotes) and local machine state snapshot
