---
name: hermes-self-maintenance
title: Hermes Self-Maintenance — Cron-Based Memory & Skills Auditing
description: Set up scheduled autonomous cron jobs that audit, prune, and consolidate Hermes memory and skills using a local NPU model, with Windows toast notification delivery.
tags: [cron, maintenance, memory, skills, npu, notifications, windows]
category: productivity
---

# Hermes Self-Maintenance

## Trigger

Use this workflow when:
- The user wants Hermes to autonomously maintain its own memory, skills, or config on a recurring schedule
- Setting up a cron job that runs on a **local model** (NPU/FLM) instead of the primary provider
- Delivering cron results as Windows notifications (not just saving to the log)

## Architecture

```
Windows Task Scheduler (optional boot trigger)
  └→ WSL / systemd
       └→ Hermes cron scheduler (built-in)
            └→ Agent runs on local NPU (custom:flm)
                 ├→ Reads ~/.hermes/memories/MEMORY.md + USER.md
                 ├→ Reads ~/.hermes/skills/
                 ├→ Makes changes via memory tool
                 └→ Fires Windows toast notification via powershell.exe
```

## Key Constraints

### Local model cron job

Set `model: { provider: 'custom:flm', model: 'gemma4-it:e4b' }` on the cron job to run the agent's reasoning on the AMD NPU instead of your primary provider (DeepSeek). The custom provider name must match what's defined in `~/.hermes/config.yaml` under `providers.<name>`.

```yaml
model:
  provider: custom:flm
  model: gemma4-it:e4b
```

### FLM must be running

Cron jobs that use `custom:flm` need the FLM server to be up. Include `npu` in `enabled_toolsets` so the flm-lifecycle hooks can auto-start it. Without this, the model call fails silently and the job errors out.

### Windows toast notification bridge

Cron jobs running in TUI mode have no live delivery channel. Bridge via PowerShell:

Write a notification helper script to the Windows filesystem:
```powershell
# C:\Users\<USER>\.hermes\hermes-notify.ps1
param($Title = "Hermes", $Message = "Done", $Duration = 8)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Command pwsh.exe).Source)
$notify.BalloonTipIcon = "Info"
$notify.BalloonTipTitle = $Title
$notify.BalloonTipText = $Message
$notify.Visible = $true
$notify.ShowBalloonTip($Duration * 1000)
Start-Sleep -Seconds ($Duration + 2)
$notify.Dispose()
```

The cron prompt's final step calls it:
```
powershell.exe -ExecutionPolicy Bypass -File "C:\Users\<user>\.hermes\hermes-notify.ps1" -Title "Hermes Audit" -Message "..." -Duration 8
```

Set `deliver: 'local'` on the cron job — the notification is the actual delivery mechanism.

## Filesystem cleanup (~/.hermes junk)

When the user asks to clean up `~/.hermes` (files/folders, not just memory), use
`references/hermes-dir-audit.md` — it has the junk-vs-keep taxonomy from a real audit
(config baks, request dumps, stale locks = junk; state.db, lsp/, active logs = keep).

**Retiring whole skills/references** (slimming stale skills, removing old model-era
docs): use `references/skill-retirement-procedure.md` — dependency-safe removal:
`hermes curator usage` telemetry to find unused skills, symlink/cross-reference graph
first, supersession checks, dangling-pointer sweep. **USER PREFERENCE: user-requested
removals are hard deletes (`rm -rf`), not `.archive/` moves — snapshot with
`hermes curator backup` first as the rollback net.** The user proactively requests this
class of cleanup ("double check md files that can be cleaned off in skills").

## Memory Audit Rules

When auditing memory (MEMORY.md + USER.md) and skills:
1. **Duplicates** — content duplicated across both memory targets. Remove from one.
2. **References to deleted skills** — if an entry mentions a skill no longer in `~/.hermes/skills/`, remove or update.
3. **Overly verbose entries** — shorten by 50%+ where possible. Static personal info (location, card details) is prime for shortening.
4. **Internalized conventions** — basic procedure notes like "Interrupt = STOP" that the user has clearly internalized can be removed.
5. **Stale project references** — references to completed one-off projects no longer reflected in any skill.

Be conservative — prefer shortening over deleting. If unsure, flag in the report.

## Pitfalls

- **FLM must be running** when the cron fires. The `npu` toolset hooks auto-start it, but if FLM is genuinely down (driver issue, out of memory), the job errors. Check `cronjob action='list'` to see last status.
- **deliver: 'local'** means results are saved only to the cron log, not sent anywhere. The notification script is the only user-facing output.
- **PowerShell execution policy** — the Windows-side script may need `-ExecutionPolicy Bypass` to run from WSL.
- **Script path** — use the full Windows path (`C:\Users\...`) not the WSL path (`/mnt/c/...`) when calling from `powershell.exe` inside WSL. The Windows `powershell.exe` doesn't understand `/mnt/c/` paths.
- **Cron job model override** — the syntax is `custom:<name>` (e.g. `custom:flm`), never bare `custom`. Must match a provider defined in `config.yaml`.
