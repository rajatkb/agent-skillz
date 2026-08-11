# gemma-npu

> 🧠 Zero-API-cost NPU tools for Hermes — Gemma 4 running on the local AMD Ryzen AI NPU via FLM.

## Overview

This plugin wires seven NPU-accelerated tools into Hermes. Instead of paying DeepSeek (or any cloud provider) per token for every summarization, classification, or vision call, the workload is offloaded to a Gemma 4 model served locally on the machine's NPU via [FLM](https://fastflowlm.com/docs) (FastFlowLM). Every tool result reports the tokens used and the DeepSeek-equivalent cost it avoided.

## Tools (toolset: `npu`)

| Tool | Purpose |
|---|---|
| `summarize_text` | Condense/extract key points from text |
| `summarize_document` | Summarize a file on disk without loading it into the main model's context |
| `extract_from_webpage` | Fetch a URL and answer a question from its content |
| `classify_text` | Categorize text into predefined classes |
| `extract_json` | Extract structured JSON from unstructured text |
| `analyze_image` | Image understanding, OCR, UI/screenshot analysis, chart/table comprehension |
| `create_plan` | Decompose a complex goal into a structured plan |

## How it works

- Each tool is a thin adapter over the local FLM HTTP endpoint (`FLM_HOST:FLM_PORT`, default `127.0.0.1:50001`)
- Context is minimal by design — only the input content + instruction go to the model, never the conversation
- Results are returned as JSON payloads carrying `input_tokens`, `output_tokens`, `model`, and `deepseek_total_cost` (the avoided cost) — consumed by `budget-tracker` and `chat-logger` for accounting
- The FLM server itself is managed by the `flm-lifecycle` plugin (up on demand, down when idle)

## Installation

```bash
cp -r plugins/gemma-npu ~/.hermes/plugins/
```

Requires a running FLM server with a Gemma 4 model (e.g. `gemma4-it:e2b`). See the `flm-lifecycle` plugin and the `flm-lifecycle` skill for server management.

## Files

| File | Purpose |
|---|---|
| `plugin.yaml` | Plugin manifest (tools, version) |
| `__init__.py` | Tool registration on the `npu` toolset |
| `schemas.py` | JSON schemas for all seven tools |
| `tools.py` | FLM client + per-tool implementations |

## Privacy

Only the image/text being processed and the instruction are sent to the local model — **no conversation context, no system prompt leakage**. Everything stays on-device.
