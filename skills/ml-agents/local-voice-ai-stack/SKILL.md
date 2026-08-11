---
name: local-voice-ai-stack
description: "Design and build local voice AI on this machine (G14 GA403): choosing open-source STT/TTS models, the sherpa-onnx runtime, voice-control tools, and the full mic→STT→LLM→TTS loop on NPU/GPU."
tags: [voice, stt, tts, asr, whisper, parakeet, sherpa-onnx, speech, voice-assistant, npu]
category: ml-agents
---

# Local Voice AI Stack (talk-to-your-machine)

## Trigger

- Choosing an open-source speech-to-text / TTS model for local use
- Building voice input, dictation, or a voice-assistant loop (mic → text → action → speech)
- Evaluating voice-control tools (Talon, Dragonfly, Ari, OpenWhispr)
- Wiring speech into Hermes / FLM on this machine

## Decision framework (mid-2026 state — details + sources in references/stt-landscape-2026.md)

- **English/European dictation, local CPU:** NVIDIA Parakeet TDT 0.6B v3 — CC-BY-4.0, INT8 ONNX ~631MB, ~3,300× realtime, ~6.3% WER (beats Whisper large-v3's ~7.4%)
- **Live text-as-you-speak:** NVIDIA Nemotron Speech Streaming (80ms–1.1s latency) or Moonshine (~245M, Apache-2.0, edge/streaming)
- **Max English accuracy:** Canary Qwen 2.5B (5.63% WER) / IBM Granite Speech 3.3 8B (Apache-2.0)
- **Multilingual (>40 langs):** Whisper large-v3 (MIT, 99 langs) or Qwen3-ASR (52 langs, Jan 2026)
- **LLM-grade understanding (context, not just transcription):** Mistral Voxtral (Apache-2.0, 3B/24B)
- **Runtime:** sherpa-onnx (k2-fsa, Apache-2.0) — runs Zipformer, Paraformer, Whisper, NeMo/Parakeet, Moonshine, SenseVoice + TTS (Piper/Kokoro) + VAD + wake word, CPU/GPU/NPU via ONNX
- **TTS:** Kokoro via sherpa-onnx (high-quality open TTS)

## Voice-control tools (open-source status matters to this user)

- **Talon = NOT fully open source** — core engine is proprietary (talonvoice.com/EULA.txt restricts redistribution); only community command sets (talonhub/community) are open. Skip when user demands open source.
- **Dragonfly + Caster** — open-source Python voice-command framework, works on Windows with Whisper/faster-whisper backend
- **Ari** (DO0OG/Ari-VoiceCommand) — open-source Windows voice agent: wake word, STT/TTS, desktop automation, MCP tools, local LLM
- **OpenWhispr / OmniDictate** — ready-made open-source Windows dictation apps (OpenWhispr ships Parakeet/Whisper/Nemotron, fully local, hotkey→cursor)
- Windows built-in Voice Access — free local baseline, but not open source

## This machine's stack (G14 GA403, XDNA2 NPU, RTX 5070 Ti)

- **NPU (FLM server):** gemma4-it:e2b is any-to-text — text/image/**audio** input → text out. whisper-v3:turbo available as dedicated STT (`flm pull whisper-v3:turbo`). See flm-lifecycle skill → references/audio-and-whisper.md.
- **No TTS in FLM catalog** — close the loop with sherpa-onnx + Kokoro (CPU/GPU) or Windows SAPI.
- Parakeet TDT INT8 runs on CPU alone — won't fight FLM for the NPU.
- Full loop (unbuilt as of Aug 2026, user halted at planning): mic → whisper-v3:turbo or gemma4 audio → gemma4-it:e2b (tools) → execute → Kokoro TTS.

## Pitfalls

- **FLM API audio input is UNVERIFIED.** `analyze_image` works via OpenAI-style content parts (`{"type":"image_url","image_url":{"url":"data:<mime>;base64,..."}}`); the audio analog `{"type":"input_audio",...}` is untested against FLM — spike it (15 min) before building an audio tool. FLM docs API page (fastflowlm.com/docs/api/) 404s; docs landing is thin.
- **Advisory questions:** when the user asks "how can I make X more useful", give the options and let them decide unprompted — an immediate clarify choice after an advisory answer drew a "stop" (Aug 2026).
- Installed-model ground truth is `flm list --filter installed`, not skill docs (they go stale).

## References

- `references/stt-landscape-2026.md` — full benchmark table, licenses, runtimes, sources
- flm-lifecycle skill → `references/audio-and-whisper.md` — FLM audio/whisper specifics (model evidence, install state)
