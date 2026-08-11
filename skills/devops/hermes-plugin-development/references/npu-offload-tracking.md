# NPU-Offload Tracking in budget-tracker + chat-logger (worked example, Aug 2026)

Goal: budget reports show the DeepSeek vs local-NPU token split and the $ saved by offloading to the NPU (Gemma 4 E2B on FLM). Built live, verified against a real research+vision session.

## Why the chat log matters

NPU tool calls never hit `post_api_request` (they're local FLM calls from the gemma-npu plugin). They only appear in chat logs as `tool_call_end` entries whose `result` is the tool's JSON payload. So the chat log is the natural source of truth for NPU usage — the plugin writes structured data there, and the budget plugin consumes the same hook stream live.

## Data flow

```
NPU tool call (agent) → post_tool_call hook
  ├─ chat-logger: parses result → entry["npu_usage"] = {tool, input_tokens, output_tokens, total_tokens, deepseek_total_cost, model}
  └─ budget-tracker: same parse → session accumulator + data.json all_time_*/period_* npu counters
DeepSeek API call  → post_api_request hook (existing) → cost via Hermes pricing engine
```

## NPU tool result shape (gemma-npu tools.py)

All 7 tools (`summarize_text`, `summarize_document`, `extract_from_webpage`, `classify_text`, `extract_json`, `analyze_image`, `create_plan`) return `json.dumps(data)` where data includes:
`input_tokens`, `output_tokens`, `deepseek_input_cost`, `deepseek_output_cost`, `deepseek_total_cost`, `model` (FLM_MODEL).
Failures: `json.dumps({"error": "..."})`. The `deepseek_total_cost` field is computed with `_compute_costs()` at DS rates ($0.14/1M in, $0.28/1M out) — trust it; don't re-derive rates in the budget plugin.

## chat-logger change

```python
_NPU_TOOLS = frozenset({
    "summarize_text", "summarize_document", "extract_from_webpage",
    "classify_text", "extract_json", "analyze_image", "create_plan",
})

def _parse_npu_usage(tool_name, result):
    if tool_name not in _NPU_TOOLS or not result or not isinstance(result, str):
        return None
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or "error" in payload:
        return None
    in_t, out_t = payload.get("input_tokens"), payload.get("output_tokens")
    if in_t is None or out_t is None:
        return None
    return {
        "tool": tool_name,
        "input_tokens": int(in_t),
        "output_tokens": int(out_t),
        "total_tokens": int(in_t) + int(out_t),
        "deepseek_total_cost": float(payload.get("deepseek_total_cost", 0.0) or 0.0),
        "model": payload.get("model", ""),
    }
```

In `_post_tool_call`: build the entry dict, then `npu = _parse_npu_usage(tool_name, result); if npu: entry["npu_usage"] = npu`. Keep `result_preview`/`result_length` unchanged (back-compat). Old logs stay parseable since `result_preview` contains the JSON head.

## budget-tracker change

- Register `post_tool_call` hook alongside the existing ones.
- `_session` accumulator gains: `npu_requests`, `npu_input_tokens`, `npu_output_tokens`, `npu_total_tokens`, `npu_savings_usd` (reset in `_on_session_start`).
- data.json defaults gain (all via `setdefault` — auto-migrates existing files):
  `all_time_npu_input/output/total` (ints), `all_time_npu_savings_usd` (float), and the same 4 `period_npu_*`.
- `_post_tool_call`: same `_parse_npu_usage`; on hit, bump accumulator + `data["all_time_npu_*"]`/`period_npu_*` then `_save_data(data)`. Also update `last_request_at` so idle reports treat NPU work as activity.
- `_on_session_end` archive row: add the 5 npu fields (`npu_savings_usd` rounded to 8).
- `_cli_reset` clears `period_npu_*` too.
- Report surfaces (all guarded to render only when nonzero):
  - `_build_report`: after the cost block → `NPU offload <tokens> saved $x` (session) + `NPU all-time <tokens> saved $x`
  - `_cli_status`: `NPU offload <tokens> (saved $x)` + `├─ Period <tokens> (saved $x)`
  - `_cli_history`: new `NPU` column (per-session `npu_savings_usd`)

## Verification transcript (live, after Hermes restart)

Test workload: 2× `extract_from_webpage` (403'd — error path skipped), `extract_json`, 2× `summarize_text`, `analyze_image` on a clipboard screenshot.

Cross-check: chat-log `npu_usage` entries summed = **1881 tokens / $0.000367**; data.json `all_time_npu_total` = **1881 / $0.000367** — exact match. `hermes budget` rendered:
```
  Est. cost     $2.3727  (saved $49.4645)        ← DeepSeek side
  NPU offload      1.9K  (saved $0.00036700)     ← local side
  ├─ Period       1.9K  (saved $0.00036700)
```
Notes: (1) pre-restart sessions have no NPU data — feature wasn't live; no backfill chosen. (2) Restart archives transient 0-request rows (013000/013041) — pre-existing reconnect behavior. (3) A session's NPU totals land in its archive row only when that session ends.
