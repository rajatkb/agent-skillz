# Hermes `computer_use` Architecture Reference

Source: [Hermes docs — Computer Use](https://hermes-agent.nousresearch.com/docs/user-guide/features/computer-use) (verified 2026-07-18)

## How it works

The `computer_use` toolset speaks MCP over stdio to `cua-driver`, an open-source background computer-use driver from [trycua/cua](https://github.com/trycua/cua). Each platform uses the appropriate accessibility + input stack:

| Platform | Accessibility | Input dispatch |
|---|---|---|
| Windows | UIAutomation | SendInput + PostMessage (no focus steal) |
| macOS | AX (SkyLight SPIs) | SLPSPostEventRecordTo (pid-scoped) |
| Linux | AT-SPI (X11/Wayland) | XTest / virtual-keyboard |

Key invariant: **background mode** — agent actions don't move the real cursor, don't switch virtual desktops, don't bring windows to front. A tinted overlay cursor shows where the agent is acting.

## Underlying cua-driver binary

Hermes spawns its own `cua-driver mcp` child process over stdio. It does **not** attach to the long-running `cua-driver serve` autostart daemon or its named pipe — the autostart daemon is only needed for SSH/remote scenarios.

- Binary resolved via `shutil.which("cua-driver")`
- Override: `HERMES_CUA_DRIVER_CMD=/path/to/cua-driver`
- Backend swap (testing): `HERMES_COMPUTER_USE_BACKEND=noop`
- Local dev builds (version 0.0.0-local-*) are accepted without the version-warning

## Installation

```bash
hermes computer-use install    # runs install.sh / install.ps1
hermes computer-use status     # verify binary reachable
hermes computer-use doctor     # structured per-check health matrix
```

## Windows SSH / daemon proxy pattern

When running from a session without an interactive desktop (SSH → Session 0), set up the autostart daemon:

```powershell
# From an interactive Windows session (RDP/console):
cua-driver autostart enable
cua-driver autostart kick
```

The daemon (`cua-driver serve`) runs in Session 1+, listening on `\\.\pipe\cua-driver`. When `cua-driver mcp` is called from SSH, it auto-detects the daemon and proxies tool calls through the named pipe.

To bypass proxying (e.g., CI already in an interactive session):
```
cua-driver mcp --no-daemon-relaunch          # flag
$env:CUA_DRIVER_RS_MCP_NO_RELAUNCH = "1"    # env var
```

## WSL considerations

WSL2 runs in its own Hyper-V VM — it's NOT Session 0. WSL can launch Windows `.exe` files as Windows-side processes, but Hermes itself is a Linux process and cross-VM stdio to a Windows binary isn't a standard path.

**No documented first-class WSL support** in Hermes or cua-driver docs. The SSH daemon-proxy pattern is the closest applicable approach but is not identical.

## Known limitations

- **UIPI (Windows)**: Medium-integrity processes cannot enumerate UIA tree of or inject input into High-integrity (admin) windows. Symptom: `capture(mode='som')` returns 0 elements, clicks silently fail, but screenshots render fine (GDI capture is below integrity check). Run Hermes elevated to target admin windows.
- **Some apps don't expose accessibility trees**: Modern UWP apps, Electron < 28, custom-drawing apps (Logic, Final Cut, some games) have sparse/empty trees. Fall back to pixel coordinates.
- **Performance**: Background dispatch is ~3–10ms on Windows UIA. Not noticeable for agent-speed clicking but visible in speed-runs.
- **Hard-blocked patterns**: type() blocks shell-dangerous strings (curl | bash, sudo rm -rf, fork bombs). No password entry via type() — use system autofill.
- **Destructive actions require approval**: click, type, drag, scroll, key, focus_app all need confirmation (CLI dialog or messaging-platform approval buttons).

## Provider compatibility

| Provider | Vision | Works | Notes |
|---|---|---|---|
| Anthropic (Claude Sonnet/Opus 3+) | ✅ | ✅ | Best overall; SOM + raw coordinates |
| OpenRouter | ✅ | ✅ | Multi-part tool messages |
| OpenAI (GPT-4+, GPT-5) | ✅ | ✅ | |
| Google (Gemini 2+) | ✅ | ✅ | |
| Local vLLM/LM Studio/Ollama (vision) | ✅ | ✅ | If model supports multi-part tool content |
| Text-only models | ❌ | ✅ (degraded) | Use mode="ax" for accessibility-tree-only |

## Telemetry

Disabled by default when Hermes spawns cua-driver (sets `CUA_DRIVER_RS_TELEMETRY_ENABLED=0`). Opt in via config.yaml:

```yaml
computer_use:
  cua_telemetry: true
```

## Token efficiency

Four layers of optimisation to keep screenshot costs down:
1. Screenshot eviction — Anthropic adapter keeps only 3 most recent screenshots
2. Client-side compression pruning — strips image parts from old tool results
3. Image-aware token estimation — each image counted as ~1500 tokens
4. Server-side context editing (Anthropic only) — clears old tool_uses via context_management

Typical 20-action session on 1568×900 display: ~30K tokens of screenshot context.
