# Service Research Verdicts — Aldaviva Gist + Gaming Guides

Cross-reference source: `github.com/Aldaviva/0eb62993639da319dc456cc01efa3fe5` + SageTweaks, Kartones blog, Microsoft docs.

## Services NOT to disable (set to Manual or keep Auto)

| Service | Verdict | Source | Details |
|---------|---------|--------|---------|
| CDPSvc | **Manual, not Disabled** | Aldaviva gist | "Will break accounts and sync your settings." Also breaks device connectivity features. Night Light depends on this via NcbService. |
| gpsvc (Group Policy Client) | **Manual, not Disabled** | Multiple guides | Can cause boot hangs ("Please wait for GPSVC" on shutdown). Critical for policy. Do not disable on any edition. |
| WpnService / WpnUserService | **Manual, not Disabled** | Aldaviva gist | "Breaking push notifications also breaks Network & Internet Settings page." |
| TokenBroker (Web Account Manager) | **Manual, not Disabled** | Aldaviva gist | "Needed to load Settings > Accounts > Sign-In Options in Windows 11." |
| CDPUserSvc_* | **Automatic (keep)** | Aldaviva gist (inferred) | User counterpart of CDPSvc. Same reasoning — breaking Connected Devices Platform breaks device sync. |

## Services safe to set to Manual (starts on demand)

| Service | Verdict | Details |
|---------|---------|---------|
| BrokerInfrastructure | **Manual OK** | Critical for Start menu but starts on demand. Disabled breaks Start menu. |
| StateRepository | **Manual OK** | Supports core Windows app behavior. Starts on demand. |
| FontCache | **Manual OK** | Font rendering cache. Starts when apps need fonts. |
| cbdhsvc_* (Clipboard User) | **Manual OK** | Needed for Snip & Sketch screenshots (Win+Shift+S). Manual = works when needed. |
| DeviceAssociationService | **Manual OK** | Needed for device pairing (Bluetooth, Phone Link). Starts on demand. |
| NcbService (Network Connection Broker) | **Manual OK** | Dependency of CDPSvc. Night Light dependent. Manual = works when CDPSvc runs. |

## Services confirmed safe to DISABLE

| Service | Source | Notes |
|---------|--------|-------|
| WSearch (Windows Search) | SageTweaks, Kartones | Saves ~50MB RAM. Search still works, just slower. |
| SysMain (Superfetch) | SageTweaks, Aldaviva | Safe on SSD. Loses RAM compression. Saves ~200MB. |
| Spooler (Print Spooler) | SageTweaks | Safe with no printer. |
| AppIDSvc (Application Identity) | revert service | Default is Manual. Disabling only breaks AppLocker (enterprise). |
| WerSvc (Windows Error Reporting) | SageTweaks | Crash reporting only. |
| Xbox Live services | Gaming guides | Auth + networking for Xbox. Safe for non-Xbox gamers. |
| GameDVR / BcastDVRUserService | Gaming guides | Frees GPU resources. |
| DoSvc (Delivery Optimization) | Gaming guides | P2P Windows update sharing. Safe. |
| WSearch | SageTweaks | File indexing. Safe on SSD. |

## Services to ALWAYS keep (Tier 3)

| Category | Services |
|----------|----------|
| GPU/Display | AMD PMF Service, nvcontainer, NVDisplay.ContainerLocalSystem, RtkAudioUniversalService |
| Audio | AudioEndpointBuilder, Audiosrv |
| Network | Dhcp, Dnscache, iphlpsvc, WlanSvc, Wcmsvc, mpssvc (firewall) |
| Security | WinDefend, MDCoreSvc, WdNisSvc, CryptSvc, SamSs, KeyIso |
| Core OS | RpcSs, RpcEptMapper, DcomLaunch, EventLog, PlugPlay, Power, Schedule, Themes, ProfSvc |
| WSL | WSLService, LanmanServer (file sharing), vmcompute |
| VPN | CloudflareWARP |
| UI customization | Windhawk |
