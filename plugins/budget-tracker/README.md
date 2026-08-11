# budget-tracker

> 📊 Token usage & budget tracking for Hermes — costs, DeepSeek balance, and local NPU offload savings, all in one end-of-session report.

## Overview

`budget-tracker` hooks into every Hermes session to track token usage and estimate cost in real time. It uses Hermes' own pricing engine (cache-aware, model-aware) so estimates match what the provider actually bills, and it folds in the DeepSeek-equivalent cost that **local NPU calls avoided** — giving you a true picture of what the setup costs versus what it would cost without on-device inference.

## Features

- **Per-session token tracking** — input / output / cache-read / cache-write / reasoning tokens
- **Cache-aware cost estimation** — reports cost *with* cache pricing and what it would have been *without* (i.e. the savings prompt-caching delivers)
- **Real DeepSeek balance** — fetches live balance from `api.deepseek.com/user/balance` (TTL-cached, 5 min)
- **Budget ceiling** — set a USD budget; live progress bar, alerts at ≥80%, 🚨 warning when exceeded
- **NPU offload accounting** — counts local gemma-npu calls and the DeepSeek-equivalent cost they avoided
- **Idle & interval reporting** — one-liner every 10 requests, mid-session report after 120s idle, full end-of-session summary
- **Persistence** — all-time + period counters survive restarts (`data.json`, atomic writes)

## Hooks

| Hook | Purpose |
|---|---|
| `on_session_start` | Reset session accumulator; fetch fresh DeepSeek balance (TTL-aware); auto-seed budget from balance on first run |
| `post_api_request` | Accumulate usage from each API response; estimate cost via Hermes pricing engine |
| `on_session_end` | Emit the full end-of-session report |

## CLI

| Command | Description |
|---|---|
| `hermes budget` | All-time totals + last known DeepSeek balance |
| `hermes budget history` | Per-session breakdown with costs & savings |
| `hermes budget set N` | Set budget ceiling in USD |
| `hermes budget reset` | Reset period counters |

## Installation

```bash
# copy the plugin into your Hermes plugins dir
cp -r plugins/budget-tracker ~/.hermes/plugins/
```

Requires `httpx` (`pip install httpx`). The DeepSeek balance feature reads `DEEPSEEK_API_KEY` from the environment (or Hermes' dotenv).

## Files

| File | Purpose |
|---|---|
| `plugin.yaml` | Plugin manifest (hooks, version) |
| `__init__.py` | Hook implementations, cost engine integration, CLI |
| `data.json` | *(runtime)* persistent counters — **not checked in** |

## Privacy

No conversation content is ever recorded — only aggregate token counts, timestamps, and cost figures.
