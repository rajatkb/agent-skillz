# Debloater Tools Comparison — July 2026

Research from a ROG G14 audit session. Covers tools that target Windows services specifically
(rather than just app removal or registry privacy tweaks).

---

## Win11Debloat (Raphire) — 50.4k stars

**Repo:** https://github.com/Raphire/Win11Debloat  
**Run:** `iwr -useb "https://win11debloat.raphi.re/" | iex`

### Capabilities
- Removes pre-installed bloatware apps (Bing News, Xbox app pack, Skype, etc.)
- Disables telemetry, diagnostics, targeted ads (registry-based)
- Disables Game Bar / Game DVR / Game Mode (registry-based)
- Disables Copilot, Recall, AI features
- Disables location services, Find My Device
- UI tweaks: dark mode, context menu (Win10 style), taskbar, search, File Explorer
- Windows Update: disable auto-restart, Delivery Optimization P2P

### Service changes
Does NOT use Set-Service directly. All changes via registry:
- GameDVR behaviour (HKLM registry keys)
- Location services (registry)
- Fast startup (registry)

### Verdict
**Best for:** App cleanup + UI declutter. Run this first, then a custom service script.
**Doesn't cover:** ~95% of the Tier-1 service list.

---

## Chris Titus WinUtil

**Repo:** https://github.com/ChrisTitusTech/winutil  
**Run:** `irm christitus.com/win | iex`

### Capabilities
- GUI-based with Standard/Minimal/Advanced presets
- App removal (provisioned packages) + winget app installer
- Registry tweaks (telemetry, consumer features, OneDrive, widgets, AI)
- Service management (via WPFTweaksServices)

### Service changes (WPFTweaksServices)
| Service | Action | Why |
|---|---|---|
| CscService (Offline Files) | → Disabled | Enterprise feature |
| DiagTrack (Telemetry) | → Disabled | Privacy |
| MapsBroker (Downloaded Maps) | → Manual | Maps aren't used daily |
| StorSvc (Storage Service) | → Manual | Storage Sense can be on-demand |
| SharedAccess (ICS) | → Disabled | Not sharing connection |
| lfsvc (Geolocation) | → Disabled | Not needed for dev/gaming |

### Verdict
**Best for:** One-click preset for new installs. Conservative — safe baseline.
**Doesn't cover:** ~85% of Tier-1 list. No Bluetooth, Xbox, Print Spooler, WSearch, SysMain.

---

## Simeon OnSecurity Windows-Optimize-Debloat

**Repo:** https://github.com/simeononsecurity/Windows-Optimize-Debloat  
**Run:** `iwr -useb 'https://simeononsecurity.ch/scripts/windowsoptimizeanddebloat.ps1' | iex`

### Capabilities
- App removal + telemetry disable + privacy hardening
- Browser extension installation (uBlock Origin, etc.)
- Microsoft account sign-in blocking

### Service changes
| Service | Action |
|---|---|
| MessagingService | → Disabled |
| PimIndexMaintenanceSvc | → Disabled |
| RetailDemo | → Disabled |
| MapsBroker | → Disabled |
| DoSvc (Delivery Optimization) | → Disabled |
| OneSyncSvc | → Disabled |
| UnistoreSvc | → Disabled |
| dmwappushservice | → Set to Automatic (undoes aggressive tweak) |
| NvTelemetryContainer | → Disabled |

Also targets third-party services: Razer Game Scanner, Logitech Gaming, Adobe Update,
Visual Studio Collector.

### Verdict
**Best for:** Privacy-focused users who want harder lockdown.
**Risks:** Blocks Microsoft Account sign-in entirely — affects Store, OneDrive, some games.
**Doesn't cover:** ~70% of Tier-1 list.

---

## O&O ShutUp10++

**Website:** https://www.oo-software.com/en/shutup10  
**Type:** Portable GUI application (not a script)

### Capabilities
- 1000+ privacy settings toggles
- "Recommended settings" one-click apply
- Premium: monitors settings and auto-restores after Windows updates
- No installation required

### Service changes
None directly. All changes via registry keys.
Cannot be scripted or automated.

### Verdict
**Good for:** Privacy hardening in a GUI.
**Bad for:** Service-level debloating. Doesn't touch service startup types.

---

## Summary Matrix

| What you need | Win11Debloat | WinUtil | Simeon Debloat | Custom Script |
|---|---|---|---|---|
| Remove bloatware apps | ✅ Full | ✅ Partial | ✅ Full | ❌ |
| Disable telemetry | ✅ Registry | ✅ Registry | ✅ Registry | ❌ |
| UI tweaks (dark mode, taskbar) | ✅ | ✅ | ❌ | ❌ |
| Game Bar / Game DVR | ✅ | ❌ | ❌ | ✅ |
| Windows Search | ❌ | ❌ | ❌ | ✅ |
| SysMain (Superfetch) | ❌ | ❌ | ❌ | ✅ |
| Print Spooler | ❌ | ❌ | ❌ | ✅ |
| Bluetooth services | ❌ | ❌ | ❌ | ✅ |
| Xbox Live Auth | ❌ | ❌ | ❌ | ✅ |
| Push Notifications | ❌ | ❌ | ❌ | ✅ |
| AMD bloat services | ❌ | ❌ | ❌ | ✅ |
| Connected Devices | ❌ | ❌ | ❌ | ✅ |
| Phone Service | ❌ | ❌ | ❌ | ✅ |
| Web Account Manager | ❌ | ❌ | ❌ | ✅ |
| Delivery Optimization | ❌ | ❌ | ✅ | ✅ |
| Maps Broker | ❌ | ✅ | ✅ | ✅ |

**Bottom line:** No single existing script covers the 40+ non-essential services on a
developer/gamer machine. The recommended approach is Win11Debloat (for apps + telemetry)
followed by a custom Set-Service script for the service list.

---

## Custom Script Template

A production-ready template is at `references/disable-bloat-template.ps1` in this skill.
It has 3 modes powered by parameter sets:

| Mode | Switch | Safety |
|------|--------|--------|
| **Apply** | (default) | Backs up states to JSON first, prompts y/N |
| **Undo** | `-Undo` | Reads backup JSON, restores every service |
| **Preview** | `-Status` | Dry-run — shows current vs intended, no changes |
| **Dry-run** | `-WhatIf` | Same as preview but without writing backup |

**Key differences from a basic apply-only script:**
- `-Status` lets you validate the service list matches your system before committing
- `-Undo` restores original states from the auto-created backup JSON
- `-WhatIf` simulates the full run without touching anything
- Log file written for every change with timestamps
- Already-correct services skipped (no noise)

**IMPORTANT:** The script template uses ASCII-only characters (`->` not `→`) because
UTF-8 arrows get mangled when the script is piped through WSL's `powershell.exe -File`.

**Note:** The _XXXX suffix on user services varies per user SID. Run this on the target
machine to discover the actual suffix before editing the script:

```powershell
Get-Service | Where-Object { $_.Name -match '_.*\d{5,}$' } | Select-Object Name
```
