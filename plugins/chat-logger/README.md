# chat-logger

> 📜 Every Hermes session recorded to disk — raw API traffic, tool calls, and lifecycle events, compressed and queryable.

## Overview

`chat-logger` is a full-fidelity session recorder: it captures every LLM API request (what went in), every API response (assistant text + tool-call decisions), every tool invocation with its result, and session lifecycle events — written as gzip-compressed JSON-lines files, one per session.

Built for debugging agent behavior after the fact: *why did the agent call that tool? what did it see? what did the model reply with?*

## Features

- **Six event types**: `session_start`, `api_request`, `api_response`, `tool_call_start`, `tool_call_end`, `session_end`
- **Tool-call fidelity** — records tool name, full argument JSON, and result (truncated previews)
- **NPU usage extraction** — recognizes gemma-npu payloads and records per-call token/cost-savings stats
- **Performance-first design**:
  - File handle stays open per session (no open/close churn)
  - **No `fsync`** — kernel page-cache latency only; at most ~4KB lost on crash
  - 1KB userspace buffer to minimize crash-loss window
  - Auto-gzip on session end (and `atexit` fallback for hard kills)
- **Orphan sweep** — on startup, compresses `.log` files left by crashed runs (older than 1h)
- **CLI management** — list, view, cat (raw JSON for `jq`), delete, prune with dry-run

## Hooks

| Hook | Purpose |
|---|---|
| `on_session_start` | Log session start (model, platform) |
| `pre_api_request` | Log outgoing request (user message preview, available tools, conversation summary) |
| `post_api_request` | Log response (content preview, tool calls, usage, duration) |
| `pre_tool_call` | Log tool invocation with args preview |
| `post_tool_call` | Log tool result + NPU usage stats |
| `on_session_end` | Log session end; flush, close & gzip |

## CLI

| Command | Description |
|---|---|
| `hermes chat-log list` | List all session logs (size, date) |
| `hermes chat-log view <session>` | Pretty-print a session |
| `hermes chat-log cat <session>` | Raw JSON-lines (pipe to `jq`) |
| `hermes chat-log delete <session>` | Delete one log |
| `hermes chat-log prune [--older-than DAYS] [--dry-run]` | Bulk-delete old logs |

## Installation

```bash
cp -r plugins/chat-logger ~/.hermes/plugins/
```

No dependencies beyond the standard library.

## Files

| File | Purpose |
|---|---|
| `plugin.yaml` | Plugin manifest (hooks, CLI, version) |
| `__init__.py` | Recorder, CLI, compression |

Logs are written to `~/.hermes/logs/chat-log/<session_id>.log.gz` — **outside the plugin dir, never checked in.**

## Privacy

Logs contain full conversation traffic by design — that's the point. Use `hermes chat-log prune` to expire them, and keep `~/.hermes/logs/` out of version control (it is).
