---
name: hermes-acp-editor
description: >-
  Connect Hermes Agent as an ACP server to external editors (Zed, VS Code,
  JetBrains) for agentic coding. Covers ACP dependency installation, editor
  config (agent_servers in Zed, custom adapters in VS Code/JetBrains), WSL
  bridging when Hermes runs inside WSL but the editor runs on Windows, and
  validation steps.
category: hermes-agent
---

# Hermes ACP — Editor Integration

## Overview

Hermes Agent can run as an ACP (Agent Client Protocol) server, allowing
external editors to spawn it as a subprocess and communicate via stdio.
The editor acts as the ACP client (hosts the chat UI, renders diffs),
Hermes acts as the ACP server (owns tools, model, runtime).

```
Editor (ACP client) ↔ stdio ↔ `hermes acp` (ACP server)
```

## Prerequisites

- Hermes Agent installed (via Homebrew, pip, or binary)
- `hermes acp --check` must pass

## ACP Dependency Installation

The ACP adapter requires the `agent-client-protocol` PyPI package, NOT the
`acp` package (which is a dummy/stub package from another project).

### Homebrew install (Hermes' own Python)

```bash
# Find Hermes' Python binary
HERMES_PYTHON=$(readlink -f $(which hermes) | xargs dirname)/../libexec/bin/python3
# Or: /home/linuxbrew/.linuxbrew/Cellar/hermes-agent/<version>/libexec/bin/python3

# Install the correct package
$HERMES_PYTHON -m pip install "agent-client-protocol==0.9.0"
```

### pip-installed Hermes

```bash
pip install -e ".[acp]"
```

### Verify

```bash
hermes acp --check
# Expected: "Hermes ACP check OK"
```

## Zed Configuration

### IMPORTANT: Use `agent_servers`, NOT `agent.path`/`agent.args`

Zed (2026+) uses the `agent_servers` key in `settings.json` for external
ACP agents. The `agent.path`/`agent.args` keys seen in some older docs
do NOT work — Zed ignores them and falls back to the built-in agent.

### Settings file location

- **Windows**: `%APPDATA%/Zed/settings.json`
  → `/mnt/c/Users/<username>/AppData/Roaming/Zed/settings.json` (from WSL)
- **macOS**: `~/Library/Application Support/Zed/settings.json`
- **Linux**: `~/.config/zed/settings.json`

### Config for WSL users

When Hermes is installed inside WSL (Homebrew) and Zed runs on Windows,
`wsl.exe` spawns a non-interactive shell — no shell rc files are sourced,
so Homebrew's PATH and HERMES_HOME are unset. The most reliable solution
is to pass them explicitly via `env`:

```json
{
  "agent_servers": {
    "hermes": {
      "type": "custom",
      "command": "wsl.exe",
      "args": ["-d", "<distro-name>", "--", "env",
        "PATH=/home/linuxbrew/.linuxbrew/bin:/usr/bin:/bin",
        "HOME=/home/<username>",
        "HERMES_HOME=/home/<username>/.hermes",
        "hermes", "acp"],
      "env": {}
    }
  }
}
```

Replace `<distro-name>` (e.g. `Ubuntu-22.04`) and `<username>` as appropriate.

Do NOT rely on `bash -lc` or `zsh -lc` — these source the shell's rc
file, which only works if Homebrew init is in that specific shell's rc
file. If brew eval lives in `.zshrc`, `bash -lc` still won't find it.
And `zsh -lc` may fail with compinit errors from missing completion
files, causing the agent process to exit with code 1.

### Config for native Linux/macOS

```json
{
  "agent_servers": {
    "hermes": {
      "type": "custom",
      "command": "hermes",
      "args": ["acp"],
      "env": {}
    }
  }
}
```

### Using the agent in Zed

1. Restart Zed after editing settings.json
2. Open the Agent Panel (Ctrl+Shift+A)
3. Click the agent selector / new-thread menu
4. Select "Hermes" from the list
5. Start a thread — Hermes runs via ACP

### Verification

- Ask the agent to run a shell command (e.g. `which hermes`)
- If it responds with Hermes' toolset (terminal, file ops) instead of
  "I'm Zed's built-in agent", it's working
- Use `dev: open acp logs` from Zed's command palette to inspect ACP
  messages between Zed and Hermes

## VS Code / JetBrains Configuration

(Not covered in detail here — VS Code uses `hermes acp` as a custom
terminal agent; JetBrains uses ACP plugin settings. The command is
always `hermes acp`.)

## Pitfalls

- **Wrong PyPI package**: Install `agent-client-protocol`, NOT `acp`.
  The `acp` package on PyPI (v0.0.0) is a dummy/stub from another
  project. Installing it causes `ModuleNotFoundError` when starting
  `hermes acp`.
- **WSL path**: Use full path `/home/linuxbrew/.linuxbrew/bin/hermes` or
  route through `wsl.exe` with explicit `env` vars. Avoid `bash -lc`
  because it only works if Homebrew is in that shell's rc file.
- **Old config format**: `agent.path`/`agent.args` at the top level of
  the `agent` object is ignored by modern Zed. Use `agent_servers.<name>`
  instead.
- **No restart**: Zed only reads settings.json at startup. Restart Zed
  after editing.
- **Silent fallback**: If the ACP agent fails to start, Zed silently
  falls back to its built-in agent. You won't see an error — the agent
  just responds like Zed's built-in one. Check ACP logs via
  `dev: open acp logs`.
- **Profile mismatch**: If `agent.default_profile` is set (e.g. "minimal"),
  it only affects Zed's built-in agent, not external ACP agents.
- **Token usage not shown**: Zed's UI does not display token counts for
  external ACP agents. Check usage on the provider's dashboard instead.
  This is a Zed limitation, not a Hermes issue.
- **Panel label says Zed Agent**: That's the editor's built-in ACP client
  panel name, not the backend. Select "Hermes" from the agent dropdown.
