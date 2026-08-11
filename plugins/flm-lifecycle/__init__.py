"""FLM Lifecycle Plugin — on-demand FLM NPU server start via pre_tool_call hook.

Starts FLM only when the agent actually calls an NPU-backed tool
(analyze_image, summarize_text, etc.). Stops FLM when the last session ends.
Tracks active session IDs as a set to deduplicate replay/ghost events.

Reconciliation (tier-1): if the session set is non-empty on start but FLM isn't
actually running, the counter is assumed stale (crashed sessions) and reset.

Reconciliation (tier-2, added Jul 2026): track process PIDs alongside session
IDs so we can detect orphan sessions from hard-killed Hermes instances
(SIGKILL, crash, etc.) where on_session_end never fired. Dead PIDs are purged
on every on_session_start and on_session_end call.
"""

import json
import logging
import os
import signal
import socket
import subprocess

logger = logging.getLogger(__name__)

_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_SESSIONS_FILE = os.path.join(_PLUGIN_DIR, "sessions.json")
_HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
_FLM_UP = os.path.join(_HERMES_HOME, "scripts", "flm-up.sh")
_FLM_DOWN = os.path.join(_HERMES_HOME, "scripts", "flm-down.sh")
_FLM_PORT = int(os.environ.get("FLM_PORT", "50001"))
_FLM_HOST = os.environ.get("FLM_HOST", "127.0.0.1")


def _is_flm_running() -> bool:
    """Check if FLM is actually serving on its port."""
    try:
        with socket.create_connection((_FLM_HOST, _FLM_PORT), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def _is_orphaned_gateway() -> bool:
    """Detect if this TUI gateway process lost its parent (TUI frontend died).

    A healthy gateway has its parent chain:
      hermes --tui → node entry.js → tui_gateway.entry

    When the user quits the TUI, the parent chain dies and this process
    gets reparented to init (PID 1). We use this as the signal that the
    session that owned us is gone and we should clean up.
    """
    ppid = os.getppid()
    return ppid <= 1  # reparented to init, or PID namespace oddity


# ── SIGTERM handler: clean up on TUI shutdown ──────────────────────────────


def _signal_cleanup(signum, frame):
    """Handle SIGTERM: clean up this process's sessions and stop FLM.

    Fires when the TUI frontend or main Hermes process sends SIGTERM
    down the process tree. Removes any sessions tracked with our PID,
    then shuts FLM down if no sessions remain.
    """
    our_pid = os.getpid()
    sessions, pids = _read_sessions()
    if not sessions:
        # Nothing tracked — but if FLM is still running, this gateway was
        # likely the last one and the bookkeeping was already empty. Stop FLM.
        if _is_flm_running():
            logger.info(
                "flm-lifecycle: SIGTERM — no tracked sessions but FLM running, stopping FLM"
            )
            _run_script(_FLM_DOWN, "flm-down")
        return

    # Strip sessions tracked by THIS process (the dying gateway)
    ours = [sid for sid, pid in list(pids.items()) if pid == our_pid]
    for sid in ours:
        sessions.discard(sid)
        pids.pop(sid, None)
        logger.info(
            "flm-lifecycle: SIGTERM — purged session %s (pid=%d)",
            sid, our_pid,
        )

    if sessions:
        _write_sessions(sessions, pids)
        logger.info(
            "flm-lifecycle: SIGTERM — %d other session(s) remain, not stopping FLM",
            len(sessions),
        )
    else:
        _write_sessions(set(), {})
        logger.info("flm-lifecycle: SIGTERM — last session gone, stopping FLM")
        _run_script(_FLM_DOWN, "flm-down")


def _is_pid_alive(pid: int) -> bool:
    """Check if a PID is alive via signal-0 probe."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_sessions() -> tuple:
    """Read the set of active session IDs and the pid map.

    Returns (set_of_ids, dict_of_pids).
    Backward-compatible: pids defaults to {} if missing.
    """
    try:
        with open(_SESSIONS_FILE, "r") as f:
            data = json.load(f)
            ids = set(data.get("session_ids", []))
            pids = data.get("pids", {})
            # Clean up any old int-keys that json may have stringified back
            pids = {k: v for k, v in pids.items() if isinstance(v, int)}
            return ids, pids
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return set(), {}


def _write_sessions(sessions: set, pids: dict):
    """Write session IDs and PID map atomically."""
    data = {"session_ids": sorted(sessions), "pids": pids}
    tmp = _SESSIONS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _SESSIONS_FILE)


def _purge_dead_pids(sessions: set, pids: dict) -> tuple:
    """Remove sessions whose recorded PID no longer exists (hard-kill orphans).

    Returns (cleaned_sessions, cleaned_pids, removed_count).
    """
    our_pid = os.getpid()
    dead = set()
    for sid in list(sessions):
        pid = pids.get(sid)
        if pid is not None and pid != our_pid and not _is_pid_alive(pid):
            dead.add(sid)
    if dead:
        sessions -= dead
        for sid in dead:
            pids.pop(sid, None)
        logger.info(
            "flm-lifecycle: purged %d dead-PID orphan session(s): %s",
            len(dead), sorted(dead),
        )
    return sessions, pids, len(dead)


def _run_script(path: str, label: str) -> bool:
    """Run a shell script, log outcome. Returns True on success."""
    if not os.path.isfile(path):
        logger.warning("flm-lifecycle: %s script not found at %s", label, path)
        return False
    try:
        result = subprocess.run(
            ["bash", path],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            logger.info("flm-lifecycle: %s succeeded — %s", label, result.stdout.strip())
            return True
        else:
            logger.warning(
                "flm-lifecycle: %s failed (exit %d) — %s",
                label, result.returncode,
                result.stderr.strip() or result.stdout.strip(),
            )
            return False
    except subprocess.TimeoutExpired:
        logger.warning("flm-lifecycle: %s timed out after 60s", label)
        return False
    except Exception as e:
        logger.warning("flm-lifecycle: %s error: %s", label, e)
        return False


def _pre_tool_call(tool_name="", args=None, task_id="", **kwargs):
    """Start FLM if an NPU-backed tool is about to be called.

    flm-up.sh is idempotent — checks port first, exits fast if already running.
    """
    if tool_name in _NPU_TOOLS:
        logger.info(
            "flm-lifecycle: NPU tool '%s' requested — ensuring FLM is up",
            tool_name,
        )
        _run_script(_FLM_UP, "flm-up")


def _on_session_start(session_id="", **kwargs):
    if not session_id:
        return

    sessions, pids = _read_sessions()

    # Tier-1 reconciliation: if we think sessions are active but FLM isn't
    # running, the state is stale (crashed sessions, hard kills) — reset clean.
    if sessions and not _is_flm_running():
        logger.warning(
            "flm-lifecycle: sessions=%d but FLM not running — resetting stale state",
            len(sessions),
        )
        sessions = set()
        pids = {}

    # Tier-2 reconciliation: purge orphan sessions whose PIDs are dead
    if not pids:
        # old-format file without pids; build pid map from live Hermes processes
        pids = {sid: 0 for sid in sessions}  # placeholder; won't match any PID
    sessions, pids, _ = _purge_dead_pids(sessions, pids)

    # Tier-3 reconciliation: detect orphaned gateway (parent TUI frontend died)
    # The gateway's parent chain is hermes --tui → node entry.js → gateway.
    # When the TUI is quit, the parent chain dies and we get reparented to
    # init (PID 1). In that case, any sessions tracked with our PID are stale.
    if sessions and _is_orphaned_gateway():
        our_pid = os.getpid()
        tracked_by_us = [sid for sid, pid in list(pids.items()) if pid == our_pid]
        if tracked_by_us:
            logger.warning(
                "flm-lifecycle: orphaned gateway (ppid=%d) — purging %d stale session(s)",
                os.getppid(), len(tracked_by_us),
            )
            for sid in tracked_by_us:
                sessions.discard(sid)
                pids.pop(sid, None)
            _write_sessions(sessions, pids)

    # Track our PID alongside session ID
    pids[session_id] = os.getpid()
    sessions.add(session_id)
    _write_sessions(sessions, pids)

    logger.info(
        "flm-lifecycle: session %s started (pid=%d) — active sessions=%d",
        session_id, os.getpid(), len(sessions),
    )


def _on_session_end(session_id="", reason="", **kwargs):
    if not session_id:
        return

    sessions, pids = _read_sessions()

    # Purge any dead-PID orphans on session end too (handles the case
    # where a concurrent session was hard-killed and this is the last
    # session ending — without this, FLM would leak.)
    sessions, pids, _ = _purge_dead_pids(sessions, pids)

    if session_id not in sessions:
        # Replayed / ghost end event. BUT if nothing is tracked and FLM is
        # still running, the bookkeeping lost track of the last session —
        # this end event is the signal to shut FLM down (pre_tool_call will
        # restart it on demand if a live session actually needs it).
        if not sessions and _is_flm_running():
            logger.info(
                "flm-lifecycle: session %s ended but was not tracked (reason=%s) — "
                "no tracked sessions left and FLM still running, stopping it",
                session_id, reason,
            )
            _run_script(_FLM_DOWN, "flm-down")
        else:
            logger.info(
                "flm-lifecycle: session %s ended but was not tracked (reason=%s) — "
                "active sessions=%d",
                session_id, reason, len(sessions),
            )
        return

    sessions.discard(session_id)
    pids.pop(session_id, None)
    _write_sessions(sessions, pids)
    logger.info(
        "flm-lifecycle: session %s ended (reason=%s) — active sessions=%d",
        session_id, reason, len(sessions),
    )

    if not sessions:
        logger.info("flm-lifecycle: last session — stopping FLM server")
        _run_script(_FLM_DOWN, "flm-down")


# ── NPU tool names that require FLM ────────────────────────────────────────

_NPU_TOOLS = {
    "analyze_image",
    "summarize_text",
    "summarize_document",
    "extract_from_webpage",
    "classify_text",
    "extract_json",
}


# ── Plugin entry point ─────────────────────────────────────────────────────

def register(ctx):
    # Seed sessions file if missing
    if not os.path.exists(_SESSIONS_FILE):
        _write_sessions(set(), {})
        logger.info("flm-lifecycle: initialised sessions file at %s", _SESSIONS_FILE)
    else:
        # Clean up orphaned old-format counter file
        old_counter = os.path.join(_PLUGIN_DIR, "sessions.count")
        if os.path.exists(old_counter):
            try:
                os.remove(old_counter)
                logger.info("flm-lifecycle: removed legacy counter %s", old_counter)
            except OSError as e:
                logger.warning("flm-lifecycle: could not remove legacy counter: %s", e)

    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("on_session_end", _on_session_end)

    # Register SIGTERM handler so gateway process cleans up sessions
    # and shuts down FLM when the TUI frontend sends SIGTERM on quit.
    try:
        signal.signal(signal.SIGTERM, _signal_cleanup)
        logger.info("flm-lifecycle: registered SIGTERM handler")
    except ValueError:
        # May fail in sub-threads; non-critical
        pass

    logger.info(
        "flm-lifecycle: registered hooks (sessions=%s, flm-up=%s, flm-down=%s)",
        _SESSIONS_FILE, _FLM_UP, _FLM_DOWN,
    )
