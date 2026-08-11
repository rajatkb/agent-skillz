"""Budget Tracker Plugin v2 — token tracking, Hermes cost estimation, DeepSeek balance API.

Tracks input/output/cache/reasoning tokens per session, estimates cost via
Hermes' own pricing engine (cache-aware, model-aware), fetches real balance
from DeepSeek's /user/balance endpoint, and reports at configurable intervals.
Also captures local NPU (gemma-npu) tool usage via post_tool_call and reports
the DeepSeek-equivalent cost those local calls avoided.

Commands:
  hermes budget          — all-time totals + last known DeepSeek balance
  hermes budget history  — per-session breakdown with costs & savings
  hermes budget set N    — set budget ceiling in USD
  hermes budget reset    — reset period counters
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_FILE = os.path.join(_PLUGIN_DIR, "data.json")
_REPORT_FILE = os.path.join(_PLUGIN_DIR, "last_report.txt")

# ── Hermes state DB for session descriptions ──────────────────────────────
_HERMES_STATE_DB = os.path.expanduser("~/.hermes/state.db")


def _get_session_title(session_id: str) -> str:
    """Look up session description from Hermes' state.db."""
    if not session_id:
        return ""
    try:
        import sqlite3
        if not os.path.exists(_HERMES_STATE_DB):
            return ""
        conn = sqlite3.connect(_HERMES_STATE_DB)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT title, display_name FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        conn.close()
        if row:
            return row["title"] or row["display_name"] or ""
        return ""
    except Exception:
        return ""
_DEFAULT_BUDGET_USD = 0.0  # 0 = not seeded yet; auto-seeded from balance on first fetch

# ── In-memory session accumulator ────────────────────────────────────────

_session = {
    "id": "",
    "started_at": 0.0,
    "last_request_at": 0.0,
    "requests": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_tokens": 0,
    "cache_write_tokens": 0,
    "reasoning_tokens": 0,
    "prompt_tokens": 0,
    "total_tokens": 0,
    "estimated_cost": 0.0,          # with cache pricing
    "estimated_cost_no_cache": 0.0, # if cache tokens were full-price input
    "cache_savings": 0.0,
    "npu_requests": 0,
    "npu_input_tokens": 0,
    "npu_output_tokens": 0,
    "npu_total_tokens": 0,
    "npu_savings_usd": 0.0,         # DeepSeek-equivalent cost avoided
}
_session_recorded = False

# ── Reporting thresholds ─────────────────────────────────────────────────

_PROGRESS_INTERVAL = 10  # print one-liner every N requests
_IDLE_THRESHOLD = 120    # seconds idle before mid-session report
_BALANCE_CACHE_TTL = 300 # re-fetch balance after 5 min

# ── I/O ──────────────────────────────────────────────────────────────────

def _load_data() -> dict:
    defaults = {
        "budget_usd": _DEFAULT_BUDGET_USD,
        "all_time_prompt": 0,
        "all_time_output": 0,
        "all_time_total": 0,
        "all_time_estimated_cost": 0.0,
        "all_time_cache_savings": 0.0,
        "all_time_npu_input": 0,
        "all_time_npu_output": 0,
        "all_time_npu_total": 0,
        "all_time_npu_savings_usd": 0.0,
        "period_prompt": 0,
        "period_output": 0,
        "period_total": 0,
        "period_estimated_cost": 0.0,
        "period_cache_savings": 0.0,
        "period_npu_input": 0,
        "period_npu_output": 0,
        "period_npu_total": 0,
        "period_npu_savings_usd": 0.0,
        "period_start": datetime.now(timezone.utc).isoformat(),
        "last_balance_total": None,
        "last_balance_currency": "USD",
        "last_balance_fetched_at": None,
        "budget_auto_seeded": False,
        "sessions": [],
    }
    if not os.path.exists(_DATA_FILE):
        return dict(defaults)
    try:
        with open(_DATA_FILE, "r") as f:
            data = json.load(f)
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("budget-tracker: corrupt data file, resetting: %s", e)
        return dict(defaults)


def _save_data(data: dict):
    tmp = _DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _DATA_FILE)


def _write_report(text: str):
    """Write to report file AND try stdout (TUI eats stdout, file is fallback)."""
    try:
        with open(_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        pass
    try:
        print(text, flush=True)
    except Exception:
        pass


# ── DeepSeek Balance API ─────────────────────────────────────────────────

_DEEPSEEK_BALANCE_URL = "https://api.deepseek.com/user/balance"


def _get_deepseek_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    # Fallback: load Hermes dotenv (needed when running outside agent subprocess)
    try:
        from hermes_cli.env_loader import load_hermes_dotenv
        load_hermes_dotenv()
        return os.environ.get("DEEPSEEK_API_KEY", "")
    except Exception:
        return ""


def _fetch_balance() -> dict | None:
    """Fetch balance from DeepSeek API. Returns {total, currency, granted} or None."""
    api_key = _get_deepseek_api_key()
    if not api_key:
        return None
    try:
        resp = httpx.get(
            _DEEPSEEK_BALANCE_URL,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("budget-tracker: balance API returned %d", resp.status_code)
            return None
        body = resp.json()
        infos = body.get("balance_infos", [])
        if not infos:
            return None
        info = infos[0]
        return {
            "total": float(info.get("total_balance", 0)),
            "currency": info.get("currency", "CNY"),
            "granted": float(info.get("granted_balance", 0)),
        }
    except Exception as e:
        logger.debug("budget-tracker: balance fetch failed: %s", e)
        return None


def _auto_seed_budget(data: dict, balance: dict):
    """Auto-seed USD budget from DeepSeek balance once."""
    if data.get("budget_auto_seeded") or data.get("budget_usd", 0) > 0:
        return
    total = balance.get("total", 0)
    if total > 0:
        data["budget_usd"] = round(total, 2)
        data["budget_auto_seeded"] = True
        logger.info(
            "budget-tracker: auto-seeded budget at $%.2f from balance", total,
        )


def _balance_age_seconds(data: dict) -> float:
    ts = data.get("last_balance_fetched_at")
    if not ts:
        return float("inf")
    try:
        return time.time() - datetime.fromisoformat(ts).timestamp()
    except Exception:
        return float("inf")


# ── Cost estimation via Hermes pricing engine ────────────────────────────

def _estimate_costs(usage: dict, model: str, provider: str, base_url: str) -> dict | None:
    """Use Hermes' pricing engine: cost with cache and without cache.
    Falls back to hardcoded DeepSeek V4 Flash rates when model unknown.
    """
    try:
        from agent.usage_pricing import estimate_usage_cost, CanonicalUsage

        in_t = usage.get("input_tokens", 0) or 0
        out_t = usage.get("output_tokens", 0) or 0
        cr_t = usage.get("cache_read_tokens", 0) or 0
        cw_t = usage.get("cache_write_tokens", 0) or 0
        re_t = usage.get("reasoning_tokens", 0) or 0

        # With cache pricing
        cu = CanonicalUsage(
            input_tokens=in_t, output_tokens=out_t,
            cache_read_tokens=cr_t, cache_write_tokens=cw_t,
            reasoning_tokens=re_t,
        )
        result = estimate_usage_cost(model, cu, provider=provider, base_url=base_url)
        cost_with = float(result.amount_usd) if result and result.amount_usd is not None else 0.0

        # Without cache: fold cache tokens into full-price input
        cu_no = CanonicalUsage(
            input_tokens=in_t + cr_t + cw_t, output_tokens=out_t,
            reasoning_tokens=re_t,
        )
        result_no = estimate_usage_cost(model, cu_no, provider=provider, base_url=base_url)
        cost_without = float(result_no.amount_usd) if result_no and result_no.amount_usd is not None else cost_with

        # Fallback: if pricing engine returned 0 for a non-zero request,
        # use hardcoded DeepSeek V4 Flash rates
        if cost_with == 0.0 and (in_t + out_t + cr_t + cw_t) > 0:
            from decimal import Decimal
            # DeepSeek V4 Flash: $0.14/1M input, $0.28/1M output
            cost_with = (
                (in_t / 1_000_000 * 0.14) +
                (cr_t / 1_000_000 * 0.07) +
                (cw_t / 1_000_000 * 0.14) +
                (out_t / 1_000_000 * 0.28)
            )
        if cost_without == 0.0 and (in_t + out_t + cr_t + cw_t) > 0:
            cost_without = (
                ((in_t + cr_t + cw_t) / 1_000_000 * 0.14) +
                (out_t / 1_000_000 * 0.28)
            )

        return {
            "cost": cost_with,
            "cost_no_cache": cost_without,
            "savings": cost_without - cost_with,
        }
    except Exception as e:
        logger.debug("budget-tracker: cost estimation failed: %s", e)
        return None


# ── Formatting ───────────────────────────────────────────────────────────

def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:,}"


def _fmt_cost(usd: float) -> str:
    if usd == 0:
        return "$0"
    if usd >= 1.0:
        return f"${usd:.4f}"
    if usd >= 0.01:
        return f"${usd:.6f}"
    if usd >= 0.0001:
        return f"${usd:.8f}"
    return f"${usd:.4e}"


def _fmt_dur(secs: int) -> str:
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m {secs % 60}s"
    h, r = divmod(secs, 3600)
    return f"{h}h {r // 60}m"


def _progress_bar(pct: float, width: int = 18) -> str:
    filled = int(width * pct / 100)
    bar = "█" * filled + "░" * (width - filled)
    if not sys.stdout.isatty():
        return bar
    if pct >= 90:
        return f"\033[91m{bar}\033[0m"
    if pct >= 70:
        return f"\033[93m{bar}\033[0m"
    return f"\033[92m{bar}\033[0m"


# ── Reports ──────────────────────────────────────────────────────────────

def _build_report(
    title: str, sid: str, dur: int, s: dict, data: dict,
    balance: dict | None = None, end_reason: str = "",
) -> str:
    """Build a report string — used for end-of-session and hermes budget."""
    budget = data.get("budget_usd", 0) or 0
    period_cost = data.get("period_estimated_cost", 0.0)
    period_savings = data.get("period_cache_savings", 0.0)
    all_cost = data.get("all_time_estimated_cost", 0.0)
    all_savings = data.get("all_time_cache_savings", 0.0)
    all_total = data.get("all_time_total", 0)
    all_prompt = data.get("all_time_prompt", 0)
    all_output = data.get("all_time_output", 0)
    n_sessions = len(data.get("sessions", []))
    pct = (period_cost / budget * 100) if budget > 0 else 0
    remaining = max(0, budget - period_cost)

    bal_cur = balance["currency"] if balance else data.get("last_balance_currency", "USD")

    lines = []
    lines.append("")
    lines.append(f"━━━ {title} ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"  Session  {sid[:24]}")
    lines.append(f"  Duration {_fmt_dur(dur)}")
    lines.append(f"  Requests {s.get('requests', 0)}")
    lines.append("")

    # Tokens
    lines.append(f"  Input   {_fmt_tokens(s.get('input_tokens', 0)):>10}")
    lines.append(f"  Output  {_fmt_tokens(s.get('output_tokens', 0)):>10}")
    if s.get("cache_read_tokens", 0):
        lines.append(f"  Cache r {_fmt_tokens(s['cache_read_tokens']):>10}")
    if s.get("cache_write_tokens", 0):
        lines.append(f"  Cache w {_fmt_tokens(s['cache_write_tokens']):>10}")
    if s.get("reasoning_tokens", 0):
        lines.append(f"  Reason  {_fmt_tokens(s['reasoning_tokens']):>10}")
    lines.append("")

    # Cost — with vs without cache side by side
    sess_cost = s.get("estimated_cost", 0.0)
    sess_cost_nc = s.get("estimated_cost_no_cache", 0.0)
    sess_save = s.get("cache_savings", 0.0)
    lines.append(f"  {'':>14} {'w/ cache':>12} {'no cache':>12}")
    lines.append(f"  This session {_fmt_cost(sess_cost):>12} {_fmt_cost(sess_cost_nc):>12}")
    lines.append(f"  Period       {_fmt_cost(period_cost):>12} {_fmt_cost(period_cost + period_savings):>12}")
    lines.append(f"  All-time     {_fmt_cost(all_cost):>12} {_fmt_cost(all_cost + all_savings):>12}")
    lines.append(f"  Cache saved  {_fmt_cost(sess_save):>12}")
    lines.append("")

    # Local NPU offload — DeepSeek-equivalent cost avoided
    npu_total_s = s.get("npu_total_tokens", 0)
    npu_save_s = s.get("npu_savings_usd", 0.0)
    npu_total_a = data.get("all_time_npu_total", 0)
    npu_save_a = data.get("all_time_npu_savings_usd", 0.0)
    if npu_total_s or npu_total_a:
        lines.append(f"  NPU offload  {_fmt_tokens(npu_total_s):>10}  saved {_fmt_cost(npu_save_s)}")
        lines.append(f"  NPU all-time {_fmt_tokens(npu_total_a):>10}  saved {_fmt_cost(npu_save_a)}")
        lines.append("")

    # Balance
    if balance:
        lines.append(f"  DeepSeek balance: {bal_cur}{balance['total']:.2f}")
    elif data.get("last_balance_total") is not None:
        lines.append(f"  Last balance: {bal_cur}{data['last_balance_total']}")
    lines.append("")

    # Budget progress
    if budget > 0:
        bar = _progress_bar(pct, 18)
        lines.append(f"  Budget   {bar}  {pct:5.1f}%")
        lines.append(f"  Spent    {_fmt_cost(period_cost):>10} / {_fmt_cost(budget)}")
        lines.append(f"  Left     {_fmt_cost(remaining):>10}")
    else:
        lines.append("  Budget   not set — use `hermes budget set N`")
    lines.append("")
    lines.append(f"  All-time {_fmt_tokens(all_total):>10}  ({_fmt_tokens(all_prompt)} in / {_fmt_tokens(all_output)} out, {n_sessions} sessions)")
    if end_reason:
        lines.append(f"  Exit: {end_reason}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")

    if pct >= 100 and budget > 0:
        over = period_cost - budget
        lines.append(f"  🚨  Budget EXCEEDED by {_fmt_cost(over)}!\n")

    return "\n".join(lines)


def _progress_line(s: dict, balance: dict | None, currency: str = "USD") -> str:
    """Compact mid-session one-liner."""
    cost = s.get("estimated_cost", 0.0)
    req = s.get("requests", 0)
    total = s.get("total_tokens", 0)
    bal = ""
    if balance:
        bal = f" | {currency}{balance['total']:.2f}"
    return f"  📊  {req} req | {_fmt_tokens(total)} | {_fmt_cost(cost)} est{bal}"


# ── Hooks ────────────────────────────────────────────────────────────────

def _on_session_start(session_id: str = "", model: str = "", **kwargs):
    global _session_recorded
    if not session_id:
        return

    _session["id"] = session_id
    _session["started_at"] = time.time()
    _session["last_request_at"] = time.time()
    _session["requests"] = 0
    _session["input_tokens"] = 0
    _session["output_tokens"] = 0
    _session["cache_read_tokens"] = 0
    _session["cache_write_tokens"] = 0
    _session["reasoning_tokens"] = 0
    _session["prompt_tokens"] = 0
    _session["total_tokens"] = 0
    _session["estimated_cost"] = 0.0
    _session["estimated_cost_no_cache"] = 0.0
    _session["cache_savings"] = 0.0
    _session["npu_requests"] = 0
    _session["npu_input_tokens"] = 0
    _session["npu_output_tokens"] = 0
    _session["npu_total_tokens"] = 0
    _session["npu_savings_usd"] = 0.0
    _session_recorded = False

    data = _load_data()
    provider = kwargs.get("provider", "")

    # Fetch fresh balance for DeepSeek provider (respect cache TTL)
    balance = None
    if provider == "deepseek" and _balance_age_seconds(data) > _BALANCE_CACHE_TTL:
        balance = _fetch_balance()
        if balance:
            data["last_balance_total"] = balance["total"]
            data["last_balance_currency"] = balance["currency"]
            data["last_balance_fetched_at"] = datetime.now(timezone.utc).isoformat()
            _auto_seed_budget(data, balance)
            _save_data(data)

            budget = data.get("budget_usd", 0) or 0
            period_cost = data.get("period_estimated_cost", 0.0)
            pct = (period_cost / budget * 100) if budget > 0 else 0
            if pct >= 80:
                print(f"  ⚡  Budget alert: {pct:.0f}% used this period", flush=True)
        else:
            logger.debug("budget-tracker: balance fetch returned None, using cached")


def _post_api_request(session_id: str = "", usage: dict = None, **kwargs):
    if not session_id or not usage:
        return

    now = time.time()
    idle_secs = now - _session.get("last_request_at", now)

    # Extract token counts
    in_t = usage.get("input_tokens", 0) or 0
    out_t = usage.get("output_tokens", 0) or 0
    total_t = usage.get("total_tokens", 0) or 0
    cr_t = usage.get("cache_read_tokens", 0) or 0
    cw_t = usage.get("cache_write_tokens", 0) or 0
    re_t = usage.get("reasoning_tokens", 0) or 0
    prompt_t = usage.get("prompt_tokens", 0) or 0

    # Estimate cost via Hermes pricing engine
    costs = _estimate_costs(usage, kwargs.get("model", ""), kwargs.get("provider", ""), kwargs.get("base_url", ""))
    cost_val = costs["cost"] if costs else 0.0
    cost_nc = costs["cost_no_cache"] if costs else 0.0
    save_val = costs["savings"] if costs else 0.0

    # Update session accumulator
    _session["requests"] += 1
    _session["input_tokens"] += in_t
    _session["output_tokens"] += out_t
    _session["prompt_tokens"] += prompt_t
    _session["total_tokens"] += total_t
    _session["cache_read_tokens"] += cr_t
    _session["cache_write_tokens"] += cw_t
    _session["reasoning_tokens"] += re_t
    _session["estimated_cost"] += cost_val
    _session["estimated_cost_no_cache"] += cost_nc
    _session["cache_savings"] += save_val
    _session["last_request_at"] = now

    # Persist running totals
    data = _load_data()
    data["all_time_prompt"] = data.get("all_time_prompt", 0) + prompt_t
    data["all_time_output"] = data.get("all_time_output", 0) + out_t
    data["all_time_total"] = data.get("all_time_total", 0) + total_t
    data["all_time_estimated_cost"] = data.get("all_time_estimated_cost", 0.0) + cost_val
    data["all_time_cache_savings"] = data.get("all_time_cache_savings", 0.0) + save_val
    data["period_prompt"] = data.get("period_prompt", 0) + prompt_t
    data["period_output"] = data.get("period_output", 0) + out_t
    data["period_total"] = data.get("period_total", 0) + total_t
    data["period_estimated_cost"] = data.get("period_estimated_cost", 0.0) + cost_val
    data["period_cache_savings"] = data.get("period_cache_savings", 0.0) + save_val
    _save_data(data)

    # ── Mid-session reporting ────────────────────────────────────────────

    # Idle report: if gap > threshold and we're past the first request
    if idle_secs > _IDLE_THRESHOLD and _session["requests"] > 1:
        bal = None
        if data.get("last_balance_total") is not None:
            bal = {"total": data["last_balance_total"], "currency": data.get("last_balance_currency", "CNY")}
        report = _build_report(
            "Session Budget (idle report)", _session["id"],
            int(now - _session["started_at"]), _session, data, bal,
        )
        _write_report(report + "\n  ⏸  Idle report — session still active\n\n")

    # Every N requests: compact progress line
    if _session["requests"] % _PROGRESS_INTERVAL == 0:
        bal = None
        bal_cur = "USD"
        if data.get("last_balance_total") is not None:
            bal = {"total": data["last_balance_total"], "currency": data.get("last_balance_currency", "USD")}
            bal_cur = bal["currency"]
        line = _progress_line(_session, bal, bal_cur)
        try:
            print(line, flush=True)
        except Exception:
            pass


# ── Local NPU tool usage (gemma-npu plugin) ──────────────────────────────

_NPU_TOOLS = frozenset({
    "summarize_text", "summarize_document", "extract_from_webpage",
    "classify_text", "extract_json", "analyze_image", "create_plan",
})


def _parse_npu_usage(tool_name: str, result) -> dict | None:
    """If *result* is a gemma-npu tool payload, extract token/cost stats."""
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


def _post_tool_call(tool_name="", args=None, result="", task_id="",
                    session_id="", **kwargs):
    """Capture local NPU tool usage — these never hit post_api_request."""
    if not session_id:
        session_id = task_id or ""
    if not session_id:
        return
    npu = _parse_npu_usage(tool_name, result)
    if not npu:
        return

    now = time.time()
    _session["npu_requests"] += 1
    _session["npu_input_tokens"] += npu["input_tokens"]
    _session["npu_output_tokens"] += npu["output_tokens"]
    _session["npu_total_tokens"] += npu["total_tokens"]
    _session["npu_savings_usd"] += npu["deepseek_total_cost"]
    _session["last_request_at"] = now

    npu_cost = npu["deepseek_total_cost"]
    data = _load_data()
    data["all_time_npu_input"] = data.get("all_time_npu_input", 0) + npu["input_tokens"]
    data["all_time_npu_output"] = data.get("all_time_npu_output", 0) + npu["output_tokens"]
    data["all_time_npu_total"] = data.get("all_time_npu_total", 0) + npu["total_tokens"]
    data["all_time_npu_savings_usd"] = data.get("all_time_npu_savings_usd", 0.0) + npu_cost
    data["period_npu_input"] = data.get("period_npu_input", 0) + npu["input_tokens"]
    data["period_npu_output"] = data.get("period_npu_output", 0) + npu["output_tokens"]
    data["period_npu_total"] = data.get("period_npu_total", 0) + npu["total_tokens"]
    data["period_npu_savings_usd"] = data.get("period_npu_savings_usd", 0.0) + npu_cost
    _save_data(data)


def _on_session_end(session_id: str = "", reason: str = "", **kwargs):
    global _session_recorded
    if not session_id or _session_recorded:
        return

    completed = kwargs.get("completed", False)
    interrupted = kwargs.get("interrupted", False)
    if not completed and not interrupted:
        return

    _session_recorded = True
    data = _load_data()
    dur = int(time.time() - _session["started_at"])

    # Fetch final balance (DeepSeek only)
    provider = kwargs.get("provider", "")
    balance = None
    if provider == "deepseek":
        balance = _fetch_balance()
        if balance:
            data["last_balance_total"] = balance["total"]
            data["last_balance_currency"] = balance["currency"]
            data["last_balance_fetched_at"] = datetime.now(timezone.utc).isoformat()

    # Look up session description from Hermes state DB
    session_title = _get_session_title(session_id)

    # Archive session
    data.setdefault("sessions", []).append({
        "id": session_id,
        "title": session_title,
        "duration": dur,
        "requests": _session["requests"],
        "input_tokens": _session["input_tokens"],
        "output_tokens": _session["output_tokens"],
        "prompt_tokens": _session["prompt_tokens"],
        "total_tokens": _session["total_tokens"],
        "cache_read_tokens": _session["cache_read_tokens"],
        "cache_write_tokens": _session["cache_write_tokens"],
        "reasoning_tokens": _session["reasoning_tokens"],
        "estimated_cost": round(_session["estimated_cost"], 8),
        "estimated_cost_no_cache": round(_session["estimated_cost_no_cache"], 8),
        "cache_savings": round(_session["cache_savings"], 8),
        "npu_requests": _session["npu_requests"],
        "npu_input_tokens": _session["npu_input_tokens"],
        "npu_output_tokens": _session["npu_output_tokens"],
        "npu_total_tokens": _session["npu_total_tokens"],
        "npu_savings_usd": round(_session["npu_savings_usd"], 8),
        "balance_end": round(balance["total"], 2) if balance else None,
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    })
    _save_data(data)

    # Write report (file + stdout)
    report = _build_report(
        "📊 Session Budget", session_id, dur, _session, data, balance, reason,
    )
    _write_report(report)


# ── CLI ──────────────────────────────────────────────────────────────────

def _cli_dispatch(args):
    action = getattr(args, "action", "status") or "status"
    {
        "status":  _cli_status,
        "set":     lambda: _cli_set(getattr(args, "value", None)),
        "reset":   _cli_reset,
        "history": _cli_history,
    }.get(action, _cli_status)()


def _cli_status():
    data = _load_data()
    budget = data.get("budget_usd", 0) or 0

    # Fetch fresh DeepSeek balance (respect cache TTL) and auto-seed budget
    bal_total = data.get("last_balance_total")
    bal_cur = data.get("last_balance_currency", "USD")
    if _balance_age_seconds(data) > _BALANCE_CACHE_TTL:
        balance = _fetch_balance()
        if balance:
            bal_total = balance["total"]
            bal_cur = balance["currency"]
            data["last_balance_total"] = bal_total
            data["last_balance_currency"] = bal_cur
            data["last_balance_fetched_at"] = datetime.now(timezone.utc).isoformat()
            was_seeded = data.get("budget_auto_seeded", False)
            _auto_seed_budget(data, balance)
            if data.get("budget_auto_seeded") and not was_seeded:
                # first auto-seed — let the user know
                print(f"  → Auto-set budget to ${data['budget_usd']:.2f} from DeepSeek balance")
            budget = data.get("budget_usd", 0) or 0  # re-read after auto-seed
            _save_data(data)

    bal_str = f"{bal_cur}{bal_total}" if bal_total is not None else "N/A (no fetch yet)"

    period_cost = data.get("period_estimated_cost", 0.0)
    period_savings = data.get("period_cache_savings", 0.0)
    all_cost = data.get("all_time_estimated_cost", 0.0)
    all_savings = data.get("all_time_cache_savings", 0.0)
    all_npu = data.get("all_time_npu_total", 0)
    all_npu_save = data.get("all_time_npu_savings_usd", 0.0)
    period_npu = data.get("period_npu_total", 0)
    period_npu_save = data.get("period_npu_savings_usd", 0.0)
    all_total = data.get("all_time_total", 0)
    all_prompt = data.get("all_time_prompt", 0)
    all_output = data.get("all_time_output", 0)
    n_sessions = len(data.get("sessions", []))
    remaining = max(0, budget - period_cost)
    pct = (period_cost / budget * 100) if budget > 0 else 0

    print("")
    print("━━━ Budget Tracker ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    if budget > 0:
        bar = _progress_bar(pct, 18)
        print(f"  Budget   {bar}  {pct:5.1f}%")
        print(f"  Spent    {_fmt_cost(period_cost):>10} / {_fmt_cost(budget)}")
        print(f"  Left     {_fmt_cost(remaining):>10}")
        print(f"  Savings  {_fmt_cost(period_savings):>10}  (from caching)")
    else:
        print(f"  Budget   not set — use `hermes budget set N`")
    print("")
    print(f"  DeepSeek balance: {bal_str}")
    print("")
    print(f"  All-time   {_fmt_tokens(all_total):>10}")
    print(f"  ├─ Input   {_fmt_tokens(all_prompt):>10}")
    print(f"  └─ Output  {_fmt_tokens(all_output):>10}")
    print(f"  Est. cost  {_fmt_cost(all_cost):>10}  (saved {_fmt_cost(all_savings)})")
    print(f"  NPU offload {_fmt_tokens(all_npu):>9}  (saved {_fmt_cost(all_npu_save)})")
    print(f"  ├─ Period  {_fmt_tokens(period_npu):>9}  (saved {_fmt_cost(period_npu_save)})")
    print(f"  Sessions   {n_sessions}")
    print("")
    print(f"  Commands: hermes budget set N  |  hermes budget reset  |  hermes budget history")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")


def _cli_set(value):
    if value is None:
        print("Usage: hermes budget set <dollars>")
        return
    if value <= 0:
        print("❌ Budget must be positive.")
        return
    data = _load_data()
    data["budget_usd"] = float(value)
    data["budget_auto_seeded"] = False
    _save_data(data)
    print(f"✅  Budget set to ${value:.2f}")


def _cli_reset():
    data = _load_data()
    data["period_prompt"] = 0
    data["period_output"] = 0
    data["period_total"] = 0
    data["period_estimated_cost"] = 0.0
    data["period_cache_savings"] = 0.0
    data["period_npu_input"] = 0
    data["period_npu_output"] = 0
    data["period_npu_total"] = 0
    data["period_npu_savings_usd"] = 0.0
    data["period_start"] = datetime.now(timezone.utc).isoformat()
    _save_data(data)
    print("🔄  Period counter reset. Fresh budget period started.")


def _cli_history():
    data = _load_data()
    sessions = data.get("sessions", [])
    if not sessions:
        print("📭  No session history yet.")
        return

    recent = sessions[-10:]
    print("")
    print("━━━ Recent Sessions ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  {'#':<3} {'Description':<36} {'Tokens':>8} {'Cost':>10} {'Saved':>8} {'NPU':>8}  {'Req':>3}  {'Dur':<8}")
    print(f"  {'─'*3} {'─'*36} {'─'*8} {'─'*10} {'─'*8} {'─'*8}  {'─'*3}  {'─'*8}")
    for s in reversed(recent):
        sid = s.get("id", "?")
        title = s.get("title", "") or sid
        title_str = title[:36]
        total = s.get("total_tokens", 0)
        cost = s.get("estimated_cost", 0)
        saved = s.get("cache_savings", 0)
        npu = s.get("npu_savings_usd", 0)
        req = s.get("requests", 0)
        dur = _fmt_dur(s.get("duration", 0))
        r = s.get("reason", "")
        emoji = {
            "user_exit": "🚪", "timeout": "⏰", "error": "⚠️",
            "keyboard_interrupt": "⌨️", "max_turns": "🎬",
        }.get(r, "•")
        print(f"  {emoji:<3} {title_str:<36} {_fmt_tokens(total):>8} {_fmt_cost(cost):>10} {_fmt_cost(saved):>8} {_fmt_cost(npu):>8}  {req:>3}  {dur:<8}")
    if len(sessions) > 10:
        print(f"  ... and {len(sessions) - 10} more")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("")


# ── Registration ─────────────────────────────────────────────────────────

def register(ctx):
    if not os.path.exists(_DATA_FILE):
        _save_data(_load_data())
        logger.info("budget-tracker: initialised data store at %s", _DATA_FILE)

    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("post_api_request", _post_api_request)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("on_session_end", _on_session_end)

    def _setup(p):
        p.add_argument(
            "action", nargs="?", default="status",
            choices=["status", "set", "reset", "history"],
            help="status | set <dollars> | reset | history",
        )
        p.add_argument("value", nargs="?", default=None, type=float,
                       help="Dollar amount for 'set' command")

    ctx.register_cli_command(
        name="budget",
        help="Track token usage, estimated cost & DeepSeek balance across sessions",
        setup_fn=_setup,
        handler_fn=_cli_dispatch,
    )

    logger.info("budget-tracker v2: ready — cache-aware, Hermes-priced, DeepSeek balance, NPU offload")
