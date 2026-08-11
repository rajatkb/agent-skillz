---
name: flm-lifecycle
description: "Manage FLM NPU server lifecycle — session-ID tracking with reconciliation, on-demand start via pre_tool_call, and manual override."
tags: [flm, npu, fastflowlm, gemma-vision, gemma-npu, cost-tracking, lifecycle, plugin, hooks, on-demand, pre-tool-call]
category: devops
---

# FLM Lifecycle — Auto-Managed NPU Server (Plugin-Based)

## Trigger

- Need NPU inference (`analyze_image`, `gemma-npu` tools, FLM provider chat)
- Setting up a new Hermes install that needs FLM auto-lifecycle
- Debugging why FLM didn't start/stop as expected
- Checking active sessions via `sessions.json`
- Switching FLM to a different model (requires manual override)
- Downloading a new FLM model (`flm pull <tag>`)
- Monitoring progress of long model downloads

## Auto-Lifecycle (Primary Mode)

The **flm-lifecycle Hermes plugin** (`~/.hermes/plugins/flm-lifecycle/`) handles FLM automatically:

- **On session start** (`on_session_start` hook): adds the session ID to `sessions.json`. If the set was empty, runs `flm-up.sh` to start the server.
- **On session end** (`on_session_end` hook): removes the session ID from `sessions.json`. If the set becomes empty, runs `flm-down.sh` to stop the server. Ignores untracked session IDs (handles replay/ghost events).

Session tracking uses a JSON file (`~/.hermes/plugins/flm-lifecycle/sessions.json`) storing a set of active session IDs, not a plain counter. This deduplicates replay/ghost events that plague the old counter approach.

This means FLM is only loaded when at least one Hermes session is active — zero idle resource waste, zero manual steps.

### Prerequisites

- `flm-up.sh` and `flm-down.sh` at `~/.hermes/scripts/` (from `amd-npu` skill)
- `flm-lifecycle` plugin in `plugins.enabled` in config.yaml (add it alongside `chat-logger`, `gemma-npu`)
- Plugin files:
  - `~/.hermes/plugins/flm-lifecycle/plugin.yaml` — manifest declaring `on_session_start` / `on_session_end` hooks
  - `~/.hermes/plugins/flm-lifecycle/__init__.py` — `register(ctx)` hooks handler + counter logic
- FLM installed on Windows at `C:\\Program Files\\flm\\flm.exe`
- `npu` toolset in `toolsets` in config.yaml (added by default)

### Plugin Architecture

Same pattern as the built-in `chat-logger` plugin — uses `ctx.register_hook()`:

```python
def register(ctx):
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("on_session_end", _on_session_end)
```

The handler functions receive session metadata (`session_id`, `model`, `platform`) and use `sessions.json` to decide whether to start/stop FLM. The `pre_tool_call` hook acts as an on-demand safety net — starts FLM only when an NPU tool is actually called.

### Sessions File

`~/.hermes/plugins/flm-lifecycle/sessions.json` — a JSON object tracking active session IDs with a **reconciliation** safety net: on session start, if any session IDs are stored but FLM isn't actually running, the state is assumed stale (crash orphan) and reset to empty before incrementing.

`~/.hermes/plugins/flm-lifecycle/sessions.json` — a JSON object tracking active session IDs:

```json
{"session_ids": ["20260723_033424_d027f1"]}
```

```bash
# Check current active sessions
cat ~/.hermes/plugins/flm-lifecycle/sessions.json
# → {"session_ids": []}  (no active sessions)
# → {"session_ids": ["20260723_033424_d027f1"]}  (1 active session)
```

### Verification

```bash
# 1. Plugin loaded? Check the log
grep 'flm-lifecycle' ~/.hermes/logs/agent.log

# 2. Session tracking works? Start a background session and check
cat ~/.hermes/plugins/flm-lifecycle/sessions.json       # expect {"session_ids": []}
hermes -z "say hi" --pass-session-id &  # bg
sleep 3
cat ~/.hermes/plugins/flm-lifecycle/sessions.json       # expect {"session_ids": ["..."]]}

# 3. FLM running? Hit the API
curl -s http://localhost:50001/v1/models | python3 -c \
  "import sys,json; print([m['id'] for m in json.load(sys.stdin)['data']])"
```

## On-Demand Lifecycle (Alternative — pre_tool_call Mode)

An alternative to Auto-Lifecycle: **start FLM only when an NPU tool is actually called**, rather than on every session start. This is more battery-friendly for short/query-only sessions that never touch the NPU.

### How it works

Replace the `on_session_start` hook with a `pre_tool_call` hook that checks the tool name:

| Hook | Fires | What it does |
|------|-------|-------------|
| `pre_tool_call` | Before every tool call | If `tool_name` is an NPU tool, runs `flm-up.sh` (idempotent — no-op if already running) |
| `on_session_end` | When session ends | Same as Auto-Lifecycle — removes session ID from set, stops FLM when set is empty |

### NPU tool set to check against

```python
_NPU_TOOLS = {
    "analyze_image",
    "summarize_text",
    "summarize_document",
    "extract_from_webpage",
    "classify_text",
    "extract_json",
}
```

### Implementation

```python
def _on_session_start(session_id="", **kwargs):
    if not session_id:
        return
    sessions = _read_sessions()
    # Reconciliation: if sessions tracked but FLM not running, state is stale
    if sessions and not _is_flm_running():
        sessions = set()
    if session_id not in sessions:
        sessions.add(session_id)
        _write_sessions(sessions)

def _on_pre_tool_call(tool_name: str, args: dict, task_id: str, **kwargs):
    """Start FLM on demand when an NPU tool is called."""
    if tool_name in _NPU_TOOLS:
        logger.debug("flm-lifecycle: NPU tool '%s' called — ensuring FLM is up", tool_name)
        _run_script(_FLM_UP, "flm-up (on-demand)")

def _on_session_end(session_id="", reason="", **kwargs):
    if not session_id:
        return
    sessions = _read_sessions()
    if session_id not in sessions:
        return  # ghost/replay event — no-op
    sessions.discard(session_id)
    _write_sessions(sessions)
    if not sessions:
        _run_script(_FLM_DOWN, "flm-down")

def register(ctx):
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("on_session_end", _on_session_end)
```

### Why both hooks are needed together

`on_session_start` adds the session ID to the set so `on_session_end` can eventually hit the set→empty transition and shut FLM down. Without it, the set stays empty and FLM is never cleaned up (this was a bug in the original on-demand implementation).

`pre_tool_call` is the *safety* layer — it ensures FLM is running when an NPU tool is actually called, even if `on_session_start` raced or the session started before the plugin was loaded. Since `flm-up.sh` checks port 50001 and exits sub-second if FLM is already up, the redundant check is cheap.

Always use **both** hooks. Never remove `on_session_start`.

### Why idempotent is safe

`flm-up.sh` checks port 50001 first and exits fast (sub-second) if FLM is already serving. So calling it before every NPU tool call is cheap — a tcp-port probe when FLM is up, a full start only on first NPU tool call in a session.

## Manual Override (Secondary Mode)

When you need to control FLM directly — e.g. different model, pre-load before a session, or force-stop:

### Start FLM

```bash
# Default model (gemma4-it:e2b):
bash ~/.hermes/scripts/flm-up.sh

# Specific model:
bash ~/.hermes/scripts/flm-up.sh gemma3:4b
bash ~/.hermes/scripts/flm-up.sh llama3.2:3b
bash ~/.hermes/scripts/flm-up.sh deepseek-r1:8b

# Via env var:
FLM_MODEL=gemma3:4b bash ~/.hermes/scripts/flm-up.sh
```

Idempotent — safe to call repeatedly even if FLM is already running. Checks port 50001 first, exits fast if serving.

**Order of precedence:** CLI arg > `FLM_MODEL` env var > default `gemma4-it:e2b`
**Port override:** `FLM_PORT` env var (default 50001)

### Stop FLM

```bash
bash ~/.hermes/scripts/flm-down.sh
```

Kills all `flm.exe` processes via `taskkill /IM flm.exe /F`. No-op if none running. Verifies process is gone.

### List / Check Downloaded Models

```powershell
# From PowerShell — show all registered models (whether downloaded or not)
& 'C:\Program Files\flm\flm.exe' list

# From PowerShell — show only installed (downloaded) models
& 'C:\Program Files\flm\flm.exe' list --filter installed

# From WSL — via FLM API (when server is running)
curl -s http://localhost:50001/v1/models | python3 -c "import sys,json; print(json.dumps([m['id'] for m in json.load(sys.stdin)['data']], indent=2))"

# Check model files on disk from WSL:
ls /mnt/c/Users/RAJAT/.flm/models/Gemma4-E2B-IT-NPU2/

# Registered model catalog (all models FLM knows about via model_list.json)
python3 -c "import json; d=json.load(open(r'/mnt/c/Program Files/flm/model_list.json')); [print(f'{fam}:{v}') for fam in d['models'] for v in d['models'][fam]]"
```

### Download a New Model

FLM's download command is `pull`, not `sys download`:

```powershell
# Download a model
& 'C:\Program Files\flm\flm.exe' pull gemma4-it:e2b

# Force re-download (after partial/cancelled download)
& 'C:\Program Files\flm\flm.exe' pull gemma4-it:e2b --force
```

**Large downloads (~2-6 GB) benefit from background mode** — foreground terminal timeouts (600s default) may hit mid-download. From WSL, use `cmd.exe /c` (not `powershell.exe -Command`) to avoid Zsh's `setopt: can't change option: monitor` error in background mode:

```bash
# In Hermes terminal tool — use cmd.exe /c for background mode
terminal(command="cmd.exe /c \"C:\\Program Files\\flm\\flm.exe\" pull gemma4-it:e2b", background=true, notify_on_complete=true)
```

**Monitor progress** while downloading by polling the background process:
```bash
process(action='poll', session_id='proc_xxxx')
# Output shows current % and MB downloaded from the model.q4nx file
```

**If download fails partway**, the 0-byte stub prevents resumption. Clear the directory and retry with `--force`:
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\\.flm\\models\\Gemma4-E2B-IT-NPU2"
& 'C:\\Program Files\\flm\\flm.exe' pull gemma4-it:e2b --force
```

Partial downloads leave 0-byte stubs on disk. `--force` is needed for re-download, but if the stub file corrupts the hash check, manually delete the model directory and re-pull cleanly:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\\.flm\\models\\Gemma4-E2B-IT-NPU2"
& 'C:\\Program Files\\flm\\flm.exe' pull gemma4-it:e2b
```

Model storage location: `%USERPROFILE%\\.flm\\models\\<Model-Name>\\` (e.g. `C:\\Users\\RAJAT\\.flm\\models\\Gemma4-E2B-IT-NPU2\\`).

### Switch Model

Check the model is downloaded first, then stop → start:

```bash
# 1. Verify model is downloaded (flm list --filter installed or check disk)
# 2. Stop current FLM
bash ~/.hermes/scripts/flm-down.sh

# 3. Start with new model
bash ~/.hermes/scripts/flm-up.sh <new-model>
```

The `flm-up.sh` script passes the model tag to `flm serve`. The model won't load if not yet downloaded — download first via `flm pull <tag>`.

## Using NPU Tools

Once FLM is running (auto or manual), these work:

- **`analyze_image`** — sends image + question to FLM server
- **`summarize_text`**, **`summarize_document`**, **`extract_from_webpage`**, **`classify_text`**, **`extract_json`** — NPU-backed text tools from `gemma-npu` plugin
- **FLM provider chat** — `hermes chat --provider flm --model <model-name>`
- **Direct API** — `curl http://localhost:50001/v1/chat/completions`

## Verifying the NPU is actually being used

**WSL can NEVER see the NPU directly** — WSL2 has no NPU passthrough (no `/dev/accel*`, no `amdxdna` kernel module in the guest). Do not diagnose "is the NPU working" from inside WSL by looking for devices/drivers there. FLM is a **Windows process** (`C:\Program Files\flm\flm.exe serve`); WSL only talks HTTP to `localhost:50001`.

Definitive backend check — run FLM's own validator from Windows:

```powershell
& 'C:\Program Files\flm\flm.exe' validate
# → [Windows]  NPU: XDNA2
# → [Windows]  NPU dirver version: 32.0.203.314
```

Supporting evidence the NPU path is live:
- FLM install dir ships NPU DLLs (`gemma_npu.dll`, `gemma4e_npu.dll`, `*_npu.dll` per model)
- Model dir is the NPU2 variant (e.g. `%USERPROFILE%\.flm\models\Gemma4-E2B-IT-NPU2\`)
- Windows device manager shows `NPU Compute Accelerator Device` (AMD 17F0), Status OK
- `flm.exe` working set ~6.6 GB for a 2B model (weights + KV cache in host RAM — normal for NPU2)

There are **no `\NPU\*` Windows performance counters** for this device — `Get-Counter` returns 0 samples. Use `flm validate`, not perf counters.

**Throughput calibration (this machine, gemma4-it:e2b on XDNA2):** ~22-23 tok/s decode, ~1s TTFT, prefill ~20 tok/s. A 94-token completion takes ~5s wall. This is the sustained NPU rate — not a malfunction.

## Pitfalls

### Killing a client mid-request wedges FLM — restart before benchmarking

If a client (e.g. `research.py` killed with `pkill`) is terminated while FLM is mid-inference, FLM can be left **wedged**: the process is alive, port is listening, `GET /v1/models` may even respond — but chat completions hang until timeout. Benchmarking against this state produces a false "NPU is slow" conclusion (a 300-token request "timing out at 120s" was actually the wedged server, not the NPU — a fresh restart did the same work in 5.3s).

**Fix:** `bash ~/.hermes/scripts/flm-down.sh` then `flm-up.sh`, THEN measure. Always restart FLM before any performance assessment — never trust a timing taken after a killed run.

### Auto-start race condition on very short sessions

A `hermes -z "hi"` session starts and ends in <1s. The hooks fire in sequence, going {}→{session}→{}. This is correct behavior — FLM doesn't actually start because the de-registration fires before the start script finishes. No harm done, but if you see FLM not starting for very brief sessions, that's expected — there's no NPU work happening anyway.

### TUI gateway leaves FLM running after quit (tier-3 orphan detection + SIGTERM — Jul 2026)

The plugin runs inside the **TUI gateway process** (`tui_gateway.entry`). When you quit the TUI, the main Hermes and Node.js frontend exit, but the gateway process may get orphaned (reparented to init) without `on_session_end` firing. The stale session ID stays in `sessions.json` and FLM leaks.

**Two mechanisms fix this:**

1. **Tier-3 orphaned gateway detection** (`_is_orphaned_gateway`): On every `on_session_start`, checks if this process's parent died (ppid=1). If so, purges any sessions tracked with our PID as stale.

2. **SIGTERM handler** (`_signal_cleanup`): Registered in `register()`. When the TUI frontend sends SIGTERM down the process tree during shutdown, the handler removes all sessions tracked by this PID and shuts FLM down if no others remain.

3. **Empty-set fallback (Aug 2026 fix)**: The old design leaked FLM when bookkeeping went empty while a session was still alive — `pre_tool_call` restarts FLM without re-registering the session, and untracked end events no-opped. Now both `_on_session_end` and `_signal_cleanup` stop FLM when the tracked set is empty **and** FLM is actually running, regardless of whether the ending session was tracked. Safe because `pre_tool_call` restarts on demand (~5s). Also fixed: `_is_flm_running()` was probing a stale WSL NAT IP (`172.29.192.1`); it now uses `127.0.0.1` (mirrored networking) — the stale IP made tier-1 reconciliation wipe live sessions on every start.

**Diagnosis commands:**
```bash
# Check gateway orphan status
ps -o ppid= -p $(ps -o pid= -C python3.11 --no-headers | head -1)
# If output is "1", the gateway is orphaned
```

### Orphaned FLM process after crash (tier-2 PID tracking — Jul 2026)

If Hermes crashes before `on_session_end` fires, the session ID set stays non-empty. Two-tier reconciliation handles this:

- **Tier-1**: FLM not running + tracked sessions exist → reset stale state (original fix).
- **Tier-2**: FLM is running but a tracked session's **process PID is dead** → purge that orphan. PIDs are stored alongside session IDs in `sessions.json`, and `os.kill(pid, 0)` checks liveness. Runs on every `_on_session_start` and `_on_session_end`.

This means **hard-killed Hermes instances (SIGKILL, crash, taskkill) no longer leak** — the orphan session is cleaned up the next time any session starts or ends.

```bash
# Manual cleanup if you ever need it (rarely needed now):
cat ~/.hermes/plugins/flm-lifecycle/sessions.json
# Reset to empty:
echo '{"session_ids": [], "pids": {}}' > ~/.hermes/plugins/flm-lifecycle/sessions.json
# Kill if needed:
bash ~/.hermes/scripts/flm-down.sh
```

### Config changes are per-profile

The plugin is enabled in the active profile's `config.yaml`. If you switch profiles (e.g. work/profile), the plugin won't auto-manage FLM in the new profile unless it's also enabled in that profile's config.

### Zsh `setopt: can't change option: monitor` error in background mode

When running Windows FLM commands from WSL Zsh in background mode, `powershell.exe -Command "..."` triggers this error and exits with code 1. Workaround — use `cmd.exe /c` instead:

```bash
# BROKEN (powershell.exe from Zsh background):
terminal(command='powershell.exe -Command "& ''C:\\Program Files\\flm\\flm.exe'' pull gemma4-it:e2b"', background=true)

# WORKS (cmd.exe from Zsh background):
terminal(command='cmd.exe /c "C:\\Program Files\\flm\\flm.exe" pull gemma4-it:e2b', background=true)
```

The `setopt: can't change option: monitor` error is a Zsh + `powershell.exe` interaction — the shell tries to manipulate job-control options in a non-interactive context. `cmd.exe` doesn't trigger it.

### Large model downloads may fail partway (~70% on slow connections)

`flm pull` on large models (5-6 GB) can fail mid-download — the connection drops and leaves a partial file. Symptoms:
- Exit code 1 after making partial progress (e.g. 70% on model.q4nx)
- model.q4nx exists but is smaller than the expected 4.45 GB

Fix: clear the model directory and re-pull:
```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.flm\models\Gemma4-E2B-IT-NPU2"
& 'C:\Program Files\flm\flm.exe' pull gemma4-it:e2b
```
If it fails repeatedly at the same point, try at a different time or on a different network.

### Corrupted model after resumed partial download — server starts but API never responds

When `flm pull` fails partway and is retried **without `--force`**, the resumed download can produce a corrupted `model.q4nx` that:
1. Download reports 100% and exits code 0
2. `flm serve` starts, logs `WebServer started on port 50001` and `Press Ctrl+C to stop.`
3. Port is listening (`netstat` shows LISTENING)
4. Working set is ~6.8 GB (seems normal)
5. **But API never responds** — `curl -s http://localhost:50001/v1/models` times out

**Diagnostic:** run `flm check <model>` from Windows PowerShell:
```powershell
& 'C:\Program Files\flm\flm.exe' check gemma4-it:e2b
```
FLM checks every file's hash and auto-removes corrupted files. Output like:
```
[FLM]  Checking file: model.q4nx...
[FLM]  Fail!
[FLM]  Removing corrupted file: model.q4nx...
```

**Root cause:** the partial download's data didn't match the hash. When `flm pull` resumed without `--force`, it only downloaded the missing bytes, but the existing partial data was corrupt. Always run `flm check` after a resumed download.

**Fix cycle:**
1. Kill all FLM processes: `bash ~/.hermes/scripts/flm-down.sh`
2. Run `flm check <model>` — it auto-removes corrupted files
3. Re-pull: `& 'C:\Program Files\flm\flm.exe' pull <model>` (downloads only missing/corrupted files)
4. Verify again with `flm check <model>` — expect all Success
5. Restart: `bash ~/.hermes/scripts/flm-up.sh <model>`

### Cron job sessions don't trigger lifecycle hooks

Cron job sessions run as isolated agent sessions that **do not trigger** `on_session_start` / `pre_tool_call` lifecycle hooks. If a cron job uses `model.provider: custom:flm` for its own inference, FLM won't auto-start — the model call will time out.

**Fix:** Add a manual `flm-up.sh` step as the first action in the cron job prompt:

```
## Step 0: Start FLM NPU server
Run this FIRST:
bash ~/.hermes/scripts/flm-up.sh
Wait for confirmation FLM is serving.
```

The cron agent has `terminal` access and can run this. Once FLM is confirmed up, the model provider connection succeeds.

### FLM provider URL must use localhost

When `flm-up.sh` reports TIMEOUT or `curl` to the FLM API from WSL fails:

1. **Check the Windows FLM process FIRST** — don't debug WSL networking:
   ```bash
   powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Select-Object Id, StartTime, WorkingSet64 | Format-Table -AutoSize"
   ```
   If the process exists with a reasonable working set (~6-7 GB for a 2B model), FLM is running. The WSL routing is usually the issue, not the server.

2. **Check from Windows directly** to rule out server-side problems:
   ```bash
   powershell.exe -NoProfile -Command "curl.exe -s --max-time 5 http://127.0.0.1:50001/v1/models | Select-String 'gemma4'"
   ```
   If this works (returns model IDs), the server is healthy — the issue is WSL→Windows routing, not a corrupted model or startup failure.

3. **Only then debug networking** — check the gateway IP, firewall rules, or `--host 0.0.0.0` binding. The Windows-local check eliminates false positives from corrupt models or zombie processes before you spend time on routing.

### Multiple FLM processes fighting over same port after failed starts

After repeated `flm-up.sh` calls that timed out, multiple FLM processes can end up listening on port 50001:
```
TCP 0.0.0.0:50001 LISTENING 22012
TCP 0.0.0.0:50001 LISTENING 23648
```
This causes connection timeouts even though the port is "listening" — requests hit the wrong process. Fix:
```bash
bash ~/.hermes/scripts/flm-down.sh   # kills all flm.exe processes
# Wait 2s, verify port is free, then re-start
bash ~/.hermes/scripts/flm-up.sh <model>
```

## References

- `references/gemma-npu-tools.md` — detailed tool schemas, usage examples, cost tracking (covers all 6 tools)
- `references/flm-model-catalog.md` — all available FLM models (⚠️ "Currently Downloaded" table is a snapshot — confirm with `flm list --filter installed`)
- `references/audio-and-whisper.md` — audio-capable FLM models (gemma4-it e2b/e4b native audio, whisper-v3:turbo STT), no-TTS gap, evidence
- `references/validation-procedure.md` — full NPU pipeline validation
- `amd-npu` skill `references/wsl-mirrored-networking.md` — WSL mirrored networking config (localhost reaches Windows)
- `~/.hermes/plugins/flm-lifecycle/__init__.py` — plugin source (canonical reference — source of truth for the actual code)
- `~/.hermes/plugins/flm-lifecycle/plugin.yaml` — plugin manifest

## Related Skills

- `amd-npu` — full NPU detection, driver checks, model catalog, battery tuning
- `gemma-npu` plugin — single unified plugin providing all 6 NPU tools
- `hermes-plugin-development` — general plugin development guide
