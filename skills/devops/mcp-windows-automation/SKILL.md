---
name: mcp-windows-automation
description: "Windows desktop and browser automation — covers BOTH Hermes' built-in computer_use toolset (cua-driver, first-party) AND third-party MCP servers as extension paths. Comparison, setup, and WSL cross-boundary guidance."
triggers:
  - user asks about Hermes computer_use toolset (how it works, Windows/WSL compatibility, installation)
  - user finds built-in computer_use insufficient and asks for third-party MCP alternatives
  - user wants to add Windows desktop automation (mouse, keyboard, screenshots, app control) to Hermes
  - user found MCP servers on GitHub and wants to integrate them
  - user asks about MCP vs built-in Hermes tools for desktop/browser automation
  - user wants to control Windows from WSL (via built-in tools or MCP)
  - user expresses security or trust concerns about third-party automation tools
  - user asks for Microsoft-approved / official / sanctioned alternatives for desktop automation
  - user asks to build a custom automation tool using Microsoft APIs only
---

# MCP Windows Automation

Hermes ships two native automation toolkits, then offers MCP servers as a third-party extension path:

| Toolset | What it does | Backend needed |
|---|---|---|
| `browser` (built-in) | Web navigation, click, type, scroll, screenshot | Browserbase / agent-browser CLI / CDP |
| `computer_use` (built-in) | Full desktop drive: click, type, scroll, drag, window focus, screenshots — background mode, no cursor warp, no focus steal | `cua-driver` binary (installed via `hermes computer-use install`) |
| `windows-computer-use` (custom skill) | Desktop drive via Microsoft winappcli + UIA — named pipe IPC, zero network ports. WSL→Windows bridge via PowerShell relay. | `winapp.exe` winget package + PowerShell server (no third-party binaries) |
| MCP servers (third-party) | Additional or alternative desktop/ browser automation | Per-server setup |

For **computer-use / desktop automation** (mouse, keyboard, screenshot, OCR, app control), Hermes now ships the **`computer_use` toolset natively** — evaluate that first before reaching for third-party MCP servers.

## Hermes built-in `computer_use` toolset

Hermes' native `computer_use` toolset drives the desktop in the **background** — your cursor doesn't move, keyboard focus doesn't change, apps don't come to front. Works with **any tool-capable model** (Claude, GPT, Gemini, local).

### Platform stack

| Platform | Accessibility tree | Input dispatch |
|---|---|---|
| Windows | UIAutomation | SendInput + PostMessage (no focus steal) |
| macOS | AX (SkyLight SPIs) | SLPSPostEventRecordTo (pid-scoped) |
| Linux | AT-SPI (X11 + Wayland) | XTest / virtual-keyboard |

### Installation

```bash
# Most direct — runs install.sh/macOS or install.ps1/Windows
hermes computer-use install

# Or interactively:
hermes tools   # then pick 🖱️ Computer Use

# Verify:
hermes computer-use status
hermes computer-use doctor   # structured per-check matrix
```

### Windows-specific from WSL

**There is no documented first-class support for running `computer_use` from inside WSL targeting the Windows desktop.** Hermes spawns `cua-driver mcp` as a child process over stdio — but from WSL (a Linux environment), there's no turnkey path for this cross-VM stdio bridge.

The closest applicable pattern is the **Windows SSH daemon proxy** documented at [cua.ai/docs/how-to-guides/driver/windows-ssh](https://cua.ai/docs/how-to-guides/driver/windows-ssh):

1. **On Windows** (PowerShell/RDP/console), install cua-driver and set up the autostart daemon:
   ```powershell
   irm https://cua.ai/driver/install.ps1 | iex
   cua-driver autostart enable
   cua-driver autostart kick
   ```
   This registers a Scheduled Task running `cua-driver serve` in your interactive session (Session 1+), listening on `\\.\pipe\cua-driver`.

2. **From WSL**, `cua-driver mcp --no-daemon-relaunch` auto-detects the daemon pipe and proxies through it. You'd need to wire this as Hermes' backend (e.g., via `HERMES_CUA_DRIVER_CMD` pointing to the Windows `cua-driver.exe` path).

**Practical options ranked:**

| Option | Feasibility | Notes |
|---|---|---|
| Run Hermes on Windows natively | ✅ Best | Use Windows-side Hermes for computer-use tasks; keep WSL Hermes for everything else |
| Autostart daemon + `HERMES_CUA_DRIVER_CMD` | 🟡 Should work | Point to Windows `cua-driver.exe` path from WSL — WSL can launch `.exe` files. Stdio bridging may have quirks |
| SSH-style daemon proxy | 🟡 Likely | Install daemon on Windows; from WSL run `cua-driver mcp --no-daemon-relaunch` which auto-detects pipe |
| MCP gateway | 🟡 Possible | Run cua-driver as standalone MCP server on Windows, point Hermes' tool gateway at it |

### Limitations

- **UIPI (Windows)**: Elevated/admin windows cannot be driven from a non-elevated Hermes process — UIA tree is invisible, clicks are silently ignored. Run Hermes elevated to target admin windows, or target only non-elevated apps.
- **cua-driver binary is platform-native**: Windows binary must run on Windows. WSL can't natively exec a `.exe` as a child process — only launch it as a separate Windows process.
- **Session 0 (SSH)**: The SSH proxy pattern above works around this. WSL is NOT Session 0 (it's a separate VM), so the SSH docs are a close but not exact analogue.

## When to use MCP vs Hermes built-in tools

| Situation | Recommended |
|---|---|
| Just browser automation (navigate, click, type) | Hermes built-in `browser` toolset with agent-browser CLI |
| Full desktop automation (click, type, drag, scroll, window focus) | Hermes built-in `computer_use` toolset (first-class, no API keys) |
| Desktop automation from WSL targeting Windows | MCP server or daemon-proxy pattern (see above) |
| **Desktop automation, maximum trust / zero third-party** | **`windows-computer-use` custom skill** (PowerShell + winappcli — Microsoft-only, named pipe IPC, zero network ports) |
| **Desktop automation, build your own Microsoft-only tool** | **`windows-computer-use` custom skill** — scripts at `~/.hermes/skills/windows-computer-use/scripts/` |
| Need a custom automation stack not covered by built-in tools | MCP server |
| Browser + desktop control as a combined MCP toolkit | MCP server (e.g. sandraschi/windows-computer-use-mcp) |
| Need screenshots + UI inspection + browser combo | MCP server or built-in `computer_use` |
| Enterprise governed deployment | Windows 365 for Agents MCP server or Copilot Studio computer-use |

## Curated MCP Servers for Windows

### Browser-focused
- **qckfx/browser-ai** — ⭐30. Playwright-based, natural language browser control. MCP server. https://github.com/qckfx/browser-ai
- **Cap-of-tea/GDD** — ⭐11. 37 MCP tools for N Chromium instances with device emulation. https://github.com/Cap-of-tea/GDD
- **thronapple/chrome-local-mcp** — Lightweight CDP Chrome control from WSL. https://github.com/thronapple/chrome-local-mcp

### Full Windows desktop + browser
- **sandraschi/windows-computer-use-mcp** — ⭐22. 22 MCP tools: click, type, screenshot, OCR, UI inspection. https://github.com/sandraschi/windows-computer-use-mcp
- **manushi4/Screenhand** — ⭐10. Screenshots, UI control, browser. https://github.com/manushi4/Screenhand
- **Nanonite-crypto/pc-control-mcp** — Mouse, keyboard, screenshots, windows, browser, clipboard. https://github.com/Nanonite-crypto/pc-control-mcp
- **Steph-ux/windows-desktop-mcp** — UIAutomation + OCR + Playwright + CDP. https://github.com/Steph-ux/windows-desktop-mcp
- **theyoungtoxic/go-to-work** — Windows-first, permission-gated, browser + desktop. https://github.com/theyoungtoxic/go-to-work

### Cross-platform computer-use
- **QwenLM/open-computer-use** — ⭐169. MCP-based computer use for Windows/macOS/Linux via accessibility API. https://github.com/QwenLM/open-computer-use
- **cgissing/windows-computer-use** — ⭐25. Agent controls Windows desktop software. https://github.com/cgissing/windows-computer-use

## Microsoft-Sanctioned / Zero Third-Party Approaches

When security concerns rule out third-party MCP servers, these approaches use **only Microsoft-shipped code** (Windows UIAutomation API, .NET, PowerShell, or Microsoft-published CLI tools). The same underlying UIAutomation API drives all Windows automation — the difference is who packaged it.

For a **turnkey, pre-built implementation** combining PowerShell + winappcli behind a named pipe server, see the sibling skill **`windows-computer-use`** (`~/.hermes/skills/windows-computer-use/`). It wraps the raw API calls below into a Hermes-callable tool with session isolation, auto-install, and WSL awareness — built during this session.

### 1. PowerShell + UIAutomation (zero dependencies)
Callable directly from WSL — no install, no third-party binaries, no pip packages.

```bash
powershell.exe -Command "
Add-Type -AssemblyName UIAutomationClient;
Add-Type -AssemblyName UIAutomationTypes;
$root = [System.Windows.Automation.AutomationElement]::RootElement;
# Find window by name, find child by automation ID, invoke pattern
$window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children,
    [System.Windows.Automation.Condition]::TrueCondition)
"
```

Full capability: find windows and controls by name/ID/class/type, invoke click patterns, get/set text, read element state, take screenshots (via `[Windows.Graphics.Capture]`). Every Windows machine since Vista has these assemblies.

**Limitation**: You write the automation logic yourself — no turnkey MCP tool surface. Best for targeted, deterministic operations (click this button, read that field).

### 2. winappCli (Microsoft-published CLI)
[github.com/microsoft/winappcli](https://github.com/microsoft/winappcli) — Official Microsoft CLI for Windows UI automation.

```bash
# From WSL:
winappcli.exe ui list    # enumerate windows/controls
winappcli.exe ui click --name "OK"  # click by accessible name
```

Uses UIAutomation under the hood. Official, maintained by Microsoft, callable from WSL as a Windows binary.

### 3. Microsoft Execution Containers (MXC) SDK (early preview)
Announced at Build 2026. Cross-platform (Windows + WSL), policy-driven agent containment. Enables process isolation (lightweight) and session isolation (full desktop separation). **Hermes Agent is integrating with it** — see [Windows Developer Blog](https://blogs.windows.com/windowsdeveloper/2026/06/02/windows-platform-security-for-ai-agents/). Currently in early preview — check for availability.

### 4. Windows 365 for Agents MCP server
Official Microsoft MCP server with full desktop control (mouse, keyboard, screenshot, browser, shell). Requires a **Cloud PC** — enterprise licensing, cloud-hosted. Governed by Entra ID and Intune. Not for local desktop control.

### 5. Microsoft Copilot Studio "computer use"
GA as of May 2026 (see [techcommunity blog](https://techcommunity.microsoft.com/blog/copilot-studio-blog/computer-using-agents-in-microsoft-copilot-studio-are-now-generally-available/4519427)). No-code agent builder with computer-use capability. Cloud-based, enterprise-governed. Not for local self-hosted agents.

### Security comparison

| Approach | Third-party code | Governance | From WSL | Best for |
|---|---|---|---|---|
| PowerShell + UIA | None (Microsoft .NET) | UIPI integrity levels | ✅ `powershell.exe` | Targeted deterministic ops |
| winappCli | None (Microsoft binary) | UIPI + MS signing | ✅ Win binary | Quick CLI automation |
| cua-driver (Hermes built-in) | Open-source binary | UIPI + cua-driver sandbox | 🟡 Daemon proxy | Full desktop drive |
| Third-party MCP server | Full third-party code | UIPI only | ✅ HTTP gateway | Rich tool surface |
| MXC SDK (preview) | None (Microsoft) | Policy-driven containment | ✅ WSL native | Enterprise-grade |

## How MCP integrates with Hermes

The user's `~/.hermes/config.yaml` can declare MCP servers under an `mcp_servers` section (if Hermes supports it) or the MCP server can be run alongside Hermes and its tools called via terminal/API from the agent's session.

Common setup pattern:
```bash
# Clone and run an MCP server (example):
git clone https://github.com/owner/repo
cd repo
npm install  # or pip install -r requirements.txt
node server.js  # or python server.py
```

The MCP server exposes tools that the agent can call if configured properly in the Hermes tool chain. If Hermes doesn't have direct MCP client support for standard MCP servers, the tools can be used via terminal commands (calling the MCP server's HTTP API directly).

## Pitfalls

- **Don't confuse MCP (Model Context Protocol) with ACP (Agent Client Protocol)** — they're different standards. Hermes has its own ACP integration for editor tools; MCP servers are a separate ecosystem.
- **MCP servers don't replace Hermes' need for a browser backend** — they provide alternative tools. You can use both in parallel.
- **MCP server quality varies** — check stars, last commit date, and issue tracker before investing setup time. Many are experimental.
- **From WSL**: MCP servers running on Windows are reachable via `172.x.x.1` gateway IP (same as FLM setup). Configure the MCP server to bind to `0.0.0.0` if it only listens on localhost.
- **Security vetting**: All third-party MCP servers run with full user-level access to the Windows desktop. Audit the code before running it. Prefer servers that use Microsoft's UIAutomation API (same OS API) rather than SendInput/input injection for click/type actions — UIA is integrity-level-gated and doesn't require the server to own the focus. For maximum trust, use the Microsoft-sanctioned approaches below (PowerShell+UIA, winappCli) which involve zero third-party binaries.
