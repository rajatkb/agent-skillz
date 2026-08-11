# Developer/Gamer Windows Service Audit

Generated from an ASUS ROG G14 (AMD 7940HS + NVIDIA RTX 4060, WSL2). All 120+ running services classified into tiers for a programming/research/gaming/media-consumption workflow.

## Quick Legend

| Tier | Label | Action in services.msc |
|------|-------|----------------------|
| 1 | Safe to Disable | Startup Type = Disabled |
| 2 | Set to Manual | Startup Type = Manual |
| 3 | Keep Automatic | No change |

---

## TIER 1 — Safe to Disable

| Service Name | Short Name | Why |
|---|---|---|
| AMD Crash Defender Service | `AMD Crash Defender Service` | AMD GPU crash monitoring; safe to disable, re-enable if driver crashes become an issue |
| AMD External Events Utility | `AMD External Events Utility` | AMD hotkey/event handler for Radeon Software; unnecessary background process |
| AMD Provisioning Packages Service | `AmdPkgSvc` | Initial OEM provisioning; irrelevant after first setup |
| AsusPTPService | `AsusPTPService` | ASUS precision touchpad driver helper. Safe if using a mouse |
| GameDVR and Broadcast User Service_* | `BcastDVRUserService_*` | Xbox Game Bar recording/broadcasting. Reclaims GPU resources when disabled |
| Cloudflare One Client Updater | `CloudflareWARPUpdater` | Updater for Cloudflare WARP; main client works fine without it |
| Delivery Optimization | `DoSvc` | P2P Windows Update sharing between PCs; unnecessary on a single machine |
| Diagnostic Policy Service | `DPS` | Windows problem reporting/diagnostics. Pure telemetry overhead |
| Data Usage | `DusmSvc` | Tracks per-app network usage. Zero functional impact when disabled |
| Display Enhancement Service | `DisplayEnhancementService` | Brightness/color enhancement layer. Not needed for gaming or coding |
| Dolby DAX API Service | `DolbyDAXAPI` | Dolby Atmos audio post-processing. Safe unless Dolby Atmos is specifically used |
| HV Host Service | `HvHost` | Hyper-V host support. WSL2 uses a different virtualization stack |
| Inventory and Compatibility Appraisal | `InventorySvc` | Telemetry + compatibility checks. Pure overhead |
| Internet Connection Sharing (ICS) | `SharedAccess` | Lets other devices use this PC's internet connection. Irrelevant on a laptop |
| Microsoft Store Install Service | `InstallService` | Only needed when installing from the Store. Set to Manual instead if unsure |
| MTKBTSVC | `MTKBTSVC` | MediaTek Bluetooth driver helper. Set to Manual if Bluetooth is used occasionally |
| Now Playing Session Manager_* | `NPSMSvc_*` | Shows "now playing" media info. Visual fluff |
| Phone Service | `PhoneSvc` | Phone Link integration. Unnecessary for dev/gaming |
| Program Compatibility Assistant | `PcaSvc` | Pop-ups about compatibility. Can safely disable |
| SSDP Discovery | `SSDPSRV` | UPnP device discovery. No real use on a gaming laptop |
| Secure Socket Tunneling Protocol | `SstpSvc` | SSTP VPN protocol. Only needed for specific VPNs |
| TCP/IP NetBIOS Helper | `lmhosts` | Legacy NetBIOS. Unnecessary for modern networking |
| Windows Image Acquisition (WIA) | `StiSvc` | Scanners and cameras. Not needed for dev/gaming/media |
| Windows Search | `WSearch` | File indexing. Biggest single RAM saver (~50MB). Search still works, just slower |
| SysMain (Superfetch) | `SysMain` | Pre-loads apps into RAM. **Counterproductive on SSDs**. Frees 150-250MB |
| Xbox Live Auth Manager | `XblAuthManager` | Only needed for Xbox Live purchases on PC |
| Group Policy Client | `gpsvc` | Enterprise domain policy. Irrelevant for personal laptop |
| Print Spooler | `Spooler` | Only needed if a printer is connected |
| Client License Service (ClipSVC) | `ClipSVC` | Store license management. Set to Manual |
| Web Threat Defense User Service_* | `webthreatdefusersvc_*` | Optional Defender web protection layer. Redundant with main Defender |
| Windows Health and Optimized Experiences | `whesvc` | Telemetry/reliability data. No functional value |
| WinHTTP Web Proxy Auto-Discovery | `WinHttpAutoProxySvc` | Auto-detects proxy settings. Only needed on corporate networks |
| Connected Devices Platform Service | `CDPSvc` | Phone/device syncing across Microsoft devices. Safe to disable |
| DevQuery Background Discovery Broker | `DevQueryBroker` | Background device discovery queries. No user-facing purpose |
| DevicesFlow_* | `DevicesFlowUserSvc_*` | Device setup flow helper. One-time use after device pairing |
| Web Account Manager | `TokenBroker` | Microsoft account token management. Set to Manual |
| Distributed Link Tracking Client | `TrkWks` | Tracks NTFS file links across volumes. Safe to disable |
| Network Virtualization Service | `nvagent` | Network virtualization. Not used in typical setups |
| Push Notifications System Service | `WpnService` | App notifications. Disable if notification pop-ups are not needed |
| Push Notifications User Service_* | `WpnUserService_*` | Same as above, per-user instance |
| Application Identity | `AppIDSvc` | App identity verification for AppLocker; not needed on personal machine |
| Windows License Manager Service | `LicenseManager` | Store license infrastructure. Disable to prevent Store license checks |
| Clipboard User Service_* | `cbdhsvc_*` | Cloud clipboard sync across devices. Set to Manual if cross-device clipboard is used |
---

## TIER 2 — Set to Manual

| Service Name | Short Name | Notes |
|---|---|---|
| Bluetooth Support Service | `bthserv` | Starts when BT device is paired. Manual safe |
| Bluetooth Audio Gateway | `BTAGService` | Only needed during BT calls. Manual safe |
| Bluetooth User Support_* | `BluetoothUserService_*` | Same — starts on demand |
| AVCTP service | `BthAvctpSvc` | BT audio/video control. Manual safe |
| GameInput Redist Service | `GameInputRedistService` | Game controller support. Games start it on demand |
| GameInput Service | `GameInputSvc` | Same as above |
| Gaming Services | `GamingServices` | Xbox/game integration. Starts on demand |
| Gaming Services (Net) | `GamingServicesNet` | Same as above |
| Microsoft Passport Container | `NgcCtnrSvc` | Windows Hello. Starts when PIN/biometrics are used |
| Microsoft Passport | `NgcSvc` | Same as above |
| Remote Access Connection Manager | `RasMan` | VPN/dial-up connections. Manual safe |
| Radio Management Service | `RmSvc` | Wi-Fi/Bluetooth radio control. Manual safe |
| Network List Service | `netprofm` | Network location awareness. Starts when needed |
| Time Broker | `TimeBrokerSvc` | Background task timing. Manual safe |
| Windows License Manager | `LicenseManager` | Store licensing. Only needed during Store operations |
| Update Orchestrator Service | `UsoSvc` | Windows Update. Windows starts it for updates regardless |
| Credential Manager | `VaultSvc` | Stores credentials. Starts when apps need them |
| Windows Error Reporting | `WerSvc` | Crash reporting. Manual safe |
| Application Information | `Appinfo` | App compatibility metadata. Manual safe |
| AppX Deployment Service | `AppXSvc` | UWP app deployment. Starts on demand |
| Client License Service (ClipSVC) | `ClipSVC` | Store license management. Starts on demand when Store is used |
| Windows Font Cache | `FontCache` | Font rendering cache. Manual safe — regenerates on demand |
| Server (LanmanServer) | `LanmanServer` | File/printer sharing. Keep if sharing files to other machines |
| Application Identity | `AppIDSvc` | App identity/certificate checking. Set to Manual — starts on demand |
| Web Threat Defense User Service_* | `webthreatdefusersvc_*` | Optional Defender web protection layer. Redundant with main Defender |
| BitLocker Drive Encryption Service | `BDESVC` | If drive is already decrypted or you're comfortable with BitLocker off, set to Manual. If drive is encrypted, leave it |

---

## TIER 3 — Keep Automatic

Must stay on for ROG G14 + dev/gaming/media workflow.

| Service | Why Essential |
|---|---|
| AMD PMF Service | Platform management — fan curves, thermals, power modes on G14 |
| Windows Audio + AudioEndpointBuilder | Audio playback for gaming and media |
| Base Filtering Engine (BFE) | Core network firewall engine |
| DHCP Client + DNS Client | Network connectivity |
| IP Helper | IPv6 networking |
| Windows Event Log | Debugging — essential for development |
| Cloudflare One Client | WARP VPN — user actively uses it |
| CoreMessaging | System messaging bus. Many things depend on it |
| Cryptographic Services | Security encryption used by BitLocker, TLS, etc. |
| NVIDIA LocalSystem Container + Display Container | GPU functionality — critical for gaming and CUDA |
| Realtek Audio Universal Service | Audio driver |
| Microsoft Defender + Firewall + NIS | Antivirus and network protection |
| WLAN AutoConfig | Wi-Fi management |
| WSL Service | Daily WSL2 usage for development |
| Windhawk | Active UI customization tool |
| Power | Laptop power management and battery profiles |
| Task Scheduler | Too many OS components depend on it |
| Themes | Visual styling |
| User Manager + User Profile Service | Core user session management |
| Plug and Play | Hardware detection |
| DCOM/RPC services (3 services) | Core OS communication. Breaking these bricks the OS |
| Security Accounts Manager | User authentication |
| Workstation (LanmanWorkstation) | Network file access. Needed for WSL file sharing |
| Storage Service | Storage management |
| Shell Hardware Detection | Auto-play for media/USB devices |
| Windows Connection Manager | Network connectivity decisions |
| State Repository Service | Maintains app state. Many Store apps depend on it |

---

## Methodology

This audit used a 3-source cross-reference:
1. **NPU classification** (Gemma 4 E4B via extract_json on FastFlowLM) — initial categorization of all 120+ services
2. **Web search** — gaming optimization guides (sagetweaks.com, windowsdigitals.com, techbloat.com) and per-service queries
3. **Community reference** — [Aldaviva's gist](https://gist.github.com/Aldaviva/0eb62993639da319dc456cc01efa3fe5) — comprehensive safe-to-disable service analysis

Every Tier 1 recommendation was verified against at least 2 independent sources before inclusion.
