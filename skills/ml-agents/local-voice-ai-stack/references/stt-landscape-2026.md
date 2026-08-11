# Open-Source STT Landscape (research, Aug 2026)

Condensed session research. WER figures are vendor/leaderboard disclosures (HF Open ASR Leaderboard where noted). Verify current rankings at https://huggingface.co/spaces/hf-audio/open_asr_leaderboard before big decisions.

## Model table

| Model | Params | Avg WER | Speed | Langs | License | Notes |
|---|---|---|---|---|---|---|
| Canary Qwen 2.5B | 2.5B | 5.63% | 418 RTFx | EN | CC-BY-4.0 | Best open EN accuracy; ~8GB VRAM |
| IBM Granite Speech 3.3 8B | 8B | 5.85% | — | EN/FR/DE/ES (+EN↔JA/ZH translation) | Apache-2.0 | Enterprise-grade |
| Parakeet TDT 0.6B v3 | 0.6B | 6.34% | ~3,300× RT | EN + 25 EU langs | CC-BY-4.0 | INT8 ONNX ~631MB; CPU-only fine; default dictation pick |
| Nemotron Speech Streaming EN | — | 6.93% (streaming) | 80ms–1.12s latency | 40 locales | NeMo stack | Live text-as-you-speak; INT8 ~680MB |
| Whisper large-v3 | 1.5B | ~7.4% | slowest (token-by-token) | 99 | MIT | Multilingual king; also largest model files |
| Moonshine (Useful Sensors) | ~245M | beats Whisper Tiny/Small; v2 more langs | streaming | v1 EN; v2 AR/ZH/JA/KO/ES/UK/VI | Apache-2.0 | Tiny/edge; words appear as you speak |
| Qwen3-ASR (Jan 2026) | 0.6B / 1.7B | — | — | 52 + dialect | Qwen/Apache | On Qwen3-Omni base; ecosystem maturing |
| Voxtral (Mistral) | 3B / 24B | — | — | many | Apache-2.0 | LLM-grade: understands context, not just transcription; ASR + TTS bundled under one name (licensed differently) |

## Runtimes

- **sherpa-onnx** (k2-fsa, Apache-2.0): runs Zipformer, Paraformer, Whisper, NeMo/Parakeet, Moonshine, SenseVoice for STT + TTS (Piper, Kokoro) + VAD + speaker ID + wake word; CPU/GPU/NPU via ONNX; cross-platform. The glue for "talk to machine" apps.
- whisper.cpp (MIT, GGML), faster-whisper (MIT, CTranslate2), parakeet.cpp.
- AMD Ryzen AI: official Whisper-on-NPU path — whisper.cpp with encoder offloaded to XDNA, Windows-only (ryzenai.docs.amd.com/en/latest/whisper_cpp.html). Accelerates Whisper itself; doesn't change model choice.

## Voice control / dictation apps (open-source status)

- **Talon**: core engine NOT open source (talonvoice.com/EULA.txt — files not licensed for redistribution); community command sets open (talonhub/community). Skip when open source is a hard requirement.
- **Dragonfly + Caster**: open-source (Python) voice-command framework for Windows; works with Windows Speech Recognition or Whisper/faster-whisper backend.
- **Ari** (DO0OG/Ari-VoiceCommand): open-source Windows voice agent — wake word, STT/TTS, desktop automation, MCP tools, local LLM.
- **OpenWhispr** (openwhispr/openwhispr): open-source Windows dictation; hotkey→cursor; ships Parakeet/Whisper/Nemotron locally; no telemetry. Their model comparison blog is a solid practical source.
- **OmniDictate**: open-source, faster-whisper based, real-time Windows dictation.

## Sources

- Northflank: Best open-source STT model 2026 benchmarks — https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks
- OpenWhispr: Parakeet vs Whisper vs Nemotron — https://openwhispr.com/blog/parakeet-vs-whisper-vs-nemotron
- HF Open ASR Leaderboard — https://huggingface.co/spaces/hf-audio/open_asr_leaderboard
- sherpa-onnx — https://github.com/k2-fsa/sherpa-onnx
- AMD Ryzen AI whisper.cpp support — https://ryzenai.docs.amd.com/en/latest/whisper_cpp.html
- Talon EULA — https://talonvoice.com/EULA.txt
- InfoQ: Mistral Voxtral — https://www.infoq.com/news/2025/07/mistral-voxtral-audio-speech-llm/
- Gladia: Qwen3-ASR + open STT models — https://www.gladia.io/blog/best-open-source-speech-to-text-models
