#!/usr/bin/env python3
"""Hermetic verification probe for NPU-offload tracking in chat-logger + budget-tracker.

Loads both plugin modules from disk, monkeypatches their data paths to a temp
dir, simulates a session with NPU tool calls + a DeepSeek request, and asserts:
  1. chat-logger writes structured npu_usage only for NPU tools (not others, not errors)
  2. budget-tracker accumulates npu_* counters into data.json (all-time + period)
  3. session archive row carries npu_* fields
  4. _build_report and _cli_status render the NPU offload section

Run with the Hermes runtime python (asdf py3.11):  python3 verify-npu-tracking.py
Exit 0 = all green. Real ~/.hermes data.json is NEVER touched.
"""
import contextlib
import gzip
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile

TMP = tempfile.mkdtemp(prefix="npu_verify_")


def load_plugin(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cl = load_plugin("chat_logger_vfy", os.path.expanduser(
    "~/.hermes/plugins/chat-logger/__init__.py"))
bt = load_plugin("budget_tracker_vfy", os.path.expanduser(
    "~/.hermes/plugins/budget-tracker/__init__.py"))

bt._DATA_FILE = os.path.join(TMP, "data.json")
bt._REPORT_FILE = os.path.join(TMP, "last_report.txt")
cl._LOG_DIR = os.path.join(TMP, "chat-log")
os.makedirs(cl._LOG_DIR, exist_ok=True)

SID = "test_sess_001"

# ── 1. chat-logger ────────────────────────────────────────────────────────
cl._post_tool_call(tool_name="summarize_text",
                   result=json.dumps({"response": "sum", "input_tokens": 500,
                                      "output_tokens": 120,
                                      "deepseek_total_cost": 0.00015,
                                      "model": "gemma4-it:e2b"}),
                   session_id=SID)
cl._post_tool_call(tool_name="web_search", result="plain non-NPU result",
                   session_id=SID)
cl._post_tool_call(tool_name="summarize_document",
                   result=json.dumps({"error": "FLM request failed: x"}),
                   session_id=SID)
cl._close(SID)

gz = os.path.join(cl._LOG_DIR, f"{SID}.log.gz")
entries = [json.loads(l) for l in gzip.open(gz, "rt", encoding="utf-8")
           if l.strip()]
assert len(entries) == 3, f"expected 3 entries, got {len(entries)}"
e0, e1, e2 = entries
assert e0.get("npu_usage") == {"tool": "summarize_text", "input_tokens": 500,
                               "output_tokens": 120, "total_tokens": 620,
                               "deepseek_total_cost": 0.00015,
                               "model": "gemma4-it:e2b"}, e0.get("npu_usage")
assert "npu_usage" not in e1, "non-NPU tool must not get npu_usage"
assert "npu_usage" not in e2, "error payload must not get npu_usage"
print("[PASS] chat-logger: npu_usage on NPU tool only")

# ── 2. budget-tracker live capture ────────────────────────────────────────
bt._on_session_start(session_id=SID, model="x", provider="custom")  # no balance fetch
bt._post_tool_call(tool_name="classify_text",
                   result=json.dumps({"response": "pos", "input_tokens": 300,
                                      "output_tokens": 50,
                                      "deepseek_total_cost": 0.00007,
                                      "model": "gemma4-it:e2b"}),
                   session_id=SID)
bt._post_tool_call(tool_name="extract_json",
                   result=json.dumps({"response": "{}", "input_tokens": 800,
                                      "output_tokens": 200,
                                      "deepseek_total_cost": 0.0002,
                                      "model": "gemma4-it:e2b"}),
                   session_id=SID)
bt._post_api_request(session_id=SID,
                     usage={"input_tokens": 1000, "output_tokens": 200,
                            "total_tokens": 1200, "prompt_tokens": 1000,
                            "cache_read_tokens": 0, "cache_write_tokens": 0,
                            "reasoning_tokens": 0},
                     model="deepseek-v4-flash", provider="deepseek",
                     base_url="https://api.deepseek.com")
bt._on_session_end(session_id=SID, reason="user_exit", completed=True)

data = bt._load_data()
assert data["all_time_npu_input"] == 1100, data["all_time_npu_input"]
assert data["all_time_npu_output"] == 250, data["all_time_npu_output"]
assert data["all_time_npu_total"] == 1350, data["all_time_npu_total"]
assert abs(data["all_time_npu_savings_usd"] - 0.00027) < 1e-12
assert data["period_npu_total"] == 1350
assert data["all_time_total"] == 1200, "DeepSeek API tokens still counted"
assert len(data["sessions"]) == 1
srow = data["sessions"][0]
assert srow["npu_requests"] == 2 and srow["npu_total_tokens"] == 1350
print("[PASS] budget-tracker: npu_* counters in data.json + session archive")

# ── 3. reports ────────────────────────────────────────────────────────────
report = bt._build_report("Test Report", SID, 10, bt._session, data,
                          end_reason="user_exit")
assert "NPU offload" in report and "NPU all-time" in report, report
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    bt._cli_status()
out = buf.getvalue()
assert "NPU offload" in out and "Period" in out.split("NPU offload")[1], out
print("[PASS] _build_report + _cli_status render NPU offload section")

# ── 4. cleanup ────────────────────────────────────────────────────────────
shutil.rmtree(TMP, ignore_errors=True)
print("\nALL CHECKS PASSED")
