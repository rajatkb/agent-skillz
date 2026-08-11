---
name: windows-debloating
description: Identify and disable unnecessary Windows services, processes, startup items, and features on a developer/gamer/media-consumer machine. PowerShell enumeration from WSL + NPU-aided classification + web research workflow.
---

# Windows Debloating (from WSL)

Audit and trim Windows services and processes for a developer/gamer machine. Everything runs from WSL — no need to install tools on Windows side.

## Workflow

### Phase 1 — Enumerate (from WSL)

**Critical: write .ps1 to /tmp, don't inline PowerShell.**

WSL's bash mangles `$_` and other PowerShell variable syntax. Always write the script to a temp file first, then execute it:

```bash
cat > /tmp/get_services.ps1 << 'PSEOF'
Get-Service | Where-Object { $_.Status -eq 'Running' } | Select-Object DisplayName, Name, Status, StartType | Format-Table -AutoSize -Wrap
Write-Output "===END OF SERVICES==="
Get-Process | Select-Object ProcessName, Company, @{n='MemMB';e={[math]::Round($_.WorkingSet/1MB,1)}} | Sort-Object ProcessName -Unique | Format-Table -AutoSize -Wrap
Write-Output "===END OF PROCESSES==="
PSEOF

/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -ExecutionPolicy Bypass -File /tmp/get_services.ps1 2>&1
```

**Useful queries to run** (each as their own .ps1 file):
- All services + start type: `Get-Service | Select-Object Name, DisplayName, Status, StartType`
- All processes with memory: `Get-Process | Sort-Object WorkingSet -Descending | Select-Object ProcessName, @{n='MB';e={[math]::Round($_.PM/1MB,1)}}`
- Startup programs: `Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location`
- Scheduled tasks (browse): `Get-ScheduledTask | Where-Object State -ne Disabled | Select-Object TaskName, State`
- Optional features: `Get-WindowsOptionalFeature -Online | Where-Object State -eq 'Enabled' | Select-Object FeatureName, State`

### Phase 2 — Classify (NPU + Web)

Use extract_json on the NPU to classify services into tiers:

```python
# In execute_code or via extract_json tool
# Schema: [{service_name, category: "essential|useful|safe_to_disable", reason}]
```

Cross-reference NPU classifications with:
1. **Web search** — search for "[ServiceName] safe disable Windows 11" and gaming optimization guides
2. **Authoritative gists** — the GitHub gist at `github.com/Aldaviva/0eb62993639da319dc456cc01efa3fe5` is the most comprehensive community reference
3. **batcmd.com** — per-service documentation with dependency info

### Phase 3 — Tiered recommendations

Present findings in 3 clear tiers:

| Tier | Label | Action |
|------|-------|--------|
| 1 | **Safe to Disable** | No real impact. Set Startup Type = Disabled |
| 2 | **Set to Manual** | Starts on demand when needed. Set Startup Type = Manual |
| 3 | **Keep Automatic** | Essential for the user's specific workflow (GPU, audio, network, WSL, security) |

### Phase 4 — Apply changes

User can apply via `services.msc` (Win+R → services.msc) or a PowerShell script:

```powershell
# Example: stop and disable a service
Stop-Service "ServiceName" -Force
Set-Service "ServiceName" -StartupType Disabled
```

For performance tip: recommend applying 5-10 changes at a time, then reboot to verify nothing breaks.

## NPU Utilization

This workflow is an ideal NPU use case:
- **extract_json** — classify large lists of services into categories (120+ items)
- **extract_from_webpage** — read optimization guides and gists, extract relevant recommendations
- **classify_text** — batch classification of remaining uncategorized services

Always cross-reference NPU results with at least 2 web sources before finalizing recommendations. NPU models can make plausible-sounding but wrong claims about specific service functions.

## Pitfalls

- **WSL mangles PowerShell `$_`** — ALWAYS write .ps1 files to /tmp and use `-File` flag. Never inline PowerShell via WSL's bash.
- **Don't disable GPU vendor services.** AMD PMF Service, NVIDIA LocalSystem/Display Containers must stay. User will lose GPU acceleration, fan control, thermals.
- **Avoid disabling core RPC/DCOM services.** RpcSs, RpcEptMapper, DcomLaunch break the entire OS.
- **SysMain on SSD**: disabling is fine and frees RAM on modern SSDs (NVMe/SATA). Only benefits HDD systems.
- **Windows Search**: disabling saves ~50MB RAM and eliminates indexing CPU spikes. Search still finds files, just slower.
- **GameDVR/Broadcast**: disabling reclaims GPU resources that the Game Bar hooks into. Improves gaming FPS by 1-5% in some titles.
- **Don't disable WSL Service** — user explicitly relies on WSL2 for daily development.
- **Windhawk** — user actively uses this for UI customization. Keep it.
- **Bluetooth services**: set to Manual (not Disabled) so they auto-start when a BT device is paired.
- **BitLocker**: leave it if drive is encrypted. Disabling the service mid-session won't unlock the drive.
- **Print Spooler**: 100% safe to disable if the user has no printer.
- **Unicode arrows (`→`) break via WSL→PowerShell pipe**: When writing a .ps1 that will be executed via `powershell.exe -File` from WSL, use ONLY ASCII characters (e.g. `->` not `→`). UTF-8 multi-byte chars get mangled through the cross-platform pipe and cause PowerShell parse errors. Write the script with ASCII output strings only.
- **Diagnostic Policy / Telemetry services**: safe to disable but some may re-enable after Windows updates. Check periodically.
- **`CDPSvc` (Connected Devices Platform Service) — DO NOT disable** despite being tempting. Aldaviva gist confirms it will **break accounts, device sync, and Settings pages**. CVE articles about CDPSvc also warn: "disabling breaks device connectivity features." Set to **Manual**, NOT Disabled. Its user-mode counterpart `CDPUserSvc_*` should also stay **Automatic** for the same reason.
- **`gpsvc` (Group Policy Client) — DO NOT disable on any Windows edition.** Multiple guides confirm disabling causes boot hangs ("Please wait for GPSVC" shutdown errors) and system instability. Even Windows Home edition applies some policies via this service. Set to **Manual**, NOT Disabled.
- **`WpnService` / `WpnUserService` (Windows Push Notifications) — DO NOT disable.** Aldaviva gist: "Breaking push notifications also breaks Network & Internet Settings page." Set to **Manual**, NOT Disabled.
- **`TokenBroker` (Web Account Manager) — DO NOT disable.** Aldaviva gist: "Needed to load Settings > Accounts > Sign-In Options in Windows 11." Set to **Manual**, NOT Disabled.
- **`cbdhsvc_*` (Clipboard User Service)** — needed for Snip & Sketch screenshots (Win+Shift+S). Setting to **Manual** is fine (starts on demand); Disabled will break screenshot workflow.
- **`BrokerInfrastructure` (Background Tasks Infrastructure)** — critical for Start menu and background app tasks. Setting to **Manual** is safe (starts on demand); Disabled can prevent Start menu from opening. Per Microsoft Answers: "Ensure BrokerInfrastructure is started" is a common fix for Start menu issues.
- **`StateRepository`** — supports core Windows app behavior (app state, browsing sessions). **Manual** is safe; it starts on demand when needed.
- **`DeviceAssociationService`** — needed for device pairing (Bluetooth, Phone Link). **Manual** is correct (starts on demand).
- **The `_XXXX` suffix is machine-specific** — services like `BcastDVRUserService_94390`, `WpnUserService_94390`, `BluetoothUserService_94390` use a suffix derived from the user SID. Always discover the actual suffix on the target machine with `Get-Service | Where-Object { $_.Name -match '_' }` before deploying any script with hardcoded service names.

## Tips for Researching Individual Services

When an NPU or internal knowledge gives a borderline classification, verify with:

1. `batcmd.com/windows/11/services/<servicename>/` — per-service docs with dependency info
2. `github.com/Aldaviva/0eb62993639da319dc456cc01efa3fe5` — community-maintained safe-to-disable gist
3. Gaming optimization guides (sagetweaks.com, techbloat.com, windowsdigitals.com)
4. **This skill's own** `references/service-research-verdicts.md` — pre-compiled verdicts from all three sources, updated per session

**NPU is good for initial pass but not authoritative.** Always cross-reference at least 2 web sources for any service that isn't obviously junk (e.g. "Print Spooler" when there's no printer is safe, but "Application Identity" needs research).

**Key services that NPU/systematic reasoning gets wrong** (per Aldaviva gist, verified in practice):
- `CDPSvc` — seems like device sync bloat (safe to disable) but actually breaks accounts + Settings pages
- `gpsvc` — seems like enterprise-only policy service but actually causes boot hangs if disabled
- `WpnService` — seems like notification junk but disabling breaks Network & Internet Settings
- `TokenBroker` — seems like account token bloat but disabling breaks Settings > Accounts
- These are the top 4 false positives in automated classification — always flag them for manual review

## Phase 5 — Apply via Existing Tools vs Custom Script

### Existing debloater tools — what they cover

| Tool | Focus | Services touched | Verdict |
|---|---|---|---|
| **Win11Debloat** (Raphire, 50k stars) | App removal, telemetry, UI tweaks | ~5 (registry-only, no Set-Service) | Good for app + UI cleanup, misses most services |
| **Chris Titus WinUtil** | App removal, tweaks, presets | ~6 (CscService, DiagTrack, MapsBroker, StorSvc, SharedAccess, lfsvc) | Conservative, misses 35+ Tier-1 services. ⚠️ Advanced tweaks can break fullscreen gaming — see `windows-gaming/windows-gaming-fullscreen-corruption` skill. **Also misses AMD/ASUS task scheduler bloat** (AMDScoSupportTypeUpdate, StartCN, StartDVR, ModifyLinkUpdate) that can add 3-5W idle drain on Zephyrus G14.
| **Simeon Windows-Optimize-Debloat** | Privacy + debloat | ~10 (Maps, DoSvc, OneSync, Messaging, etc.) | More aggressive but still partial |
| **O&O ShutUp10++** | Privacy registry toggles | 0 service changes | GUI privacy tool only |

**None of these cover the full Tier-1 list (35-42 services).** The recommended strategy:

```
Win11Debloat first  →  app removal, telemetry, UI cleanup
   then
Custom service script →  all 42 Tier-1 + 24 Tier-2 services in one pass
```

### Discover the user SID suffix

Services with `_XXXX` suffixes (e.g. `_94390`, `_12345`) vary per Windows user SID. Before writing the script, discover the actual suffix on the target machine:

```powershell
# Find all services with user-SID suffixes
Get-Service | Where-Object { $_.Name -match '_.*\\d{5,}$' } | Select-Object Name, DisplayName
```

Common suffix-bearing services: `BcastDVRUserService_*`, `WpnUserService_*`, `NPSMSvc_*`, `BluetoothUserService_*`, `cbdhsvc_*`, `DevicesFlowUserSvc_*`, `webthreatdefusersvc_*`. Update the script's array with the actual suffix.

### Building the custom service script

Structure as a single PowerShell `.ps1` with 3 modes using a parameter set:

| Mode | Switch | What it does |
|------|--------|-------------|
| **Apply** | no switch (default) | Tier 1 → Disabled, Tier 2 → Manual. Backs up original states to JSON. |
| **Undo** | `-Undo` | Reads backup JSON, restores every service to original startup type. Deletes backup when done. |
| **Preview** | `-Status` | Shows current vs intended state. No changes. |
| **Dry-run** | `-WhatIf` | Shows what would change, logs nothing, writes no backup. |

See the reference template at `references/disable-bloat-template.ps1` for a production-ready example.

**Key design decisions:**
- **No System Restore point** — user explicitly opts out. The JSON backup + `-Undo` switch is the safety mechanism.
- **JSON backup** saves original `StartMode` for each service. `-Undo` reads it back and restores.
- **Log file** records every change with timestamp. Path: `debloat-log-<yyyyMMdd-HHmmss>.txt`.
- **Confirmation prompt** on Apply mode (skipped with `-WhatIf`).
- **Yes/No skip** for already-correct services, not-found services reported in yellow.

### Azure VMs / corporate machines

Skip the debloat entirely — Group Policy, enterprise AV, and security compliance tools will revert changes and may flag the script as malicious.

## Verification

After disabling services:
1. Reboot
2. Run `Get-Service | Where-Object { $_.Status -eq 'Running' } | Measure-Object` to count remaining running services
3. Run GPU benchmark / game session to verify no performance regression
4. Verify WSL starts and works
5. Open the browser and verify networking
6. Play audio/video to verify media playback

## Related Files

- `references/developer-gamer-service-audit.md` — full classified service list from a ROG G14 audit, with per-service reasoning
- `references/debloater-tools-comparison.md` — comparison of Win11Debloat, Chris Titus WinUtil, Simeon Debloat, O&O ShutUp10++ against the Tier-1 list
- `references/service-research-verdicts.md` — Aldaviva gist + gaming guide cross-reference for every service in the audit, with per-service verdicts on safety of disabling
- `references/copilot-plus-features-debloat-impact.md` — which Windows 11 25H2 Copilot+ AI features are stripped by debloating, hardware requirements, and whether better alternatives exist
- `templates/disable-bloat.ps1` — production-ready PowerShell script with Apply/Undo/Status/WhatIf modes, JSON backup, and change logging
