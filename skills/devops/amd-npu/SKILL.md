---
name: amd-npu
description: "Detect, validate, and use AMD Ryzen AI NPUs (XDNA/XDNA2) on hybrid WSL/Windows systems. Covers FastFlowLM setup, driver checks, and cross-platform serving."
tags: [amd, npu, ryzen-ai, xdna, fastflowlm, wsl, llm]
category: devops
---

# AMD NPU / Ryzen AI — Detection & Usage

## Trigger

Use this skill when the user asks about:
- AMD Ryzen AI NPU detection or validation
- FastFlowLM, Lemonade Server, or any NPU-accelerated LLM runtime
- Running LLMs on AMD hardware (Strix Point, Strix Halo, Kraken, Gorgon Point)
- WSL NPU access or cross-platform LLM serving

## Pitfalls

### Default to FLM, Not Ollama

On this Windows/NPU system, **all model serving goes through FastFlowLM (FLM)**. FLM is the NPU runtime — `flm.exe` on Windows, driven from WSL via `flm serve`. Do not default to Ollama suggestions unless the user explicitly asks for Ollama (e.g., for CPU-only models or non-NPU workflows). Ollama is not installed on this system and does not access the NPU.

When the user mentions a new model or model capability (vision, audio, function calling), check `flm.exe list` first to see if it's available in FLM's catalog. The FLM model tags may differ from Ollama's (e.g., `gemma4-it:e4b` vs Ollama's `gemma4:e4b`).

### FLM Vision Models Need Image on Windows-Accessible Path

When sending images via `flm run` CLI mode, the image file must be at a path accessible from Windows (e.g., `/mnt/c/Users/...`). FLM runs on Windows and reads the image file. WSL-only paths (`/tmp/`, `/home/...`) are not visible to the Windows-side FLM process. Copy images to `/mnt/c/Users/<user>/Downloads/` or similar first. For Python API calls (base64-encoded images via OpenAI SDK), any path works since the file is read client-side.

## WSL NPU Limitation (Critical)

The AMD NPU (`amdxdna` kernel driver + XRT userspace stack) is **not accessible from WSL2**. The Microsoft-custom WSL2 kernel does not include `amdxdna`, and there is no NPU-PV paravirtualization like GPU-PV.

**Workaround:** Install the NPU runtime natively on **Windows**, then drive it from WSL via:
1. **Server mode** (recommended): `flm serve <model>` on Windows, then `curl http://localhost:52625` from WSL
2. **Direct .exe**: `flm.exe run <model>` from WSL spawns a Windows process with full NPU access

## NPU Detection

### From WSL (Windows side)

Use `powershell.exe` to query Windows hardware. **Must escape `$` as `\$`** to prevent bash interpolation:

```bash
# Check if NPU device exists
powershell.exe -Command "Get-CimInstance Win32_PnPEntity | Where-Object { \$_.Name -match 'NPU' -or \$_.Name -match 'Compute Accelerator' } | Select-Object Name, Status | Format-Table -AutoSize"

# Get driver version
powershell.exe -Command "Get-WmiObject Win32_PnPSignedDriver | Where-Object { \$_.DeviceName -match 'NPU|Compute Accelerator' } | Select-Object DeviceName, DriverVersion, DriverDate | Format-Table -AutoSize"

# Get full device details
powershell.exe -Command "Get-CimInstance Win32_PnPEntity | Where-Object { \$_.Name -eq 'NPU Compute Accelerator Device' } | Select-Object *"
```

### From Linux (native, not WSL)

On a real Linux install, check for the `amdxdna` driver and `/dev/accel/accel0`:

```bash
ls -la /dev/accel/accel0  # NPU device node
ls /dev/dri/              # DRM subsystem
modinfo amdxdna           # Kernel driver
xrt-smi examine           # XRT userspace (if installed)
```

## FastFlowLM Setup

### Prerequisites (Windows)

| Check | Command from WSL |
|---|---|
| NPU device OK | `powershell.exe -Command "Get-CimInstance Win32_PnPEntity \| Where-Object { \$_.Name -match 'NPU' } \| Select-Object Name, Status"` |
| Driver version | `powershell.exe -Command "Get-WmiObject Win32_PnPSignedDriver \| Where-Object { \$_.DeviceName -match 'NPU' } \| Select-Object DeviceName, DriverVersion"` |
| Min driver | 32.0.203.304 (recommended: 32.0.203.311+) |

### Install

1. Download `flm-setup.exe` from https://github.com/FastFlowLM/FastFlowLM/releases/latest
2. Run installer on Windows
3. Open a WSL terminal

### Usage from WSL

```bash
# Server mode — start on Windows side, consume from WSL
# MUST use --host 0.0.0.0 for WSL2 accessibility (defaults to 127.0.0.1)

# Option A: Start via Start-Process from WSL (recommended)
powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'C:\Program Files\flm\flm.exe' -ArgumentList 'serve qwen3:0.6b --host 0.0.0.0'"

# Option B: Run in a separate Windows terminal (visible, easier to debug)
# Open a Windows CMD/PowerShell window and run:
#   flm serve qwen3:0.6b --host 0.0.0.0

# Option C: From WSL with Hermes background process (if pty=true works)
# terminal(command='powershell.exe -NoProfile -Command "& ''C:\\Program Files\\flm\\flm.exe'' serve qwen3.5:2b --host 0.0.0.0"', background=True, notify_on_complete=False)

# Verify FLM is running
sleep 5
powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Format-Table Id, ProcessName, WorkingSet, StartTime"
powershell.exe -NoProfile -Command "netstat -ano | findstr ':50001'"

# Then from WSL (localhost works with mirrored networking)
curl http://localhost:50001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:1b","messages":[{"role":"user","content":"Hello"}]}'

# Or with custom port
powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'C:\Program Files\flm\flm.exe' -ArgumentList 'serve qwen3:0.6b --host 0.0.0.0 --port 50001'"

# Direct run (interactive — opens in a new window)
flm.exe run llama3.2:1b

### Pull/Download a Model

```bash
# Pull/download a model explicitly (re-downloads if --force)
flm.exe pull llama3.2:1b
flm.exe pull qwen2.5:0.5b --force

# Pull larger models (4GB+) — download can be slow from HuggingFace
# Expect ~5-10 minutes for a 4GB model on typical broadband
# Use a long timeout or run in background:
#   flm.exe pull qwen3.5:4b
# The download progress shows percentage and MB; check C:\Users\<user>\.flm\models\ for partial downloads

# List available models with install status
flm.exe list
flm.exe list --filter installed  # Only show already-downloaded models

# Check the full model catalog JSON for footprints, features, and model capabilities
# Located at: C:\Program Files\flm\model_list.json
powershell.exe -NoProfile -Command "Get-Content 'C:\Program Files\flm\model_list.json' | ConvertFrom-Json | ConvertTo-Json -Depth 3" 2>&1 | head -100

# Server endpoints (confirmed — FLM API docs)
#   GET  /v1/models                 — list loaded models
#   POST /v1/chat/completions       — chat (OpenAI-compatible)
#   POST /v1/embeddings             — embeddings (embed-gemma models)
#   POST /v1/audio/transcriptions   — Whisper audio transcription
#   Note: NO FIM (Fill-in-the-Middle) endpoint — inline code completion
#         in editors (Zed, VS Code Copilot) will NOT work with FLM.
```

### Battery Optimization (Windows Laptop on NPU)

The XDNA2 NPU is already ~3-8W during inference — significantly more efficient than CPU (~15-25W) or iGPU (~20-40W) for the same work. To minimize battery drain:

- **Start FLM on-demand, stop when idle** — don't leave `flm serve` running 24/7. The NPU silicon is powered when a model is loaded. Use the Dynamic Lifecycle pattern (`scripts/flm-up.sh` / `scripts/flm-down.sh`) for this.
- **Use the smallest viable model** — 1.7B vs 4B is ~2x fewer compute cycles per token → finishes faster → NPU powered for less time.
- **Keep context short** — longer contexts mean more prefill compute. For tool calls / parsing, 4K context is usually enough.
- **Batch requests** — one batch to FLM uses similar total energy to several sequential requests but keeps NPU active for less wall-clock time.
- **No idle drain** — when FLM is not processing, the NPU should enter a low-power state. Verify with a power meter if concerned.

### Linux (native)

On Ubuntu 24.04+ with kernel 7.0+:

```bash
sudo add-apt-repository ppa:lemonade-team/stable
sudo apt update
sudo apt install libxrt-npu2 amdxdna-dkms
sudo reboot
# Then install the .deb from releases
sudo apt install ./fastflowlm*.deb
flm validate
```

See `docs/linux-getting-started.md` in the FastFlowLM repo for Arch Linux and other distros.

## iGPU Memory vs NPU Memory (Common Confusion)

**The NPU and iGPU are separate hardware blocks with independent memory domains.**

- **iGPU (Radeon 890M on HX 370):** Has dedicated VRAM for graphics frame buffer. On the G14, dxdiag reports 284 MB dedicated, WMI reports 512 MB AdapterRAM. This VRAM is **entirely irrelevant** to NPU model loading.
- **NPU (XDNA2):** Has ~16 MB local SRAM across 32 tiles — this is a streaming workspace, not where model weights live. Model weights are stored in system RAM and streamed tile-by-tile via DMA.

When investigating GPU/NPU memory on a hybrid system:

```bash
# iGPU dedicated VRAM (from WSL)
powershell.exe -NoProfile -Command "Get-CimInstance Win32_VideoController | Where-Object { \$_.Name -like '*Radeon*' } | Select-Object Name, AdapterRAM"

# Full display memory breakdown (dxdiag — most accurate)
powershell.exe -NoProfile -Command "
\$tmp = [System.IO.Path]::GetTempFileName() + '.txt'
Start-Process -NoNewWindow -Wait dxdiag -ArgumentList \"/t \$tmp\"
Start-Sleep -Seconds 2
\$content = Get-Content \$tmp -Raw
\$lines = \$content -split \"`r?`n\"
\$lines | Select-String 'Card name|Display Memory|Dedicated Memory|Shared Memory|890M|Radeon' | ForEach-Object { \$_.Line.Trim() }
Remove-Item \$tmp -Force
"

# Verify: iGPU VRAM is NOT NPU memory
# NPU memory = system RAM (check with next section)
```

**WMI vs dxdiag discrepancy:** `Win32_VideoController.AdapterRAM` reports the BIOS pre-allocated buffer (512 MB on the G14), while dxdiag reports actual available dedicated memory (284 MB). The difference is overhead/reserved. Neither value affects NPU model capacity.

## NPU Memory / Shared Memory Limits

The NPU has **no dedicated VRAM** — it uses system RAM via UMA (Unified Memory Architecture).

**WSL2 VM memory is NOT the NPU's memory limit.** The NPU runs on the Windows host and can access all system RAM. WSL2's `free -h` (typically ~3.3-3.8 GB) is the WSL VM allocation, irrelevant to NPU.

If you see a discrepancy between expected and actual NPU-accessible memory, check:
1. **BIOS** → Advanced → AMD CBS → NPU Configuration (UMA allocation on G14)
2. **Windows Settings** → Display → Graphics → Change default graphics settings (NPU memory slider)
3. **Total system RAM** — verify with:
   ```bash
   powershell.exe -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB"
   ```

See `references/npu-memory-limits.md` for full investigation commands, registry queries, and G14-specific details.

## Model Storage Paths

- **Windows:** `C:\\Users\\<USER>\\.flm\\models\\` (confirmed on G14 — NOT `Documents\\flm\\models\\`)
- **Linux:** `~/.config/flm/`
- **Override:** Set `FLM_MODEL_PATH` env var

### Checking Installed Models (from WSL)

Write a .ps1 to a Windows path first to avoid PowerShell execution policy blocking scripts from WSL paths:

```bash
# Write script to Windows path
cat > /mnt/c/Users/<user>/check_models.ps1 << 'SCRIPT'
$paths = @(
    "$env:USERPROFILE\.flm\models"
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "=== $p ==="
        Get-ChildItem $p | ForEach-Object {
            $size = (Get-ChildItem $_.FullName -Recurse -File | Measure-Object Length -Sum).Sum
            Write-Host "$($_.Name) - $([math]::Round($size/1GB, 2)) GB"
        }
    }
}
SCRIPT

# Execute with Bypass policy
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\<user>\check_models.ps1"
```

**Why not `-File /tmp/check_models.ps1`?** PowerShell's `-File` parameter rejects UNC paths (`\\wsl.localhost\...`). WSL paths under `/tmp/` resolve to UNC from Windows. Write scripts to `/mnt/c/Users/<user>/` instead.

## Common Pitfall: Windows Port Exclusion (Hyper-V)

FLM defaults to port **52625**, but Hyper-V / Windows NAT often reserves port ranges including `52602-52701`, causing `bind: An attempt was made to access a socket in a way forbidden by its access permissions [system:10013]`.

**Diagnose:**
```bash
powershell.exe -Command "netsh interface ipv4 show excludedportrange protocol=tcp"
```

**Fix:** Set a different port via `FLM_PORT`:
```bash
# Ephemeral
FLM_PORT=50001 flm.exe serve qwen3:0.6b

# Permanent (Windows user env var) — run from WSL:
powershell.exe -Command "[Environment]::SetEnvironmentVariable('FLM_PORT','50001','User')"
```

Ports in the 3000-9000 range or 50001+ outside excluded ranges work reliably.

### WSL Mirrored Networking — `localhost` Works (No Gateway IP Tricks)

This system has `.wslconfig` set to `networkingMode=mirrored` at `C:\Users\<user>\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

With mirrored networking, WSL shares the Windows host's network stack. This means:
- **`localhost` and `127.0.0.1` in WSL reach Windows services directly** — no gateway IP, no netsh portproxy, no `--host 0.0.0.0` needed
- The WSL gateway IP (`ip route show default`) is irrelevant for reaching Windows
- FLM can bind to default `127.0.0.1` and still be reachable from WSL at `localhost:50001`

**Verification from WSL after starting FLM on Windows:**
```bash
curl -s --max-time 5 http://localhost:50001/v1/models | python3 -c \
  "import sys,json; print([m['id'] for m in json.load(sys.stdin)['data']])"
```

**Config location to check or modify mirrored mode:**
```bash
cat /mnt/c/Users/<user>/.wslconfig
# Changes require `wsl --shutdown` and `wsl` restart to take effect
```

**Implication for tools and scripts:** All `FLM_HOST` references should use `localhost` (not a hardcoded gateway IP). The `gemma-npu` plugin defaults to `FLM_HOST=localhost`.

### Legacy (Non-Mirrored WSL2) — For Reference Only

If `.wslconfig` ever removes `networkingMode=mirrored`, WSL2 reverts to NAT mode where `localhost` means the WSL VM, not Windows. In that case:

**Option A:** `--host 0.0.0.0` + find the Windows host IP:
```bash
flm.exe serve qwen3:0.6b --host 0.0.0.0
curl -s http://$(ip route show default | awk '{print $3}'):50001/v1/models
```

**Option B:** `netsh portproxy` (admin) to forward `0.0.0.0:50001 → 127.0.0.1:50001`.

**Verify FLM Listening Address:**
```bash
powershell.exe -Command "netstat -ano | findstr :<port>"
```
`127.0.0.1:<port>` → only localhost; `0.0.0.0:<port>` → reachable externally.

## Hermes Agent Integration

FLM's server exposes an OpenAI-compatible API. There are two integration paths:

1. **Custom provider** — route the whole chat session through an FLM model (replaces your cloud provider)
2. **Custom tool plugin** — expose an FLM model as a single tool the orchestrator can call on demand (better for specialized capabilities like vision)

### Add FLM as a Custom Provider

Add it in `~/.hermes/config.yaml`:

```yaml
providers:
  flm:
    api: http://127.0.0.1:<port>/v1
    api_key: ""
    default_model: qwen3:0.6b
    models:
      - qwen3:0.6b
      - qwen3.5:0.8b
      - llama3.2:1b
      # ... plus `flm.exe list` output
    name: FLM-NPU
```

Usage:
```bash
# One-off — MUST use --provider flag separately
# --model flm/qwen3:0.6b does NOT work (sends full string as model name to default provider)
hermes chat --provider flm --model qwen3:0.6b

# Single query test
hermes chat --provider flm --model qwen3:0.6b -q "say hello"

# Set as default provider
hermes config set model.provider flm
hermes config set model.default qwen3:0.6b

# Must update config.yaml api field if WSL gateway IP changes from netsh proxy
providers.flm.api: http://<gateway-ip>:<port>/v1
```

Requires the FLM server to be running before Hermes tries to connect.
FLM serve command MUST use `--host 0.0.0.0` (or netsh proxy must be active) for WSL to reach it.

### Tiered Architecture: DeepSeek Orchestrator + FLM Subagents

**Pattern:** Use DeepSeek (or another large model) for reasoning/planning, delegate tool-execution and parsing to FLM subagents. This keeps the fast, low-power NPU model handling the routine work while the expensive cloud model handles complex reasoning.

**⚠ Battery performance caveat — confirmed on G14 (Strix Point, XDNA2):** On battery power, qwen3.5:2b subagent response times are unacceptably slow for interactive use ("took ages"). The NPU's ~3-8W power envelope means lower clock speeds on battery, and subagent tool-calling loops (multiple inference rounds per delegation) compound the latency. This pattern is only viable **plugged in** or with a much smaller model that doesn't need tool calling. On battery, direct tool calling from the orchestrator model performs better despite higher per-call cost, because there's no subagent round-trip overhead.

**Config setup:**
```yaml
# Default: cloud model for your session
model:
  provider: deepseek
  default: deepseek-v4-flash

# Delegation: all subagents use FLM on NPU
delegation:
  provider: flm
  model: qwen3:1.7b          # or the best model you've downloaded
  max_concurrent_children: 3  # XDNA2 can handle 3 parallel subagents
```

**Workflow:** You chat with DeepSeek. When tool work is needed (searching, parsing, file ops, command execution), DeepSeek calls `delegate_task`. FLM subagents run in parallel, execute the work, and return summaries. DeepSeek continues reasoning on the results.

**See also:** `delegate_task` tool docs — subagents inherit parent model by default unless `delegation.provider` is set.

### Custom Cross-Platform Path

Store models on the Windows drive for access from both Windows and WSL:

```bash
# From WSL
export FLM_MODEL_PATH=/mnt/c/Users/<user>/flm/models
flm.exe serve llama3.2:1b

# Make permanent
echo 'export FLM_MODEL_PATH=/mnt/c/Users/<user>/flm/models' >> ~/.bashrc
# or ~/.zshrc

# From Windows PowerShell
$env:FLM_MODEL_PATH = "C:\\Users\\<user>\\flm\\models"
flm serve llama3.2:1b
```

### Dynamic (On-Demand) FLM Lifecycle — Start When Needed, Stop When Done

**Preferred pattern:** Use the **flm-lifecycle Hermes plugin** (`~/.hermes/plugins/flm-lifecycle/`) for automatic lifecycle management. The plugin:
- Increments a session counter on each `on_session_start`
- Starts FLM via `pre_tool_call` only when an NPU tool is actually called (lazy start saves battery on short sessions)
- Stops FLM via `on_session_end` when the last session ends (counter 1→0)

This is the plug-and-play approach — no manual steps, no orphaned processes.

**Two scripts** under `scripts/` in this skill handle the manual lifecycle (if you need ad-hoc control apart from the plugin):

- `scripts/flm-up.sh` — checks if FLM is already running; if not, starts the server and waits for `/v1/models` to respond. Idempotent. Accepts model name as optional `$1` arg.
- `scripts/flm-down.sh` — kills the FLM process via `taskkill /IM flm.exe /F`, unloading the NPU model. Model-agnostic.

**Usage pattern (model arg supported):**
```bash
# Default model (gemma4-it:e2b):
bash ~/.hermes/skills/devops/amd-npu/scripts/flm-up.sh

# Specific model via CLI arg:
bash ~/.hermes/skills/devops/amd-npu/scripts/flm-up.sh gemma3:4b
bash ~/.hermes/skills/devops/amd-npu/scripts/flm-up.sh qwen3.5:2b

# Or via env var (overridden by CLI arg):
FLM_MODEL=gemma3:4b bash ~/.hermes/skills/devops/amd-npu/scripts/flm-up.sh

# Verify running
curl -s --max-time 5 http://localhost:50001/v1/models

# Use the model — if non-default, set FLM_MODEL so tools log it correctly:
export FLM_MODEL=gemma3:4b
analyze_image(...)

# When finished:
bash ~/.hermes/skills/devops/amd-npu/scripts/flm-down.sh
```

**Order of precedence** (highest to lowest): CLI arg > `FLM_MODEL` env var > default `gemma4-it:e2b`

**Cleaning up orphaned instances:** If `flm-down.sh` was not called (e.g., terminal closed abruptly), FLM continues running on Windows. Check for orphaned instances:
```bash
powershell.exe -NoProfile -Command "Get-Process flm -ErrorAction SilentlyContinue | Format-Table Id, StartTime"
```

**Note:** There is no Hermes `on_session_end` hook for auto-cleanup. The dynamic pattern is intentional — the user explicitly chose manual lifecycle over auto-cleanup to keep resources available for non-Hermes NPU work.

### Custom Tool Plugins for FLM Models

For specialized capabilities (vision, audio, classification) that should NOT consume orchestrator context or tokens, create a **Hermes plugin** that exposes an FLM model as a first-class tool. This keeps the tool call isolated — the local model sees only the relevant input, not the full session.

**When to use each integration path:**

| Path | Use case |
|---|---|
| Custom provider | Full chat replacement; the model handles conversation, planning, tool use |
| Custom tool plugin | Expose one model capability as a callable tool within an orchestrator session |
| Standalone script | Ad-hoc calls via terminal/execute_code (no native agent integration) |

**See also:** the `hermes-plugin-development` skill for hook-based/observability plugins (budget tracking, chat logging, lifecycle) — this section covers tool plugins only. The budget-tracker plugin now tracks NPU-offload token usage/savings via a `post_tool_call` hook (DeepSeek vs local split in `hermes budget`).

**Plugin structure** (4 files under `~/.hermes/plugins/<name>/`):

```
~/.hermes/plugins/gemma-vision/
  plugin.yaml       # Manifest: name, version, description, provides_tools
  schemas.py        # LLM-facing JSON schema — the model reads this to decide when to call
  tools.py          # Handler code — executes when the tool is called
  __init__.py       # Registration — wires schemas to handlers via ctx.register_tool()
```

**Key rules for custom NPU tool plugins:**

1. **Minimal context** — the handler should construct a fresh, small request to FLM with ONLY the data the model needs. Never forward orchestrator conversation history or session context. This keeps NPU prefill fast and avoids wasting tokens.

2. **OpenAI-compatible API** — FLM speaks the OpenAI chat format. Use `from openai import OpenAI` with `base_url=f"http://{GW_IP}:{FLM_PORT}/v1"` and `api_key="dummykey"`.

3. **Toolset separation** — register tools under a distinct toolset name (e.g., `toolset="vision"`) so they can be enabled/disabled independently.

4. **Single-turn stateless** — each tool call is independent. The model does not need conversation history for image analysis.

**Concrete example — gemma-vision plugin:**

The `gemma-vision` plugin registers an `analyze_image` tool that sends ONLY a system prompt (~40 tokens) + base64 image + user question to the FLM `gemma4-it:e2b` server on the NPU. No session context, no conversation history, no tool output from the orchestrator.

```bash
# Enable the plugin
hermes plugins enable gemma-vision

# Verify (takes effect on next session)
hermes plugins list --plain --no-bundled | grep gemma
```

**Plugin lifecycle commands:**
- `hermes plugins list` — show all plugins with status
- `hermes plugins enable <name>` — activate a plugin (next session)
- `hermes plugins disable <name>` — deactivate without removing
- Plugins in `~/.hermes/plugins/<name>/` are auto-discovered as "user" sources

The live `gemma-npu` plugin (`~/.hermes/plugins/gemma-npu/`) is the production reference — see its `schemas.py`, `tools.py`, `__init__.py`, and `plugin.yaml` for the full pattern.

## Web UI (Open WebUI)

FLM is backend-only (OpenAI-compatible REST on port 52625). Attach a frontend:

```bash
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:52625 \
  -e OPENAI_API_KEY=unused \
  --name open-webui \
  ghcr.io/open-webui/open-webui:main
```

Open `http://localhost:3000`. Also compatible with AnythingLLM, LobeChat, Continue.dev — any OpenAI-compatible frontend pointed at `http://localhost:52625`.

## Model Catalog (FLM v0.9.43)

Use `flm.exe list` to see available models. Output indicators:
- `✅` — model already downloaded and cached
- `⏬` — available in catalog but not yet pulled (run `flm.exe pull <tag>` to download)

### Checking Tool Calling Support

**Always check FLM's official model card pages** — they explicitly mark `Tool Calling Support: Yes/No` per model variant. These are authoritative and override general assumptions about a model's capabilities:

- Qwen models: `https://fastflowlm.com/docs/models/qwen/`
- Phi models: `https://fastflowlm.com/docs/models/phi/`
- LLaMA models: `https://fastflowlm.com/docs/models/llama/`
- Gemma models: `https://fastflowlm.com/docs/models/gemma/`
- DeepSeek models: `https://fastflowlm.com/docs/models/deepseek/`

**Key finding:** FLM confirms tool calling at 2B+ for Qwen3.5, but not for Phi-4-mini-instruct (4B) or any sub-2B model.

### Chat / Generation Models

`TC` = Tool Calling Support (`Yes`/`No` per FLM model card). Fastest decode speeds from FLM benchmarks @ 1K context.

| Tag | Params | TC | Decode | Realistic Uses |
|---|---|---|---|---|
| `qwen3:0.6b` | ~600M | No | 66.5 t/s | Classification, routing, simple Q&A, short extraction |
| `qwen3.5:0.8b` | ~800M | No | 39.2 t/s | Same as 0.6b with slightly better coherence |
| `qwen3:1.7b` | ~1.7B | No | 40.2 t/s | Short-form chat, light reasoning — **not for tool calling** |
| `llama3.2:1b` | ~1B | Check card | — | General-purpose small chat |
| `llama3.2:3b` | ~3B | Check card | — | Better reasoning, multi-turn chat |
| `qwen3.5:2b` | ~2B | **Yes** | 26.8 t/s | **Smallest model with tool calling** — best speed/quality trade-off for subagents |
| `phi4-mini-it:4b` | ~4B | **No** | 21.8 t/s | Code, math, structured output — surprisingly no tool calling per FLM |
| `qwen3:4b` | ~4B | Yes | 19.6 t/s | General chat, moderate reasoning, tool calling |
| `qwen3-it:4b` | ~4B | Yes | — | Instruct fine-tune variant of Qwen3-4B |
| `qwen3-tk:4b` | ~4B | Yes | — | Always-on thinking variant of Qwen3-4B |
| `qwen3.5:4b` | ~4B | Yes | 15.0 t/s | Newest gen at 4B with tool calling, 5.2GB footprint |
| `qwen3.5:9b` | ~9B | Yes | — | Newest gen, largest Qwen3.5 variant, 8.94GB footprint |
| `gemma3:1b` | ~1B | Check card | — | Google Gemma 3, instruction-tuned |
| `gemma3:4b` | ~4B | Check card | — | Google Gemma 3 larger variant |
| `gemma4-it:e2b` | ~2B eff / 5B total | Check FLM card | Toggleable | Gemma 4 edge model, 6.0GB FLM footprint, vision+audio+128K ctx |
| `gemma4-it:e4b` | ~4.5B eff / 8B total | Yes (per FLM card) | Toggleable | Gemma 4 edge vision model, 9.1GB FLM footprint, vision+audio+128K ctx, native function calling. Runs on XDNA2 NPU (~3-4s/image analysis). |
| `deepseek-r1:8b` | ~8B | Check card | — | Chain-of-thought reasoning (R1 distilled) |
| `llama3.1:8b` | ~8B | Check card | — | General-purpose, solid quality |
| `qwen3:8b` | ~8B | Yes | 11.9 t/s | Best quality in Qwen3, tool calling |
| `qwen3.5:9b` | ~9B | Yes | — | Newest gen, largest Qwen3 variant |
| `nanbeige4.1:3b` | ~3B | Check card | — | Nanbeige reasoning, 3.1GB footprint |
| `gpt-oss:20b` | 20B MoE | Check card | — | MoE (4B active), 14GB footprint |
| `lfm2:1.2b` / `lfm2:2.6b` | ~1.2B/2.6B | Check card | — | Liquid Foundation Models (state-space architecture) |

### Specialized Models

| Tag | Purpose | Notes |
|---|---|---|
| `embed-gemma:300m` | Text embeddings / RAG | Google's dedicated embedding model; `POST /v1/embeddings` |
| `whisper-v3:turbo` | Audio transcription | NPU-accelerated speech-to-text |
| `medgemma:4b` | Medical QA (fine-tuned) | Domain-specific |
| `translate-gemma:4b` | Translation | — |
| `gpt-oss:20b` / `gpt-oss-sg:20b` | MoE generation (20B total, 4B active) | Sparse MoE — active params fit NPU |

### Vision Models

| Tag | Notes |
|---|---|
| `qwen2.5vl-it:3b` | Qwen2.5 Vision-Language |
| `qwen3vl-it:4b` | Qwen3 Vision-Language |
| `gemma4-it:e2b` | Gemma 4 E2B — native multimodal (text+image+audio), 128K ctx, function calling. Lightweight default (6.0GB, 2x faster). |
| `gemma4-it:e4b` | Gemma 4 E4B — native multimodal (text+image+audio), 128K ctx, function calling. Large vision model (9.1GB). |

### Vision & Image Understanding Workflow (Gemma 4 on NPU)

Gemma 4 (E2B/E4B) on FLM provides fast, local image analysis on the NPU with minimal context overhead.

**Key principle — context isolation:** When using Gemma 4 for image analysis, send ONLY the system prompt (~40 tokens) + base64-encoded image + user question. Do NOT inject orchestrator session context (DeepSeek conversation history, tool outputs, file listings). The model does not need it and it wastes NPU prefill compute.

**Model selection:** The `analyze_image` tool reads the `FLM_MODEL` env var to determine which FLM model to query. Set `export FLM_MODEL=<tag>` before calling if you started FLM with a non-default model. Defaults to `gemma4-it:e2b` if unset.

**FLM server command:**
```bash
powershell.exe -NoProfile -Command "Start-Process -WindowStyle Hidden -FilePath 'C:\Program Files\flm\flm.exe' -ArgumentList 'serve gemma4-it:e2b --host 0.0.0.0 --port 50001'"
```

**Image analysis:** done via the agent's `analyze_image` tool (gemma-npu plugin) — no standalone script needed. The tool sends ONLY system prompt + image + question to the NPU and returns the model's analysis. Detail levels 70/140/280/560/1120 map to visual token budgets (280 = default balance; 560 for text-heavy images; 70 for quick classification).

**API format (for custom integrations):**
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:50001/v1", api_key="dummykey")
response = client.chat.completions.create(
    model="gemma4-it:e2b",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": "Describe this image."}
        ]
    }],
    temperature=0.3
)
```

**Performance:** ~2-4s per image on G14 NPU (Strix Point XDNA2). First call includes model load (~4s), subsequent calls faster (~3s). Detail level 280 is a good default balance; use 560 for text-heavy images and 70 for quick classification.

**FLM model card (Gemma 4 E4B):**
- Type: Any-to-Text (text + image + audio input, text output)
- Tool Calling: Yes
- Think: Toggleable
- Quantization: Q4_1
- Default context: 64K, max 128K

The API format above is the working reference for setup and custom integrations.

### RAG / Embeddings for NPU

**Generation models (Qwen3, LLaMA, Gemma, etc.) are NOT good for embeddings.** They are causal decoders — mean-pooling their hidden states produces weak vectors. For vector retrieval you need a dedicated embedding model.

FLM provides `embed-gemma:300m` and supports `POST /v1/embeddings`. See `references/embedding-models.md` for MTEB benchmarks and alternatives.

### Realistic Capability by Model Size

A rough guide for what to expect from NPU-friendly models. **Tool calling** is a separate dimension — always check FLM's model card pages for `Tool Calling Support` rather than inferring from size alone (e.g. Phi-4-mini 4B marks "No" while Qwen3.5-2B marks "Yes").

| Size | Good for | Bad for |
|---|---|---|
| <1B | Classification, routing, simple extraction, intent detection | Multi-step reasoning, code generation, long-form writing, factual recall; no tool calling |
| 1B–3B | Short chat, light reasoning, summarization, translation; **tool calling at 2B+** (Qwen3.5, check card) | Complex chain-of-thought, deep domain expertise, hallucination-prone |
| 4B–8B | Solid reasoning, multi-turn chat, basic code, structured output; tool calling often available | Real-time latency (slower), heavy context lengths >16K |
| 8B+ | Deep reasoning, CoT, good code, strongest quality; tool calling typically supported | May saturate NPU memory; watch context window |

See `flm-lifecycle/references/flm-model-catalog.md` for the current catalog snapshot.

## References

- `references/wsl-powershell-quirks.md` — escaping `$`, path issues, and UNC path workarounds when calling PowerShell/CMD from WSL bash
- `references/npu-memory-limits.md` — NPU shared memory investigation, UMA limits, BIOS/Windows settings, WSL2 vs NPU memory confusion, G14 system details
- `references/embedding-models.md` — MTEB benchmark, embed-gemma:300m usage, comparison of CPU vs NPU embedding models for RAG
- `references/wsl-mirrored-networking.md` — WSL `networkingMode=mirrored` setup, diagnosis, and FLM_HOST implications for `localhost` access to Windows services
- FastFlowLM docs: https://fastflowlm.com/docs/
- FastFlowLM repo: https://github.com/FastFlowLM/FastFlowLM
