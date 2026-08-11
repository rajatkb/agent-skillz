# Microsoft-Approved Windows Desktop Automation Approaches

Research compiled July 2026. Sources: Microsoft Learn, Windows Developer Blog, cua.ai docs, GitHub.

## Official Microsoft Automation APIs

### Windows UI Automation (UIA) — the core API
- Built into Windows since Vista. No install, no third-party code.
- Same API used by: Narrator (built-in screen reader), JAWS, WinAppDriver (Microsoft's Selenium-for- desktop), Visual Studio's coded UI tests, winappCli.
- **Integrity-level gated (UIPI)**: A Medium-integrity process cannot enumerate or inject into a High-integrity (admin) window. This is a security feature, not a bug.
- Consumable from:
  - **.NET**: `System.Windows.Automation` namespace (UIAutomationClient.dll, UIAutomationTypes.dll)
  - **COM**: via IUIAutomation interface
  - **C++**: via UIAutomation.h
  - **PowerShell**: via `Add-Type -AssemblyName UIAutomationClient`

### From WSL — call pattern
```bash
powershell.exe -Command "
Add-Type -AssemblyName UIAutomationClient;
Add-Type -AssemblyName UIAutomationTypes;
$root = [System.Windows.Automation.AutomationElement]::RootElement;
# Find window by name
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, 'Calculator');
$calc = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond);
# Find button by automation ID
$btnCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'num7Button');
$btn7 = $calc.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $btnCond);
# Invoke (click) the button
$invoke = [System.Windows.Automation.InvokePattern]($btn7.GetCurrentPattern(
    [System.Windows.Automation.InvokePattern]::Pattern));
$invoke.Invoke();
"
```

## Microsoft-Published CLI Tools

### winappCli
- **Repo**: github.com/microsoft/winappcli
- **CLI command**: `winapp ui list`, `winapp ui click`, `winapp ui get`
- **Under the hood**: UIAutomation COM API
- **WSL**: callable via `winappcli.exe` (Windows binary runs from WSL)
- **Notable**: First-party Microsoft, actively maintained. Uses UIA patterns (not input injection) so no focus steal.

## Microsoft Agent / MCP Ecosystem

### Windows 365 for Agents MCP Server
- **URL**: learn.microsoft.com/en-us/windows-365/agents/mcp-tool-overview
- **What**: Full MCP server with desktop interaction (mouse, keyboard, screenshot, command execution, browser, UI accessibility)
- **How**: Runs on Cloud PCs — fully managed, Entra ID-joined, Intune-governed virtual Windows desktops
- **Status**: Preview (as of June 2026)
- **License**: Requires Windows 365 subscription (enterprise)
- **Not for**: Local desktop control — cloud-only

### Microsoft Copilot Studio Computer Use
- **Status**: GA as of May 13, 2026 (techcommunity blog)
- **What**: No-code agent builder with computer-use capability (click, type, scroll, screenshot)
- **How**: Cloud-based, runs through Copilot Studio
- **Governance**: Microsoft Entra ID, Intune, DLP policies
- **Not for**: Local self-hosted agents

### Microsoft Execution Containers (MXC) SDK
- **Announced**: Build 2026 (June 2, 2026)
- **Blog**: blogs.windows.com/windowsdeveloper/2026/06/02/windows-platform-security-for-ai-agents/
- **What**: Cross-platform (Windows + WSL), policy-driven execution layer for agents
- **Capabilities**:
  - Process isolation (lightweight, per-agent)
  - Session isolation (full desktop separation with distinct user accounts)
- **Status**: Early preview (Windows Insider builds)
- **Hermes integration**: Explicitly mentioned in the blog — "Hermes Agent will be integrating OpenShell and MXC in their new Windows application."
- **Partners**: Also integrating with OpenClaw, NVIDIA OpenShell, GitHub Copilot CLI

### Agent 365
- **URL**: learn.microsoft.com/en-us/microsoft-agent-365/
- **What**: Enterprise agent management platform
- **Capabilities**: Discover, monitor, apply policy-based controls to local agents (OpenClaw, GitHub Copilot CLI, Claude Code)
- **Integration**: Works with MXC, Windows 365 for Agents, Intune, Entra ID

## Security Architecture of Windows Desktop Automation

### UIPI (User Interface Privilege Isolation)
- Windows prevents Medium-integrity processes from sending input to High-integrity (admin) windows
- Symptom: UIA tree returns empty for elevated windows, clicks silently fail
- Fix: Run the automation process at matching integrity level
- This applies to ALL automation approaches — cua-driver, MCP servers, PowerShell UIA, everything

### MCP Server Containment (Windows On-Device Agent Registry)
- learn.microsoft.com/en-us/windows/ai/mcp/servers/mcp-server-overview
- MCP servers registered through the Windows ODR run in a securely contained agent session
- Only MSIX-packaged servers with package identity get this containment
- Unpackaged servers (.exe, MSI, MCP bundles) require user opt-in to "Reduce protections for agent connectors"

### What's currently possible (no enterprise licensing)

| Approach | Trust level | Setup effort | Feature depth |
|---|---|---|---|
| PowerShell + UIA from WSL | Maximum (Microsoft only) | Medium (write scripts) | Medium (UIA patterns only) |
| winappCli from WSL | Maximum (Microsoft binary) | Low (install CLI) | Medium |
| cua-driver (Hermes built-in) | Medium (open-source binary) | Low (hermes computer-use install) | Full (incl. screenshots, SOM) |
| Third-party MCP server via HTTP | Low-Medium (audit required) | Low (pip install + start) | Full to Very Full |
