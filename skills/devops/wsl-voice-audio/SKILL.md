---
name: wsl-voice-audio
description: "Get microphone/speaker audio working in WSL (WSLg → PulseAudio → sounddevice) and wire Hermes Voice Mode — push-to-talk STT via faster-whisper, model selection, user preferences."
tags: [wsl, wslg, audio, microphone, voice, speech-to-text, faster-whisper, hermes, pulseaudio]
category: devops
---

# WSL Voice & Audio (WSLg → Pulse → sounddevice → faster-whisper)

## Trigger
- Voice input / push-to-talk in Hermes (TUI or CLI, `/voice on`)
- Mic or speakers not visible in WSL (`pactl` empty, sounddevice raises "PortAudio library not found")
- WSLg not initialized: no `/mnt/wslg/PulseServer`, `DISPLAY` empty, no audio at all
- "I want to talk to my machine" — voice commands/dictation into the agent

## Architecture (why it works)
```
speech → G14 mic (Windows) → WSLg bridge (PulseAudioRDPSource)
       → /mnt/wslg/PulseServer socket → PulseAudio in distro
       → PortAudio (libportaudio2) → sounddevice → faster-whisper (Whisper base, CPU int8)
       → agent message → tools act (winappcli/terminal/MCP) → text reply (TTS optional)
```

## Step 1 — Is WSLg actually enabled? (most common root cause)
`guiApplications=false` in `~/.wslconfig` **disables WSLg entirely** — no audio in/out, no GUI, no `/mnt/wslg/PulseServer`, `DISPLAY` empty, no wslg processes on Windows. A restart will NOT fix it; the config must change first:
- Edit `C:\Users\<user>\.wslconfig`: set `guiApplications=true` (under `[wsl2]`)
- `wsl --shutdown` from Windows, reopen WSL
- Verify: `ls /mnt/wslg/PulseServer`; `echo $DISPLAY` → `:0`; `echo $PULSE_SERVER` → `unix:/mnt/wslg/PulseServer`
- Healthy `/mnt/wslg/` contains: `PulseServer`, `PulseAudioRDPSink`, `PulseAudioRDPSource`, `weston.log`, `pulseaudio.log`. If it contains only `run/user/`, WSLg is disabled or half-initialized — config problem, not a restart problem.

## Step 2 — Install client packages (NO sudo password needed)
WSL's default root user has no password — run apt as root via interop, bypassing `sudo: a password is required` entirely (no SUDO_PASSWORD env needed):
```bash
wsl.exe -d <distro> -u root -e apt-get update
wsl.exe -d <distro> -u root -e apt-get install -y libportaudio2 pulseaudio-utils libasound2-plugins
```
- `libportaudio2` → the C lib sounddevice needs (absence = `OSError: PortAudio library not found` on import)
- `pulseaudio-utils` → pactl diagnostics
- `libasound2-plugins` → ALSA→Pulse shim (needed if PortAudio uses the ALSA backend)

## Step 3 — Verify the chain (headless, before any live demo)
```bash
pactl list sources short   # expect RDPSource (mic) — SUSPENDED state is NORMAL (idle)
pactl list sinks short     # expect RDPSink (speakers)
ldconfig -p | grep portaudio
python -c "import sounddevice; print(sounddevice.query_devices())"  # expect ['pulse']
```
Then run `scripts/verify_voice_chain.py` (records 3s + transcribes with faster-whisper, prints RMS + transcript).
- RMS ≈ 0.00003 with a tiny peak = chain flowing, room was quiet → fine.
- Pure zeros = Windows mic privacy block: Settings → Privacy & security → Microphone, grant the terminal app.
- First faster-whisper run downloads `base` (~150MB) — do it in the headless test, not during a live demo.

## Step 4 — Hermes Voice Mode
- Deps (Hermes python env): `sounddevice` + `faster-whisper` + `numpy` — code lives in `hermes_cli/voice.py` (recording loop), `tools/voice_mode.py` (`transcribe_recording` + hallucination filter), `tools/transcription_tools.py` (`WhisperModel` load, `DEFAULT_LOCAL_MODEL`).
- Usage: `/voice on` → **Ctrl+B** → speak → auto-stops after 3s silence (configurable: `voice.silence_threshold`, `voice.silence_duration`, `voice.record_key`, `voice.beep_enabled`).
- STT: faster-whisper, `DEFAULT_LOCAL_MODEL="base"`, CPU int8. Sizes: `tiny/base/small/medium/large-v3`. Hallucination filter (26 known phrases + repeat regex) strips phantom text from silence.
- TTS is OPTIONAL and independent (`/voice tts`) — input-only voice mode needs zero TTS config.

## Model selection for STT (this user's setup)
| Option | Verdict |
|---|---|
| faster-whisper `base` | Start here — native voice-mode integration, CPU int8, near-instant on short commands |
| FLM `whisper-v3:turbo` (NPU) | Accuracy upgrade (~7.75% WER vs base's several-points-worse). Needs `flm pull whisper-v3:turbo` + a shim (voice mode dispatches to faster-whisper/Groq/OpenAI only). FLM serves ONE model per instance — whisper displaces the LLM, or run a 2nd instance on `FLM_PORT` |
| gemma4-it:e2b native audio | Audio UNDERSTANDING (~300M encoder, any-to-text), NOT tuned for raw ASR WER — good for audio QA experiments, wrong tool for transcription. Do not route STT through it |

## User preferences (this user)
- Voice INPUT only — no TTS output wanted; keep TTS off (never `/voice tts`).
- NO Edge / Microsoft voice anything — `tts.provider: edge` is banned. If TTS is ever wanted: NeuTTS, Piper, or Kokoro (local, non-Microsoft).
- Never create `.bak` files during edits.

## Pitfalls
- `wsl.exe` output piped through cmd/powershell arrives UTF-16-garbled (letter-spaced "W S L") — invoke `wsl.exe` directly from WSL bash, or pipe `| tr -d '\r'`.
- pactl missing → distro has no audio stack; check `.wslconfig guiApplications` FIRST (WSLg is the audio server; installing pulseaudio server packages in the distro is unnecessary).
- `wsl.exe -d <distro> -u root` works on default WSL installs (root has no password) — prefer over asking for SUDO_PASSWORD.
- Editing Windows files from WSL: .wslconfig/INI edits are fine; YAML/JSON on NTFS can pick up a UTF-8 BOM (see WSL→NTFS BOM memory note).
- Voice deps may appear/disappear across WSL restarts — verify with the Hermes python (`/home/<user>/.asdf/installs/python/3.11.0/bin/python`), not bare `python3` if PATH is mixed.

## Support files
- `scripts/verify_voice_chain.py` — record-3s + transcribe probe (prints devices, RMS, transcript)
