# flm-lifecycle

> 🔄 On-demand lifecycle management for the local FLM NPU inference server — up only when an NPU tool actually needs it, down when the last session ends.

## Overview

Hermes' NPU tools (`analyze_image`, `summarize_text`, …) are backed by [FLM](https://fastflowlm.com/docs) serving a Gemma 4 model on the local NPU. Running that server 24/7 wastes power and RAM. `flm-lifecycle` starts it lazily — the moment an NPU-backed tool is called — and shuts it down when no session needs it anymore.

## Features

- **On-demand start** — `pre_tool_call` hook triggers `flm-up.sh` only for NPU tools (idempotent: no-op if already serving)
- **Session-aware shutdown** — tracks active session IDs; FLM stops when the last one ends
- **3-tier reconciliation** against stale/crashed state:
  1. **Tier-1** — sessions tracked but FLM not running ⇒ state is stale (crash), reset clean
  2. **Tier-2** — dead-PID purge: sessions whose owner process was hard-killed (SIGKILL) are removed
  3. **Tier-3** — orphaned-gateway detection: if the TUI frontend died and this process got reparented to init, its tracked sessions are purged
- **SIGTERM cleanup** — on TUI shutdown, the dying gateway purges its own sessions and stops FLM if it was the last one
- **Ghost-event handling** — replayed/duplicate `on_session_end` events can't leak FLM: if nothing is tracked but FLM is running, the end event stops it

## Hooks

| Hook | Purpose |
|---|---|
| `on_session_start` | Register session (with PID); run reconciliation tiers |
| `pre_tool_call` | Ensure FLM is up when an NPU tool is about to run |
| `on_session_end` | Deregister session; stop FLM if it was the last one |

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `FLM_PORT` | `50001` | FLM server port |
| `FLM_HOST` | `127.0.0.1` | FLM server host |
| `HERMES_HOME` | `~/.hermes` | Where `scripts/flm-up.sh` / `scripts/flm-down.sh` live |

## Installation

```bash
cp -r plugins/flm-lifecycle ~/.hermes/plugins/
# requires the companion scripts to exist:
#   ~/.hermes/scripts/flm-up.sh
#   ~/.hermes/scripts/flm-down.sh
```

## Files

| File | Purpose |
|---|---|
| `plugin.yaml` | Plugin manifest (hooks, version) |
| `__init__.py` | Session tracking, reconciliation, signal handling |
| `sessions.json` | *(runtime)* active session IDs + PID map — **not checked in** |

## Dependencies

- `flm-up.sh` / `flm-down.sh` scripts (see `scripts/` in this repo)
- FLM server installed and configured (see the `flm-lifecycle` skill)
