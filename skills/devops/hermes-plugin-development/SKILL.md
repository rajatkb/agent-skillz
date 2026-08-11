---
name: hermes-plugin-development
description: "Build and extend Hermes user plugins — hook-based plugins (budget tracking, chat logging, lifecycle), data persistence, CLI subcommands, and hermetic verification. Companion to amd-npu's tool-plugin section."
tags: [hermes, plugins, hooks, budget, observability, python]
category: devops
---

# Hermes Plugin Development (hooks, data, CLI)

## Trigger

Use this skill when the user asks to build, extend, or debug a Hermes **user plugin** — anything in `~/.hermes/plugins/<name>/` that is hook-based or data-persisting: budget trackers, chat loggers, lifecycle managers, custom CLI subcommands, or wiring new data (e.g. NPU-usage telemetry) into existing plugins. Tool-only plugins (exposing an FLM/NPU model as a callable tool) are covered in the amd-npu skill's "Custom Tool Plugins" section — this skill covers the rest.

## Plugin anatomy & lifecycle

- `~/.hermes/plugins/<name>/` → `plugin.yaml` (manifest) + `__init__.py` (registration + logic). Tool plugins add `schemas.py` + `tools.py`.
- Entry point: `register(ctx)` — call `ctx.register_hook(...)`, `ctx.register_tool(...)`, `ctx.register_cli_command(...)`.
- Plugins are auto-discovered and loaded **at Hermes start**. **No hot reload** — after editing, the running instance keeps old registrations; tell the user changes apply on next start (offer restart, never experiment with live reload).
- `register()` runs once per process; module import ≠ register (register is only called by Hermes — safe to import plugin modules in test scripts).

## Hook reference (verified signatures)

```python
on_session_start(session_id="", model="", platform="", provider="", **kwargs)
pre_api_request(session_id="", user_message="", model="", provider="", tool_count=0,
                message_count=0, request=None, conversation_history=None, **kwargs)
post_api_request(session_id="", assistant_message=None, usage=None, model="",
                 finish_reason="", api_duration=0, assistant_tool_call_count=0, **kwargs)
pre_tool_call(tool_name="", args=None, task_id="", session_id="", tool_call_id="", turn_id="", **kwargs)
post_tool_call(tool_name="", args=None, result="", task_id="", session_id="", **kwargs)
on_session_end(session_id="", reason="", completed=False, interrupted=False, **kwargs)
```

All hooks must accept `**kwargs` (Hermes passes extra fields). `post_tool_call`'s `result` is the **full result string**, not a preview.

## What each hook sees — the key architectural insight

- `post_api_request` fires **only for cloud LLM API calls**. Its `usage` dict carries `input_tokens`, `output_tokens`, `total_tokens`, `prompt_tokens`, `cache_read/write_tokens`, `reasoning_tokens`; plus `model`/`provider`/`base_url` for cost estimation.
- **Local NPU/FLM tool calls NEVER hit `post_api_request`** — they're direct local HTTP calls from the gemma-npu plugin. They are only visible in `pre/post_tool_call`, via the tool name and the result string.
- `pre/post_tool_call` fire for **every** tool (web_search, browser, NPU, etc.), so gate on tool name.
- To capture "offloaded" work: parse the NPU tool's result JSON in a `post_tool_call` hook (see worked example below).

## Data persistence pattern (budget-tracker class)

- `data.json` lives next to `__init__.py`; module-level `_DATA_FILE`/`_REPORT_FILE` constants computed from `__file__`.
- **Atomic writes**: write to `data.json.tmp`, `flush()` + `os.fsync()`, then `os.replace(tmp, data.json)`.
- **Forward-compatible schema**: `_load_data()` seeds defaults via `setdefault` — new keys appear automatically in existing files on next load. No migration script needed.
- Pattern: in-memory session accumulator (reset in `on_session_start`, archived in `on_session_end`) + persisted all-time/period counters updated per event (`_load_data()` → mutate → `_save_data()`).
- CLI subcommand: `ctx.register_cli_command(name=..., help=..., setup_fn=argparse_setup, handler_fn=dispatch)`; dispatch maps `args.action` to handlers. `register` itself must create the data file if missing.

## Capturing NPU tool usage (worked pattern)

The gemma-npu plugin's 7 tools (`summarize_text`, `summarize_document`, `extract_from_webpage`, `classify_text`, `extract_json`, `analyze_image`, `create_plan`) all return `json.dumps({...})` containing `input_tokens`, `output_tokens`, `deepseek_total_cost`, `model` — i.e. they already compute the DeepSeek-equivalent cost the local call avoided. Failures return `{"error": ...}`.

Capture rules: in `post_tool_call`, parse `result` only if (a) tool name ∈ NPU set, (b) result is a `str`, (c) JSON parses to a dict, (d) no `"error"` key, (e) `input_tokens`/`output_tokens` present. **NPU savings are additive** — they're avoided cost, never subtracted from API cost.

Full implementation: `references/npu-offload-tracking.md` (chat-logger `npu_usage` field + budget-tracker hook/counters/reports).

## Hermetic verification (critical)

Never let a test touch the real `data.json`:

1. Load plugin modules directly: `importlib.util.spec_from_file_location(name, path_to___init__.py)` + `exec_module` (works because register() isn't called on import; plugins have no package-relative imports).
2. Monkeypatch module-level path constants BEFORE any hook call: `bt._DATA_FILE = tempfile.mkdtemp() + "/data.json"`, `cl._LOG_DIR = tempdir` — all reads/writes go to temp.
3. Simulate a session: `_on_session_start(sid, provider="custom")` (avoid `"deepseek"` → triggers real balance API fetch), NPU `_post_tool_call`s with realistic result JSON, one `_post_api_request` with a fake usage dict, `_on_session_end(sid, completed=True)`.
4. **Cross-check two independent sources**: sum `npu_usage` entries from the written chat log vs the counters in temp data.json — they must match exactly.
5. Verify report surfaces: call `_build_report(...)` and the CLI handler under `contextlib.redirect_stdout`, assert the new lines appear.
6. `py_compile` both files before/after. Clean up temp dirs (user cares about session cleanup) and any stray `__pycache__` test-module files.

### Live end-to-end check (after restart)

Hermetic tests prove the logic; the live check proves the hooks actually registered in the running Hermes:

1. Grep `~/.hermes/logs/agent.log` for the plugin's registration line (e.g. `budget-tracker v2: ready — ... NPU offload`) — confirms the new code loaded.
2. Snapshot baseline counters from data.json (all `npu_*` at 0 on first run).
3. Run a real workload exercising the NPU tools. Include a call that FAILS (403 fetch, FLM down): its `{"error": ...}` result doubles as a free error-path test — it must NOT register.
4. Three-way cross-check: `hermes budget` output vs data.json counters vs the sum of chat-log `npu_usage` entries — all must agree exactly.
5. Per-session attribution caveat: an open session's usage lands in its archive row only when the session ends; global all-time/period counters update immediately. Restart can archive transient 0-request rows — expected, don't chase.

Re-runnable probe: `scripts/verify-npu-tracking.py`.

## Pitfalls

- **V4A multi-hunk patch validation is atomic**: one ambiguous hunk fails the ENTIRE patch (no files modified). On "Found 2 matches for old_string", add a discriminator line — the line *after* the block that differs between the two functions (e.g. `remaining = max(0, budget - period_cost)` vs `pct = ...` ordering distinguishes `_cli_status` from `_build_report`).
- **Session-id fallback**: `post_tool_call` may receive empty `session_id` — fall back to `task_id` (chat-logger uses `"unknown"`).
- **Restart artifacts**: Hermes restarts can archive transient 0-request session rows (reconnect sessions) — pre-existing behavior, don't chase it as a bug. Also: a resumed session's in-memory accumulator is wiped by restart; global counters survive.
- **Report formatting**: reuse the plugin's existing `_fmt_tokens`/`_fmt_cost` helpers for consistency; `_fmt_cost` switches precision by magnitude.
- User conventions: no `.bak` files; no live-reload experiments; report accept/reject/modify when a plan was generated; model names stay env-configurable (never hardcode).
- Cross-plugin import is fragile (plugins may be disabled) — duplicate small helpers (e.g. the NPU-tool set) rather than importing between plugins.

## References

- `references/npu-offload-tracking.md` — worked example: structured `npu_usage` in chat-logger, budget-tracker `post_tool_call` hook, data.json schema additions, report surfaces, live-verification transcript
- `scripts/verify-npu-tracking.py` — hermetic end-to-end verification probe (temp data.json + temp log dir; asserts chat-log ↔ counters match)
