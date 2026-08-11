<#
.SYNOPSIS
    Disable or restore non-essential Windows services on a dev/gaming machine.
.DESCRIPTION
    Default mode: Sets Tier 1 services -> Disabled, Tier 2 services -> Manual.
    -Undo: Restores every service to its original startup type from a backup JSON.
    -Status: Shows current vs intended state without making changes.
    -WhatIf: Preview changes without applying them.
.PARAMETER Undo
    Restore services to original startup types from the backup file.
.PARAMETER Status
    Show current vs intended state for all targeted services. No changes made.
.PARAMETER WhatIf
    Show what would change without actually applying anything.
.PARAMETER LogPath
    Path to the change log. Default: script-dir/debloat-log-<date>.txt
.PARAMETER BackupPath
    Path to the backup JSON. Default: script-dir/service-backup.json
.EXAMPLE
    .\disable-bloat.ps1
    Apply all service changes.
.EXAMPLE
    .\disable-bloat.ps1 -Undo
    Restore all services to original states.
.EXAMPLE
    .\disable-bloat.ps1 -Status
    Preview what would change.
.NOTES
    Run as Administrator.
    The _XXXX suffix on user services is machine-specific --
    run 'Get-Service | ? Name -match '_\\\\d{5,}$'' to find your suffix.
#>

[CmdletBinding(DefaultParameterSetName = 'Apply')]
param(
    [Parameter(ParameterSetName = 'Undo')]
    [switch]$Undo,

    [Parameter(ParameterSetName = 'Status')]
    [switch]$Status,

    [switch]$WhatIf,

    [string]$LogPath,
    [string]$BackupPath
)

# --- Resolve paths ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $LogPath)  { $LogPath  = Join-Path $ScriptDir "debloat-log-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt" }
if (-not $BackupPath) { $BackupPath = Join-Path $ScriptDir "service-backup.json" }

# --- Service definitions ---
# Edit these arrays to match YOUR machine's service names.
# Use ASCII only (no Unicode arrows etc.) -- WSL pipe mangles non-ASCII.

$Tier1 = @(
    # AMD/ASUS bloat
    'AMD Crash Defender Service'
    'AMD External Events Utility'
    'AmdPpkgSvc'           # AMD Provisioning Packages
    'AsusPTPService'       # ASUS touchpad helper
    # Telemetry / data collection
    'DPS'                  # Diagnostic Policy Service
    'InventorySvc'         # Inventory & Compatibility Appraisal
    'whesvc'               # Windows Health & Optimized Experiences
    'DusmSvc'              # Data Usage
    'webthreatdefusersvc_XXXX'  # Web Threat Defense (update suffix)
    # Push notifications
    'WpnService'
    'WpnUserService_XXXX'  # update suffix
    # Xbox / Store licensing
    'XblAuthManager'
    'ClipSVC'
    'LicenseManager'
    'InstallService'
    # Search / indexing
    'WSearch'
    'SysMain'              # Superfetch
    # Background junk
    'DoSvc'                # Delivery Optimization
    'Spooler'              # Print Spooler (no printer)
    'PhoneSvc'             # Phone Link
    'SSDPSRV'              # SSDP Discovery
    'SstpSvc'              # SSTP VPN
    'lmhosts'              # NetBIOS Helper
    'StiSvc'               # Windows Image Acquisition (scanner)
    'gpsvc'                # Group Policy Client
    'WinHttpAutoProxySvc'  # WinHTTP Proxy Auto-Detect
    'CDPSvc'               # Connected Devices Platform
    'DevQueryBroker'       # DevQuery Background Discovery
    'DevicesFlowUserSvc_XXXX'  # update suffix
    'TokenBroker'          # Web Account Manager
    'TrkWks'               # Distributed Link Tracking
    'nvagent'              # Network Virtualization
    'AppIDSvc'             # Application Identity
    'SharedAccess'         # Internet Connection Sharing
    # Other
    'BcastDVRUserService_XXXX'  # GameDVR (update suffix)
    'CloudflareWARPUpdater'
    'DisplayEnhancementService'
    'DolbyDAXAPI'
    'HvHost'               # Hyper-V Host
    'MTKBTSVC'             # MediaTek BT helper
    'NPSMSvc_XXXX'         # Now Playing Session Manager (update suffix)
)

$Tier2 = @(
    # Bluetooth stack (on-demand)
    'bthserv'              # Bluetooth Support Service
    'BTAGService'          # Bluetooth Audio Gateway
    'BluetoothUserService_XXXX'  # update suffix
    'BthAvctpSvc'          # AVCTP service
    # Gaming input (on-demand)
    'GameInputRedistService'
    'GameInputSvc'
    'GamingServices'
    'GamingServicesNet'
    # Windows Hello
    'NgcCtnrSvc'           # Microsoft Passport Container
    'NgcSvc'               # Microsoft Passport
    # Networking / system (on-demand)
    'RasMan'               # Remote Access Connection Manager (VPN)
    'RmSvc'                # Radio Management
    'netprofm'             # Network List Service
    'TimeBrokerSvc'        # Time Broker
    'UsoSvc'               # Update Orchestrator
    'VaultSvc'             # Credential Manager
    'WerSvc'               # Windows Error Reporting
    'Appinfo'              # Application Information
    'BrokerInfrastructure' # Background Tasks Infrastructure
    'FontCache'            # Windows Font Cache
    'DeviceAssociationService'
    'BDESVC'               # BitLocker Drive Encryption
    'cbdhsvc_XXXX'         # Clipboard User (update suffix)
    'hns'                  # Host Network Service
    'NcbService'           # Network Connection Broker
    'StateRepository'      # State Repository Service
)

$AllServices = $Tier1 + $Tier2

# --- Helpers ---
function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    Add-Content -Path $LogPath -Value $line
    Write-Host $line
}

function Get-OriginalStartType {
    param([string]$ServiceName)
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $svc) { return $null }
    try {
        $startType = (Get-CimInstance -ClassName Win32_Service -Filter "Name='$ServiceName'").StartMode
        return $startType
    } catch {
        return $null
    }
}

function Get-IntendedStartType {
    param([string]$ServiceName)
    if ($Tier1 -contains $ServiceName) { return 'Disabled' }
    if ($Tier2 -contains $ServiceName) { return 'Manual' }
    return $null
}

function Set-ServiceStartType {
    param([string]$Name, [string]$StartType)
    try {
        Set-Service -Name $Name -StartupType $StartType -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# --- Status mode ---
if ($Status) {
    Write-Host "`n=== Service Debloat Status ===`n" -ForegroundColor Cyan
    $anyMissing = $false
    foreach ($name in $AllServices) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Host "  [?] $name -- NOT FOUND on this system" -ForegroundColor DarkYellow
            $anyMissing = $true
            continue
        }
        $current = Get-OriginalStartType $name
        $intended = Get-IntendedStartType $name
        $icon = if ($current -eq $intended) { '[OK]' } else { '[CH]' }
        $color = if ($current -eq $intended) { 'Green' } else { 'Red' }
        Write-Host "  $icon [$current -> $intended] $name" -ForegroundColor $color
    }
    if ($anyMissing) {
        Write-Host "`nSome services weren't found -- they may have a different _XXXX suffix." -ForegroundColor Yellow
        Write-Host "Update the script with `$Tier1 / `$Tier2 entries if needed.`n" -ForegroundColor Yellow
    }
    exit 0
}

# --- Undo mode ---
if ($Undo) {
    if (-not (Test-Path $BackupPath)) {
        Write-Host "ERROR: Backup file not found at $BackupPath" -ForegroundColor Red
        Write-Host "Nothing to undo." -ForegroundColor Red
        exit 1
    }
    Write-Host "`n=== Undo Mode -- Restoring Original Service States ===`n" -ForegroundColor Cyan
    $backup = Get-Content $BackupPath | ConvertFrom-Json
    $restored = 0
    $failed = 0
    foreach ($entry in $backup) {
        $name = $entry.Name
        $original = $entry.OriginalStartType
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Host "  [?] $name -- not found, skipping" -ForegroundColor DarkYellow
            continue
        }
        if ($WhatIf) {
            Write-Host "  [?] Would restore $name -> $original" -ForegroundColor Yellow
            continue
        }
        if (Set-ServiceStartType $name $original) {
            Write-Log "UNDO: $name -> $original (restored)"
            $restored++
        } else {
            Write-Host "  [FAIL] $name -> $original" -ForegroundColor Red
            $failed++
        }
    }
    Write-Host "`nDone. Restored: $restored, Failed: $failed" -ForegroundColor Cyan
    if ($restored -gt 0 -and -not $WhatIf) {
        Remove-Item $BackupPath -Force
        Write-Host "Backup file removed: $BackupPath" -ForegroundColor Gray
    }
    exit 0
}

# --- Apply mode (default) ---
Write-Host "`n=== Windows Service Debloat -- Apply ===`n" -ForegroundColor Cyan
Write-Host "This will change startup types for $($AllServices.Count) services:"
Write-Host "  Tier 1 (-> Disabled): $($Tier1.Count)"
Write-Host "  Tier 2 (-> Manual):   $($Tier2.Count)"
Write-Host ""

if (-not $WhatIf) {
    $confirm = Read-Host "Continue? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "Aborted." -ForegroundColor Yellow
        exit 0
    }
}

# --- Backup current states ---
Write-Host "`nBacking up current service states..." -ForegroundColor Gray
$backupData = @()
foreach ($name in $AllServices) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) { continue }
    $original = Get-OriginalStartType $name
    if ($original) {
        $backupData += [PSCustomObject]@{ Name = $name; OriginalStartType = $original }
    }
}
if (-not $WhatIf) {
    $backupData | ConvertTo-Json | Set-Content $BackupPath -Force
    Write-Host "  Saved $($backupData.Count) entries -> $BackupPath" -ForegroundColor Gray
}

# --- Apply changes ---
$changed = 0
$skipped = 0
$errors = 0

# Tier 1 -> Disabled
Write-Host "`nTier 1 -- Setting to Disabled..." -ForegroundColor Yellow
foreach ($name in $Tier1) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host "  [?] $name -- not found, skipped" -ForegroundColor DarkYellow
        $skipped++
        continue
    }
    $current = Get-OriginalStartType $name
    if ($current -eq 'Disabled') {
        Write-Host "  [=] $name -- already Disabled" -ForegroundColor DarkGray
        $skipped++
        continue
    }
    if ($WhatIf) {
        Write-Host "  [->] $name  ($current -> Disabled)" -ForegroundColor Yellow
        $changed++
        continue
    }
    if (Set-ServiceStartType $name 'Disabled') {
        Write-Log "CHANGE: $name -> Disabled (was $current)"
        Write-Host "  [OK] $name  ($current -> Disabled)" -ForegroundColor Green
        $changed++
    } else {
        Write-Host "  [FAIL] $name  ($current -> Disabled)" -ForegroundColor Red
        $errors++
    }
}

# Tier 2 -> Manual
Write-Host "`nTier 2 -- Setting to Manual..." -ForegroundColor Yellow
foreach ($name in $Tier2) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host "  [?] $name -- not found, skipped" -ForegroundColor DarkYellow
        $skipped++
        continue
    }
    $current = Get-OriginalStartType $name
    if ($current -eq 'Manual') {
        Write-Host "  [=] $name -- already Manual" -ForegroundColor DarkGray
        $skipped++
        continue
    }
    if ($WhatIf) {
        Write-Host "  [->] $name  ($current -> Manual)" -ForegroundColor Yellow
        $changed++
        continue
    }
    if (Set-ServiceStartType $name 'Manual') {
        Write-Log "CHANGE: $name -> Manual (was $current)"
        Write-Host "  [OK] $name  ($current -> Manual)" -ForegroundColor Green
        $changed++
    } else {
        Write-Host "  [FAIL] $name  ($current -> Manual)" -ForegroundColor Red
        $errors++
    }
}

# --- Summary ---
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Applied: $changed  Skipped: $skipped  Errors: $errors" -ForegroundColor Cyan
Write-Host "  Log: $LogPath" -ForegroundColor Cyan
Write-Host "  Backup: $BackupPath" -ForegroundColor Cyan
Write-Host "  To undo later: .\disable-bloat.ps1 -Undo" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
