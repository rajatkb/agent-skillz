# FLM Model Catalog — Ryzen AI 9 HX 370 (Strix Point)

System: ROG Zephyrus G14 GA403WR, 32 GB RAM (~16 GB NPU-accessible), XDNA2 NPU (50 TOPS).

All benchmark data from official FastFlowLM docs (fastflowlm.com/docs/benchmarks/) on Kraken Point. Strix Point (HX 370) is faster — expect +5-15% over these numbers.

---

## Currently Downloaded (✅) — SNAPSHOT; verify with `flm list --filter installed` (this table goes stale)

| Tag | Params | Type | Thinking | Tools | Vision | Decode TPS | Prefill TPS | Notes |
|-----|--------|------|----------|-------|--------|-----------|-------------|-------|
| `gemma4-it:e2b` | 2B | Any-to-Text | Toggleable | Yes | ✅ + Audio | **22.6** | 721 | Default model. Text/image/audio → text. 1.7s image TTFT. See audio-and-whisper.md. |
| `gemma4-it:e4b` | 4B | Any-to-Text | Toggleable | Yes | ✅ + Audio | — | — | Larger sibling of default; native audio too. |
| `llama3.2:1b` | 1B | Text-to-Text | No | No | ❌ | **64.5** | 1686 | Downloaded (Llama-3.2-1B-NPU2 on disk, Aug 2026). Trivial-task workhorse — see capability profile below. |

Snapshot Aug 2026: `qwen3.5:2b` listed in earlier versions is NOT installed; `whisper-v3:turbo` (FLM's STT model) is NOT downloaded — `flm pull whisper-v3:turbo` first.

### Capability profile: llama3.2:1b (researched Aug 2026)

Model card (fastflowlm.com/docs → Models → LLaMA): Text-to-Text, **Think: No, Tool Calling: No**, Q4_1, max ctx 128k (default 128k). Fastest chat model in the catalog — ~64.5 dec / 1686 prefill TPS on Kraken Point; Strix Point (HX 370) +5-15%.

Meta's own positioning (Llama 3.2 release blog): SOTA-in-class for on-device **summarization, instruction following, rewriting**. It's pruned+distilled from the 3B — solid on single-step, well-scoped tasks; collapses on multi-step reasoning. Artificial Analysis Intelligence Index: **6/100**; math/code genuinely weak (~GSM8K 25%, HumanEval ~7%).

Good fits: high-volume batch classification/tagging, entity/keyword extraction, JSON normalization/formatting, short-doc summarization, query routing + irrelevant-doc filtering (e.g. crawl4ai pipelines), anything where gemma4-it:e2b (22 TPS, ~6.6 GB working set) is overkill — 3x speed, ~0.55 GB Q4_1 weights. Need more capability in the same class? Step up to `llama3.2:3b` (26.3 TPS, same no-think/no-tools profile).

---

## Best Candidates to Download

### Vision Models

| Tag | Params | Thinking | Tools | Decode TPS | Prefill TPS | Image TTFT | Why |
|-----|--------|----------|-------|-----------|-------------|------------|-----|
| `gemma4-it:e2b` | 2B | Toggleable | Yes | **22.6** | 721 | 1.7s | Faster vision + same feature set as E4B. Good light-weight alternative. |
| `qwen3vl-it:4b` | 4B | ✅ | ❌ | ~16 | ~500 | 3.3s @720p | Vision + thinking but no tools. Slower than Gemma4 on images. |

### Text + Thinking + Tools

| Tag | Params | Decode TPS | Prefill TPS | Max Ctx | Why |
|-----|--------|-----------|-------------|---------|-----|
| `qwen3:8b` | 8B | 11.9 | 357 | 32k | Best text quality. Toggleable thinking + tools. Same speed as Gemma4. |
| `qwen3:4b` | 4B | **19.6** | 509 | 32k | Thinking + tools at 2x speed. Sweet spot for quality/speed. |
| `qwen3.5:4b` | 4B | 15.0 | 378 | 32k | Qwen3.5 generation. Slightly slower than Qwen3-4B but newer. |
| `qwen3.5:9b` | 9B | 9.3 | 284 | 32k | Largest Qwen. May OOM at longer contexts (16 GB NPU limit). |

### Sparse / MoE (Large but Efficient)

| Tag | Params | Arch | Reasoning | Decode TPS | Prefill TPS | Max Ctx | Notes |
|-----|--------|------|-----------|-----------|-------------|---------|-------|
| `gpt-oss:20b` | 20B | **MoE** | Low/Med/High effort | **18.2** | 221 | 128k | **Largest model on FLM.** MoE sparsity makes it faster than 8B dense models. No tools, no vision. |
| `lfm2:2.6b` | 2.6B | SSM | No | ~20 | ~500 | 32k | Liquid Foundation Model. Alternative architecture, small. |
| `lfm2.5-it:1.2b` | 1.2B | SSM | ✅ | ~35 | ~800 | 32k | Fastest thinking model. Tiny but has thinking mode. |

### Reasoning (Always-on Thinking)

| Tag | Params | Tools | Decode TPS | Max Ctx | Notes |
|-----|--------|-------|-----------|---------|-------|
| `deepseek-r1:8b` | 8B | No | ~9-10 | 128k (16k default) | Strong R1 chain-of-thought. No tool calling. |
| `deepseek-r1-0528:8b` | 8B | No | ~9-10 | 64k (16k default) | Updated R1 variant on Qwen3 base. |

### No Thinking, No Tools (Simple & Fast)

| Tag | Params | Decode TPS | Prefill TPS | Max Ctx | Notes |
|-----|--------|-----------|-------------|---------|-------|
| `phi4-mini-it:4b` | 4B | **21.8** | 643 | 128k | Fast, clean Microsoft Phi. Good for structured output. |
| `nanbeige4.1:3b` | 3B | 23.5 | 612 | 32k | Fast, competitive quality. |
| `llama3.1:8b` | 8B | 12.8 | 403 | 128k | Reliable baseline. No frills. |
| `llama3.2:3b` | 3B | 26.3 | 766 | 128k | Fastest Llama option. |
| `llama3.2:1b` | 1B | **64.5** | 1686 | 128k | Blazing fast for trivial tasks. |

### Special-Purpose

| Tag | Use | Notes |
|-----|-----|-------|
| `medgemma:4b` | Medical QA | Fine-tuned Gemma for clinical text |
| `translategemma:4b` | Translation | Can translate between languages |
| `whisper-v3:turbo` | Audio transcription | Speech-to-text |
| `embed-gemma:300m` | Embeddings | Text embeddings, not chat |

---

## System Limits

| Constraint | Value |
|-----------|-------|
| Total DRAM | 32 GB |
| NPU-accessible | ~16 GB (Linux: <50% of system DRAM) |
| Model weight at Q4_1 | ~0.55 GB per 1B params |
| Approx max model size | 20-24B params at Q4_1 (fits in 16 GB with context overhead) |
| 32k context KV cache | ~0.5-2 GB depending on model |
| 128k context KV cache | ~2-8 GB — may OOM 8B+ models on 16 GB limit |

---

## Selection Heuristics

1. **Need vision?** → `gemma4-it:e2b` (current default, faster) or `gemma4-it:e4b` (larger, slower)
2. **Need tools + thinking + max quality?** → `qwen3:8b` (text) or `gemma4-it:e2b` (vision)
3. **Need speed + tools + thinking?** → `qwen3:4b` (19.6 TPS) or `qwen3.5:4b` (15 TPS)
4. **Need max quality, no vision/tools?** → `gpt-oss:20b` (MoE, 18.2 TPS, reasoning effort)
5. **Need reasoning only?** → `deepseek-r1:8b` (thinking always on)
6. **Need raw speed, no thinking/tools?** → `phi4-mini-it:4b` (21.8 TPS) or `llama3.2:3b` (26.3 TPS)
7. **Need an embedding model?** → `embed-gemma:300m`

---

## Source

All data from https://fastflowlm.com/docs/ — model cards and benchmarks pages, last verified July 2026.
