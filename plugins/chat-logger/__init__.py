"""Chat Logger Plugin — records every session to disk.

Logs raw chat history showing:
  - Session start
  - Every LLM API request (messages going in)
  - Every LLM API response (assistant text + tool_calls — marks the moment
    the agent decides to use a tool)
  - Every tool call invocation and its result
  - Session end

Logs go to ~/.hermes/logs/chat-log/<session_id>.log.gz — one gzip-compressed
JSON-lines file per session.

Design choices for performance:
  - File stays OPEN per session (no open/close per write)
  - NO fsync ever — kernel page-cache latency only, async to disk
  - Buffer auto-flushes to kernel after every write via ``flush()`` but we
    explicitly skip ``os.fsync()``.  If the process crashes, at most the
    last ~4KB of entries are lost (acceptable for debug logging).
  - Final flush + close on session_end, then gzip compression.

Viewing:
    hermes chat-log list              # list all logs
    hermes chat-log view <session>    # pretty-print
    hermes chat-log cat <session>     # raw JSON lines (pipe to jq)
"""

import atexit
import gzip
import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_LOG_DIR = os.path.join(
    os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
    "logs", "chat-log",
)

# Open file handles per session — avoids open/close on every event.
# Key: session_id, Value: open TextIOWrapper in append mode.
_files: dict[str, object] = {}


def _ensure_log_dir():
    os.makedirs(_LOG_DIR, exist_ok=True)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_path(session_id: str) -> str:
    return os.path.join(_LOG_DIR, f"{session_id}.log")


def _gz_path(session_id: str) -> str:
    return os.path.join(_LOG_DIR, f"{session_id}.log.gz")


def _write(session_id: str, entry: dict):
    """Append one JSON line to the session log.

    Reuses an open file handle if available (opened on first write for the
    session).  Writes are flushed to the kernel immediately but NOT fsynced
    — the kernel decides when to commit to disk.  This means on crash the
    last ~4 KB of entries may be lost, which is acceptable for debug logs.
    """
    if not session_id:
        return
    _ensure_log_dir()

    # Get or create the file handle
    f = _files.get(session_id)
    if f is None:
        path = _log_path(session_id)
        try:
            # Open with a small buffer (1 KB) so crash loss is tiny, but
            # still skip fsync — kernel page cache handles durability.
            f = open(path, "a", encoding="utf-8", buffering=1024)
            _files[session_id] = f
        except Exception as e:
            logger.warning("chat-logger: failed to open %s: %s", path, e)
            return

    try:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        # Flush to kernel: pushes data from userspace buffer into the
        # kernel page cache.  NO fsync — no disk wait.  On crash the
        # kernel may lose uncommitted page-cache pages, but that's ~a
        # few KB at most.
        f.flush()
    except Exception as e:
        logger.warning("chat-logger: write error for session %s: %s",
                       session_id, e)


def _close(session_id: str):
    """Flush and close the open file handle, then gzip."""
    f = _files.pop(session_id, None)
    if f is not None:
        try:
            f.close()  # closes → flushes userspace buffer → kernel (no fsync)
        except Exception as e:
            logger.warning("chat-logger: close error for %s: %s",
                           session_id, e)

    # Compress
    raw = _log_path(session_id)
    gz = _gz_path(session_id)
    if not os.path.exists(raw):
        return
    try:
        with open(raw, "rb") as f_in:
            with gzip.open(gz, "wb", compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
        raw_size = os.path.getsize(raw)
        gz_size = os.path.getsize(gz)
        os.remove(raw)
        logger.info("chat-logger: session %s compressed %d→%d bytes (%d%%)",
                     session_id, raw_size, gz_size,
                     int(gz_size / raw_size * 100) if raw_size else 0)
    except Exception as e:
        logger.warning("chat-logger: failed to compress %s: %s", raw, e)


def _close_all():
    """Close + compress every open session handle.

    Registered as an ``atexit`` handler so even if ``on_session_end``
    never fires (crash, SIGTERM without cleanup), the log is preserved
    in compressed form.
    """
    session_ids = list(_files.keys())
    if not session_ids:
        return
    logger.info("chat-logger: atexit — closing %d open session(s)", len(session_ids))
    for sid in session_ids:
        _close(sid)


def _sweep_orphaned_logs(max_age_hours=1):
    """Compress any ``.log`` files not tracked by an open handle.

    Handles the case where the process was killed before ``on_session_end``
    could fire for a prior run.  Files younger than *max_age_hours* are
    left alone in case another process is still writing to them.
    """
    _ensure_log_dir()
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    orphaned = 0
    for name in os.listdir(_LOG_DIR):
        if not name.endswith(".log"):
            continue
        sid = name[:-4]  # strip ".log"
        if sid in _files:
            continue  # still open, skip
        path = os.path.join(_LOG_DIR, name)
        try:
            mtime = os.path.getmtime(path)
            if mtime > cutoff:
                continue  # too recent, might still be in use
            # Compress it
            gz_path = path + ".gz"
            with open(path, "rb") as f_in:
                with gzip.open(gz_path, "wb", compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            raw_size = os.path.getsize(path)
            gz_size = os.path.getsize(gz_path)
            os.remove(path)
            orphaned += 1
            logger.info(
                "chat-logger: compressed orphaned log %s (%d→%d bytes)",
                name, raw_size, gz_size,
            )
        except Exception as e:
            logger.warning("chat-logger: failed to sweep %s: %s", name, e)
    if orphaned:
        logger.info("chat-logger: swept %d orphaned log(s)", orphaned)


def _preview(text, max_len=3000):
    if text and isinstance(text, str) and len(text) > max_len:
        return text[:max_len] + f"\n... [truncated, {len(text)} chars]"
    return text


def _summarize_messages(messages, max_msgs=6):
    if not messages:
        return []
    if len(messages) <= max_msgs:
        return [{"role": m.get("role", "?"),
                 "content_preview": _preview(str(m.get("content", "")), 200)}
                for m in messages]
    head = messages[:3]
    tail = messages[-3:]
    return ([{"role": m.get("role", "?"),
              "content_preview": _preview(str(m.get("content", "")), 200)}
             for m in head]
            + [{"__omitted": f"{len(messages) - 6} messages"}]
            + [{"role": m.get("role", "?"),
                "content_preview": _preview(str(m.get("content", "")), 200)}
               for m in tail])


# ── NPU tool usage extraction ────────────────────────────────────────────────

_NPU_TOOLS = frozenset({
    "summarize_text", "summarize_document", "extract_from_webpage",
    "classify_text", "extract_json", "analyze_image", "create_plan",
})


def _parse_npu_usage(tool_name: str, result) -> dict | None:
    """If *result* is a gemma-npu tool payload, extract token/cost stats.

    The gemma-npu plugin returns a JSON string carrying input_tokens,
    output_tokens and deepseek_total_cost (the cost the local call avoided).
    Returns None for non-NPU tools, failures, or malformed payloads.
    """
    if tool_name not in _NPU_TOOLS or not result:
        return None
    if not isinstance(result, str):
        return None
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or "error" in payload:
        return None
    in_t = payload.get("input_tokens")
    out_t = payload.get("output_tokens")
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


# ── Hooks ───────────────────────────────────────────────────────────────────


def _on_session_start(session_id="", model="", platform="", **kwargs):
    if not session_id:
        return
    _write(session_id, {
        "event": "session_start",
        "ts": _ts(),
        "session_id": session_id,
        "model": model,
        "platform": platform,
    })


def _pre_api_request(session_id="", user_message="", model="", provider="",
                     tool_count=0, message_count=0, request=None,
                     conversation_history=None, **kwargs):
    if not session_id:
        return
    tools_info = None
    if request and isinstance(request, dict):
        body = request.get("body", {})
        raw_tools = body.get("tools", [])
        if raw_tools:
            tools_info = [
                {"name": t.get("function", {}).get("name", t.get("name", "?")),
                 "description_preview": _preview(
                     t.get("function", {}).get("description", ""), 100)}
                for t in raw_tools
            ]
    entry = {
        "event": "api_request",
        "ts": _ts(),
        "session_id": session_id,
        "model": model,
        "provider": provider,
        "user_message_preview": _preview(user_message, 500),
        "message_count": message_count,
        "tool_count": tool_count,
        "available_tools": tools_info,
    }
    if conversation_history:
        entry["conversation_summary"] = _summarize_messages(conversation_history)
    _write(session_id, entry)


def _post_api_request(session_id="", assistant_message=None, usage=None,
                      model="", finish_reason="", api_duration=0,
                      assistant_tool_call_count=0, **kwargs):
    if not session_id:
        return
    response_text = ""
    tool_calls = []
    if assistant_message:
        response_text = getattr(assistant_message, "content", "") or ""
        for tc in (getattr(assistant_message, "tool_calls", None) or []):
            tc_id = getattr(tc, "id", "?")
            tc_fn = getattr(tc, "function", None)
            tool_calls.append({
                "id": tc_id,
                "function": {
                    "name": getattr(tc_fn, "name", "?") if tc_fn else "?",
                    "arguments": getattr(tc_fn, "arguments", "{}") if tc_fn else "{}",
                },
            })
    entry = {
        "event": "api_response",
        "ts": _ts(),
        "session_id": session_id,
        "model": model,
        "finish_reason": finish_reason,
        "api_duration_ms": round(api_duration * 1000, 1) if api_duration else 0,
        "assistant_content_preview": _preview(response_text, 2000),
        "assistant_tool_call_count": assistant_tool_call_count,
    }
    if tool_calls:
        entry["assistant_tool_calls"] = tool_calls
    if usage:
        entry["usage"] = usage
    _write(session_id, entry)


def _pre_tool_call(tool_name="", args=None, task_id="", session_id="",
                   tool_call_id="", turn_id="", **kwargs):
    if not session_id:
        session_id = task_id or "unknown"
    _write(session_id, {
        "event": "tool_call_start",
        "ts": _ts(),
        "session_id": session_id,
        "tool": tool_name,
        "args_preview": _preview(json.dumps(args or {}, indent=2), 1000),
        "tool_call_id": tool_call_id,
        "turn_id": turn_id,
    })


def _post_tool_call(tool_name="", args=None, result="", task_id="",
                    session_id="", **kwargs):
    if not session_id:
        session_id = task_id or "unknown"
    entry = {
        "event": "tool_call_end",
        "ts": _ts(),
        "session_id": session_id,
        "tool": tool_name,
        "result_preview": _preview(result, 2000),
        "result_length": len(result) if result else 0,
    }
    npu_usage = _parse_npu_usage(tool_name, result)
    if npu_usage:
        entry["npu_usage"] = npu_usage
    _write(session_id, entry)


def _on_session_end(session_id="", reason="", **kwargs):
    if not session_id:
        return
    _write(session_id, {
        "event": "session_end",
        "ts": _ts(),
        "session_id": session_id,
        "reason": reason,
    })
    _close(session_id)


# ── Registration ────────────────────────────────────────────────────────────


def register(ctx):
    # Sweep any orphaned .log files from prior crashed runs
    _sweep_orphaned_logs()

    # Register atexit handler to close + compress any sessions still open
    # on clean shutdown (catches SIGTERM, sys.exit(), falling off end).
    atexit.register(_close_all)

    ctx.register_hook("on_session_start",  _on_session_start)
    ctx.register_hook("pre_api_request",   _pre_api_request)
    ctx.register_hook("post_api_request",  _post_api_request)
    ctx.register_hook("pre_tool_call",     _pre_tool_call)
    ctx.register_hook("post_tool_call",    _post_tool_call)
    ctx.register_hook("on_session_end",    _on_session_end)

    # Register a simple CLI subcommand via argparse
    def _setup(p):
        p.add_argument("action", nargs="?", default="list",
                       choices=["list", "view", "cat", "delete", "prune"],
                       help="list | view <id> | cat <id> | delete <id> | prune [--older-than DAYS] [--dry-run]")
        p.add_argument("session_id", nargs="?", default="",
                       help="Session ID (from list)")
        p.add_argument("--older-than", type=int, default=0,
                       help="Prune: delete logs older than N days")
        p.add_argument("--dry-run", action="store_true",
                       help="Prune: show what would be deleted without deleting")

    ctx.register_cli_command(
        name="chat-log",
        help="View and manage chat session logs",
        setup_fn=_setup,
        handler_fn=_cli_dispatch,
    )

    logger.info("chat-logger: registered hooks (logs → %s)", _LOG_DIR)


def _cli_dispatch(args):
    """Dispatch from argparse namespace."""
    action = getattr(args, "action", "list") or "list"
    session_id = getattr(args, "session_id", "") or ""
    if action == "list":
        _cli_list()
    elif action == "view":
        if not session_id:
            print("Usage: hermes chat-log view <session_id>")
            return
        _cli_view(session_id)
    elif action == "cat":
        if not session_id:
            print("Usage: hermes chat-log cat <session_id>")
            return
        _cli_cat(session_id)
    elif action == "delete":
        if not session_id:
            print("Usage: hermes chat-log delete <session_id>")
            return
        _cli_delete(session_id)
    elif action == "prune":
        older_than = getattr(args, "older_than", 0) or 0
        dry_run = getattr(args, "dry_run", False)
        _cli_prune(older_than, dry_run)


def _cli_list():
    _ensure_log_dir()
    files = sorted(f for f in os.listdir(_LOG_DIR) if f.endswith(".log.gz"))
    if not files:
        print(f"No session logs found. Log dir: {_LOG_DIR}")
        return
    total = 0
    print(f"{'Session ID':<36} {'Size':>10} {'Modified':>20}")
    print("-" * 68)
    for f in files:
        path = os.path.join(_LOG_DIR, f)
        size = os.path.getsize(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
        sid = f.replace(".log.gz", "")
        print(f"{sid:<36} {size:>8,}B {mtime:>20}")
        total += size
    print("-" * 68)
    print(f"{len(files)} files, {total:,} bytes total")


def _cli_view(session_id):
    gz = _gz_path(session_id)
    if not os.path.exists(gz):
        print(f"Session log not found: {gz}")
        return
    try:
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    event = entry.get("event", "?")
                    ts = entry.get("ts", "?")
                    tool = entry.get("tool", "")
                    preview = (entry.get("result_preview", "")
                               or entry.get("assistant_content_preview", "")
                               or "")
                    tcalls = entry.get("assistant_tool_calls", [])

                    if event == "session_start":
                        print(f"\n{'='*60}")
                        print(f"SESSION START [{ts}]")
                        print(f"  model:    {entry.get('model', '?')}")
                        print(f"  platform: {entry.get('platform', '?')}")
                        print(f"{'='*60}\n")
                    elif event == "api_request":
                        print(f"\n── LLM REQUEST [{ts}] ──")
                        print(f"  provider: {entry.get('provider','?')}  "
                              f"model: {entry.get('model','?')}")
                        print(f"  user: {entry.get('user_message_preview','')[:200]}")
                        at = entry.get("available_tools")
                        if at:
                            print(f"  tools: {[t['name'] for t in at]}")
                    elif event == "api_response":
                        tcc = entry.get("assistant_tool_call_count", 0)
                        if tcc > 0:
                            print(f"\n★★ TOOL CALL TAKEOVER [{ts}] ★★")
                            print(f"  {tcc} tool call(s):")
                            for tc in tcalls:
                                fn = tc.get("function", {})
                                print(f"  → {fn.get('name','?')}"
                                      f"({fn.get('arguments','')[:200]})")
                        else:
                            print(f"\n── LLM RESPONSE [{ts}] ──")
                        print(f"  finish: {entry.get('finish_reason','?')}  "
                              f"duration: {entry.get('api_duration_ms','?')}ms")
                        if preview:
                            print(f"  text: {_preview(preview, 300)}")
                    elif event == "tool_call_start":
                        print(f"\n  ▶ [{ts}] {tool}"
                              f"({entry.get('args_preview','')[:200]})")
                    elif event == "tool_call_end":
                        print(f"  ◀ [{ts}] {tool} → {preview[:200]}")
                        print(f"     ({entry.get('result_length',0)} "
                              f"bytes)")
                    elif event == "session_end":
                        print(f"\n{'='*60}")
                        print(f"SESSION END [{ts}]")
                        print(f"  reason: {entry.get('reason','')}")
                        print(f"{'='*60}\n")
                except json.JSONDecodeError:
                    print(f"  [parse error] {line[:200]}")
    except Exception as e:
        print(f"Error: {e}")


def _cli_cat(session_id):
    """Raw JSON lines to stdout — for piping to jq/grep."""
    gz = _gz_path(session_id)
    if not os.path.exists(gz):
        print(f"Session log not found: {gz}")
        return
    try:
        with gzip.open(gz, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    print(line)
    except Exception as e:
        print(f"Error: {e}", file=__import__('sys').stderr)


def _cli_delete(session_id):
    """Delete a single session log file."""
    gz = _gz_path(session_id)
    raw = _log_path(session_id)
    target = gz if os.path.exists(gz) else raw
    if not os.path.exists(target):
        print(f"❌ Session log not found: {session_id}")
        return
    try:
        size = os.path.getsize(target)
        os.remove(target)
        print(f"🗑️  Deleted {os.path.basename(target)} ({size:,} bytes)")
    except Exception as e:
        print(f"❌ Failed to delete {target}: {e}")


def _cli_prune(older_than_days: int, dry_run: bool = False):
    """Delete session logs older than N days."""
    import time
    _ensure_log_dir()
    now = time.time()
    files = [f for f in os.listdir(_LOG_DIR)
             if f.endswith(".log.gz") or f.endswith(".log")]
    if not files:
        print("📭 No session logs to prune.")
        return

    if older_than_days <= 0:
        print("⚠️  Specify --older-than N (days). Example: hermes chat-log prune --older-than 7")
        return

    cutoff = now - (older_than_days * 86400)
    matched = []
    for f in sorted(files):
        path = os.path.join(_LOG_DIR, f)
        mtime = os.path.getmtime(path)
        if mtime < cutoff:
            matched.append((f, path, mtime))

    if not matched:
        print(f"📭 No logs older than {older_than_days} day(s).")
        return

    total_size = 0
    if dry_run:
        print(f"🔍 Dry-run: {len(matched)} file(s) would be deleted (--older-than {older_than_days}d):\n")
        for fname, path, mtime in matched:
            size = os.path.getsize(path)
            total_size += size
            age_days = (now - mtime) / 86400
            print(f"  {fname:<42} {size:>8,}B  ({age_days:.0f} days old)")
        print(f"\n  Total: {len(matched)} files, {total_size:,} bytes")
        print("  Run without --dry-run to delete.")
    else:
        for fname, path, mtime in matched:
            size = os.path.getsize(path)
            os.remove(path)
            total_size += size
            print(f"  🗑️  {fname}")
        print(f"\n  Deleted {len(matched)} file(s), {total_size:,} bytes freed.")
