# FLM Audio / Speech Capabilities (verified Aug 2026)

## Models with audio input

| Model | Audio | Role | Installed (Aug 2026)? |
|---|---|---|---|
| `gemma4-it:e2b` | ✅ native audio input | Any-to-text: text/image/audio → text (~300M audio encoder) | ✅ (default) |
| `gemma4-it:e4b` | ✅ native audio input | Same, larger/slower | ✅ |
| `whisper-v3:turbo` | 🎯 dedicated STT | Whisper V3 Turbo (MIT) on NPU — pure transcription | ❌ `flm pull whisper-v3:turbo` |

Everything else in the FLM catalog (qwen3.5, qwen3, llama3.x, deepseek-r1, gpt-oss, phi4-mini, lfm2, embed-gemma, medgemma, translategemma) is **text-only**. `lfm2-trans:2.6b` is a transcript-*processing* LLM (text), NOT audio input.

## Evidence gemma4-it:e2b handles audio (verified from disk + HF card)

- Model dir `C:\Users\<user>\.flm\models\Gemma4-E2B-IT-NPU2\` contains `audio_weight.q4nx` + `vision_weight.q4nx` alongside `model.q4nx`
- `config.json` keys: `audio_config`, `audio_token_id`, `boa_token_id`, `eoa_token_id` (begin/end-of-audio), `audio_model_weight`, `vision_config`; `model_type: gemma4_text`, `Gemma4ForConditionalGeneration`
- HF card `FastFlowLM/Gemma4-E2B-IT-NPU2` (Google Gemma 4, Apache-2.0, pipeline_tag any-to-any): "Processes Text, Image… Video, and Audio (featured natively on the E2B and E4B models)"; E2B/E4B have ~300M audio encoder. Dense table: E2B/E4B supported modalities = Text, Image, Audio; 31B = Text, Image (no audio).
- Skill catalog already typed it "Any-to-Text — Vision ✅ + Audio".

## No TTS in FLM

FLM catalog has no speech-output model. A voice loop needs TTS elsewhere: sherpa-onnx + Kokoro/Piper, or Windows SAPI.

## Ground truth for installed models

`flm list --filter installed` (PowerShell) — NOT the model catalog reference (goes stale). Aug 2026: installed = `gemma4-it:e2b`, `gemma4-it:e4b`; whisper-v3:turbo NOT downloaded; qwen3.5:2b NOT installed despite being listed in an earlier catalog snapshot.

## Adding an audio tool to the gemma-npu plugin (unbuilt as of Aug 2026)

- Plugin: `~/.hermes/plugins/gemma-npu/` — registers 7 tools, all hitting FLM OpenAI-compatible API at `http://localhost:50001/v1` (openai client, api_key dummy).
- `analyze_image` sends OpenAI-style content parts: `{"type":"image_url","image_url":{"url":"data:<mime>;base64,<b64>"}}`.
- Audio analog = `{"type":"input_audio","input_audio":{"data":b64,"format":"wav"}}` — **UNVERIFIED against FLM API; spike first** (15 min). FLM docs API page (fastflowlm.com/docs/api/) 404s; docs landing is thin.
- Whisper alternative for pure transcription: pull `whisper-v3:turbo` and call it as its own model.

## Links

- FLM docs: https://fastflowlm.com/docs/
- HF model card: https://huggingface.co/FastFlowLM/Gemma4-E2B-IT-NPU2
